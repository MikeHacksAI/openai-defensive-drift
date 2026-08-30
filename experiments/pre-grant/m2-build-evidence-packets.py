#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

REQUIRED_QUEUE_COLUMNS = {
    "review_rank",
    "review_tier",
    "combined_candidate_id",
    "source_repository",
    "source_relative_path",
    "exact_content_group_id",
    "exact_content_group_size",
}
REQUIRED_INVENTORY_COLUMNS = {
    "combined_candidate_id",
    "source_state",
    "coverage_origin",
    "source_repository",
    "source_relative_path",
    "source_commit",
    "source_git_blob_sha",
    "source_sha256",
    "source_bytes",
    "source_model",
    "template_family",
    "discovery_score",
    "severity_raw",
    "recurrence_raw",
    "drift_id_raw",
    "title",
}
CORE_TIER = "CORE_100"


def clean(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def run_git(repo: Path, args: list[str], *, text: bool = False) -> bytes | str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {stderr}")
    if text:
        return proc.stdout.decode("utf-8", errors="strict")
    return proc.stdout


def status_bytes(repo: Path) -> bytes:
    return run_git(
        repo,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )  # type: ignore[return-value]


def load_csv(path: Path) -> tuple[list[dict[str, str]], set[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = set(reader.fieldnames or [])
        return list(reader), cols


def load_duplicate_groups(path: Path) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    if not path.is_file():
        return groups
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gid = clean(row.get("content_identity"))
            members = [x for x in clean(row.get("candidate_ids")).split(";") if x]
            if gid and members:
                groups[gid] = members
    return groups


def resolve_repo(row: dict[str, str], git_root: Path, cache_root: Path) -> Path:
    repo_name = clean(row.get("source_repository"))
    origin = clean(row.get("coverage_origin"))
    repo = (cache_root if origin == "GITHUB_REMOTE" else git_root) / repo_name
    if not (repo / ".git").exists():
        raise RuntimeError(
            f"Source repository clone/cache not found for {repo_name}: {repo} "
            f"(coverage_origin={origin})"
        )
    return repo


def md_escape(value: str) -> str:
    return value.replace("|", r"\|")


def discovery_hash_semantics(row: dict[str, str]) -> str:
    source_state = clean(row.get("source_state"))
    if source_state in {
        "TRACKED_LOCAL_CHECKPOINT",
        "TRACKED_LOCAL_DELTA",
        "UNTRACKED",
        "IGNORED_UNTRACKED",
    }:
        return "WORKTREE_BYTES_AT_DISCOVERY"
    if clean(row.get("source_sha256")):
        return "DISCOVERY_SOURCE_BYTES"
    return "NOT_RECORDED"


def git_object_sha(repo: Path, source_bytes: bytes) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "--stdin"],
        input=source_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git hash-object failed in {repo}: {stderr}")
    return proc.stdout.decode("ascii", errors="strict").strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize private M2 evidence packets transactionally for core human review "
            "without assigning ground truth."
        )
    )
    parser.add_argument("--private-repo", required=True)
    parser.add_argument("--git-root", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--expected-queue", type=int, default=150)
    parser.add_argument("--core", type=int, default=100)
    args = parser.parse_args()

    private_repo = Path(args.private_repo)
    git_root = Path(args.git_root)
    cache_root = Path(args.cache_root)

    queue_csv = private_repo / "adjudication-working" / "review-queue" / "review-queue.csv"
    inventory_csv = (
        private_repo
        / "source-index"
        / "comprehensive"
        / "combined-drift-evidence-candidates.csv"
    )
    duplicate_csv = (
        private_repo
        / "adjudication-working"
        / "candidate-profile"
        / "exact-content-duplicate-groups.csv"
    )
    output_root = private_repo / "adjudication-working" / "evidence-packets"
    temp_root = private_repo / "adjudication-working" / "evidence-packets.__building__"

    for required in (queue_csv, inventory_csv, duplicate_csv):
        if not required.is_file():
            raise SystemExit(f"Required input missing: {required}")

    if output_root.exists():
        raise SystemExit(
            f"Canonical evidence-packet output already exists: {output_root}. "
            "Refusing to overwrite possible human adjudication work."
        )
    if temp_root.exists():
        raise SystemExit(
            f"Builder-owned temporary output already exists: {temp_root}. "
            "Refusing implicit cleanup."
        )

    queue, queue_cols = load_csv(queue_csv)
    inventory, inventory_cols = load_csv(inventory_csv)

    missing_queue = sorted(REQUIRED_QUEUE_COLUMNS - queue_cols)
    missing_inventory = sorted(REQUIRED_INVENTORY_COLUMNS - inventory_cols)
    if missing_queue:
        raise SystemExit(f"Review queue missing columns: {', '.join(missing_queue)}")
    if missing_inventory:
        raise SystemExit(
            f"Candidate inventory missing columns: {', '.join(missing_inventory)}"
        )

    if len(queue) != args.expected_queue:
        raise SystemExit(
            f"Review queue count mismatch: expected {args.expected_queue}, found {len(queue)}"
        )

    core_rows = [row for row in queue if clean(row.get("review_tier")) == CORE_TIER]
    if len(core_rows) != args.core:
        raise SystemExit(
            f"Core review count mismatch: expected {args.core}, found {len(core_rows)}"
        )

    inventory_by_id: dict[str, dict[str, str]] = {}
    for row in inventory:
        cid = clean(row.get("combined_candidate_id"))
        if not cid:
            raise SystemExit("Inventory contains a row without combined_candidate_id")
        if cid in inventory_by_id:
            raise SystemExit(f"Duplicate combined_candidate_id in inventory: {cid}")
        inventory_by_id[cid] = row

    duplicate_groups = load_duplicate_groups(duplicate_csv)

    source_repo_paths: dict[str, Path] = {}
    for qrow in core_rows:
        cid = clean(qrow.get("combined_candidate_id"))
        irow = inventory_by_id.get(cid)
        if irow is None:
            raise SystemExit(f"Queue candidate not present in inventory: {cid}")
        repo = resolve_repo(irow, git_root, cache_root)
        source_repo_paths[f"{clean(irow.get('source_repository'))}:{repo}"] = repo

    before_status = {key: status_bytes(repo) for key, repo in source_repo_paths.items()}

    # Read-only preflight: validate every source before any packet directory is created.
    preflight: list[dict[str, object]] = []
    for qrow in sorted(core_rows, key=lambda row: int(clean(row.get("review_rank"), "0"))):
        rank = int(clean(qrow.get("review_rank"), "0"))
        cid = clean(qrow.get("combined_candidate_id"))
        irow = inventory_by_id[cid]
        repo = resolve_repo(irow, git_root, cache_root)

        blob_sha = clean(irow.get("source_git_blob_sha")).lower()
        if not blob_sha:
            raise SystemExit(
                f"{cid} has no Git blob SHA; packet builder requires tracked source evidence."
            )

        object_type = clean(
            run_git(repo, ["cat-file", "-t", blob_sha], text=True)  # type: ignore[arg-type]
        )
        if object_type != "blob":
            raise SystemExit(f"{cid} provenance object {blob_sha} is not a Git blob")

        source_bytes = run_git(repo, ["cat-file", "blob", blob_sha])
        assert isinstance(source_bytes, bytes)
        try:
            source_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"{cid} source blob is not valid UTF-8 Markdown: {exc}") from exc

        computed_git_object_sha = git_object_sha(repo, source_bytes)
        if computed_git_object_sha.lower() != blob_sha:
            raise SystemExit(
                f"{cid} Git object identity mismatch: inventory={blob_sha} "
                f"computed={computed_git_object_sha}"
            )

        source_commit = clean(irow.get("source_commit"))
        relative_path = clean(irow.get("source_relative_path")).replace("\\", "/")
        if source_commit:
            commit_path_blob = clean(
                run_git(
                    repo,
                    ["rev-parse", f"{source_commit}:{relative_path}"],
                    text=True,
                )  # type: ignore[arg-type]
            ).lower()
            if commit_path_blob != blob_sha:
                raise SystemExit(
                    f"{cid} commit/path/blob mismatch: commit={source_commit} "
                    f"path={relative_path} expected_blob={blob_sha} actual_blob={commit_path_blob}"
                )

        blob_sha256 = hashlib.sha256(source_bytes).hexdigest()
        discovery_sha256 = clean(irow.get("source_sha256")).lower()
        hash_semantics = discovery_hash_semantics(irow)

        # For local tracked evidence, source_sha256 is the discovery-time worktree-byte hash.
        # Git may normalize CRLF worktree bytes into LF blob bytes. Preserve both identities.
        preflight.append(
            {
                "qrow": qrow,
                "irow": irow,
                "rank": rank,
                "cid": cid,
                "blob_sha": blob_sha,
                "source_bytes": source_bytes,
                "blob_sha256": blob_sha256,
                "discovery_sha256": discovery_sha256,
                "hash_semantics": hash_semantics,
            }
        )

    after_preflight_status = {
        key: status_bytes(repo) for key, repo in source_repo_paths.items()
    }
    preflight_changed_sources = [
        key for key in before_status if before_status[key] != after_preflight_status[key]
    ]
    if preflight_changed_sources:
        raise SystemExit(
            "Source repository integrity failure during read-only preflight: "
            + ", ".join(preflight_changed_sources)
        )

    # Transactional generation: write only under a builder-owned temporary directory.
    index_rows: list[dict[str, str | int]] = []
    source_copy_count = 0
    exact_group_packets = 0

    temp_root.mkdir(parents=True, exist_ok=False)
    try:
        for item in preflight:
            qrow = item["qrow"]
            irow = item["irow"]
            assert isinstance(qrow, dict)
            assert isinstance(irow, dict)

            rank = int(item["rank"])
            cid = str(item["cid"])
            blob_sha = str(item["blob_sha"])
            source_bytes = item["source_bytes"]
            assert isinstance(source_bytes, bytes)
            blob_sha256 = str(item["blob_sha256"])
            discovery_sha256 = str(item["discovery_sha256"])
            hash_semantics = str(item["hash_semantics"])

            packet_id = f"M2-PACKET-{rank:04d}"
            packet_dir = temp_root / packet_id
            packet_dir.mkdir()

            source_copy = packet_dir / "source-record.md"
            source_copy.write_bytes(source_bytes)
            if hashlib.sha256(source_copy.read_bytes()).hexdigest() != blob_sha256:
                raise RuntimeError(f"{cid} derived source copy hash verification failed")
            source_copy_count += 1

            group_id = clean(qrow.get("exact_content_group_id"))
            group_members = duplicate_groups.get(group_id, []) if group_id else []
            if group_id:
                exact_group_packets += 1

            manifest = {
                "packet_id": packet_id,
                "review_rank": rank,
                "review_tier": clean(qrow.get("review_tier")),
                "combined_candidate_id": cid,
                "record_suitability": "NOT_REVIEWED",
                "benchmark_case_status": "NOT_SELECTED",
                "historical_context_status": (
                    "EXACT_CONTENT_HINTS_AVAILABLE" if group_members else "NOT_ASSEMBLED"
                ),
                "ground_truth_assigned": False,
                "source": {
                    "repository": clean(irow.get("source_repository")),
                    "source_state": clean(irow.get("source_state")),
                    "coverage_origin": clean(irow.get("coverage_origin")),
                    "relative_path": clean(irow.get("source_relative_path")),
                    "commit": clean(irow.get("source_commit")),
                    "git_blob_sha": blob_sha,
                    "git_blob_sha256": blob_sha256,
                    "discovery_source_sha256": discovery_sha256,
                    "discovery_source_sha256_semantics": hash_semantics,
                    "discovery_source_bytes": clean(irow.get("source_bytes")),
                    "source_model": clean(irow.get("source_model"), "UNKNOWN"),
                    "template_family": clean(irow.get("template_family"), "UNKNOWN"),
                },
                "discovery_metadata": {
                    "discovery_score": clean(irow.get("discovery_score")),
                    "severity_raw": clean(irow.get("severity_raw")),
                    "recurrence_raw": clean(irow.get("recurrence_raw")),
                    "drift_id_raw": clean(irow.get("drift_id_raw")),
                    "title": clean(irow.get("title")),
                },
                "relationship_hints": {
                    "exact_content_group_id": group_id,
                    "exact_content_group_size": len(group_members) if group_id else 0,
                    "exact_content_candidate_ids": group_members,
                    "warning": (
                        "Exact-content identity is a retrieval/context hint only and does not establish DUPLICATE ground truth."
                        if group_id
                        else ""
                    ),
                },
            }
            (packet_dir / "packet-manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            peer_lines = (
                "\n".join(f"- `{member}`" for member in group_members)
                if group_members
                else "- None identified by exact-content identity."
            )
            discovery_hash_display = discovery_sha256 or "NOT_RECORDED"
            packet_md = f"""# {packet_id} — Human Adjudication Evidence Packet

## Status

- Record suitability: **NOT_REVIEWED**
- Benchmark case status: **NOT_SELECTED**
- Ground truth assigned: **NO**
- Historical-context status: **{manifest["historical_context_status"]}**

This packet is private staging material. It does not assign a benchmark relationship label.

## Queue identity

| Field | Value |
|---|---|
| Review rank | {rank} |
| Candidate ID | `{cid}` |
| Source repository | `{md_escape(clean(irow.get("source_repository")))}` |
| Source path | `{md_escape(clean(irow.get("source_relative_path")))}` |
| Source model | `{md_escape(clean(irow.get("source_model"), "UNKNOWN"))}` |
| Template family | `{md_escape(clean(irow.get("template_family"), "UNKNOWN"))}` |
| Discovery score | `{md_escape(clean(irow.get("discovery_score")))}` |
| Raw severity | `{md_escape(clean(irow.get("severity_raw")))}` |
| Raw recurrence | `{md_escape(clean(irow.get("recurrence_raw")))}` |
| Raw Drift ID | `{md_escape(clean(irow.get("drift_id_raw")))}` |

## Provenance

- Source commit: `{clean(irow.get("source_commit"))}`
- Source Git blob: `{blob_sha}`
- Extracted Git-blob SHA-256: `{blob_sha256}`
- Discovery source SHA-256: `{discovery_hash_display}`
- Discovery SHA-256 semantics: `{hash_semantics}`
- The Git blob identity is validated independently through Git object hashing and commit/path linkage.
- A locally discovered worktree SHA-256 may legitimately differ from Git-blob SHA-256 when Git line-ending normalization converts CRLF worktree bytes to LF blob bytes.
- `source-record.md` is an exact private copy of the Git blob used for adjudication; it does not replace or modify the original.

## Exact-content relationship hints

Group: `{group_id or "NONE"}`

{peer_lines}

**Important:** exact content does not automatically mean the same underlying incident and must never create `DUPLICATE` ground truth by itself.

## Adjudication preparation

Before assigning ground truth:

1. Determine whether this record is an actual incident/observation suitable for benchmark construction rather than a template, runbook, policy, administrative note, or other non-case artifact.
2. Assemble relevant historical incidents and supporting evidence.
3. Apply `benchmark/ground-truth/ADJUDICATION-PROTOCOL.md`.
4. Do not infer hidden facts absent from supplied evidence.
5. If evidence cannot safely establish a stronger relationship, use `INSUFFICIENT_EVIDENCE`.

"""
            (packet_dir / "packet.md").write_text(
                packet_md,
                encoding="utf-8",
                newline="\n",
            )

            adjudication_notes = """# Human Adjudication Notes

## Suitability review

- Record suitability: `NOT_REVIEWED`
- Suitable as benchmark observation?:
- If no, rejection reason:

## Historical context assembled

- Historical incident IDs / candidate IDs:
- Supporting evidence references:
- Missing evidence:

## Ground-truth decision

- Relationship:
- Matched incident IDs:
- Remediation state:
- Severity:
- Dangerous if misclassified as duplicate:
- Confidence:
- Reasoning summary:

## Review status

- Adjudicator:
- Adjudicated at:
- Status: `NOT_STARTED`
- Review notes:

"""
            (packet_dir / "adjudication-notes.md").write_text(
                adjudication_notes,
                encoding="utf-8",
                newline="\n",
            )

            index_rows.append(
                {
                    "packet_id": packet_id,
                    "review_rank": rank,
                    "combined_candidate_id": cid,
                    "source_repository": clean(irow.get("source_repository")),
                    "source_relative_path": clean(irow.get("source_relative_path")),
                    "source_model": clean(irow.get("source_model"), "UNKNOWN"),
                    "template_family": clean(irow.get("template_family"), "UNKNOWN"),
                    "source_git_blob_sha": blob_sha,
                    "source_blob_sha256": blob_sha256,
                    "discovery_source_sha256": discovery_sha256,
                    "discovery_source_sha256_semantics": hash_semantics,
                    "exact_content_group_id": group_id,
                    "exact_content_group_size": len(group_members) if group_id else 0,
                    "record_suitability": "NOT_REVIEWED",
                    "historical_context_status": manifest["historical_context_status"],
                    "ground_truth_assigned": "NO",
                }
            )

        index_path = temp_root / "packet-index.csv"
        with index_path.open("w", encoding="utf-8", newline="") as f:
            fieldnames = list(index_rows[0].keys()) if index_rows else []
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(index_rows)

        summary = {
            "core_packets": len(index_rows),
            "source_record_copies": source_copy_count,
            "source_repositories_read": len(source_repo_paths),
            "packets_with_exact_content_hints": exact_group_packets,
            "ground_truth_assigned": 0,
            "source_repositories_modified": 0,
            "provenance_model": {
                "git_blob_identity": "git_blob_sha + git_blob_sha256",
                "discovery_source_sha256": (
                    "preserved separately because local worktree bytes may differ from normalized Git blob bytes"
                ),
            },
        }
        (temp_root / "build-summary.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        (temp_root / "README.md").write_text(
            "# M2 Human-Adjudication Evidence Packets\n\n"
            "This directory contains private staging packets for the core human-review tier.\n\n"
            "Each packet contains an exact private copy of the selected Git blob, provenance metadata, "
            "exact-content relationship hints when available, and a blank adjudication worksheet. "
            "No packet assigns ground truth or automatically promotes a discovery candidate into the benchmark.\n\n"
            "Git-blob and discovery-worktree SHA-256 values are preserved separately because line-ending "
            "normalization can make their byte hashes differ while the Git object still represents the intended source.\n",
            encoding="utf-8",
            newline="\n",
        )

        packet_dirs = sorted(p for p in temp_root.iterdir() if p.is_dir())
        if len(packet_dirs) != args.core:
            raise RuntimeError(
                f"Temporary packet validation failed: expected {args.core} packet directories, found {len(packet_dirs)}"
            )
        for packet_dir in packet_dirs:
            for name in (
                "source-record.md",
                "packet-manifest.json",
                "packet.md",
                "adjudication-notes.md",
            ):
                if not (packet_dir / name).is_file():
                    raise RuntimeError(
                        f"Temporary packet validation failed: missing {packet_dir / name}"
                    )

        after_status = {key: status_bytes(repo) for key, repo in source_repo_paths.items()}
        changed_sources = [
            key for key in before_status if before_status[key] != after_status[key]
        ]
        if changed_sources:
            raise RuntimeError(
                "Source repository integrity failure; status changed during packet build: "
                + ", ".join(changed_sources)
            )

        os.replace(temp_root, output_root)

    except BaseException:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise

    print("M2 core evidence-packet build complete")
    print(f"CorePackets={len(index_rows)}")
    print(f"SourceCopies={source_copy_count}")
    print(f"SourceRepositoriesRead={len(source_repo_paths)}")
    print(f"PacketsWithExactContentHints={exact_group_packets}")
    print("GroundTruthAssigned=0")
    print("SourceRepositoriesModified=0")
    print("TransactionMode=READ_ONLY_PREFLIGHT_THEN_ATOMIC_PROMOTION")
    print(f"OutputDirectory={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
