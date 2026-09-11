# Reconciliation — Grok M2 Context-Sufficiency Workbook Review

**Reconciliation date:** 2026-09-10  
**Grant phase:** M2  
**Scope:** Artifact identity and concrete Grok findings only  
**Execution status after reconciliation:** **Do not execute yet; obtain a clean independent review of the exact canonical blobs because the prior Grok attachment identity cannot be proven.**

## Authoritative artifacts inspected

### Recovery runner

Path:

`experiments/pre-grant/m2-context-sufficiency-workbook-parser-repair-runner.ps1`

Current canonical Git blob:

`2733b49f7d4b250e3c2a0200365e56bdeb0f8791`

Known commit introducing the current private-repository guard behavior:

`3eaed15e777e0659c26f0887c910fd88eed43e95` — `Allow docs-only private commits in M2 workbook recovery`

### Workbook builder

Path:

`experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1`

Current canonical Git blob:

`2a6e58bdcc36ba7cc4288e371f73351b5f36456d`

### Private M2 evidence state

Authoritative evidence checkpoint:

`0c3df389b37ea948129c801276a844ecf3430b9e`

Current private `main` during this reconciliation:

`a5f7fdf3b5f04189401f48511e8e4e631ef4183c`

Repository comparison proves:

- the evidence checkpoint is the merge base and current private `main` is five commits ahead;
- all changes after the evidence checkpoint are under `docs/`;
- no file under `adjudication-working/context-evidence` changed.

This is exactly the condition the current runner is designed to permit.

---

## Finding 1 — CRITICAL: runner allegedly lacks the newer private-repository guards

**Grok report:** The inspected runner did not contain `git merge-base --is-ancestor`, the path-scoped `git diff --quiet`, or current-private-HEAD pass-through.

**Reconciliation:** **CONTRADICTED for the canonical runner blob.**

The current canonical runner blob `2733b49f7d4b250e3c2a0200365e56bdeb0f8791` explicitly contains all three controls:

1. `git -C $PrivateRepo merge-base --is-ancestor $ExpectedEvidenceCheckpoint $PrivateHead`
2. `git -C $PrivateRepo diff --quiet $ExpectedEvidenceCheckpoint $PrivateHead -- 'adjudication-working/context-evidence'`
3. invocation of the temporary builder with `-ExpectedPrivateHead $PrivateHead`

Commit `3eaed15e777e0659c26f0887c910fd88eed43e95` shows these exact changes replacing the older exact-private-HEAD equality gate.

### Provenance conclusion

The evidence does **not** prove that Grok received a stale file, and it does **not** prove that Grok misread the attachment. The exact external attachment bytes were not preserved with a hash.

What is proven is narrower:

> Grok's CRITICAL description does not match the canonical runner blob that is currently in GitHub and that the checkpoint identifies as the intended runner.

Therefore no code change should be made to the canonical runner merely to add controls it already contains.

---

## Finding 2 — HIGH: runner should independently re-validate the saved workbook

**Grok report:** A saved workbook might survive a later validation failure; the runner should independently re-check 3 sheets, hyperlink counts, and the initial summary invariants.

**Reconciliation:** **THE CANONICAL BUILDER ALREADY PERFORMS THE NAMED POST-SAVE VALIDATIONS; THE RUNNER ALSO REMOVES OUTPUT WHEN THE TEMPORARY BUILDER FAILS.**

The canonical builder:

1. saves the workbook;
2. closes the initial workbook object;
3. reopens the saved workbook read-only;
4. verifies exactly 3 worksheets and requires `Summary`, `Review`, and `ContextEvidence`;
5. verifies `Review.Hyperlinks.Count -eq 200`;
6. verifies `ContextEvidence.Hyperlinks.Count -eq 1952`;
7. verifies Total Cases = 100;
8. verifies Reviewed = 0;
9. verifies Remaining = 100;
10. verifies Relationship Ground Truth Assigned = 0;
11. throws if any invariant fails.

The recovery runner wraps execution in a failure handler. If execution started, did not complete successfully, and an output workbook exists, the runner removes that newly generated workbook before rethrowing the error.

### Patch decision

No additional duplicate validation logic is justified from the preserved Grok finding alone. The runner pins the exact builder blob, verifies the working-tree builder bytes against that blob, applies only three exactly-once text replacements, parser-validates the temporary script, and executes that temporary script. The post-save invariant checks therefore remain part of the exact execution path.

A second copy of the same Excel COM validation logic in the runner would add maintenance and COM-lifecycle complexity without addressing a demonstrated gap.

---

## Finding 3 — MEDIUM: Git blob SHA-1 implementation

**Grok report:** `Get-GitBlobSha1FromBytes` correctly computes canonical Git blob identity.

**Reconciliation:** **CONFIRMED / CLOSED.**

The implementation prefixes the raw bytes with ASCII `blob <length>\0`, computes SHA-1 over header plus raw content bytes, and renders lowercase hexadecimal. This matches standard Git blob identity.

---

## Finding 4 — MEDIUM: `Replace-ExactlyOnce`

**Grok report:** The helper is sufficiently narrow for the current patches.

**Reconciliation:** **CONFIRMED / CLOSED.**

The runner fails unless each expected source string occurs exactly once before replacement. Current replacements are limited to:

- `${CaseIndex}:` parser repair;
- explicit UTF-8 decoding for the review CSV;
- explicit UTF-8 decoding for the context-map CSV.

---

## Finding 5 — LOW: possible lingering Excel COM process

**Grok report:** An unusual failure path might leave Excel COM process state behind.

**Reconciliation:** **NO REPRODUCIBLE DEFECT ESTABLISHED.**

The builder's `finally` block attempts workbook close, releases workbook/sheet COM objects, calls `Excel.Quit()`, releases the Excel COM object, and forces GC/finalizer processing. A hypothetical orphaned process remains worth checking after an actual failure, but the preserved review provides no concrete path demonstrating that the current cleanup is defective.

No code change is justified without a reproducible failure.

---

# Artifact-identity conclusion

The exact external attachment identity remains **unknown** because no Grok-upload hash was preserved.

The repository identity is **known**:

- runner blob: `2733b49f7d4b250e3c2a0200365e56bdeb0f8791`;
- builder blob: `2a6e58bdcc36ba7cc4288e371f73351b5f36456d`;
- runner guard commit: `3eaed15e777e0659c26f0887c910fd88eed43e95`;
- evidence checkpoint: `0c3df389b37ea948129c801276a844ecf3430b9e`;
- current private main at reconciliation: `a5f7fdf3b5f04189401f48511e8e4e631ef4183c`, with only documentation changes after the evidence checkpoint.

Because the previous Grok review's CRITICAL observation conflicts with the canonical runner and the actual upload bytes cannot be proven, that review cannot serve as the final independent execution gate.

## Required next gate

Perform one fresh independent adversarial review using the **exact canonical files above**, and include the two blob SHAs in the review prompt. The reviewer must explicitly confirm that the runner it sees contains the three private-repository guards and that the builder contains the named post-save validation checks before issuing PASS/FAIL.

No M2 workbook generation should occur until that clean exact-artifact review is reconciled.
