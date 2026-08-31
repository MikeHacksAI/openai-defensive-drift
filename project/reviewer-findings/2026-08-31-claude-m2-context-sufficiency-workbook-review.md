# Claude Review Findings — M2 Context-Sufficiency Workbook Recovery

## Review disposition

Claude returned **FAIL for executing the recovery runner as-is** and **SAFE TO EXECUTE AFTER PATCHES: YES**.

The reported parser failure was correctly diagnosed as a single invalid expandable-string variable token (`$CaseIndex:`), but the review identified additional defects that must be corrected before the operator executes the recovery runner.

## Reviewed artifacts

1. `experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1`
   - failed builder commit: `52bd9e8becacc92c80cf9c67bbd04ef389be9988`
   - failed builder blob: `2a6e58bdcc36ba7cc4288e371f73351b5f36456d`

2. `experiments/pre-grant/m2-context-sufficiency-workbook-parser-repair-runner.ps1`
   - recovery runner commit: `c26719b8dfb288653027c22ae9fc3cfd6f2d58a9`
   - recovery runner blob: `a1d83564461a2ff1eed170459176feaf234f9537`

## Confirmed findings

### CRITICAL — reported parser failure

The canonical builder contains exactly one unbraced `$CaseIndex:` token in an expandable string. PowerShell interprets the colon as part of variable syntax. The narrow `${CaseIndex}:` repair is correct and no broader parser rewrite is required.

### HIGH — verification/execution source mismatch (TOCTOU)

The recovery runner verifies the committed builder identity with `git rev-parse HEAD:<path>` but then reads and executes the working-tree file. A locally modified working tree could therefore pass the Git blob identity check while different bytes are patched and executed.

**Required rule:** the bytes whose identity is verified must be the same bytes that are parsed, patched, and executed. Prefer reading the exact Git object (for example `git show HEAD:<path>`) or cryptographically verifying the exact execution payload before use.

### HIGH — invalid workbook residue after post-save validation failure

The workbook builder can save `$OutputPath`, fail a later workbook-integrity check, and leave the invalid `.xlsx` behind. The next run then stops at the existing-output guard and requires manual operator deletion.

**Required rule:** generated output must be transactional. If post-generation validation fails, remove/quarantine the invalid newly generated artifact before rethrowing, while never deleting a pre-existing operator artifact.

### MEDIUM — CSV encoding ambiguity on Windows PowerShell 5.1

`Import-Csv` without an explicit encoding can use the Windows ANSI code page under Windows PowerShell 5.1 and silently corrupt non-ASCII text.

**Required rule:** text/CSV encoding must be explicit when correctness depends on stable cross-version decoding. For the current UTF-8 research CSVs, use `Import-Csv -Encoding UTF8`.

### LOW — repository precondition specificity

A missing public repository is ultimately caught by Git failure, but an explicit `.git`/repository guard would provide a clearer fail-fast message.

### LOW — replace-all safety depends on occurrence guard

The repair runner's `.Replace()` call is acceptable only because it first proves there is exactly one target occurrence. That single-occurrence guard is part of the repair invariant and must not be removed independently.

## Required tests before operator execution

1. Parser test: original known-bad builder fails as expected; patched exact payload has zero parser errors.
2. Artifact-identity test: prove that the content verified by Git/blob identity is exactly the content written to the temporary execution script.
3. Existing-output precondition test: a deliberately pre-existing output file must stop execution before Excel COM is created.
4. Fault-injection cleanup test: force a post-save validation failure and confirm the newly generated invalid workbook is removed.
5. Encoding test: include a non-ASCII CSV value under Windows PowerShell 5.1 and confirm correct round-trip into the workbook.
6. Final real smoke run: verify 200 Review hyperlinks, 1,952 ContextEvidence hyperlinks, Total=100, Reviewed=0, Remaining=100, GroundTruthAssigned=0, and no unintended leftover Excel process created by the test workflow.

## Reusable engineering lessons

These findings are not one-off M2 trivia. They establish reusable MikeHacksAI engineering expectations:

- **verify and execute the same artifact bytes**;
- **treat generated outputs transactionally** and clean failed new artifacts;
- **declare text encodings explicitly** across version-sensitive environments;
- **parser success is necessary but not sufficient**;
- **failure-path smoke tests are mandatory** for nontrivial executable workflows;
- **single-purpose repair runners must prove their repair scope** before mutation;
- **operator retry burden is a correctness concern**, not merely a usability concern.

These lessons are also promoted to the canonical `mikehacksai-engineering-standards` repository so future code work can inherit them across projects.

## Scientific boundary

This review concerns implementation quality only. Claude did not assign, and external reviewers must not assign, Defensive Drift benchmark relationship ground truth.