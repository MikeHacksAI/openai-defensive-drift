#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with",
    "without", "after", "before", "drift", "log", "incident", "ai", "assistant", "record",
    "records", "failure", "failed",
}
DATE_RE = re.compile(
    r"(?P<y>20\d{2})[-_](?P<m>\d{2})[-_](?P<d>\d{2})"
    r"(?:[_T -](?P<h>\d{2})[-:](?P<mi>\d{2})(?:[-:](?P<s>\d{2}))?)?"
)
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def clean(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def run_git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def load_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def tokens(*parts: str) -> set[str]:
    result: set[str] = set()
    for part in parts:
        for token in TOKEN_RE.findall(part.lower()):
            if len(token) < 3 or token in STOPWORDS or token.isdigit():
                continue
            result.add(token)
    return result


def parse_explicit_timestamp(*values: str) -> datetime | None:
    for value in values:
        match = DATE_RE.search(value)
        if not match:
            continue
        gd = match.groupdict()
        try:
            return datetime(
                int(gd["y"]), int(gd["m"]), int(gd["d"]),
                int(gd["h"] or 0), int(gd["mi"] or 0), int(gd["s"] or 0),
            )
        except ValueError:
            continue
    return None


def temporal_relation(current: datetime | None, candidate: datetime | None) -> str:
    if current is None or candidate is None:
        return "UNKNOWN"
    if candidate < current:
        return "OLDER"
    if candidate == current:
        return "SAME_TIME"
    return "NEWER"


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic metadata-only historical-context candidate index for the "
            "100 human-screened suitable M2 observations without assigning relationship ground truth."
        )
    )
    parser.add_argument("--private-repo", required=True)
    parser.add_argument("--expected-private-head", required=True)
    parser.add_argument("--context-limit", type=int, default=20)
    args = parser.parse_args()

    private_repo = Path(args.private_repo)
    if not (private_repo / ".git").is_dir():
        raise SystemExit(f"Private repository missing: {private_repo}")

    status = run_git(private_repo, ["status", "--porcelain=v1", "--untracked-files=all"])
    if status:
        raise SystemExit("Private repository is dirty; historical-context build not started.")

    head = run_git(private_repo, ["rev-parse", "HEAD"])
    if head != args.expected_private_head:
        raise SystemExit(
            f"Unexpected private checkpoint: expected={args.expected_private_head} actual={head}"
        )

    original_decisions_path = (
        private_repo / "adjudication-working" / "suitability-screening" / "excel-import"
        / "2026-08-30-completed-review-decisions.csv"
    )
    replacement_intake_path = (
        private_repo / "adjudication-working" / "replacement-review" / "intake"
        / "2026-08-31-completed-replacement-review.json"
    )
    replacement_set_path = (
        private_repo / "adjudication-working" / "replacement-review" / "replacement-review-set.csv"
    )
    inventory_path = (
        private_repo / "source-index" / "comprehensive" / "combined-drift-evidence-candidates.csv"
    )
    output_root = private_repo / "adjudication-working" / "historical-context"

    for path in (
        original_decisions_path, replacement_intake_path, replacement_set_path, inventory_path
    ):
        if not path.is_file():
            raise SystemExit(f"Required input missing: {path}")

    if output_root.exists():
        raise SystemExit(
            f"Historical-context output already exists; refusing overwrite: {output_root}"
        )

    original_rows, _ = load_csv(original_decisions_path)
    replacement_rows, _ = load_csv(replacement_set_path)
    inventory_rows, _ = load_csv(inventory_path)

    original_suitable = [
        row for row in original_rows if clean(row.get("record_suitability")) == "SUITABLE"
    ]
    if len(original_suitable) != 78:
        raise SystemExit(
            f"Expected 78 original suitable observations; found {len(original_suitable)}"
        )

    replacement_intake = json.loads(replacement_intake_path.read_text(encoding="utf-8"))
    decisions = replacement_intake.get("decisions", [])
    if len(decisions) != 22:
        raise SystemExit(f"Expected 22 replacement decisions; found {len(decisions)}")
    if any(clean(item.get("record_suitability")) != "SUITABLE" for item in decisions):
        raise SystemExit("Replacement intake contains a non-SUITABLE decision.")

    replacement_by_candidate = {
        clean(row.get("combined_candidate_id")): row for row in replacement_rows
    }
    replacement_suitable: list[dict[str, str]] = []
    for item in decisions:
        cid = clean(item.get("combined_candidate_id"))
        row = replacement_by_candidate.get(cid)
        if row is None:
            raise SystemExit(f"Replacement decision missing from review set: {cid}")
        replacement_suitable.append(row)

    pool: list[dict[str, str]] = []
    for row in original_suitable:
        pool.append({
            "pool_origin": "CORE_ORIGINAL",
            "packet_id": clean(row.get("packet_id")),
            "combined_candidate_id": clean(row.get("combined_candidate_id")),
            "source_repository": clean(row.get("source_repository")),
            "source_relative_path": clean(row.get("source_relative_path")),
            "source_model": clean(row.get("source_model"), "UNKNOWN"),
            "template_family": clean(row.get("template_family"), "UNKNOWN"),
            "evidence_path": clean(row.get("evidence_path")),
        })
    for row in replacement_suitable:
        relative = clean(row.get("evidence_relative_path")).replace("/", "\\")
        pool.append({
            "pool_origin": "REPLACEMENT",
            "packet_id": clean(row.get("packet_id")),
            "combined_candidate_id": clean(row.get("combined_candidate_id")),
            "source_repository": clean(row.get("source_repository")),
            "source_relative_path": clean(row.get("source_relative_path")),
            "source_model": clean(row.get("source_model"), "UNKNOWN"),
            "template_family": clean(row.get("template_family"), "UNKNOWN"),
            "evidence_path": str(
                private_repo / "adjudication-working" / "replacement-review" / relative
            ),
        })

    if len(pool) != 100:
        raise SystemExit(f"Expected final suitable pool of 100; found {len(pool)}")
    pool_ids = [row["combined_candidate_id"] for row in pool]
    if len(set(pool_ids)) != 100:
        raise SystemExit("Final suitable pool contains duplicate candidate IDs.")

    inventory_by_id: dict[str, dict[str, str]] = {}
    for row in inventory_rows:
        cid = clean(row.get("combined_candidate_id"))
        if not cid:
            raise SystemExit("Candidate inventory contains a blank combined_candidate_id.")
        if cid in inventory_by_id:
            raise SystemExit(f"Duplicate candidate ID in inventory: {cid}")
        inventory_by_id[cid] = row

    missing = [cid for cid in pool_ids if cid not in inventory_by_id]
    if missing:
        raise SystemExit("Suitable pool IDs missing from inventory: " + ", ".join(missing))

    prepared_inventory: list[dict[str, object]] = []
    for row in inventory_rows:
        title = clean(row.get("title"))
        path = clean(row.get("source_relative_path"))
        drift_id = clean(row.get("drift_id_raw"))
        recurrence = clean(row.get("recurrence_raw"))
        prepared_inventory.append({
            "row": row,
            "candidate_id": clean(row.get("combined_candidate_id")),
            "repository": clean(row.get("source_repository")),
            "model": clean(row.get("source_model"), "UNKNOWN"),
            "template": clean(row.get("template_family"), "UNKNOWN"),
            "drift_id": drift_id,
            "timestamp": parse_explicit_timestamp(drift_id, path, title),
            "tokens": tokens(title, path, drift_id, recurrence),
            "blob": clean(row.get("source_git_blob_sha")).lower(),
        })

    context_rows: list[dict[str, object]] = []
    case_rows: list[dict[str, object]] = []

    for case_index, pool_row in enumerate(pool, start=1):
        current_id = pool_row["combined_candidate_id"]
        current = inventory_by_id[current_id]
        current_title = clean(current.get("title"))
        current_path = clean(current.get("source_relative_path"))
        current_drift_id = clean(current.get("drift_id_raw"))
        current_recurrence = clean(current.get("recurrence_raw"))
        current_repo = clean(current.get("source_repository"))
        current_model = clean(current.get("source_model"), "UNKNOWN")
        current_template = clean(current.get("template_family"), "UNKNOWN")
        current_blob = clean(current.get("source_git_blob_sha")).lower()
        current_time = parse_explicit_timestamp(current_drift_id, current_path, current_title)
        current_tokens = tokens(
            current_title, current_path, current_drift_id, current_recurrence
        )

        scored: list[tuple[float, str, dict[str, object], str]] = []
        for item in prepared_inventory:
            candidate_id = str(item["candidate_id"])
            if candidate_id == current_id:
                continue

            relation = temporal_relation(current_time, item["timestamp"])
            if relation in {"NEWER", "SAME_TIME"}:
                continue

            score = 0.0
            reasons: list[str] = []
            candidate_blob = str(item["blob"])
            if current_blob and candidate_blob and current_blob == candidate_blob:
                score += 100.0
                reasons.append("EXACT_GIT_BLOB")

            candidate_drift_id = str(item["drift_id"])
            if (
                current_drift_id and candidate_drift_id
                and current_drift_id.lower() == candidate_drift_id.lower()
            ):
                score += 90.0
                reasons.append("SAME_DRIFT_ID_RAW")

            similarity = jaccard(current_tokens, item["tokens"])
            if similarity > 0:
                score += similarity * 40.0
                reasons.append(f"TOKEN_JACCARD={similarity:.3f}")

            if current_repo and current_repo == item["repository"]:
                score += 6.0
                reasons.append("SAME_REPOSITORY")
            if current_model and current_model == item["model"]:
                score += 2.0
                reasons.append("SAME_MODEL_GROUP")
            if current_template and current_template == item["template"]:
                score += 1.0
                reasons.append("SAME_TEMPLATE_FAMILY")

            if relation == "OLDER":
                score += 3.0
                reasons.append("EXPLICITLY_OLDER")
            else:
                reasons.append("TEMPORAL_RELATION_UNKNOWN")

            substantive = (
                "EXACT_GIT_BLOB" in reasons
                or "SAME_DRIFT_ID_RAW" in reasons
                or similarity >= 0.08
            )
            if substantive:
                scored.append((score, candidate_id, item, relation))

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = scored[: args.context_limit]

        for context_rank, (score, candidate_id, item, relation) in enumerate(
            selected, start=1
        ):
            candidate = item["row"]
            if not isinstance(candidate, dict):
                raise SystemExit("Internal candidate row type error.")
            similarity = jaccard(current_tokens, item["tokens"])
            reason_parts: list[str] = []
            candidate_blob = str(item["blob"])
            if current_blob and candidate_blob and current_blob == candidate_blob:
                reason_parts.append("EXACT_GIT_BLOB")
            candidate_drift_id = str(item["drift_id"])
            if (
                current_drift_id and candidate_drift_id
                and current_drift_id.lower() == candidate_drift_id.lower()
            ):
                reason_parts.append("SAME_DRIFT_ID_RAW")
            if similarity > 0:
                reason_parts.append(f"TOKEN_JACCARD={similarity:.3f}")
            if current_repo == item["repository"]:
                reason_parts.append("SAME_REPOSITORY")
            if current_model == item["model"]:
                reason_parts.append("SAME_MODEL_GROUP")
            if current_template == item["template"]:
                reason_parts.append("SAME_TEMPLATE_FAMILY")
            reason_parts.append(
                "EXPLICITLY_OLDER" if relation == "OLDER" else "TEMPORAL_RELATION_UNKNOWN"
            )

            context_rows.append({
                "case_index": case_index,
                "case_candidate_id": current_id,
                "case_packet_id": pool_row["packet_id"],
                "context_rank": context_rank,
                "context_candidate_id": candidate_id,
                "context_source_repository": clean(candidate.get("source_repository")),
                "context_source_relative_path": clean(candidate.get("source_relative_path")),
                "context_source_model": clean(candidate.get("source_model"), "UNKNOWN"),
                "context_template_family": clean(candidate.get("template_family"), "UNKNOWN"),
                "context_title": clean(candidate.get("title")),
                "context_drift_id_raw": clean(candidate.get("drift_id_raw")),
                "context_recurrence_raw": clean(candidate.get("recurrence_raw")),
                "context_git_blob_sha": clean(candidate.get("source_git_blob_sha")),
                "temporal_relation": relation,
                "retrieval_score": f"{score:.6f}",
                "retrieval_reasons": ";".join(reason_parts),
                "ground_truth_assigned": "NO",
            })

        case_rows.append({
            "case_index": case_index,
            "pool_origin": pool_row["pool_origin"],
            "packet_id": pool_row["packet_id"],
            "combined_candidate_id": current_id,
            "source_repository": pool_row["source_repository"],
            "source_relative_path": pool_row["source_relative_path"],
            "source_model": pool_row["source_model"],
            "template_family": pool_row["template_family"],
            "evidence_path": pool_row["evidence_path"],
            "explicit_timestamp_status": "AVAILABLE" if current_time else "UNKNOWN",
            "retrieved_context_candidates": len(selected),
            "historical_context_status": (
                "CANDIDATES_RETRIEVED" if selected else "NO_METADATA_MATCHES"
            ),
            "ground_truth_assigned": "NO",
        })

    output_root.mkdir(parents=True, exist_ok=False)

    write_csv(output_root / "suitable-pool-100.csv", case_rows, [
        "case_index", "pool_origin", "packet_id", "combined_candidate_id",
        "source_repository", "source_relative_path", "source_model", "template_family",
        "evidence_path", "explicit_timestamp_status", "retrieved_context_candidates",
        "historical_context_status", "ground_truth_assigned",
    ])
    write_csv(output_root / "historical-context-candidates.csv", context_rows, [
        "case_index", "case_candidate_id", "case_packet_id", "context_rank",
        "context_candidate_id", "context_source_repository", "context_source_relative_path",
        "context_source_model", "context_template_family", "context_title",
        "context_drift_id_raw", "context_recurrence_raw", "context_git_blob_sha",
        "temporal_relation", "retrieval_score", "retrieval_reasons", "ground_truth_assigned",
    ])

    context_counts = Counter(row["historical_context_status"] for row in case_rows)
    timestamp_counts = Counter(row["explicit_timestamp_status"] for row in case_rows)
    summary = {
        "schema_version": 1,
        "private_checkpoint": head,
        "suitable_pool": 100,
        "original_suitable": 78,
        "replacement_suitable": 22,
        "candidate_universe": len(inventory_rows),
        "context_limit_per_case": args.context_limit,
        "context_rows": len(context_rows),
        "cases_with_context_candidates": context_counts.get("CANDIDATES_RETRIEVED", 0),
        "cases_without_metadata_matches": context_counts.get("NO_METADATA_MATCHES", 0),
        "cases_with_explicit_timestamp": timestamp_counts.get("AVAILABLE", 0),
        "cases_with_unknown_timestamp": timestamp_counts.get("UNKNOWN", 0),
        "ground_truth_assigned": 0,
        "method": (
            "Deterministic metadata retrieval only: exact Git-blob identity, exact raw Drift ID, "
            "token overlap, repository/model/template affinity, and explicit timestamp ordering. "
            "Known newer/same-time candidates are not supplied as historical context. Retrieval "
            "candidates are hints only and do not establish relationship ground truth."
        ),
        "next_gate": (
            "Materialize evidence for retrieved historical candidates, human-review context "
            "sufficiency, then assign relationship/remediation/severity/dangerous-false-duplicate/"
            "confidence labels."
        ),
    }
    (output_root / "build-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    (output_root / "README.md").write_text(
        """# M2 Historical-Context Candidate Index\n\n"
        "This directory is private adjudication staging. It freezes the 100 human-screened "
        "suitable observations (78 original + 22 replacement) and creates a deterministic "
        "metadata-only retrieval index of potentially relevant historical records.\n\n"
        "## Boundary\n\n"
        "This retrieval stage does **not** assign `NEW`, `DUPLICATE`, `RECURRENCE`, "
        "`RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE`. Similarity is not ground truth.\n\n"
        "Known newer or same-time records are excluded when both timestamps can be explicitly "
        "parsed. Unknown ordering remains eligible and is marked `TEMPORAL_RELATION_UNKNOWN`.\n\n"
        "The next stage must materialize retrieved evidence and apply the frozen human "
        "adjudication protocol.\n",
        encoding="utf-8",
        newline="\n",
    )

    final_status = run_git(
        private_repo, ["status", "--porcelain=v1", "--untracked-files=all"]
    )
    unexpected = [
        line for line in final_status.splitlines()
        if line and not line.startswith("?? adjudication-working/historical-context/")
    ]
    if unexpected:
        raise SystemExit(
            "Unexpected private-repository changes after build: " + " | ".join(unexpected)
        )

    print("M2_HISTORICAL_CONTEXT_INDEX=SUCCESS")
    print("SuitablePool=100")
    print(f"CandidateUniverse={len(inventory_rows)}")
    print(f"ContextRows={len(context_rows)}")
    print(f"CasesWithContextCandidates={context_counts.get('CANDIDATES_RETRIEVED', 0)}")
    print(f"CasesWithoutMetadataMatches={context_counts.get('NO_METADATA_MATCHES', 0)}")
    print(f"CasesWithExplicitTimestamp={timestamp_counts.get('AVAILABLE', 0)}")
    print(f"CasesWithUnknownTimestamp={timestamp_counts.get('UNKNOWN', 0)}")
    print("GroundTruthAssigned=0")
    print(f"Output={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
