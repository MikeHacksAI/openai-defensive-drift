#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
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
    "coverage_origin",
    "source_repository",
    "source_relative_path",
    "source_commit",
    "source_git_blob_sha",
    "source_sha256",
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
    return run_git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])  # type: ignore[return-value]


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
    if origin == "GITHUB_REMOTE":
        repo = cache_root / repo_name
    else:
        repo = git_root / repo_name
    if not (repo / ".git").exists():
        raise RuntimeError(
            f"Source repository clone/cache not found for {repo_name}: {repo} "
            f"(coverage_origin={origin})"
        )
    return repo


def md_escape(value: str) -> str:
    return value.replace("|", r"\|")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize private M2 evidence packets for core human review without assigning ground truth."
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

    for required in (queue_csv, inventory_csv, duplicate_csv):
        if not required.is_file():
            raise SystemExit(f"Required input missing: {required}")

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

    if output_root.exists():
        raise SystemExit(
            f"Evidence-packet output already exists: {output_root}. "
            "Refusing to overwrite possible human adjudication work."
        )
    output_root.mkdir(parents=True, exist_ok=False)

    index_rows: list[dict[str, str | int]] = []
    source_copy_count = 0
    exact_group_packets = 0

    for qrow in sorted(core_rows, key=lambda row: int(clean(row.get("review_rank"), "0"))):
        rank = int(clean(qrow.get("review_rank"), "0"))
        cid = clean(qrow.get("combined_candidate_id"))
        irow = inventory_by_id[cid]
        packet_id = f"M2-PACKET-{rank:04d}"
        packet_dir = output_root / packet_id
        packet_dir.mkdir()

        repo = resolve_repo(irow, git_root, cache_root)
        blob_sha = clean(irow.get("source_git_blob_sha"))
        if not blob_sha:
            raise SystemExit(
                f"{cid} has no Git blob SHA; evidence packet builder currently requires tracked source evidence."
            )

        source_bytes = run_git(repo, ["cat-file", "blob", blob_sha])  # type: ignore[assignment]
        assert isinstance(source_bytes, bytes)
        try:
            source_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"{cid} source blob is not valid UTF-8 Markdown: {exc}") from exc

        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        recorded_sha256 = clean(irow.get("source_sha256")).lower()
        if recorded_sha256 and recorded_sha256 != source_sha256:
            raise SystemExit(
                f"{cid} SHA-256 mismatch: inventory={recorded_sha256} extracted={source_sha256}"
            )

        source_copy = packet_dir / "source-record.md"
        source_copy.write_bytes(source_bytes)
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
                "coverage_origin": clean(irow.get("coverage_origin")),
                "relative_path": clean(irow.get("source_relative_path")),
                "commit": clean(irow.get("source_commit")),
                "git_blob_sha": blob_sha,
                "content_sha256": source_sha256,
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
- Extracted source SHA-256: `{source_sha256}`
- Original source was read only through Git blob content.
- `source-record.md` is a derived private copy for adjudication; it does not replace or modify the original.

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
        (packet_dir / "packet.md").write_text(packet_md, encoding="utf-8", newline="\n")

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
            adjudication_notes, encoding="utf-8", newline="\n"
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
                "source_content_sha256": source_sha256,
                "exact_content_group_id": group_id,
                "exact_content_group_size": len(group_members) if group_id else 0,
                "record_suitability": "NOT_REVIEWED",
                "historical_context_status": manifest["historical_context_status"],
                "ground_truth_assigned": "NO",
            }
        )

    after_status = {key: status_bytes(repo) for key, repo in source_repo_paths.items()}
    changed_sources = [key for key in before_status if before_status[key] != after_status[key]]
    if changed_sources:
        raise SystemExit(
            "Source repository integrity failure; status changed during packet build: "
            + ", ".join(changed_sources)
        )

    index_path = output_root / "packet-index.csv"
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
    }
    (output_root / "build-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (output_root / "README.md").write_text(
        "# M2 Human-Adjudication Evidence Packets\n\n"
        "This directory contains private staging packets for the 100-entry core human-review tier.\n\n"
        "Each packet contains an exact private copy of the selected source Git blob, provenance metadata, "
        "exact-content relationship hints when available, and a blank adjudication worksheet. "
        "No packet assigns ground truth or automatically promotes a discovery candidate into the benchmark.\n\n"
        "Human review must first determine record suitability, then assemble historical context, then apply "
        "the frozen adjudication protocol.\n",
        encoding="utf-8",
        newline="\n",
    )

    print("M2 core evidence-packet build complete")
    print(f"CorePackets={len(index_rows)}")
    print(f"SourceCopies={source_copy_count}")
    print(f"SourceRepositoriesRead={len(source_repo_paths)}")
    print(f"PacketsWithExactContentHints={exact_group_packets}")
    print("GroundTruthAssigned=0")
    print("SourceRepositoriesModified=0")
    print(f"OutputDirectory={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
