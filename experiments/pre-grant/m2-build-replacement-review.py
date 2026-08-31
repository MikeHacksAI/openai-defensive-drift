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
from typing import Any

CORE_TIER = "CORE_100"
RESERVE_TIER = "EXPANSION_RESERVE"
ALLOWED_SUITABILITY = {"SUITABLE", "UNSUITABLE", "NEEDS_MORE_CONTEXT"}

REQUIRED_QUEUE_COLUMNS = {
    "review_rank",
    "review_tier",
    "combined_candidate_id",
    "source_repository",
    "source_model",
    "template_family",
    "discovery_score",
    "severity_raw",
    "recurrence_raw",
    "drift_id_raw",
    "source_relative_path",
    "title",
    "exact_content_group_id",
    "exact_content_group_size",
    "selection_reasons",
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
REQUIRED_DECISION_COLUMNS = {
    "packet_id",
    "combined_candidate_id",
    "record_suitability",
}


def clean(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def load_csv(path: Path) -> tuple[list[dict[str, str]], set[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), set(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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
    result = run_git(
        repo,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    assert isinstance(result, bytes)
    return result


def git_object_sha(repo: Path, data: bytes) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "--stdin"],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git hash-object failed in {repo}: {stderr}")
    return proc.stdout.decode("ascii", errors="strict").strip()


def resolve_repo(row: dict[str, str], git_root: Path, cache_root: Path) -> Path:
    repo_name = clean(row.get("source_repository"))
    origin = clean(row.get("coverage_origin"))
    repo = (cache_root if origin == "GITHUB_REMOTE" else git_root) / repo_name
    if not (repo / ".git").is_dir():
        raise RuntimeError(
            f"Source repository/cache missing for {repo_name}: {repo} "
            f"(coverage_origin={origin})"
        )
    return repo


def load_duplicate_groups(path: Path) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    if not path.is_file():
        return groups
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            gid = clean(row.get("content_identity"))
            members = [
                member
                for member in clean(row.get("candidate_ids")).split(";")
                if member
            ]
            if gid and members:
                groups[gid] = members
    return groups


def parse_int(value: str | None, default: int = 0) -> int:
    try:
        return int(clean(value, str(default)))
    except ValueError:
        return default


def severity_bucket(value: str) -> str:
    upper = value.upper()
    for sev in ("SEV-1", "SEV‑1", "SEV-2", "SEV‑2", "SEV-3", "SEV‑3", "SEV-4", "SEV‑4"):
        if sev in upper:
            return sev.replace("‑", "-")
    return "UNKNOWN"


def base_score(row: dict[str, str]) -> int:
    score = 0
    reason = clean(row.get("selection_reasons"))
    if reason == "explicit_recurrence_metadata":
        score += 8
    elif reason.startswith("model_minimum:"):
        score += 7
    elif reason.startswith("template_minimum:"):
        score += 5
    elif reason == "greedy_diversity_fill":
        score += 3

    if clean(row.get("recurrence_raw")):
        score += 4

    sev = severity_bucket(clean(row.get("severity_raw")))
    if sev == "SEV-1":
        score += 3
    elif sev == "SEV-3":
        score += 2
    elif sev == "SEV-2":
        score += 1

    score += min(parse_int(row.get("discovery_score")), 18)
    return score


def dynamic_score(
    row: dict[str, str],
    selected_models: set[str],
    selected_templates: set[str],
    selected_severities: set[str],
    selected_reason_families: set[str],
) -> int:
    score = base_score(row)
    model = clean(row.get("source_model"), "UNKNOWN")
    template = clean(row.get("template_family"), "UNKNOWN")
    sev = severity_bucket(clean(row.get("severity_raw")))
    reason = clean(row.get("selection_reasons"))

    if model not in selected_models:
        score += 20
    if template not in selected_templates:
        score += 14
    if sev not in selected_severities:
        score += 6

    reason_family = reason.split(":", 1)[0] if reason else "NONE"
    if reason_family not in selected_reason_families:
        score += 5

    exact_group_size = parse_int(row.get("exact_content_group_size"))
    if exact_group_size > 1:
        score -= 8

    return score


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


def md_escape(value: str) -> str:
    return value.replace("|", r"\|")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Construct a deterministic diversity-preserving M2 replacement review set "
            "from the existing expansion reserve, then materialize provenance-safe "
            "private evidence packets without assigning relationship ground truth."
        )
    )
    parser.add_argument("--private-repo", required=True)
    parser.add_argument("--git-root", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--slots", type=int, default=22)
    parser.add_argument("--expected-private-head", required=True)
    args = parser.parse_args()

    private_repo = Path(args.private_repo)
    git_root = Path(args.git_root)
    cache_root = Path(args.cache_root)
    slots = args.slots

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
    decisions_csv = (
        private_repo
        / "adjudication-working"
        / "suitability-screening"
        / "excel-import"
        / "2026-08-30-completed-review-decisions.csv"
    )

    output_root = private_repo / "adjudication-working" / "replacement-review"
    temp_root = private_repo / "adjudication-working" / "replacement-review.__building__"

    for required in (queue_csv, inventory_csv, duplicate_csv, decisions_csv):
        if not required.is_file():
            raise SystemExit(f"Required input missing: {required}")

    if output_root.exists():
        raise SystemExit(
            f"Replacement review output already exists: {output_root}. "
            "Refusing to overwrite possible human review work."
        )
    if temp_root.exists():
        raise SystemExit(
            f"Builder temporary output already exists: {temp_root}. "
            "Refusing implicit cleanup."
        )

    if status_bytes(private_repo):
        raise SystemExit("Private repository must be clean before replacement construction.")

    actual_head = clean(
        run_git(private_repo, ["rev-parse", "HEAD"], text=True)  # type: ignore[arg-type]
    )
    if actual_head != args.expected_private_head:
        raise SystemExit(
            f"Unexpected private HEAD: expected={args.expected_private_head} actual={actual_head}"
        )

    queue, queue_cols = load_csv(queue_csv)
    inventory, inventory_cols = load_csv(inventory_csv)
    decisions, decision_cols = load_csv(decisions_csv)

    missing_queue = sorted(REQUIRED_QUEUE_COLUMNS - queue_cols)
    missing_inventory = sorted(REQUIRED_INVENTORY_COLUMNS - inventory_cols)
    missing_decisions = sorted(REQUIRED_DECISION_COLUMNS - decision_cols)
    if missing_queue:
        raise SystemExit(f"Review queue missing columns: {', '.join(missing_queue)}")
    if missing_inventory:
        raise SystemExit(f"Inventory missing columns: {', '.join(missing_inventory)}")
    if missing_decisions:
        raise SystemExit(f"Decision intake missing columns: {', '.join(missing_decisions)}")

    if len(queue) != 150:
        raise SystemExit(f"Expected review queue size 150; found {len(queue)}")
    if len(decisions) != 100:
        raise SystemExit(f"Expected 100 completed decisions; found {len(decisions)}")

    for row in decisions:
        suitability = clean(row.get("record_suitability"))
        if suitability not in ALLOWED_SUITABILITY:
            raise SystemExit(f"Invalid suitability in completed decisions: {suitability}")

    suitable_ids = {
        clean(row.get("combined_candidate_id"))
        for row in decisions
        if clean(row.get("record_suitability")) == "SUITABLE"
    }
    unsuitable_ids = {
        clean(row.get("combined_candidate_id"))
        for row in decisions
        if clean(row.get("record_suitability")) == "UNSUITABLE"
    }
    more_context_ids = {
        clean(row.get("combined_candidate_id"))
        for row in decisions
        if clean(row.get("record_suitability")) == "NEEDS_MORE_CONTEXT"
    }

    if len(suitable_ids) != 78 or len(unsuitable_ids) != 22 or more_context_ids:
        raise SystemExit(
            "Completed-decision totals do not match the accepted checkpoint "
            f"(suitable={len(suitable_ids)} unsuitable={len(unsuitable_ids)} "
            f"more_context={len(more_context_ids)})."
        )

    core_rows = [row for row in queue if clean(row.get("review_tier")) == CORE_TIER]
    reserve_rows = [row for row in queue if clean(row.get("review_tier")) == RESERVE_TIER]
    if len(core_rows) != 100:
        raise SystemExit(f"Expected 100 core rows; found {len(core_rows)}")
    if len(reserve_rows) != 50:
        raise SystemExit(f"Expected 50 reserve rows; found {len(reserve_rows)}")
    if slots <= 0 or slots > len(reserve_rows):
        raise SystemExit(f"Invalid replacement slot count: {slots}")

    inventory_by_id: dict[str, dict[str, str]] = {}
    for row in inventory:
        cid = clean(row.get("combined_candidate_id"))
        if not cid:
            raise SystemExit("Inventory contains a row without combined_candidate_id")
        if cid in inventory_by_id:
            raise SystemExit(f"Duplicate combined_candidate_id in inventory: {cid}")
        inventory_by_id[cid] = row

    duplicate_groups = load_duplicate_groups(duplicate_csv)

    ranking_rows: list[dict[str, Any]] = []
    eligible_rows: list[dict[str, str]] = []

    for row in reserve_rows:
        cid = clean(row.get("combined_candidate_id"))
        if cid not in inventory_by_id:
            raise SystemExit(f"Reserve candidate missing from inventory: {cid}")

        group_id = clean(row.get("exact_content_group_id"))
        group_members = set(duplicate_groups.get(group_id, [])) if group_id else set()
        suitable_collision = sorted(group_members & suitable_ids)

        exclusion = ""
        if cid in suitable_ids or cid in unsuitable_ids:
            exclusion = "ALREADY_IN_CORE_DECISIONS"
        elif suitable_collision:
            exclusion = "EXACT_CONTENT_MATCHES_SUITABLE_CORE"

        ranking_rows.append(
            {
                "reserve_review_rank": parse_int(row.get("review_rank")),
                "combined_candidate_id": cid,
                "source_repository": clean(row.get("source_repository")),
                "source_model": clean(row.get("source_model"), "UNKNOWN"),
                "template_family": clean(row.get("template_family"), "UNKNOWN"),
                "discovery_score": parse_int(row.get("discovery_score")),
                "severity_bucket": severity_bucket(clean(row.get("severity_raw"))),
                "recurrence_raw": clean(row.get("recurrence_raw")),
                "source_relative_path": clean(row.get("source_relative_path")),
                "title": clean(row.get("title")),
                "exact_content_group_id": group_id,
                "exact_content_group_size": parse_int(row.get("exact_content_group_size")),
                "selection_reasons": clean(row.get("selection_reasons")),
                "base_score": base_score(row),
                "eligible": "NO" if exclusion else "YES",
                "exclusion_reason": exclusion,
                "selected": "NO",
                "replacement_rank": "",
                "dynamic_selection_score": "",
            }
        )
        if not exclusion:
            eligible_rows.append(row)

    if len(eligible_rows) < slots:
        raise SystemExit(
            f"Only {len(eligible_rows)} reserve candidates remain eligible for {slots} slots."
        )

    selected: list[dict[str, str]] = []
    selected_ids: set[str] = set()
    selected_group_ids: set[str] = set()
    selected_models: set[str] = set()
    selected_templates: set[str] = set()
    selected_severities: set[str] = set()
    selected_reason_families: set[str] = set()
    selection_scores: dict[str, int] = {}

    while len(selected) < slots:
        candidates: list[tuple[int, int, str, dict[str, str]]] = []
        for row in eligible_rows:
            cid = clean(row.get("combined_candidate_id"))
            if cid in selected_ids:
                continue
            group_id = clean(row.get("exact_content_group_id"))
            if group_id and group_id in selected_group_ids:
                continue

            score = dynamic_score(
                row,
                selected_models,
                selected_templates,
                selected_severities,
                selected_reason_families,
            )
            review_rank = parse_int(row.get("review_rank"), 999999)
            candidates.append((score, -review_rank, cid, row))

        if not candidates:
            raise SystemExit(
                f"Selection exhausted after {len(selected)} records; cannot fill {slots} slots "
                "without reusing an exact-content group."
            )

        candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        score, _, cid, chosen = candidates[0]
        selected.append(chosen)
        selected_ids.add(cid)
        selection_scores[cid] = score

        group_id = clean(chosen.get("exact_content_group_id"))
        if group_id:
            selected_group_ids.add(group_id)
        selected_models.add(clean(chosen.get("source_model"), "UNKNOWN"))
        selected_templates.add(clean(chosen.get("template_family"), "UNKNOWN"))
        selected_severities.add(severity_bucket(clean(chosen.get("severity_raw"))))
        reason = clean(chosen.get("selection_reasons"))
        selected_reason_families.add(reason.split(":", 1)[0] if reason else "NONE")

    selected_by_id = {
        clean(row.get("combined_candidate_id")): index
        for index, row in enumerate(selected, start=1)
    }

    ranking_by_id = {row["combined_candidate_id"]: row for row in ranking_rows}
    for cid, replacement_rank in selected_by_id.items():
        ranking = ranking_by_id[cid]
        ranking["selected"] = "YES"
        ranking["replacement_rank"] = replacement_rank
        ranking["dynamic_selection_score"] = selection_scores[cid]

    if len(selected_ids) != slots:
        raise SystemExit("Replacement selection contains duplicate candidate IDs.")
    selected_groups = [
        clean(row.get("exact_content_group_id"))
        for row in selected
        if clean(row.get("exact_content_group_id"))
    ]
    if len(selected_groups) != len(set(selected_groups)):
        raise SystemExit("Replacement selection reused an exact-content group.")

    source_repo_paths: dict[str, Path] = {}
    preflight: list[dict[str, Any]] = []

    for row in selected:
        cid = clean(row.get("combined_candidate_id"))
        irow = inventory_by_id[cid]
        repo = resolve_repo(irow, git_root, cache_root)
        source_repo_paths[f"{clean(irow.get('source_repository'))}:{repo}"] = repo

    before_status = {key: status_bytes(repo) for key, repo in source_repo_paths.items()}

    for replacement_rank, qrow in enumerate(selected, start=1):
        cid = clean(qrow.get("combined_candidate_id"))
        irow = inventory_by_id[cid]
        repo = resolve_repo(irow, git_root, cache_root)

        blob_sha = clean(irow.get("source_git_blob_sha")).lower()
        if not blob_sha:
            raise SystemExit(f"{cid} has no Git blob SHA; replacement packet requires tracked source.")

        object_type = clean(
            run_git(repo, ["cat-file", "-t", blob_sha], text=True)  # type: ignore[arg-type]
        )
        if object_type != "blob":
            raise SystemExit(f"{cid} provenance object {blob_sha} is not a Git blob.")

        source_bytes = run_git(repo, ["cat-file", "blob", blob_sha])
        assert isinstance(source_bytes, bytes)
        source_bytes.decode("utf-8", errors="strict")

        computed_object_sha = git_object_sha(repo, source_bytes).lower()
        if computed_object_sha != blob_sha:
            raise SystemExit(
                f"{cid} Git object identity mismatch: inventory={blob_sha} "
                f"computed={computed_object_sha}"
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

        preflight.append(
            {
                "replacement_rank": replacement_rank,
                "qrow": qrow,
                "irow": irow,
                "cid": cid,
                "blob_sha": blob_sha,
                "source_bytes": source_bytes,
                "blob_sha256": hashlib.sha256(source_bytes).hexdigest(),
            }
        )

    after_preflight_status = {
        key: status_bytes(repo) for key, repo in source_repo_paths.items()
    }
    changed_sources = [
        key
        for key in before_status
        if before_status[key] != after_preflight_status[key]
    ]
    if changed_sources:
        raise SystemExit(
            "Source repository integrity failure during read-only preflight: "
            + ", ".join(changed_sources)
        )

    temp_root.mkdir(parents=True, exist_ok=False)
    try:
        packet_rows: list[dict[str, Any]] = []

        for item in preflight:
            replacement_rank = int(item["replacement_rank"])
            qrow = item["qrow"]
            irow = item["irow"]
            cid = str(item["cid"])
            blob_sha = str(item["blob_sha"])
            blob_sha256 = str(item["blob_sha256"])
            source_bytes = item["source_bytes"]
            assert isinstance(qrow, dict)
            assert isinstance(irow, dict)
            assert isinstance(source_bytes, bytes)

            packet_id = f"M2-REPL-{replacement_rank:04d}"
            packet_dir = temp_root / packet_id
            packet_dir.mkdir()

            source_copy = packet_dir / "source-record.md"
            source_copy.write_bytes(source_bytes)
            if hashlib.sha256(source_copy.read_bytes()).hexdigest() != blob_sha256:
                raise RuntimeError(f"{cid} replacement source-copy hash verification failed")

            group_id = clean(qrow.get("exact_content_group_id"))
            group_members = duplicate_groups.get(group_id, []) if group_id else []

            manifest = {
                "packet_id": packet_id,
                "replacement_rank": replacement_rank,
                "reserve_review_rank": parse_int(qrow.get("review_rank")),
                "combined_candidate_id": cid,
                "record_suitability": "NOT_REVIEWED",
                "benchmark_case_status": "REPLACEMENT_CANDIDATE",
                "ground_truth_assigned": False,
                "selection": {
                    "dynamic_score": selection_scores[cid],
                    "selection_reason": clean(qrow.get("selection_reasons")),
                    "selection_policy": (
                        "Deterministic diversity-preserving greedy selection from the "
                        "pre-existing 50-case expansion reserve after excluding exact-content "
                        "matches to already-suitable core records and reusing no exact-content group."
                    ),
                },
                "source": {
                    "repository": clean(irow.get("source_repository")),
                    "source_state": clean(irow.get("source_state")),
                    "coverage_origin": clean(irow.get("coverage_origin")),
                    "relative_path": clean(irow.get("source_relative_path")),
                    "commit": clean(irow.get("source_commit")),
                    "git_blob_sha": blob_sha,
                    "git_blob_sha256": blob_sha256,
                    "discovery_source_sha256": clean(irow.get("source_sha256")),
                    "discovery_source_sha256_semantics": discovery_hash_semantics(irow),
                    "source_bytes": clean(irow.get("source_bytes")),
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
                        "Exact-content identity is a retrieval/context hint only and does not "
                        "establish DUPLICATE ground truth."
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

            packet_md = f"""# {packet_id} — Replacement Suitability Evidence Packet

## Status

- Record suitability: **NOT_REVIEWED**
- Benchmark case status: **REPLACEMENT_CANDIDATE**
- Ground truth assigned: **NO**

This packet is private M2 staging material. Human suitability review must happen before
this record can enter the 100-case benchmark candidate set.

## Identity

| Field | Value |
|---|---|
| Replacement rank | {replacement_rank} |
| Original reserve rank | {parse_int(qrow.get("review_rank"))} |
| Candidate ID | `{cid}` |
| Repository | `{md_escape(clean(irow.get("source_repository")))}` |
| Source path | `{md_escape(clean(irow.get("source_relative_path")))}` |
| Source model | `{md_escape(clean(irow.get("source_model"), "UNKNOWN"))}` |
| Template family | `{md_escape(clean(irow.get("template_family"), "UNKNOWN"))}` |
| Discovery score | `{md_escape(clean(irow.get("discovery_score")))}` |
| Raw severity | `{md_escape(clean(irow.get("severity_raw")))}` |
| Raw recurrence | `{md_escape(clean(irow.get("recurrence_raw")))}` |

## Provenance

- Source commit: `{clean(irow.get("source_commit"))}`
- Source Git blob: `{blob_sha}`
- Extracted Git-blob SHA-256: `{blob_sha256}`
- The `source-record.md` file is an exact private copy of the validated Git blob.
- Original source repositories were read only and are not modified by this builder.

## Selection rationale

- Reserve selection reason: `{clean(qrow.get("selection_reasons"))}`
- Dynamic diversity score at selection: `{selection_scores[cid]}`
- Exact-content group: `{group_id or "NONE"}`
- Exact-content group reuse inside this replacement set: **NO**
- Exact-content collision with an already-suitable core record: **NO**

## Human suitability boundary

At this stage decide only:

- `SUITABLE`
- `UNSUITABLE`
- `NEEDS_MORE_CONTEXT`

Do **not** assign `NEW`, `DUPLICATE`, `RECURRENCE`,
`RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE` yet.
"""
            (packet_dir / "packet.md").write_text(
                packet_md,
                encoding="utf-8",
                newline="\n",
            )

            notes_md = """# Replacement Suitability Review Notes

- Record suitability: `NOT_REVIEWED`
- Rejection reason:
- Reviewer notes:
- Reviewed at:

## Boundary

Do not assign relationship ground truth in this file during replacement suitability review.
"""
            (packet_dir / "adjudication-notes.md").write_text(
                notes_md,
                encoding="utf-8",
                newline="\n",
            )

            packet_rows.append(
                {
                    "replacement_rank": replacement_rank,
                    "packet_id": packet_id,
                    "reserve_review_rank": parse_int(qrow.get("review_rank")),
                    "combined_candidate_id": cid,
                    "source_repository": clean(irow.get("source_repository")),
                    "source_relative_path": clean(irow.get("source_relative_path")),
                    "source_model": clean(irow.get("source_model"), "UNKNOWN"),
                    "template_family": clean(irow.get("template_family"), "UNKNOWN"),
                    "severity_bucket": severity_bucket(clean(irow.get("severity_raw"))),
                    "recurrence_raw": clean(irow.get("recurrence_raw")),
                    "selection_reasons": clean(qrow.get("selection_reasons")),
                    "dynamic_selection_score": selection_scores[cid],
                    "record_suitability": "NOT_REVIEWED",
                    "rejection_reason": "",
                    "reviewer_notes": "",
                    "ground_truth_assigned": "NO",
                    "evidence_relative_path": f"{packet_id}/source-record.md",
                }
            )

        ranking_fields = [
            "reserve_review_rank",
            "combined_candidate_id",
            "source_repository",
            "source_model",
            "template_family",
            "discovery_score",
            "severity_bucket",
            "recurrence_raw",
            "source_relative_path",
            "title",
            "exact_content_group_id",
            "exact_content_group_size",
            "selection_reasons",
            "base_score",
            "eligible",
            "exclusion_reason",
            "selected",
            "replacement_rank",
            "dynamic_selection_score",
        ]
        ranking_rows.sort(key=lambda row: int(row["reserve_review_rank"]))
        write_csv(temp_root / "replacement-candidate-ranking.csv", ranking_rows, ranking_fields)

        packet_fields = [
            "replacement_rank",
            "packet_id",
            "reserve_review_rank",
            "combined_candidate_id",
            "source_repository",
            "source_relative_path",
            "source_model",
            "template_family",
            "severity_bucket",
            "recurrence_raw",
            "selection_reasons",
            "dynamic_selection_score",
            "record_suitability",
            "rejection_reason",
            "reviewer_notes",
            "ground_truth_assigned",
            "evidence_relative_path",
        ]
        write_csv(temp_root / "replacement-review-set.csv", packet_rows, packet_fields)

        selected_model_counts: dict[str, int] = {}
        selected_template_counts: dict[str, int] = {}
        selected_severity_counts: dict[str, int] = {}
        for row in packet_rows:
            selected_model_counts[row["source_model"]] = (
                selected_model_counts.get(row["source_model"], 0) + 1
            )
            selected_template_counts[row["template_family"]] = (
                selected_template_counts.get(row["template_family"], 0) + 1
            )
            selected_severity_counts[row["severity_bucket"]] = (
                selected_severity_counts.get(row["severity_bucket"], 0) + 1
            )

        summary = {
            "schema_version": 1,
            "core_reviewed": 100,
            "core_suitable": 78,
            "core_unsuitable": 22,
            "replacement_slots_required": slots,
            "reserve_size": len(reserve_rows),
            "eligible_reserve_after_exact_content_core_exclusion": len(eligible_rows),
            "selected_replacements": len(packet_rows),
            "selected_unique_candidate_ids": len(selected_ids),
            "selected_exact_content_groups_reused": 0,
            "ground_truth_assigned": 0,
            "source_repositories_modified": 0,
            "selected_model_counts": selected_model_counts,
            "selected_template_counts": selected_template_counts,
            "selected_severity_counts": selected_severity_counts,
            "selection_policy": (
                "Deterministic greedy selection balancing model, template family, severity, "
                "selection-reason family, discovery score, recurrence metadata, and duplicate risk. "
                "Reserve candidates that exactly match already-suitable core content are excluded; "
                "no exact-content group is reused within the 22 selected replacements."
            ),
            "next_gate": (
                "Human suitability review of the 22 replacement packets. Relationship ground truth "
                "remains unassigned until 100 suitable benchmark observations are assembled."
            ),
        }
        (temp_root / "build-summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        readme = f"""# M2 Replacement Review

This private workspace was generated after completion of the first 100-case human suitability screen.

- Core reviewed: 100
- Core suitable: 78
- Core unsuitable: 22
- Replacement slots: {slots}
- Expansion reserve evaluated: {len(reserve_rows)}
- Replacement packets generated: {len(packet_rows)}
- Relationship ground truth assigned: 0

`replacement-candidate-ranking.csv` preserves the deterministic reserve ranking and exclusions.

`replacement-review-set.csv` is the human review worklist.

Each `M2-REPL-####/` directory contains an exact Git-blob evidence copy plus provenance metadata.

No source repository is modified by this workflow.
"""
        (temp_root / "README.md").write_text(
            readme,
            encoding="utf-8",
            newline="\n",
        )

        final_status = {
            key: status_bytes(repo) for key, repo in source_repo_paths.items()
        }
        changed_sources_after_build = [
            key
            for key in before_status
            if before_status[key] != final_status[key]
        ]
        if changed_sources_after_build:
            raise RuntimeError(
                "Source repository integrity failure during packet generation: "
                + ", ".join(changed_sources_after_build)
            )

        os.replace(temp_root, output_root)
    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise

    print("M2_REPLACEMENT_REVIEW_BUILD=SUCCESS")
    print("CoreSuitable=78")
    print("CoreUnsuitable=22")
    print(f"ReserveEvaluated={len(reserve_rows)}")
    print(f"ReserveEligible={len(eligible_rows)}")
    print(f"ReplacementPackets={slots}")
    print(f"SelectedModels={len({clean(row.get('source_model'), 'UNKNOWN') for row in selected})}")
    print(f"SelectedTemplates={len({clean(row.get('template_family'), 'UNKNOWN') for row in selected})}")
    print(f"SelectedSeverities={len({severity_bucket(clean(row.get('severity_raw'))) for row in selected})}")
    print("ExactContentGroupReuse=0")
    print("GroundTruthAssigned=0")
    print("SourceRepositoriesModified=0")
    print(f"Output={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
