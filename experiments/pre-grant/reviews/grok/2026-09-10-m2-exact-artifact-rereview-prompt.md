# Grok Exact-Artifact Re-Review Prompt — M2 Context-Sufficiency Workbook Recovery

Use this prompt only with the exact canonical artifacts named below.

## Canonical artifacts

1. `experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1`
   - Git blob: `2a6e58bdcc36ba7cc4288e371f73351b5f36456d`
2. `experiments/pre-grant/m2-context-sufficiency-workbook-parser-repair-runner.ps1`
   - Git blob: `2733b49f7d4b250e3c2a0200365e56bdeb0f8791`

## Evidence state

- M2 evidence checkpoint: `0c3df389b37ea948129c801276a844ecf3430b9e`
- Current private `main` verified during reconciliation: `a5f7fdf3b5f04189401f48511e8e4e631ef4183c`
- Git comparison shows only `docs/` changes after the evidence checkpoint; `adjudication-working/context-evidence` is unchanged.
- Known runner guard commit: `3eaed15e777e0659c26f0887c910fd88eed43e95`

## Prompt to Grok

Act as the adversarial second implementation reviewer for Defensive Drift Grant M2. Review only the two exact PowerShell artifacts supplied with this prompt. Do not redesign the project, broaden scope, assign benchmark ground truth, or recommend changes to immutable evidence.

Before issuing any PASS/FAIL finding, explicitly confirm whether the runner artifact you can see contains each of these exact controls:

1. `git -C $PrivateRepo merge-base --is-ancestor $ExpectedEvidenceCheckpoint $PrivateHead`
2. `git -C $PrivateRepo diff --quiet $ExpectedEvidenceCheckpoint $PrivateHead -- 'adjudication-working/context-evidence'`
3. the temporary builder invocation passes `-ExpectedPrivateHead $PrivateHead`

Also explicitly confirm whether the builder performs post-save validation by reopening the saved workbook and checking all of these invariants:

1. exactly 3 worksheets;
2. sheet names `Summary`, `Review`, and `ContextEvidence`;
3. 200 hyperlinks on `Review`;
4. 1,952 hyperlinks on `ContextEvidence`;
5. Total Cases = 100;
6. Reviewed = 0;
7. Remaining = 100;
8. Relationship Ground Truth Assigned = 0.

Then review for concrete hidden assumptions, brittle preconditions, false-success paths, destructive behavior, state-recovery failures, Excel COM cleanup defects, operator retry traps, or divergence from the research/governance contract.

Preserve these boundaries:

- source evidence is read-only;
- immutable evidence bytes must never be normalized or rewritten;
- no relationship ground truth may be assigned by code or by you;
- unknown stays unknown;
- `main` is the only working branch;
- unrelated documentation commits must not invalidate M2 evidence if the evidence checkpoint remains an ancestor and `adjudication-working/context-evidence` is unchanged.

Return exactly:

1. **ARTIFACT CONFIRMATION** — state whether you see all three runner controls and all eight builder post-save checks above.
2. **PASS or FAIL**.
3. **SAFE TO EXECUTE: YES or NO**.
4. Only concrete findings, ranked CRITICAL / HIGH / MEDIUM / LOW.
5. For every finding, quote or identify the exact relevant code behavior and explain why existing validation does not catch it.
6. Give only the smallest safe patch/test for each confirmed defect.
7. If a prior concern is already handled by the supplied code, mark it `ALREADY HANDLED` rather than repeating it as a defect.

Do not infer artifact identity from filenames. The expected Git blobs are:

- builder: `2a6e58bdcc36ba7cc4288e371f73351b5f36456d`
- runner: `2733b49f7d4b250e3c2a0200365e56bdeb0f8791`

If your interface cannot independently verify Git blob hashes from the uploaded bytes, say so explicitly. In that case, treat the hashes as expected identifiers supplied by the operator, and base your code review only on the actual text of the two attached files.
