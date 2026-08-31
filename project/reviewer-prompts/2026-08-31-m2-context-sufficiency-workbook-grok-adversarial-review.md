# Grok Adversarial Review Prompt — M2 Context-Sufficiency Workbook Recovery

## Use after Claude findings were patched

Claude returned `FAIL` for the prior runner and identified three material fixes: exact execution-source identity, failed-workbook cleanup, and explicit UTF-8 CSV decoding. Those findings have been incorporated into the reviewed recovery runner.

Because the workflow has already produced repeated operator-facing failures and Claude identified substantive defects beyond the original parser issue, a second independent adversarial review is required before operator execution.

## Artifacts

1. Canonical known-failed workbook builder
   - path: `experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1`
   - blob: `2a6e58bdcc36ba7cc4288e371f73351b5f36456d`

2. Claude-informed recovery runner
   - path: `experiments/pre-grant/m2-context-sufficiency-workbook-parser-repair-runner.ps1`
   - commit: `62823b6ab76c1dfcfcd859fd6689da113482727f`
   - blob: `320fbc23ce0108cd67cb93381aeab6b606ad39ed`

3. Claude findings record
   - path: `project/reviewer-findings/2026-08-31-claude-m2-context-sufficiency-workbook-review.md`

## Exact prompt to Grok

Act as an adversarial implementation reviewer for the Defensive Drift cybersecurity research project. Assume a conventional Claude review has already been completed and its confirmed findings were incorporated into the recovery runner. Do not redesign the project and do not broaden scope.

Review the canonical workbook builder and the updated recovery runner I provide. The canonical builder is intentionally preserved at its known failed blob; the recovery runner reads its bytes, proves the working-tree bytes have the expected Git blob identity, applies narrowly guarded in-memory repairs, parser-validates the temporary execution payload, runs it against the existing private evidence checkpoint, and removes a newly generated workbook if execution/validation fails.

Claude previously identified:

1. one invalid `$CaseIndex:` PowerShell interpolation, repaired to `${CaseIndex}:`;
2. a verification/execution source mismatch, addressed by reading the actual builder bytes and computing their Git blob SHA-1 before using those same in-memory bytes;
3. failed workbook residue after post-save validation failure, addressed by runner-level cleanup when execution has started but has not succeeded;
4. implicit CSV encoding under Windows PowerShell 5.1, addressed by exactly-once temporary patches adding `-Encoding UTF8` to both `Import-Csv` calls.

Look specifically for concrete hidden assumptions or false-success/failure-recovery problems in the updated runner, including:

- whether `Get-GitBlobSha1FromBytes` correctly computes standard Git blob identity for the exact bytes that are then decoded and patched;
- whether UTF-8 decoding/writing choices could change execution semantics or mishandle a BOM;
- whether each `Replace-ExactlyOnce` invariant is sufficiently narrow and fails safely;
- whether the runner can accidentally delete a pre-existing workbook or delete a valid completed workbook;
- whether builder failure after Excel creates/saves a workbook is reliably surfaced to the runner;
- whether PowerShell non-terminating errors, `$LASTEXITCODE`, or script invocation semantics could allow a false success;
- Windows PowerShell 5.1 compatibility of the runner constructs;
- any Excel COM/process-leak concern that could materially block the operator after success or failure;
- whether the existing builder post-save checks genuinely establish: 3 sheets, 200 Review hyperlinks, 1,952 ContextEvidence hyperlinks, Total=100, Reviewed=0, Remaining=100, GroundTruthAssigned=0;
- whether the runner's final success banner claims anything it did not actually verify;
- operator retry traps or leftover-state problems.

Preserve these invariants:

- private evidence checkpoint remains `0c3df389b37ea948129c801276a844ecf3430b9e`;
- do not rerun corpus discovery or historical evidence materialization;
- source evidence and immutable evidence bytes remain untouched;
- no relationship ground truth is assigned;
- unknown stays unknown;
- `main` remains the only working branch;
- do not recommend a broad rewrite if a small patch suffices.

Return exactly:

1. `PASS` or `FAIL` for operator execution of the updated recovery runner.
2. Only concrete reproducible findings, each ranked `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.
3. For each finding, explain whether existing checks catch it and give the smallest safe patch/test.
4. State the strongest failure modes you checked even if no issue remains.
5. Final line: `SAFE TO EXECUTE: YES` or `SAFE TO EXECUTE: NO`.

Do not assign Defensive Drift benchmark labels and do not request private raw evidence.

## Return path

Bring Grok's complete response back to the primary Defensive Drift conversation. The primary assistant will reconcile it with Claude's findings and deterministic validation requirements before providing any execution command.