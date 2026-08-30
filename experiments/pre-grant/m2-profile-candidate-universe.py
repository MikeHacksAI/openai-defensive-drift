#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED_COLUMNS = {
    "combined_candidate_id",
    "source_state",
    "coverage_origin",
    "source_repository",
    "source_model",
    "template_family",
    "discovery_score",
    "severity_raw",
    "recurrence_raw",
    "source_git_blob_sha",
    "source_sha256",
    "drift_id_raw",
}


def clean(value: str | None, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def normalized_score(value: str | None) -> str:
    value = (value or "").strip()
    try:
        return str(int(float(value)))
    except ValueError:
        return "UNKNOWN"


def write_counter_csv(path: Path, key_name: str, counter: Counter[str]) -> None:
    rows = sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold()))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow([key_name, "candidate_count"])
        writer.writerows(rows)


def markdown_table(counter: Counter[str], limit: int = 20) -> list[str]:
    rows = sorted(counter.items(), key=lambda item: (-item[1], item[0].casefold()))[:limit]
    lines = ["| Value | Candidates |", "|---|---:|"]
    for key, count in rows:
        safe = key.replace("|", "\\|")
        lines.append(f"| {safe} | {count} |")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile the Defensive Drift M2 candidate universe without assigning ground truth."
    )
    parser.add_argument("--private-repo", required=True, help="Path to openai-defensive-drift-private")
    parser.add_argument("--expected-candidates", type=int, default=1914)
    args = parser.parse_args()

    private_repo = Path(args.private_repo)
    input_csv = private_repo / "source-index" / "comprehensive" / "combined-drift-evidence-candidates.csv"
    output_dir = private_repo / "adjudication-working" / "candidate-profile"

    if not input_csv.is_file():
        raise SystemExit(f"Input candidate inventory not found: {input_csv}")

    with input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise SystemExit(f"Candidate inventory missing required columns: {', '.join(missing)}")
        rows = list(reader)

    if len(rows) != args.expected_candidates:
        raise SystemExit(
            f"Candidate count mismatch: expected {args.expected_candidates}, found {len(rows)}"
        )

    candidate_ids = [clean(row.get("combined_candidate_id"), "") for row in rows]
    if any(not cid for cid in candidate_ids):
        raise SystemExit("At least one candidate is missing combined_candidate_id")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise SystemExit("Duplicate combined_candidate_id values detected")

    counters: dict[str, Counter[str]] = {
        "repository": Counter(clean(row.get("source_repository")) for row in rows),
        "model": Counter(clean(row.get("source_model")) for row in rows),
        "template": Counter(clean(row.get("template_family")) for row in rows),
        "source_state": Counter(clean(row.get("source_state")) for row in rows),
        "coverage_origin": Counter(clean(row.get("coverage_origin")) for row in rows),
        "severity": Counter(clean(row.get("severity_raw")) for row in rows),
        "recurrence": Counter(clean(row.get("recurrence_raw")) for row in rows),
        "discovery_score": Counter(normalized_score(row.get("discovery_score")) for row in rows),
    }

    explicit_drift_ids = sum(1 for row in rows if clean(row.get("drift_id_raw"), "") != "")
    explicit_severity = sum(1 for row in rows if clean(row.get("severity_raw"), "") != "")
    explicit_recurrence = sum(1 for row in rows if clean(row.get("recurrence_raw"), "") != "")
    known_models = sum(1 for row in rows if clean(row.get("source_model")) != "UNKNOWN")

    duplicate_identity: defaultdict[str, list[str]] = defaultdict(list)
    for row in rows:
        blob = clean(row.get("source_git_blob_sha"), "")
        sha256 = clean(row.get("source_sha256"), "")
        if blob:
            identity = f"git_blob:{blob.lower()}"
        elif sha256:
            identity = f"sha256:{sha256.lower()}"
        else:
            continue
        duplicate_identity[identity].append(clean(row.get("combined_candidate_id"), ""))

    duplicate_groups = [
        (identity, ids) for identity, ids in duplicate_identity.items() if len(ids) > 1
    ]
    duplicate_groups.sort(key=lambda item: (-len(item[1]), item[0]))
    duplicate_candidate_memberships = sum(len(ids) for _, ids in duplicate_groups)

    output_dir.mkdir(parents=True, exist_ok=True)

    write_counter_csv(output_dir / "by-repository.csv", "source_repository", counters["repository"])
    write_counter_csv(output_dir / "by-model.csv", "source_model", counters["model"])
    write_counter_csv(output_dir / "by-template-family.csv", "template_family", counters["template"])
    write_counter_csv(output_dir / "by-source-state.csv", "source_state", counters["source_state"])
    write_counter_csv(output_dir / "by-coverage-origin.csv", "coverage_origin", counters["coverage_origin"])
    write_counter_csv(output_dir / "by-severity.csv", "severity_raw", counters["severity"])
    write_counter_csv(output_dir / "by-recurrence.csv", "recurrence_raw", counters["recurrence"])
    write_counter_csv(
        output_dir / "by-discovery-score.csv", "discovery_score", counters["discovery_score"]
    )

    with (output_dir / "exact-content-duplicate-groups.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["content_identity", "member_count", "candidate_ids"])
        for identity, ids in duplicate_groups:
            writer.writerow([identity, len(ids), ";".join(ids)])

    generated = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# M2 Candidate-Universe Profile",
        "",
        f"Generated: {generated}",
        "",
        "## Scope",
        "",
        "This profile summarizes the completed M2 discovery-candidate universe. It does not assign benchmark ground truth, remove records, or decide which records become benchmark cases.",
        "",
        "## Integrity checks",
        "",
        f"- Candidate records: **{len(rows)}**",
        f"- Unique `combined_candidate_id` values: **{len(set(candidate_ids))}**",
        f"- Candidates with explicit Drift ID: **{explicit_drift_ids}**",
        f"- Candidates with explicit severity: **{explicit_severity}**",
        f"- Candidates with explicit recurrence metadata: **{explicit_recurrence}**",
        f"- Candidates with non-UNKNOWN model provenance: **{known_models}**",
        f"- Exact-content identity groups with more than one candidate: **{len(duplicate_groups)}**",
        f"- Candidate memberships inside exact-content duplicate groups: **{duplicate_candidate_memberships}**",
        "",
        "Exact-content groups are relationship hints only. No candidate is deleted or automatically labeled `DUPLICATE` because content identity alone does not establish incident relationship ground truth.",
        "",
        "## Top source repositories",
        "",
        *markdown_table(counters["repository"]),
        "",
        "## Source-model provenance",
        "",
        *markdown_table(counters["model"]),
        "",
        "## Template families",
        "",
        *markdown_table(counters["template"]),
        "",
        "## Source states",
        "",
        *markdown_table(counters["source_state"]),
        "",
        "## Severity metadata",
        "",
        *markdown_table(counters["severity"]),
        "",
        "## Recurrence metadata",
        "",
        *markdown_table(counters["recurrence"]),
        "",
        "## Discovery scores",
        "",
        *markdown_table(counters["discovery_score"]),
        "",
        "## Next step",
        "",
        "Use these distributions to construct a diverse human-review queue. Queue construction may use provenance, metadata completeness, discovery score, exact-content groups, source/model diversity, and explicit relationship hints for prioritization, but it must not assign final `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE` labels automatically.",
        "",
    ]
    (output_dir / "candidate-profile-summary.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )

    print("M2 candidate-universe profile complete")
    print(f"Candidates={len(rows)}")
    print(f"Repositories={len(counters['repository'])}")
    print(f"Models={len(counters['model'])}")
    print(f"TemplateFamilies={len(counters['template'])}")
    print(f"ExactContentDuplicateGroups={len(duplicate_groups)}")
    print(f"ExactContentDuplicateMemberships={duplicate_candidate_memberships}")
    print(f"OutputDirectory={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
