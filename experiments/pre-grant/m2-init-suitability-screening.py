#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path

EXPECTED_PACKET_FIELDS = {
    "packet_id",
    "review_rank",
    "combined_candidate_id",
    "source_repository",
    "source_relative_path",
    "source_model",
    "template_family",
    "record_suitability",
    "ground_truth_assigned",
}


def clean(value: object, default: str = "") -> str:
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def artifact_hint(path: str, title: str) -> tuple[str, str]:
    normalized = path.replace("\\", "/").lower()
    name = Path(normalized).name
    title_lower = title.lower()

    if "/templates/" in f"/{normalized}" or "template" in name or "template" in title_lower:
        return "TEMPLATE_PATH", "template indicator in path/title"

    if "/runbooks/" in f"/{normalized}" or "/runbook/" in f"/{normalized}":
        return "RUNBOOK_PATH", "runbook indicator in path"

    if name == "readme.md":
        return "README_PATH", "README filename"

    if (
        "/standards/" in f"/{normalized}"
        or "standard" in name
        or "policy" in name
        or "rules" in name
    ):
        return "STANDARD_POLICY_PATH", "standard/policy/rules indicator"

    if (
        "project-summary" in normalized
        or "project_requirements" in normalized
        or "project-requirements" in normalized
    ):
        return "PROJECT_DOC_PATH", "project summary/requirements indicator"

    if "checkpoint" in normalized or "handoff" in name:
        return "CHECKPOINT_HANDOFF_PATH", "checkpoint/handoff indicator"

    if "ai-chat-history/" in normalized:
        return "CHAT_HISTORY_RECORD", "AI chat-history evidence path"

    if name in {"drift-log.md", "drift_log.md"}:
        return "DRIFT_LOG_CONTAINER", "generic drift-log container filename"

    if "/incidents/" in f"/{normalized}" or re.match(
        r"^drift-\d{4}-\d{2}-\d{2}", name
    ):
        return "INCIDENT_PATH", "path resembles an individual incident record"

    return "UNKNOWN", "no deterministic artifact-type hint"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize the M2 human suitability-screening worklist without "
            "making suitability or ground-truth decisions."
        )
    )
    parser.add_argument("--private-repo", required=True)
    parser.add_argument("--expected-packets", type=int, default=100)
    args = parser.parse_args()

    private_repo = Path(args.private_repo)
    packet_root = private_repo / "adjudication-working" / "evidence-packets"
    packet_index = packet_root / "packet-index.csv"
    output_root = private_repo / "adjudication-working" / "suitability-screening"
    temp_root = private_repo / "adjudication-working" / "suitability-screening.__building__"

    if output_root.exists() or temp_root.exists():
        raise SystemExit(
            "Suitability-screening output already exists; refusing to overwrite prior human work."
        )

    if not packet_index.is_file():
        raise SystemExit(f"Packet index missing: {packet_index}")

    with packet_index.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(EXPECTED_PACKET_FIELDS - fields)
        if missing:
            raise SystemExit("Packet index missing fields: " + ", ".join(missing))
        index_rows = list(reader)

    if len(index_rows) != args.expected_packets:
        raise SystemExit(
            f"Expected {args.expected_packets} packets; found {len(index_rows)}"
        )

    prepared: list[dict[str, str | int]] = []
    hints: Counter[str] = Counter()
    seen_packet_ids: set[str] = set()
    seen_candidate_ids: set[str] = set()

    # Read-only preflight of every packet happens before any output directory is created.
    for row in sorted(
        index_rows, key=lambda item: int(clean(item.get("review_rank"), "0"))
    ):
        packet_id = clean(row.get("packet_id"))
        candidate_id = clean(row.get("combined_candidate_id"))

        if not packet_id or not candidate_id:
            raise SystemExit("Packet index contains a blank packet or candidate ID")
        if packet_id in seen_packet_ids:
            raise SystemExit(f"Duplicate packet ID: {packet_id}")
        if candidate_id in seen_candidate_ids:
            raise SystemExit(f"Duplicate candidate ID: {candidate_id}")
        seen_packet_ids.add(packet_id)
        seen_candidate_ids.add(candidate_id)

        if clean(row.get("record_suitability")) != "NOT_REVIEWED":
            raise SystemExit(
                f"{packet_id} already has a suitability decision in packet index"
            )
        if clean(row.get("ground_truth_assigned")) != "NO":
            raise SystemExit(f"{packet_id} unexpectedly has ground truth assigned")

        packet_dir = packet_root / packet_id
        manifest_path = packet_dir / "packet-manifest.json"
        source_path = packet_dir / "source-record.md"
        notes_path = packet_dir / "adjudication-notes.md"

        for required in (manifest_path, source_path, notes_path):
            if not required.is_file():
                raise SystemExit(f"Required packet artifact missing: {required}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        if clean(manifest.get("packet_id")) != packet_id:
            raise SystemExit(f"{packet_id} manifest packet_id mismatch")
        if clean(manifest.get("combined_candidate_id")) != candidate_id:
            raise SystemExit(f"{packet_id} manifest candidate mismatch")
        if clean(manifest.get("record_suitability")) != "NOT_REVIEWED":
            raise SystemExit(
                f"{packet_id} manifest already contains a suitability decision"
            )
        if manifest.get("ground_truth_assigned") is not False:
            raise SystemExit(f"{packet_id} manifest unexpectedly contains ground truth")

        discovery = manifest.get("discovery_metadata") or {}
        source = manifest.get("source") or {}
        title = clean(discovery.get("title"))
        relative_path = clean(
            source.get("relative_path"), clean(row.get("source_relative_path"))
        )

        hint, hint_basis = artifact_hint(relative_path, title)
        hints[hint] += 1

        source_bytes = source_path.read_bytes()
        try:
            source_text = source_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SystemExit(
                f"{packet_id} source-record.md is not valid UTF-8: {exc}"
            ) from exc

        first_heading = ""
        for line in source_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                first_heading = stripped.lstrip("#").strip()
                break

        prepared.append(
            {
                "screening_rank": int(clean(row.get("review_rank"), "0")),
                "packet_id": packet_id,
                "combined_candidate_id": candidate_id,
                "source_repository": clean(row.get("source_repository")),
                "source_relative_path": relative_path,
                "source_model": clean(row.get("source_model"), "UNKNOWN"),
                "template_family": clean(row.get("template_family"), "UNKNOWN"),
                "source_bytes": len(source_bytes),
                "source_lines": len(source_text.splitlines()),
                "first_heading": first_heading,
                "exact_content_group_id": clean(row.get("exact_content_group_id")),
                "exact_content_group_size": clean(
                    row.get("exact_content_group_size"), "0"
                ),
                "artifact_hint": hint,
                "artifact_hint_basis": hint_basis,
                "screening_status": "NOT_REVIEWED",
                "record_suitability": "",
                "rejection_reason": "",
                "reviewer_notes": "",
                "reviewed_at": "",
            }
        )

    if len(prepared) != args.expected_packets:
        raise SystemExit(
            f"Prepared screening row count mismatch: expected {args.expected_packets}, "
            f"found {len(prepared)}"
        )

    temp_root.mkdir(parents=True, exist_ok=False)

    try:
        fieldnames = list(prepared[0].keys())
        with (temp_root / "screening-worklist.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fieldnames, lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(prepared)

        summary = {
            "packets": len(prepared),
            "human_suitability_decisions": 0,
            "ground_truth_assigned": 0,
            "artifact_hint_counts": dict(sorted(hints.items())),
        }
        (temp_root / "screening-summary.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        lines = [
            "# M2 Human Suitability Screening",
            "",
            f"- Packets awaiting human screening: **{len(prepared)}**",
            "- Human suitability decisions recorded: **0**",
            "- Ground truth assigned: **0**",
            "",
            "## Deterministic artifact hints",
            "",
            "Artifact hints are navigation aids only. They do not determine whether a record is suitable for the benchmark.",
            "",
            "| Hint | Packets |",
            "|---|---:|",
        ]
        for hint, count in sorted(hints.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"| {hint} | {count} |")
        lines.extend(
            [
                "",
                "## Human decision fields",
                "",
                "For each row, the human reviewer records `record_suitability` as `SUITABLE`, `UNSUITABLE`, or `NEEDS_MORE_CONTEXT` and documents any rejection reason or notes. No relationship ground truth is assigned at this stage.",
                "",
            ]
        )
        (temp_root / "screening-summary.md").write_text(
            "\n".join(lines), encoding="utf-8", newline="\n"
        )

        (temp_root / "README.md").write_text(
            "# Suitability Screening\n\n"
            "`screening-worklist.csv` is the 100-packet human screening worklist. "
            "Deterministic artifact hints help navigation but never make suitability or ground-truth decisions.\n\n"
            "Allowed human suitability values: `SUITABLE`, `UNSUITABLE`, `NEEDS_MORE_CONTEXT`.\n\n"
            "Suggested rejection reasons: `TEMPLATE_OR_BLANK_FORM`, `RUNBOOK_OR_POLICY`, "
            "`PROJECT_ADMIN_DOC`, `DUPLICATE_ARTIFACT_NOT_OBSERVATION`, `INCOMPLETE_FRAGMENT`, "
            "`NOT_SECURITY_RELEVANT`, `OTHER`.\n",
            encoding="utf-8",
            newline="\n",
        )

        os.replace(temp_root, output_root)
    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise

    print("M2 suitability-screening worklist initialized")
    print(f"Packets={len(prepared)}")
    print("HumanSuitabilityDecisions=0")
    print("GroundTruthAssigned=0")
    for hint, count in sorted(hints.items()):
        print(f"Hint[{hint}]={count}")
    print(f"OutputDirectory={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
