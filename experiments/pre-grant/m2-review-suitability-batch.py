#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

REQUIRED_COLUMNS = {
    "screening_rank",
    "packet_id",
    "combined_candidate_id",
    "source_repository",
    "source_relative_path",
    "source_model",
    "template_family",
    "source_bytes",
    "source_lines",
    "first_heading",
    "exact_content_group_id",
    "exact_content_group_size",
    "artifact_hint",
    "artifact_hint_basis",
    "screening_status",
    "record_suitability",
    "rejection_reason",
    "reviewer_notes",
    "reviewed_at",
}

REJECTION_REASONS = {
    "1": "TEMPLATE_OR_SCHEMA",
    "2": "RUNBOOK_STANDARD_OR_POLICY",
    "3": "PROJECT_ADMIN_HANDOFF_OR_CHECKPOINT",
    "4": "AGGREGATE_CONTAINER_NOT_SINGLE_OBSERVATION",
    "5": "NOT_AN_INCIDENT_OR_OBSERVATION",
    "6": "MIRROR_OR_REDUNDANT_COPY",
    "7": "OTHER",
}


def clean(value: str | None) -> str:
    return "" if value is None else value.strip()


def atomic_write(path: Path, text: str) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp, path)


def write_csv_atomic(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)


def preview(text: str, lines: int) -> str:
    source_lines = text.splitlines()
    shown = source_lines[:lines]
    suffix = (
        "\n... [preview truncated; press V for full source] ..."
        if len(source_lines) > lines
        else ""
    )
    return "\n".join(shown) + suffix


def rebuild_summary(root: Path, rows: list[dict[str, str]]) -> None:
    total = len(rows)
    counts = Counter(clean(row["record_suitability"]) or "NOT_REVIEWED" for row in rows)
    reviewed = sum(
        1 for row in rows if clean(row["screening_status"]) == "REVIEWED"
    )
    remaining = total - reviewed

    summary = {
        "packets": total,
        "human_suitability_decisions": reviewed,
        "suitable": counts["SUITABLE"],
        "unsuitable": counts["UNSUITABLE"],
        "needs_more_context": counts["NEEDS_MORE_CONTEXT"],
        "remaining_not_reviewed": remaining,
        "ground_truth_assigned": 0,
    }
    atomic_write(
        root / "screening-summary.json",
        json.dumps(summary, indent=2) + "\n",
    )

    markdown = [
        "# M2 Human Suitability Screening",
        "",
        f"- Packets: **{total}**",
        f"- Human suitability decisions recorded: **{reviewed}**",
        f"- Suitable: **{counts['SUITABLE']}**",
        f"- Unsuitable: **{counts['UNSUITABLE']}**",
        f"- Needs more context: **{counts['NEEDS_MORE_CONTEXT']}**",
        f"- Remaining not reviewed: **{remaining}**",
        "- Ground truth assigned: **0**",
        "",
        "Suitability decisions are human review decisions only. They do not assign benchmark relationship ground truth.",
        "",
    ]
    atomic_write(root / "screening-summary.md", "\n".join(markdown))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactively record a resumable batch of human M2 suitability decisions."
    )
    parser.add_argument("--private-repo", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--preview-lines", type=int, default=45)
    args = parser.parse_args()

    if args.batch_size < 1 or args.batch_size > 100:
        raise SystemExit("--batch-size must be between 1 and 100")

    private_repo = Path(args.private_repo)
    screening_root = (
        private_repo / "adjudication-working" / "suitability-screening"
    )
    worklist_path = screening_root / "screening-worklist.csv"
    packet_root = private_repo / "adjudication-working" / "evidence-packets"
    decision_root = screening_root / "decision-records"

    if not worklist_path.is_file():
        raise SystemExit(f"Missing screening worklist: {worklist_path}")
    if not packet_root.is_dir():
        raise SystemExit(f"Missing evidence-packet root: {packet_root}")

    with worklist_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - set(fieldnames))
        if missing:
            raise SystemExit("Missing worklist columns: " + ", ".join(missing))
        rows = list(reader)

    if len(rows) != 100:
        raise SystemExit(f"Expected 100 screening rows, found {len(rows)}")

    decision_root.mkdir(exist_ok=True)

    # Existing decision records are an audit layer and must agree with the aggregate worklist.
    for decision_path in decision_root.glob("M2-PACKET-*.json"):
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        packet_id = clean(decision.get("packet_id"))
        matches = [row for row in rows if clean(row["packet_id"]) == packet_id]
        if len(matches) != 1:
            raise SystemExit(
                f"Decision record does not map uniquely to the worklist: {decision_path}"
            )
        row = matches[0]
        if clean(row["screening_status"]) != "REVIEWED":
            raise SystemExit(f"Decision/worklist status mismatch for {packet_id}")
        if clean(row["record_suitability"]) != clean(
            decision.get("record_suitability")
        ):
            raise SystemExit(f"Decision/worklist suitability mismatch for {packet_id}")

    pending = [
        row
        for row in sorted(rows, key=lambda item: int(item["screening_rank"]))
        if clean(row["screening_status"]) == "NOT_REVIEWED"
    ]

    if not pending:
        print("All 100 screening rows are already reviewed.")
        rebuild_summary(screening_root, rows)
        return 0

    targets = pending[: args.batch_size]
    session: list[dict[str, object]] = []

    for row in targets:
        packet_id = clean(row["packet_id"])
        source_path = packet_root / packet_id / "source-record.md"
        manifest_path = packet_root / packet_id / "packet-manifest.json"
        if not source_path.is_file() or not manifest_path.is_file():
            raise SystemExit(f"Evidence packet is incomplete: {packet_id}")

        source_text = source_path.read_text(encoding="utf-8")

        print("\n" + "=" * 88)
        print(
            f"SCREENING {row['screening_rank']}/100 — {packet_id} — "
            f"{row['combined_candidate_id']}"
        )
        print(f"Repository: {row['source_repository']}")
        print(f"Path:       {row['source_relative_path']}")
        print(f"Model:      {row['source_model']}")
        print(f"Template:   {row['template_family']}")
        print(
            f"Hint:       {row['artifact_hint']} "
            f"({row['artifact_hint_basis']})"
        )
        print(f"Heading:    {row['first_heading']}")
        print(
            "Exact group:"
            f"{row['exact_content_group_id'] or 'NONE'} "
            f"size={row['exact_content_group_size'] or '0'}"
        )
        print("-" * 88)
        print(preview(source_text, args.preview_lines))
        print("-" * 88)

        quit_requested = False
        while True:
            choice = input(
                "[S]uitable  [U]nsuitable  [M]ore-context  "
                "[V]iew-full  [D]efer  [Q]uit/save > "
            ).strip().upper()

            if choice == "V":
                print("\n" + source_text + "\n")
                continue
            if choice == "D":
                print("Deferred; no decision recorded.")
                break
            if choice == "Q":
                quit_requested = True
                break
            if choice not in {"S", "U", "M"}:
                print("Invalid choice.")
                continue

            suitability = {
                "S": "SUITABLE",
                "U": "UNSUITABLE",
                "M": "NEEDS_MORE_CONTEXT",
            }[choice]

            rejection_reason = ""
            if choice == "U":
                print("Rejection reason:")
                for key, value in REJECTION_REASONS.items():
                    print(f"  {key}. {value}")
                while True:
                    reason_choice = input("Reason [1-7] > ").strip()
                    if reason_choice not in REJECTION_REASONS:
                        print("Invalid reason.")
                        continue
                    rejection_reason = REJECTION_REASONS[reason_choice]
                    if rejection_reason == "OTHER":
                        other_reason = input("Short rejection reason > ").strip()
                        if not other_reason:
                            print("A reason is required for OTHER.")
                            continue
                        rejection_reason = "OTHER:" + other_reason
                    break

            reviewer_notes = input("Reviewer notes (optional) > ").strip()
            reviewed_at = datetime.now().astimezone().isoformat(timespec="seconds")

            row["screening_status"] = "REVIEWED"
            row["record_suitability"] = suitability
            row["rejection_reason"] = rejection_reason
            row["reviewer_notes"] = reviewer_notes
            row["reviewed_at"] = reviewed_at

            session.append(
                {
                    "packet_id": packet_id,
                    "combined_candidate_id": clean(row["combined_candidate_id"]),
                    "screening_rank": int(row["screening_rank"]),
                    "reviewer": args.reviewer,
                    "reviewed_at": reviewed_at,
                    "record_suitability": suitability,
                    "rejection_reason": rejection_reason,
                    "reviewer_notes": reviewer_notes,
                    "artifact_hint": clean(row["artifact_hint"]),
                    "source_repository": clean(row["source_repository"]),
                    "source_relative_path": clean(row["source_relative_path"]),
                    "ground_truth_assigned": False,
                }
            )
            print(f"Recorded: {suitability}")
            break

        if quit_requested:
            break

    # Validate the whole batch before materializing any new decision files.
    for decision in session:
        decision_path = decision_root / f"{decision['packet_id']}.json"
        if decision_path.exists():
            raise SystemExit(
                "Decision record already exists; refusing overwrite: "
                f"{decision_path}"
            )

    if session:
        for decision in session:
            decision_path = decision_root / f"{decision['packet_id']}.json"
            atomic_write(
                decision_path,
                json.dumps(decision, indent=2, ensure_ascii=False) + "\n",
            )
        write_csv_atomic(worklist_path, rows, fieldnames)
        rebuild_summary(screening_root, rows)

    reviewed_total = sum(
        1 for row in rows if clean(row["screening_status"]) == "REVIEWED"
    )
    remaining = 100 - reviewed_total

    print("\nM2 human suitability batch complete")
    print(f"SessionDecisions={len(session)}")
    print(f"ReviewedTotal={reviewed_total}")
    print(f"Remaining={remaining}")
    print("GroundTruthAssigned=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
