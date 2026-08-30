#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED_COLUMNS = {
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
}

SEED = "defensive-drift-m2-review-queue-v1"


def clean(value: str | None, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def stable_key(candidate_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{candidate_id}".encode("utf-8")).hexdigest()


def score_band(value: str | None) -> str:
    try:
        score = int(float((value or "").strip()))
    except ValueError:
        return "UNKNOWN"
    if score <= 5:
        return "3-5"
    if score <= 8:
        return "6-8"
    if score <= 12:
        return "9-12"
    return "13+"


def load_duplicate_groups(path: Path) -> tuple[dict[str, tuple[str, int]], dict[str, list[str]]]:
    candidate_to_group: dict[str, tuple[str, int]] = {}
    group_members: dict[str, list[str]] = {}
    if not path.is_file():
        return candidate_to_group, group_members
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gid = clean(row.get("content_identity"), "")
            ids = [x for x in clean(row.get("candidate_ids"), "").split(";") if x]
            if not gid or len(ids) < 2:
                continue
            group_members[gid] = ids
            for cid in ids:
                candidate_to_group[cid] = (gid, len(ids))
    return candidate_to_group, group_members


def markdown_counter(counter: Counter[str], limit: int = 30) -> list[str]:
    lines = ["| Value | Selected |", "|---|---:|"]
    for value, count in sorted(counter.items(), key=lambda x: (-x[1], x[0].casefold()))[:limit]:
        lines.append(f"| {value.replace('|', r'\|')} | {count} |")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a stratified human-adjudication review queue without assigning ground truth."
    )
    parser.add_argument("--private-repo", required=True)
    parser.add_argument("--expected-candidates", type=int, default=1914)
    parser.add_argument("--target", type=int, default=150)
    parser.add_argument("--core", type=int, default=100)
    args = parser.parse_args()

    if args.core > args.target:
        raise SystemExit("--core cannot exceed --target")

    private_repo = Path(args.private_repo)
    inventory = private_repo / "source-index" / "comprehensive" / "combined-drift-evidence-candidates.csv"
    profile_dir = private_repo / "adjudication-working" / "candidate-profile"
    dup_csv = profile_dir / "exact-content-duplicate-groups.csv"
    outdir = private_repo / "adjudication-working" / "review-queue"

    if not inventory.is_file():
        raise SystemExit(f"Candidate inventory not found: {inventory}")
    if not dup_csv.is_file():
        raise SystemExit(f"Duplicate-group profile not found: {dup_csv}")

    with inventory.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise SystemExit(f"Inventory missing columns: {', '.join(missing)}")
        rows = list(reader)

    if len(rows) != args.expected_candidates:
        raise SystemExit(f"Candidate count mismatch: expected {args.expected_candidates}, found {len(rows)}")

    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        cid = clean(row.get("combined_candidate_id"), "")
        if not cid:
            raise SystemExit("Candidate missing combined_candidate_id")
        if cid in by_id:
            raise SystemExit(f"Duplicate candidate id: {cid}")
        by_id[cid] = row

    candidate_group, group_members = load_duplicate_groups(dup_csv)

    population_repo = Counter(clean(row.get("source_repository")) for row in rows)
    population_model = Counter(clean(row.get("source_model")) for row in rows)
    population_template = Counter(clean(row.get("template_family")) for row in rows)
    dominant_repo = population_repo.most_common(1)[0][0]

    selected: list[str] = []
    selected_set: set[str] = set()
    reasons: defaultdict[str, set[str]] = defaultdict(set)
    selected_group_counts: Counter[str] = Counter()

    def can_select(cid: str) -> bool:
        if cid in selected_set:
            return False
        group = candidate_group.get(cid)
        if group and selected_group_counts[group[0]] >= 2:
            return False
        return True

    def add(cid: str, reason: str) -> bool:
        if len(selected) >= args.target or not can_select(cid):
            return False
        selected.append(cid)
        selected_set.add(cid)
        reasons[cid].add(reason)
        group = candidate_group.get(cid)
        if group:
            selected_group_counts[group[0]] += 1
        return True

    def rarity_sort(candidates: list[str]) -> list[str]:
        def key(cid: str) -> tuple[float, str]:
            row = by_id[cid]
            repo = clean(row.get("source_repository"))
            model = clean(row.get("source_model"))
            template = clean(row.get("template_family"))
            recurrence = clean(row.get("recurrence_raw"), "")
            severity = clean(row.get("severity_raw"), "")
            drift_id = clean(row.get("drift_id_raw"), "")
            score = 0.0
            score += 12.0 / population_repo[repo]
            score += 8.0 / population_model[model]
            score += 6.0 / population_template[template]
            score += 1.5 if recurrence else 0.0
            score += 0.8 if severity else 0.0
            score += 0.8 if drift_id else 0.0
            score += 0.5 if cid in candidate_group else 0.0
            return (-score, stable_key(cid))

        return sorted(candidates, key=key)

    # Phase 1: deliberately oversample candidates outside the dominant repository.
    non_dominant = [
        cid
        for cid, row in by_id.items()
        if clean(row.get("source_repository")) != dominant_repo
    ]
    for cid in rarity_sort(non_dominant):
        add(cid, "cross_repository_coverage")

    # Phase 2: ensure minimum source-model representation.
    model_minima: dict[str, int] = {}
    for model, count in population_model.items():
        if count <= 10:
            model_minima[model] = count
        elif count <= 100:
            model_minima[model] = min(15, count)
        else:
            model_minima[model] = min(20, count)

    def selected_count(field: str, value: str) -> int:
        return sum(1 for cid in selected if clean(by_id[cid].get(field)) == value)

    for model in sorted(model_minima, key=lambda value: (population_model[value], value.casefold())):
        need = model_minima[model] - selected_count("source_model", model)
        if need <= 0:
            continue
        pool = [
            cid
            for cid, row in by_id.items()
            if clean(row.get("source_model")) == model and can_select(cid)
        ]
        for cid in rarity_sort(pool)[:need]:
            add(cid, f"model_minimum:{model}")

    # Phase 3: ensure template-family representation.
    template_minima: dict[str, int] = {}
    for template, count in population_template.items():
        if count <= 10:
            template_minima[template] = count
        elif count <= 100:
            template_minima[template] = min(12, count)
        else:
            template_minima[template] = min(18, count)

    for template in sorted(
        template_minima,
        key=lambda value: (population_template[value], value.casefold()),
    ):
        need = template_minima[template] - selected_count("template_family", template)
        if need <= 0:
            continue
        pool = [
            cid
            for cid, row in by_id.items()
            if clean(row.get("template_family")) == template and can_select(cid)
        ]
        for cid in rarity_sort(pool)[:need]:
            add(cid, f"template_minimum:{template}")

    # Phase 4: prioritize explicit recurrence metadata without treating it as ground truth.
    recurrence_available = sum(
        1 for row in rows if clean(row.get("recurrence_raw"), "") != ""
    )
    recurrence_target = min(30, recurrence_available)
    current_recurrence = sum(
        1
        for cid in selected
        if clean(by_id[cid].get("recurrence_raw"), "") != ""
    )
    pool = [
        cid
        for cid, row in by_id.items()
        if clean(row.get("recurrence_raw"), "") != "" and can_select(cid)
    ]
    for cid in rarity_sort(pool)[: max(0, recurrence_target - current_recurrence)]:
        add(cid, "explicit_recurrence_metadata")

    # Phase 5: fill remaining slots with a greedy diversity score.
    selected_repo = Counter(clean(by_id[cid].get("source_repository")) for cid in selected)
    selected_model = Counter(clean(by_id[cid].get("source_model")) for cid in selected)
    selected_template = Counter(clean(by_id[cid].get("template_family")) for cid in selected)
    selected_band = Counter(score_band(by_id[cid].get("discovery_score")) for cid in selected)

    while len(selected) < args.target:
        best_cid: str | None = None
        best_tuple: tuple[float, str] | None = None
        for cid, row in by_id.items():
            if not can_select(cid):
                continue
            repo = clean(row.get("source_repository"))
            model = clean(row.get("source_model"))
            template = clean(row.get("template_family"))
            band = score_band(row.get("discovery_score"))
            recurrence = clean(row.get("recurrence_raw"), "")
            severity = clean(row.get("severity_raw"), "")
            drift_id = clean(row.get("drift_id_raw"), "")
            group = candidate_group.get(cid)
            diversity = (
                12.0 / (1 + selected_repo[repo])
                + 8.0 / (1 + selected_model[model])
                + 6.0 / (1 + selected_template[template])
                + 3.0 / (1 + selected_band[band])
                + (2.0 if recurrence else 0.0)
                + (1.0 if severity else 0.0)
                + (1.0 if drift_id else 0.0)
                + (0.8 if group and selected_group_counts[group[0]] == 0 else 0.0)
            )
            candidate_tuple = (diversity, stable_key(cid))
            if best_tuple is None or candidate_tuple > best_tuple:
                best_tuple = candidate_tuple
                best_cid = cid

        if best_cid is None:
            break

        add(best_cid, "greedy_diversity_fill")
        row = by_id[best_cid]
        selected_repo[clean(row.get("source_repository"))] += 1
        selected_model[clean(row.get("source_model"))] += 1
        selected_template[clean(row.get("template_family"))] += 1
        selected_band[score_band(row.get("discovery_score"))] += 1

    if len(selected) != args.target:
        raise SystemExit(
            f"Unable to construct requested queue of {args.target}; selected {len(selected)}"
        )

    outdir.mkdir(parents=True, exist_ok=True)

    queue_fields = [
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
        "adjudication_status",
        "relationship_label",
        "remediation_state",
        "adjudicator_confidence",
        "evidence_notes",
    ]

    with (outdir / "review-queue.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=queue_fields, lineterminator="\n")
        writer.writeheader()
        for index, cid in enumerate(selected, start=1):
            row = by_id[cid]
            group_id, group_size = candidate_group.get(cid, ("", 0))
            writer.writerow(
                {
                    "review_rank": index,
                    "review_tier": "CORE_100" if index <= args.core else "EXPANSION_RESERVE",
                    "combined_candidate_id": cid,
                    "source_repository": clean(row.get("source_repository")),
                    "source_model": clean(row.get("source_model")),
                    "template_family": clean(row.get("template_family")),
                    "discovery_score": clean(row.get("discovery_score"), ""),
                    "severity_raw": clean(row.get("severity_raw"), ""),
                    "recurrence_raw": clean(row.get("recurrence_raw"), ""),
                    "drift_id_raw": clean(row.get("drift_id_raw"), ""),
                    "source_relative_path": clean(row.get("source_relative_path"), ""),
                    "title": clean(row.get("title"), ""),
                    "exact_content_group_id": group_id,
                    "exact_content_group_size": group_size if group_id else "",
                    "selection_reasons": ";".join(sorted(reasons[cid])),
                    "adjudication_status": "NOT_STARTED",
                    "relationship_label": "",
                    "remediation_state": "",
                    "adjudicator_confidence": "",
                    "evidence_notes": "",
                }
            )

    selected_repo = Counter(clean(by_id[cid].get("source_repository")) for cid in selected)
    selected_model = Counter(clean(by_id[cid].get("source_model")) for cid in selected)
    selected_template = Counter(clean(by_id[cid].get("template_family")) for cid in selected)
    selected_recurrence = sum(
        1 for cid in selected if clean(by_id[cid].get("recurrence_raw"), "") != ""
    )
    selected_severity = sum(
        1 for cid in selected if clean(by_id[cid].get("severity_raw"), "") != ""
    )
    selected_drift_ids = sum(
        1 for cid in selected if clean(by_id[cid].get("drift_id_raw"), "") != ""
    )
    exact_group_members = sum(1 for cid in selected if cid in candidate_group)
    paired_groups = sum(1 for count in selected_group_counts.values() if count >= 2)

    with (outdir / "selection-audit.csv").open("w", encoding="utf-8", newline="") as f:
        fields = [
            "combined_candidate_id",
            "selected",
            "review_rank",
            "review_tier",
            "source_repository",
            "source_model",
            "template_family",
            "discovery_score",
            "exact_content_group_id",
            "exact_content_group_size",
            "selection_reasons",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        rank_by_id = {cid: index for index, cid in enumerate(selected, start=1)}
        for cid in sorted(by_id, key=stable_key):
            row = by_id[cid]
            group_id, group_size = candidate_group.get(cid, ("", 0))
            rank = rank_by_id.get(cid, "")
            writer.writerow(
                {
                    "combined_candidate_id": cid,
                    "selected": "YES" if cid in selected_set else "NO",
                    "review_rank": rank,
                    "review_tier": (
                        "CORE_100"
                        if rank and int(rank) <= args.core
                        else "EXPANSION_RESERVE"
                        if rank
                        else ""
                    ),
                    "source_repository": clean(row.get("source_repository")),
                    "source_model": clean(row.get("source_model")),
                    "template_family": clean(row.get("template_family")),
                    "discovery_score": clean(row.get("discovery_score"), ""),
                    "exact_content_group_id": group_id,
                    "exact_content_group_size": group_size if group_id else "",
                    "selection_reasons": (
                        ";".join(sorted(reasons[cid])) if cid in selected_set else ""
                    ),
                }
            )

    with (outdir / "queue-summary.md").open("w", encoding="utf-8", newline="\n") as f:
        lines = [
            "# M2 Stratified Human-Adjudication Review Queue",
            "",
            f"- Candidate universe: **{len(rows)}**",
            f"- Queue size: **{len(selected)}**",
            f"- Core review tier: **{args.core}**",
            f"- Expansion reserve: **{args.target - args.core}**",
            f"- Dominant source repository in universe: `{dominant_repo}` ({population_repo[dominant_repo]} candidates)",
            f"- Non-dominant repositories represented in queue: **{sum(1 for repo in selected_repo if repo != dominant_repo)}**",
            f"- Selected candidates with explicit recurrence metadata: **{selected_recurrence}**",
            f"- Selected candidates with explicit severity metadata: **{selected_severity}**",
            f"- Selected candidates with explicit Drift ID: **{selected_drift_ids}**",
            f"- Selected candidates belonging to exact-content groups: **{exact_group_members}**",
            f"- Exact-content groups represented by two queue members: **{paired_groups}**",
            "",
            "## Selection policy",
            "",
            "This is a stratified evaluation-review queue, not a prevalence sample. Cross-repository and rare-provenance candidates are intentionally oversampled so the benchmark is not dominated by the largest source repository.",
            "",
            "No queue rule assigns `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE`. Exact-content groups are context hints only and are capped at two selected members per group.",
            "",
            f"The first {args.core} entries form the core adjudication tier. Entries {args.core + 1}–{args.target} are an expansion/replacement reserve for unusable cases, class-balance correction after human adjudication, and the planned 150–200 case expansion path.",
            "",
            "## Repository representation",
            "",
            *markdown_counter(selected_repo),
            "",
            "## Model representation",
            "",
            *markdown_counter(selected_model),
            "",
            "## Template-family representation",
            "",
            *markdown_counter(selected_template),
            "",
            "## Human-adjudication rule",
            "",
            "The queue only prioritizes records for review. Human adjudication under `benchmark/ground-truth/ADJUDICATION-PROTOCOL.md` creates ground truth and may reject a queued record as unsuitable for a benchmark case.",
            "",
        ]
        f.write("\n".join(lines))

    with (outdir / "README.md").open("w", encoding="utf-8", newline="\n") as f:
        f.write(
            "# M2 Review Queue\n\n"
            "`review-queue.csv` is the ordered human-adjudication worklist. "
            "`selection-audit.csv` records which discovery candidates were selected and why. "
            "`queue-summary.md` documents the stratification policy and resulting coverage.\n\n"
            "Blank adjudication fields are intentional. Ground truth must be entered only through the human adjudication workflow.\n"
        )

    print("M2 stratified review queue complete")
    print(f"CandidateUniverse={len(rows)}")
    print(f"QueueSize={len(selected)}")
    print(f"CoreTier={args.core}")
    print(f"ExpansionReserve={args.target - args.core}")
    print(f"RepositoriesSelected={len(selected_repo)}")
    print(f"ModelsSelected={len(selected_model)}")
    print(f"TemplatesSelected={len(selected_template)}")
    print(f"ExplicitRecurrenceSelected={selected_recurrence}")
    print(f"ExactContentPairGroups={paired_groups}")
    print("GroundTruthAssigned=0")
    print(f"OutputDirectory={outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
