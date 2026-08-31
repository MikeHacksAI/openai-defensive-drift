#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_RELATIVE = "experiments/pre-grant/m2-materialize-context-evidence.py"
EXPECTED_BASE_BLOB = "d1f17beba9f590e71dc1c201fd16075ece4e8004"
EXPECTED_PRIVATE_HEAD_DEFAULT = "f4584161d7f6ee6cbbc828afee081abd164d223c"

OLD_UTF8_GATE = '''            try:\n                source_bytes.decode("utf-8", errors="strict")\n            except UnicodeDecodeError as exc:\n                raise RuntimeError(\n                    f"{cid} historical evidence is not valid UTF-8 Markdown: {exc}"\n                ) from exc\n\n'''

NEW_BYTE_BOUNDARY = '''            # Evidence identity is byte-level. Legacy Markdown may use a non-UTF-8\n            # encoding; preserve the exact verified bytes without transcoding.\n\n'''


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
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


def git_status(repo: Path) -> list[str]:
    text = git_text(repo, "status", "--porcelain=v1", "--untracked-files=all")
    return [line for line in text.splitlines() if line]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resume M2 context-evidence materialization after the legacy non-UTF-8 "
            "evidence defect by applying one verified byte-preservation patch to the "
            "reviewed base materializer, then validating, committing, and pushing the "
            "private evidence workspace."
        )
    )
    parser.add_argument("--public-repo", required=True)
    parser.add_argument("--private-repo", required=True)
    parser.add_argument("--git-root", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument(
        "--expected-private-head",
        default=EXPECTED_PRIVATE_HEAD_DEFAULT,
    )
    args = parser.parse_args()

    public_repo = Path(args.public_repo)
    private_repo = Path(args.private_repo)
    git_root = Path(args.git_root)
    cache_root = Path(args.cache_root)
    expected_private_head = args.expected_private_head

    base_script = public_repo / BASE_RELATIVE
    output_root = private_repo / "adjudication-working" / "context-evidence"
    temp_root = private_repo / "adjudication-working" / "context-evidence.__building__"

    print("=" * 76)
    print(" DEFENSIVE DRIFT — M2 BYTE-PRESERVING CONTEXT MATERIALIZATION RECOVERY")
    print("=" * 76)

    print("\n[1/7] Verify reviewed base materializer and clean workspaces...")
    if not (public_repo / ".git").is_dir():
        raise SystemExit(f"Public repository missing: {public_repo}")
    if not (private_repo / ".git").is_dir():
        raise SystemExit(f"Private repository missing: {private_repo}")
    if not base_script.is_file():
        raise SystemExit(f"Base materializer missing: {base_script}")

    public_dirty = git_status(public_repo)
    if public_dirty:
        raise SystemExit("Public repository is dirty: " + " | ".join(public_dirty))

    private_dirty = git_status(private_repo)
    if private_dirty:
        raise SystemExit("Private repository is dirty: " + " | ".join(private_dirty))

    current_base_blob = git_text(public_repo, "rev-parse", f"HEAD:{BASE_RELATIVE}")
    if current_base_blob != EXPECTED_BASE_BLOB:
        raise SystemExit(
            "Reviewed base materializer changed: "
            f"expected={EXPECTED_BASE_BLOB} actual={current_base_blob}"
        )

    private_head = git_text(private_repo, "rev-parse", "HEAD")
    if private_head != expected_private_head:
        raise SystemExit(
            f"Unexpected private checkpoint: expected={expected_private_head} "
            f"actual={private_head}"
        )

    if output_root.exists():
        raise SystemExit(f"Context-evidence output already exists: {output_root}")
    if temp_root.exists():
        raise SystemExit(
            f"Builder-owned temporary directory remains from an earlier run: {temp_root}"
        )

    print(f"  BaseBuilderBlob=PASS — {current_base_blob}")
    print(f"  PrivateCheckpoint=PASS — {private_head}")
    print("  FailedRunResidue=NONE")

    print("\n[2/7] Build and validate exact byte-preservation repair...")
    source = base_script.read_text(encoding="utf-8")
    occurrences = source.count(OLD_UTF8_GATE)
    if occurrences != 1:
        raise SystemExit(
            f"Expected exactly one strict UTF-8 gate in reviewed builder; found {occurrences}."
        )

    patched = source.replace(OLD_UTF8_GATE, NEW_BYTE_BOUNDARY, 1)
    ast.parse(patched, filename="m2-materialize-context-evidence-byte-preserving.py")
    patched_sha256 = hashlib.sha256(patched.encode("utf-8")).hexdigest()

    print("  RepairScope=ONE strict UTF-8 admission gate removed")
    print("  EvidenceBehavior=EXACT VERIFIED BYTES PRESERVED")
    print(f"  PatchedSourceSHA256={patched_sha256}")
    print("  PythonAST=PASS")

    print("\n[3/7] Run repaired materializer from temporary reviewed copy...")
    with tempfile.TemporaryDirectory(prefix="defensive-drift-m2-encoding-repair-") as td:
        patched_path = Path(td) / "m2-materialize-context-evidence-byte-preserving.py"
        patched_path.write_text(patched, encoding="utf-8", newline="\n")

        cmd = [
            sys.executable,
            str(patched_path),
            "--private-repo",
            str(private_repo),
            "--git-root",
            str(git_root),
            "--cache-root",
            str(cache_root),
            "--expected-private-head",
            expected_private_head,
        ]
        proc = run(cmd, capture=False, check=False)
        if proc.returncode != 0:
            raise SystemExit(f"Repaired materializer failed with exit code {proc.returncode}.")

    print("\n[4/7] Validate complete context-evidence workspace...")
    required_files = {
        "library": output_root / "evidence-library-index.csv",
        "map": output_root / "case-context-map.csv",
        "review": output_root / "context-sufficiency-review.csv",
        "summary": output_root / "build-summary.json",
        "readme": output_root / "README.md",
    }
    for label, path in required_files.items():
        if not path.is_file():
            raise SystemExit(f"Required {label} artifact missing: {path}")

    library = read_csv(required_files["library"])
    context_rows = read_csv(required_files["map"])
    review_rows = read_csv(required_files["review"])
    summary = json.loads(required_files["summary"].read_text(encoding="utf-8"))

    if len(context_rows) != 1952:
        raise SystemExit(f"Expected 1,952 case-context rows; found {len(context_rows)}.")
    if len(review_rows) != 100:
        raise SystemExit(f"Expected 100 sufficiency-review rows; found {len(review_rows)}.")
    if len(library) != int(summary.get("unique_context_candidates", -1)):
        raise SystemExit("Evidence-library count does not match build summary.")
    if any(row.get("context_sufficiency") != "NOT_REVIEWED" for row in review_rows):
        raise SystemExit("Context-sufficiency decisions were assigned before human review.")
    if any(row.get("ground_truth_assigned") != "NO" for row in review_rows):
        raise SystemExit("Ground truth was assigned in context-sufficiency review rows.")
    if any(row.get("ground_truth_assigned") != "NO" for row in context_rows):
        raise SystemExit("Ground truth was assigned in the case-context map.")

    non_utf8_evidence = 0
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
            non_utf8_evidence += 1

    if int(summary.get("suitable_cases", -1)) != 100:
        raise SystemExit("Summary suitable-case count is invalid.")
    if int(summary.get("context_rows", -1)) != 1952:
        raise SystemExit("Summary context-row count is invalid.")
    if int(summary.get("cases_ready_for_context_sufficiency_review", -1)) != 100:
        raise SystemExit("Summary readiness count is invalid.")
    if int(summary.get("context_sufficiency_decisions_assigned", -1)) != 0:
        raise SystemExit("Context-sufficiency decisions were unexpectedly assigned.")
    if int(summary.get("ground_truth_assigned", -1)) != 0:
        raise SystemExit("Ground truth was unexpectedly assigned.")
    if int(summary.get("source_repositories_modified", -1)) != 0:
        raise SystemExit("Source-repository integrity boundary failed.")

    print("  SuitableCases=PASS — 100")
    print("  ContextRows=PASS — 1952")
    print(f"  UniqueContextCandidates={summary['unique_context_candidates']}")
    print(f"  EvidenceHashVerification=PASS — {len(library)}")
    print(f"  NonUTF8EvidencePreserved={non_utf8_evidence}")
    print("  ContextSufficiencyDecisionsAssigned=PASS — 0")
    print("  GroundTruthAssigned=PASS — 0")
    print("  SourceRepositoriesModified=PASS — 0")

    print("\n[5/7] Stage and validate private evidence workspace...")
    run(["git", "-C", str(private_repo), "add", "--", "adjudication-working/context-evidence"])
    diff_check = run(
        ["git", "-C", str(private_repo), "diff", "--cached", "--check"],
        check=False,
    )
    if diff_check.returncode != 0:
        raise SystemExit("Git staged-content validation failed:\n" + diff_check.stdout + diff_check.stderr)

    staged = [
        line
        for line in git_text(private_repo, "diff", "--cached", "--name-only").splitlines()
        if line
    ]
    expected_staged = 2 * int(summary["unique_context_candidates"]) + 5
    if len(staged) != expected_staged:
        raise SystemExit(
            f"Unexpected staged artifact count: expected={expected_staged} actual={len(staged)}"
        )
    unexpected_staged = [
        path for path in staged
        if not path.startswith("adjudication-working/context-evidence/")
    ]
    if unexpected_staged:
        raise SystemExit("Unexpected staged paths: " + " | ".join(unexpected_staged))

    print(f"  StagedArtifacts=PASS — {len(staged)}")

    print("\n[6/7] Commit and push private checkpoint...")
    run(
        [
            "git",
            "-C",
            str(private_repo),
            "commit",
            "-m",
            "Materialize M2 historical context evidence with byte-preserving legacy support",
        ],
        capture=False,
    )
    run(["git", "-C", str(private_repo), "push", "origin", "main"], capture=False)
    new_head = git_text(private_repo, "rev-parse", "HEAD")

    print("\n[7/7] Final verification...")
    final_dirty = git_status(private_repo)
    if final_dirty:
        raise SystemExit("Private repository is dirty after commit: " + " | ".join(final_dirty))

    print("\n" + "=" * 76)
    print(" M2 CONTEXT EVIDENCE MATERIALIZATION RECOVERED")
    print(f" PrivateCommit={new_head}")
    print(" SuitableCases=100")
    print(" ContextRows=1952")
    print(f" UniqueContextCandidates={summary['unique_context_candidates']}")
    print(f" EvidenceCopies={len(library)}")
    print(f" NonUTF8EvidencePreserved={non_utf8_evidence}")
    print(" CasesReadyForContextSufficiencyReview=100")
    print(" ContextSufficiencyDecisionsAssigned=0")
    print(" GroundTruthAssigned=0")
    print(" SourceRepositoriesModified=0")
    print(" NEXT=create Excel-native 100-case context-sufficiency review workbook")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
