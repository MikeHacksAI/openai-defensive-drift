# Grok Adversarial Review — M2 Context-Sufficiency Workbook Recovery

**Review date:** 2026-09-10  
**Reviewer:** Grok  
**Review role:** Adversarial second reviewer  
**Status returned by reviewer:** **FAIL**  
**Reviewer execution verdict:** **SAFE TO EXECUTE: NO**

## Provenance

This file preserves the Grok findings recorded in the Defensive Drift full-chat checkpoint. It is a **source-faithful reconstruction from that checkpoint**, not a claim that the original Grok response bytes were captured verbatim here.

The exact identity of the runner attachment that Grok inspected was unresolved at checkpoint time. Therefore this artifact preserves what Grok reported without treating Grok's description of the inspected runner as proof of the attachment's Git blob identity.

## Artifacts stated as supplied to Grok

1. `experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1`
2. `experiments/pre-grant/m2-context-sufficiency-workbook-parser-repair-runner.ps1`

## Findings preserved from the checkpoint

### CRITICAL — reviewer reported missing newer private-repository guards

Grok reported that the runner artifact it inspected did **not** show the newer:

- `git merge-base --is-ancestor` ancestry check;
- path-scoped `git diff --quiet` over `adjudication-working/context-evidence`;
- resolved current-private-HEAD pass-through to the temporary builder.

Grok instead reported seeing the older exact-private-HEAD equality behavior.

**Important provenance boundary:** this is Grok's reported observation. The checkpoint explicitly records that the exact attachment identity remained unresolved and that a later assistant claim that Grok had received a stale local copy was unsupported.

### HIGH — reviewer requested independent post-save validation

Grok raised a concern that a workbook could be created/saved and later validation could fail, leaving residual workbook state. Grok recommended that the recovery runner independently re-validate these workbook invariants after builder execution:

- exactly 3 sheets;
- 200 hyperlinks on `Review`;
- 1,952 hyperlinks on `ContextEvidence`;
- Total = 100;
- Reviewed = 0;
- Remaining = 100;
- GroundTruth = 0.

### MEDIUM — Git blob SHA-1 implementation

Grok concluded that `Get-GitBlobSha1FromBytes` correctly computes standard Git blob identity using:

`blob <decimal-content-length>\0<raw-content-bytes>`

### MEDIUM — narrow patch helper

Grok concluded that `Replace-ExactlyOnce` was sufficiently narrow for the current parser/encoding repair scope.

### LOW — Excel COM cleanup

Grok noted possible lingering Excel COM process state on unusual failure paths.

## Review-boundary reminder

External-model review is advisory. Deterministic parser checks, repository state validation, exact Git blobs, preserved evidence, and human acceptance remain authoritative. No external reviewer assigns benchmark relationship ground truth.

## Reconciliation

The authoritative reconciliation of these findings is maintained separately in:

`experiments/pre-grant/reviews/grok/2026-09-10-m2-context-sufficiency-workbook-review-reconciliation.md`
