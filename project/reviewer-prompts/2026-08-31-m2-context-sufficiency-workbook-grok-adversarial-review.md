# Grok Adversarial Review Prompt — M2 Context-Sufficiency Workbook Recovery

## Use after Claude findings were patched

Claude returned `FAIL` for the prior runner and identified material fixes involving execution-source identity, failed-workbook cleanup, and explicit UTF-8 CSV decoding. Those findings were incorporated into the recovery runner.

Since that review, the private repository legitimately advanced beyond the M2 evidence checkpoint because new roadmap documentation was added. The context-evidence subtree itself must remain unchanged. The recovery runner was therefore revised so documentation-only private commits do not create a false blocker while the scientific evidence checkpoint remains protected.

Because the workflow has already produced repeated operator-facing failures and the runner now contains this additional state-validation logic, a second independent adversarial review is required before operator execution.

## Artifacts

1. Canonical known-failed workbook builder
   - path: `experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1`
   - blob: `2a6e58bdcc36ba7cc4288e371f73351b5f36456d`

2. Claude-informed, evidence-checkpoint-aware recovery runner
   - path: `experiments/pre-grant/m2-context-sufficiency-workbook-parser-repair-runner.ps1`
   - commit: `3eaed15e777e0659c26f0887c910fd88eed43e95`
   - blob: `2733b49f7d4b250e3c2a0200365e56bdeb0f8791`

3. Claude findings record
   - path: `project/reviewer-findings/2026-08-31-claude-m2-context-sufficiency-workbook-review.md`

## Exact prompt to Grok

Act as an adversarial implementation reviewer for the Defensive Drift cybersecurity research project. Assume a conventional Claude review has already been completed and its confirmed findings were incorporated into the recovery runner. Do not redesign the project and do not broaden scope.

Review the canonical workbook builder and the updated recovery runner I provide. The canonical builder is intentionally preserved at its known failed blob. The recovery runner verifies the builder artifact, applies narrowly guarded in-memory repairs, parser-validates the temporary execution payload, and invokes the builder against the existing M2 context evidence.

The private repository has legitimately advanced beyond evidence checkpoint `0c3df389b37ea948129c801276a844ecf3430b9e` because documentation/roadmap files were added. The runner now:

1. resolves the current private HEAD;
2. proves `0c3df389b37ea948129c801276a844ecf3430b9e` is an ancestor of that HEAD;
3. uses `git diff --quiet <checkpoint> <current-head> -- adjudication-working/context-evidence` to require that the M2 context-evidence subtree is unchanged;
4. requires the private worktree to be clean;
5. passes the resolved current private HEAD into the temporary builder's existing exact-HEAD parameter so a concurrent repository change between runner preflight and builder execution still causes the builder to fail safely.

Claude previously identified:

1. one invalid `$CaseIndex:` PowerShell interpolation, repaired to `${CaseIndex}:`;
2. a verification/execution source mismatch, addressed by verifying the actual builder bytes used by the runner against the expected Git blob identity;
3. failed workbook residue after post-save validation failure, addressed by runner-level cleanup when execution has started but has not succeeded;
4. implicit CSV encoding under Windows PowerShell 5.1, addressed by exactly-once temporary patches adding `-Encoding UTF8` to both `Import-Csv` calls.

Look specifically for concrete hidden assumptions or false-success/failure-recovery problems in the updated runner, including:

- whether `Get-GitBlobSha1FromBytes` correctly computes standard Git blob identity for the exact bytes that are then decoded and patched;
- whether UTF-8 decoding/writing choices could change execution semantics or mishandle a BOM;
- whether each `Replace-ExactlyOnce` invariant is sufficiently narrow and fails safely;
- whether the new ancestor + path-scoped `git diff --quiet` check correctly allows unrelated documentation commits while blocking any change inside `adjudication-working/context-evidence`;
- whether `$LASTEXITCODE` is handled correctly for `git merge-base --is-ancestor` and `git diff --quiet` (0=no difference/success, 1=difference where applicable, other values=error);
- whether passing the already-resolved current private HEAD into the builder preserves a useful TOCTOU guard against a concurrent private-repository commit;
- whether the runner can accidentally delete a pre-existing workbook or delete a valid completed workbook;
- whether builder failure after Excel creates/saves a workbook is reliably surfaced to the runner;
- whether PowerShell non-terminating errors, native-command status, or script invocation semantics could allow false success;
- Windows PowerShell 5.1 / PowerShell 7 compatibility of the constructs used;
- any Excel COM/process-leak concern that could materially block the operator after success or failure;
- whether the existing builder post-save checks genuinely establish: 3 sheets, 200 Review hyperlinks, 1,952 ContextEvidence hyperlinks, Total=100, Reviewed=0, Remaining=100, GroundTruthAssigned=0;
- whether the runner's final success banner claims anything it did not actually verify;
- operator retry traps or leftover-state problems.

Preserve these invariants:

- the authoritative M2 evidence checkpoint remains `0c3df389b37ea948129c801276a844ecf3430b9e`;
- unrelated private documentation commits are permitted only if the context-evidence subtree is unchanged;
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