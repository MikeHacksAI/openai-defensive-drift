#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")
LOCAL_WORKTREE_STATES = {"UNTRACKED", "IGNORED_UNTRACKED"}

def clean(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    value = value.strip()
    return value if value else default

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

def run_git_bytes(repo: Path, args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {stderr}")
    return proc.stdout

def run_git_text(repo: Path, args: list[str]) -> str:
    return run_git_bytes(repo, args).decode("utf-8", errors="strict").strip()

def repo_status(repo: Path) -> bytes:
    return run_git_bytes(
        repo,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )

def resolve_repo(
    row: dict[str, str],
    git_root: Path,
    cache_root: Path,
) -> Path:
    repo_name = clean(row.get("source_repository"))
    coverage_origin = clean(row.get("coverage_origin"))
    if not repo_name:
        raise RuntimeError("Candidate inventory row is missing source_repository.")
    root = cache_root if coverage_origin == "GITHUB_REMOTE" else git_root
    repo = root / repo_name
    if not (repo / ".git").is_dir():
        raise RuntimeError(
            f"Source repository clone/cache not found for {repo_name}: {repo} "
            f"(coverage_origin={coverage_origin or 'UNKNOWN'})"
        )
    return repo

def git_object_sha(repo: Path, source_bytes: bytes) -> str:
    return (
        run_git_bytes(repo, ["hash-object", "--stdin"], input_bytes=source_bytes)
        .decode("ascii", errors="strict")
        .strip()
    )

def materialize_candidate(
    candidate: dict[str, str],
    git_root: Path,
    cache_root: Path,
) -> tuple[bytes, str, Path, str]:
    repo = resolve_repo(candidate, git_root, cache_root)
    blob_sha = clean(candidate.get("source_git_blob_sha")).lower()
    source_state = clean(candidate.get("source_state"))
    relative_path = clean(candidate.get("source_relative_path")).replace("\\", "/")

    if blob_sha:
        object_type = run_git_text(repo, ["cat-file", "-t", blob_sha])
        if object_type != "blob":
            raise RuntimeError(
                f"{clean(candidate.get('combined_candidate_id'))} provenance object "
                f"{blob_sha} is not a Git blob."
            )
        source_bytes = run_git_bytes(repo, ["cat-file", "blob", blob_sha])
        computed_blob = git_object_sha(repo, source_bytes).lower()
        if computed_blob != blob_sha:
            raise RuntimeError(
                f"{clean(candidate.get('combined_candidate_id'))} Git object identity "
                f"mismatch: expected={blob_sha} actual={computed_blob}"
            )

        source_commit = clean(candidate.get("source_commit"))
        if source_commit and relative_path:
            commit_path_blob = run_git_text(
                repo,
                ["rev-parse", f"{source_commit}:{relative_path}"],
            ).lower()
            if commit_path_blob != blob_sha:
                raise RuntimeError(
                    f"{clean(candidate.get('combined_candidate_id'))} commit/path/blob "
                    f"mismatch: commit={source_commit} path={relative_path} "
                    f"expected={blob_sha} actual={commit_path_blob}"
                )
        return source_bytes, "GIT_BLOB", repo, blob_sha

    if source_state not in LOCAL_WORKTREE_STATES:
        raise RuntimeError(
            f"{clean(candidate.get('combined_candidate_id'))} has no Git blob SHA and "
            f"is not a supported discovery-time worktree state: {source_state or 'UNKNOWN'}"
        )

    if clean(candidate.get("coverage_origin")) == "GITHUB_REMOTE":
        raise RuntimeError(
            f"{clean(candidate.get('combined_candidate_id'))} is remote-only but has "
            "no Git blob SHA; untracked remote evidence cannot be materialized."
        )

    source_path = repo / Path(relative_path)
    if not source_path.is_file():
        raise RuntimeError(
            f"Discovery-time worktree source is missing: {source_path}"
        )

    source_bytes = source_path.read_bytes()
    expected_sha256 = clean(candidate.get("source_sha256")).lower()
    if not expected_sha256:
        raise RuntimeError(
            f"{clean(candidate.get('combined_candidate_id'))} worktree evidence has "
            "no discovery SHA-256."
        )
    actual_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"{clean(candidate.get('combined_candidate_id'))} discovery worktree bytes "
            f"changed: expected_sha256={expected_sha256} actual_sha256={actual_sha256}"
        )
    return source_bytes, "DISCOVERY_WORKTREE_BYTES", repo, ""

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize deduplicated historical-context evidence and build the private "
            "M2 context-sufficiency review workspace without assigning relationship ground truth."
        )
    )
    parser.add_argument("--private-repo", required=True)
    parser.add_argument("--git-root", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--expected-private-head", required=True)
    args = parser.parse_args()

    private_repo = Path(args.private_repo)
    git_root = Path(args.git_root)
    cache_root = Path(args.cache_root)

    if not (private_repo / ".git").is_dir():
        raise SystemExit(f"Private repository missing: {private_repo}")

    if repo_status(private_repo):
        raise SystemExit("Private repository is dirty; materialization not started.")

    private_head = run_git_text(private_repo, ["rev-parse", "HEAD"])
    if private_head != args.expected_private_head:
        raise SystemExit(
            f"Unexpected private checkpoint: expected={args.expected_private_head} "
            f"actual={private_head}"
        )

    history_root = private_repo / "adjudication-working" / "historical-context"
    pool_csv = history_root / "suitable-pool-100.csv"
    context_csv = history_root / "historical-context-candidates.csv"
    history_summary_json = history_root / "build-summary.json"
    inventory_csv = (
        private_repo
        / "source-index"
        / "comprehensive"
        / "combined-drift-evidence-candidates.csv"
    )

    output_root = private_repo / "adjudication-working" / "context-evidence"
    temp_root = private_repo / "adjudication-working" / "context-evidence.__building__"

    for required in (pool_csv, context_csv, history_summary_json, inventory_csv):
        if not required.is_file():
            raise SystemExit(f"Required input missing: {required}")

    if output_root.exists():
        raise SystemExit(f"Context-evidence output already exists: {output_root}")
    if temp_root.exists():
        raise SystemExit(
            f"Builder-owned temporary output already exists: {temp_root}; "
            "refusing implicit cleanup."
        )

    pool_rows = read_csv(pool_csv)
    context_rows = read_csv(context_csv)
    inventory_rows = read_csv(inventory_csv)
    history_summary = json.loads(history_summary_json.read_text(encoding="utf-8"))

    if len(pool_rows) != 100:
        raise SystemExit(f"Expected 100 suitable cases; found {len(pool_rows)}")
    if len({clean(row.get("combined_candidate_id")) for row in pool_rows}) != 100:
        raise SystemExit("Suitable pool candidate IDs are not unique.")
    if any(clean(row.get("ground_truth_assigned")) != "NO" for row in pool_rows):
        raise SystemExit("Suitable pool already contains relationship ground truth.")

    expected_context_rows = int(history_summary.get("context_rows", -1))
    if expected_context_rows != len(context_rows):
        raise SystemExit(
            f"Historical-context row count mismatch: summary={expected_context_rows} "
            f"csv={len(context_rows)}"
        )
    if len(context_rows) < 1:
        raise SystemExit("Historical-context index is empty.")
    if any(clean(row.get("ground_truth_assigned")) != "NO" for row in context_rows):
        raise SystemExit("Historical-context index already contains relationship ground truth.")

    pool_ids = {clean(row.get("combined_candidate_id")) for row in pool_rows}
    for row in context_rows:
        case_id = clean(row.get("case_candidate_id"))
        context_id = clean(row.get("context_candidate_id"))
        if case_id not in pool_ids:
            raise SystemExit(f"Context row references unknown suitable case: {case_id}")
        if not context_id:
            raise SystemExit("Context row is missing context_candidate_id.")
        if context_id == case_id:
            raise SystemExit(f"Context row self-references case candidate: {case_id}")

    inventory_by_id: dict[str, dict[str, str]] = {}
    for row in inventory_rows:
        cid = clean(row.get("combined_candidate_id"))
        if not cid:
            raise SystemExit("Candidate inventory contains an empty combined_candidate_id.")
        if cid in inventory_by_id:
            raise SystemExit(f"Duplicate candidate inventory ID: {cid}")
        inventory_by_id[cid] = row

    unique_context_ids = sorted(
        {clean(row.get("context_candidate_id")) for row in context_rows}
    )
    if not unique_context_ids:
        raise SystemExit("No unique context candidates were identified.")

    for cid in unique_context_ids:
        if cid not in inventory_by_id:
            raise SystemExit(f"Context candidate missing from inventory: {cid}")
        if not SAFE_ID.fullmatch(cid):
            raise SystemExit(f"Unsafe candidate ID for evidence-library path: {cid}")

    resolved_repos: dict[str, Path] = {}
    for cid in unique_context_ids:
        candidate = inventory_by_id[cid]
        repo = resolve_repo(candidate, git_root, cache_root)
        resolved_repos[str(repo)] = repo

    before_status = {
        key: repo_status(repo)
        for key, repo in resolved_repos.items()
    }

    evidence_lookup: dict[str, dict[str, str]] = {}
    library_rows: list[dict[str, Any]] = []
    materialization_modes: Counter[str] = Counter()
    unique_git_blobs: set[str] = set()

    temp_root.mkdir(parents=True, exist_ok=False)
    try:
        library_root = temp_root / "evidence-library"
        library_root.mkdir()

        total_unique = len(unique_context_ids)
        for number, cid in enumerate(unique_context_ids, start=1):
            candidate = inventory_by_id[cid]
            source_bytes, mode, repo, blob_sha = materialize_candidate(
                candidate,
                git_root,
                cache_root,
            )

            try:
                source_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise RuntimeError(
                    f"{cid} historical evidence is not valid UTF-8 Markdown: {exc}"
                ) from exc

            materialized_sha256 = hashlib.sha256(source_bytes).hexdigest()
            candidate_dir = library_root / cid
            candidate_dir.mkdir()

            evidence_file = candidate_dir / "source-record.md"
            evidence_file.write_bytes(source_bytes)
            if hashlib.sha256(evidence_file.read_bytes()).hexdigest() != materialized_sha256:
                raise RuntimeError(f"{cid} materialized evidence hash verification failed.")

            manifest = {
                "candidate_id": cid,
                "materialization_mode": mode,
                "materialized_sha256": materialized_sha256,
                "source": {
                    "repository": clean(candidate.get("source_repository")),
                    "source_state": clean(candidate.get("source_state")),
                    "coverage_origin": clean(candidate.get("coverage_origin")),
                    "relative_path": clean(candidate.get("source_relative_path")),
                    "commit": clean(candidate.get("source_commit")),
                    "git_blob_sha": clean(candidate.get("source_git_blob_sha")).lower(),
                    "discovery_source_sha256": clean(candidate.get("source_sha256")).lower(),
                    "source_model": clean(candidate.get("source_model"), "UNKNOWN"),
                    "template_family": clean(candidate.get("template_family"), "UNKNOWN"),
                    "title": clean(candidate.get("title")),
                    "drift_id_raw": clean(candidate.get("drift_id_raw")),
                },
                "ground_truth_assigned": False,
            }
            (candidate_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            relative_evidence = (
                Path("evidence-library") / cid / "source-record.md"
            ).as_posix()
            evidence_lookup[cid] = {
                "relative_path": relative_evidence,
                "sha256": materialized_sha256,
                "mode": mode,
            }
            materialization_modes[mode] += 1
            if blob_sha:
                unique_git_blobs.add(blob_sha)

            library_rows.append({
                "context_candidate_id": cid,
                "source_repository": clean(candidate.get("source_repository")),
                "source_relative_path": clean(candidate.get("source_relative_path")),
                "source_state": clean(candidate.get("source_state")),
                "coverage_origin": clean(candidate.get("coverage_origin")),
                "source_model": clean(candidate.get("source_model"), "UNKNOWN"),
                "template_family": clean(candidate.get("template_family"), "UNKNOWN"),
                "source_git_blob_sha": clean(candidate.get("source_git_blob_sha")).lower(),
                "discovery_source_sha256": clean(candidate.get("source_sha256")).lower(),
                "materialized_sha256": materialized_sha256,
                "materialization_mode": mode,
                "evidence_relative_path": relative_evidence,
                "ground_truth_assigned": "NO",
            })

            if number == 1 or number % 100 == 0 or number == total_unique:
                print(f"MaterializedContextEvidence={number}/{total_unique}")

        map_rows: list[dict[str, Any]] = []
        case_counts: Counter[str] = Counter()
        for row in context_rows:
            context_id = clean(row.get("context_candidate_id"))
            evidence = evidence_lookup[context_id]
            case_id = clean(row.get("case_candidate_id"))
            case_counts[case_id] += 1
            map_rows.append({
                **row,
                "materialized_evidence_relative_path": evidence["relative_path"],
                "materialized_evidence_sha256": evidence["sha256"],
                "materialization_mode": evidence["mode"],
            })

        review_rows: list[dict[str, Any]] = []
        for row in pool_rows:
            case_id = clean(row.get("combined_candidate_id"))
            count = case_counts.get(case_id, 0)
            if count < 1:
                raise RuntimeError(
                    f"Suitable case has no materialized context candidates: {case_id}"
                )
            review_rows.append({
                "case_index": clean(row.get("case_index")),
                "pool_origin": clean(row.get("pool_origin")),
                "packet_id": clean(row.get("packet_id")),
                "combined_candidate_id": case_id,
                "source_repository": clean(row.get("source_repository")),
                "source_relative_path": clean(row.get("source_relative_path")),
                "source_model": clean(row.get("source_model"), "UNKNOWN"),
                "template_family": clean(row.get("template_family"), "UNKNOWN"),
                "observation_evidence_path": clean(row.get("evidence_path")),
                "retrieved_context_candidates": count,
                "context_sufficiency": "NOT_REVIEWED",
                "reviewer_notes": "",
                "ground_truth_assigned": "NO",
            })

        write_csv(
            temp_root / "evidence-library-index.csv",
            library_rows,
            [
                "context_candidate_id",
                "source_repository",
                "source_relative_path",
                "source_state",
                "coverage_origin",
                "source_model",
                "template_family",
                "source_git_blob_sha",
                "discovery_source_sha256",
                "materialized_sha256",
                "materialization_mode",
                "evidence_relative_path",
                "ground_truth_assigned",
            ],
        )

        map_fields = list(context_rows[0].keys()) + [
            "materialized_evidence_relative_path",
            "materialized_evidence_sha256",
            "materialization_mode",
        ]
        write_csv(
            temp_root / "case-context-map.csv",
            map_rows,
            map_fields,
        )

        write_csv(
            temp_root / "context-sufficiency-review.csv",
            review_rows,
            [
                "case_index",
                "pool_origin",
                "packet_id",
                "combined_candidate_id",
                "source_repository",
                "source_relative_path",
                "source_model",
                "template_family",
                "observation_evidence_path",
                "retrieved_context_candidates",
                "context_sufficiency",
                "reviewer_notes",
                "ground_truth_assigned",
            ],
        )

        after_status = {
            key: repo_status(repo)
            for key, repo in resolved_repos.items()
        }
        modified_sources = [
            key for key in before_status
            if before_status[key] != after_status[key]
        ]
        if modified_sources:
            raise RuntimeError(
                "Source repository integrity failure during evidence materialization: "
                + ", ".join(modified_sources)
            )

        summary = {
            "schema_version": 1,
            "private_checkpoint": private_head,
            "suitable_cases": 100,
            "context_rows": len(context_rows),
            "unique_context_candidates": len(unique_context_ids),
            "unique_git_blobs": len(unique_git_blobs),
            "git_blob_materializations": materialization_modes.get("GIT_BLOB", 0),
            "discovery_worktree_materializations": materialization_modes.get(
                "DISCOVERY_WORKTREE_BYTES", 0
            ),
            "cases_ready_for_context_sufficiency_review": len(review_rows),
            "context_sufficiency_decisions_assigned": 0,
            "ground_truth_assigned": 0,
            "source_repositories_modified": 0,
            "next_gate": (
                "Human context-sufficiency review across 100 cases. Relationship ground-truth "
                "labels remain prohibited until supplied historical evidence is reviewed."
            ),
        }
        (temp_root / "build-summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        readme = """# M2 Context Evidence and Sufficiency Review

This private workspace materializes the historical evidence referenced by the deterministic
M2 retrieval index and prepares the 100 suitable observations for human context-sufficiency
review.

## Evidence library

Each unique retrieved context candidate is materialized once under
`evidence-library/<candidate-id>/source-record.md`, with a provenance manifest beside it.
The 1,952 case-to-context retrieval rows reference that deduplicated library through
`case-context-map.csv`.

Tracked evidence is extracted by Git blob SHA and verified through `git hash-object`.
Discovery-time untracked/ignored evidence is accepted only when the current bytes still
match the preserved discovery SHA-256.

## Scientific boundary

This stage does **not** assign `NEW`, `DUPLICATE`, `RECURRENCE`,
`RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE`.

The human sufficiency gate asks only whether the supplied historical evidence is adequate
to proceed to relationship adjudication:

- `SUFFICIENT_FOR_ADJUDICATION`
- `MORE_CONTEXT_REQUIRED`

Similarity and retrieval rank remain context-retrieval aids, not ground truth.

## Outputs

- `evidence-library/` — deduplicated exact evidence copies plus provenance manifests;
- `evidence-library-index.csv` — evidence-library provenance and hashes;
- `case-context-map.csv` — all case-to-context retrieval links;
- `context-sufficiency-review.csv` — 100-case human review worklist;
- `build-summary.json` — materialization and integrity counts.
"""
        (temp_root / "README.md").write_text(
            readme,
            encoding="utf-8",
            newline="\n",
        )

        temp_root.rename(output_root)

    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise

    final_status = repo_status(private_repo)
    records = [record for record in final_status.split(b"\x00") if record]
    expected_prefix = b"?? adjudication-working/context-evidence/"
    unexpected = [
        record.decode("utf-8", errors="replace")
        for record in records
        if not record.startswith(expected_prefix)
    ]
    if unexpected:
        raise SystemExit(
            "Unexpected private-repository changes after materialization: "
            + " | ".join(unexpected)
        )

    print("M2_CONTEXT_EVIDENCE_MATERIALIZATION=SUCCESS")
    print("SuitableCases=100")
    print(f"ContextRows={len(context_rows)}")
    print(f"UniqueContextCandidates={len(unique_context_ids)}")
    print(f"UniqueGitBlobs={len(unique_git_blobs)}")
    print(f"GitBlobMaterializations={materialization_modes.get('GIT_BLOB', 0)}")
    print(
        "DiscoveryWorktreeMaterializations="
        f"{materialization_modes.get('DISCOVERY_WORKTREE_BYTES', 0)}"
    )
    print("CasesReadyForContextSufficiencyReview=100")
    print("ContextSufficiencyDecisionsAssigned=0")
    print("GroundTruthAssigned=0")
    print("SourceRepositoriesModified=0")
    print(f"Output={output_root}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
