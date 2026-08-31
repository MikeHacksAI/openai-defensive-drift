#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

EXPECTED_PRIVATE_HEAD_DEFAULT = "f4584161d7f6ee6cbbc828afee081abd164d223c"
EXPECTED_CONTEXT_ROWS = 1952
EXPECTED_REVIEW_ROWS = 100
EXPECTED_UNIQUE_CONTEXT = 820
EXPECTED_NON_UTF8 = 2
EXPECTED_STAGED = (2 * EXPECTED_UNIQUE_CONTEXT) + 5


def run(args: list[str], *, capture: bool = True, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and proc.returncode != 0:
        detail = ""
        if capture:
            detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(args)}"
            + (f"\n{detail}" if detail else "")
        )
    return proc


def git_text(repo: Path, *args: str) -> str:
    return run(["git", "-C", str(repo), *args]).stdout.strip()


def git_bytes(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.decode("utf-8", errors="replace").strip()
            or f"git {' '.join(args)} failed"
        )
    return proc.stdout


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize the already-materialized M2 context-evidence workspace after the "
            "generic whitespace validator incorrectly rejected immutable source bytes."
        )
    )
    parser.add_argument("--private-repo", required=True)
    parser.add_argument(
        "--expected-private-head",
        default=EXPECTED_PRIVATE_HEAD_DEFAULT,
    )
    args = parser.parse_args()

    private_repo = Path(args.private_repo)
    expected_head = args.expected_private_head
    output_root = private_repo / "adjudication-working" / "context-evidence"
    temp_root = private_repo / "adjudication-working" / "context-evidence.__building__"

    print("=" * 76)
    print(" DEFENSIVE DRIFT — M2 FINALIZE MATERIALIZED CONTEXT EVIDENCE")
    print("=" * 76)

    if not (private_repo / ".git").is_dir():
        raise SystemExit(f"Private repository missing: {private_repo}")

    head = git_text(private_repo, "rev-parse", "HEAD")
    if head != expected_head:
        raise SystemExit(
            f"Unexpected private checkpoint: expected={expected_head} actual={head}"
        )

    if not output_root.is_dir():
        raise SystemExit(f"Materialized context-evidence workspace missing: {output_root}")
    if temp_root.exists():
        raise SystemExit(f"Unexpected builder temporary residue exists: {temp_root}")

    print(f"PrivateCheckpoint=PASS — {head}")

    library_path = output_root / "evidence-library-index.csv"
    map_path = output_root / "case-context-map.csv"
    review_path = output_root / "context-sufficiency-review.csv"
    summary_path = output_root / "build-summary.json"
    readme_path = output_root / "README.md"

    for required in (library_path, map_path, review_path, summary_path, readme_path):
        if not required.is_file():
            raise SystemExit(f"Required artifact missing: {required}")

    library = read_csv(library_path)
    context_rows = read_csv(map_path)
    review_rows = read_csv(review_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    if len(library) != EXPECTED_UNIQUE_CONTEXT:
        raise SystemExit(
            f"Expected {EXPECTED_UNIQUE_CONTEXT} evidence-library rows; found {len(library)}"
        )
    if len(context_rows) != EXPECTED_CONTEXT_ROWS:
        raise SystemExit(
            f"Expected {EXPECTED_CONTEXT_ROWS} case-context rows; found {len(context_rows)}"
        )
    if len(review_rows) != EXPECTED_REVIEW_ROWS:
        raise SystemExit(
            f"Expected {EXPECTED_REVIEW_ROWS} sufficiency-review rows; found {len(review_rows)}"
        )

    if int(summary.get("unique_context_candidates", -1)) != EXPECTED_UNIQUE_CONTEXT:
        raise SystemExit("Build summary unique-context count is invalid.")
    if int(summary.get("context_rows", -1)) != EXPECTED_CONTEXT_ROWS:
        raise SystemExit("Build summary context-row count is invalid.")
    if int(summary.get("suitable_cases", -1)) != EXPECTED_REVIEW_ROWS:
        raise SystemExit("Build summary suitable-case count is invalid.")
    if int(summary.get("cases_ready_for_context_sufficiency_review", -1)) != EXPECTED_REVIEW_ROWS:
        raise SystemExit("Build summary review-readiness count is invalid.")
    if int(summary.get("context_sufficiency_decisions_assigned", -1)) != 0:
        raise SystemExit("Context-sufficiency decisions were unexpectedly assigned.")
    if int(summary.get("ground_truth_assigned", -1)) != 0:
        raise SystemExit("Relationship ground truth was unexpectedly assigned.")
    if int(summary.get("source_repositories_modified", -1)) != 0:
        raise SystemExit("Source-repository integrity boundary failed.")

    if any(row.get("context_sufficiency") != "NOT_REVIEWED" for row in review_rows):
        raise SystemExit("Human context-sufficiency decisions are already present.")
    if any(row.get("ground_truth_assigned") != "NO" for row in review_rows):
        raise SystemExit("Ground truth is present in review rows.")
    if any(row.get("ground_truth_assigned") != "NO" for row in context_rows):
        raise SystemExit("Ground truth is present in case-context rows.")

    non_utf8 = 0
    for row in library:
        rel = (row.get("evidence_relative_path") or "").replace("/", "\\")
        evidence = output_root / rel
        if not evidence.is_file():
            raise SystemExit(f"Materialized evidence missing: {evidence}")
        raw = evidence.read_bytes()
        actual_hash = hashlib.sha256(raw).hexdigest()
        expected_hash = (row.get("materialized_sha256") or "").lower()
        if actual_hash != expected_hash:
            raise SystemExit(f"Materialized evidence hash mismatch: {evidence}")
        try:
            raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            non_utf8 += 1

    if non_utf8 != EXPECTED_NON_UTF8:
        raise SystemExit(
            f"Expected {EXPECTED_NON_UTF8} preserved non-UTF8 evidence records; found {non_utf8}"
        )

    print(f"EvidenceHashVerification=PASS — {len(library)}")
    print(f"NonUTF8EvidencePreserved=PASS — {non_utf8}")
    print(f"ContextRows=PASS — {len(context_rows)}")
    print(f"ReviewRows=PASS — {len(review_rows)}")
    print("GroundTruthAssigned=PASS — 0")

    print("\n[generated-artifact validation]")
    generated_files: list[Path] = [
        library_path,
        map_path,
        review_path,
        summary_path,
        readme_path,
    ]
    generated_files.extend(output_root.glob("evidence-library/*/manifest.json"))

    if len(generated_files) != EXPECTED_UNIQUE_CONTEXT + 5:
        raise SystemExit(
            f"Unexpected generated-artifact count: expected={EXPECTED_UNIQUE_CONTEXT + 5} "
            f"actual={len(generated_files)}"
        )

    for path in generated_files:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"Generated artifact is not UTF-8: {path}: {exc}") from exc

        if path.suffix == ".json":
            json.loads(text)
        elif path.suffix == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                list(csv.DictReader(handle))

        for line_no, line in enumerate(text.splitlines(), start=1):
            if line.endswith(" ") or line.endswith("\t"):
                raise SystemExit(
                    f"Generated artifact has trailing whitespace: {path}:{line_no}"
                )

    print(f"GeneratedArtifactsValidated=PASS — {len(generated_files)}")

    print("\n[staged-workspace validation]")
    status_raw = git_bytes(
        private_repo,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    status_records = [record for record in status_raw.split(b"\x00") if record]
    if not status_records:
        raise SystemExit(
            "Private repository is unexpectedly clean; the materialized workspace is not staged."
        )

    unexpected_status: list[str] = []
    for record in status_records:
        decoded = record.decode("utf-8", errors="replace")
        if "adjudication-working/context-evidence/" not in decoded:
            unexpected_status.append(decoded)
    if unexpected_status:
        raise SystemExit(
            "Unexpected private-repository changes: " + " | ".join(unexpected_status)
        )

    staged_raw = git_bytes(
        private_repo,
        "diff",
        "--cached",
        "--name-only",
        "-z",
    )
    staged = [
        item.decode("utf-8", errors="strict")
        for item in staged_raw.split(b"\x00")
        if item
    ]
    if len(staged) != EXPECTED_STAGED:
        raise SystemExit(
            f"Unexpected staged artifact count: expected={EXPECTED_STAGED} actual={len(staged)}"
        )
    if any(
        not path.startswith("adjudication-working/context-evidence/")
        for path in staged
    ):
        raise SystemExit("Unexpected staged path outside context-evidence workspace.")

    print(f"StagedArtifacts=PASS — {len(staged)}")
    print("ImmutableEvidenceWhitespaceCheck=SKIPPED_BY_DESIGN")
    print("EvidenceIntegrityGate=GIT_PROVENANCE_PLUS_SHA256")

    print("\n[commit and push]")
    run(
        [
            "git",
            "-C",
            str(private_repo),
            "commit",
            "-m",
            "Materialize M2 historical context evidence with byte-preserving validation",
        ],
        capture=False,
    )
    run(
        ["git", "-C", str(private_repo), "push", "origin", "main"],
        capture=False,
    )

    new_head = git_text(private_repo, "rev-parse", "HEAD")
    final_status = git_bytes(
        private_repo,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if final_status:
        raise SystemExit("Private repository is not clean after evidence commit.")

    print("\n" + "=" * 76)
    print(" M2 CONTEXT EVIDENCE FINALIZATION COMPLETE")
    print(f" PrivateCommit={new_head}")
    print(" SuitableCases=100")
    print(" ContextRows=1952")
    print(" UniqueContextCandidates=820")
    print(" EvidenceCopies=820")
    print(" NonUTF8EvidencePreserved=2")
    print(" CasesReadyForContextSufficiencyReview=100")
    print(" ContextSufficiencyDecisionsAssigned=0")
    print(" GroundTruthAssigned=0")
    print(" SourceRepositoriesModified=0")
    print(" NEXT=create Excel-native 100-case context-sufficiency review workbook")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
