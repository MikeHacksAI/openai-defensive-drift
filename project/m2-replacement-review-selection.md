# M2 Replacement Review Selection

## Purpose

The first 100-case human suitability screen completed with 78 records marked `SUITABLE`, 22 marked `UNSUITABLE`, and 0 marked `NEEDS_MORE_CONTEXT`.

M2 therefore requires 22 replacement observations before the 100-case benchmark candidate set can proceed to relationship-ground-truth adjudication.

The replacement step must not simply consume the next 22 reserve rows. Human suitability screening removed templates, runbooks, administrative/checkpoint material, mirrors/redundant copies, and other non-case artifacts, so replacement selection must preserve useful coverage while minimizing obvious duplicate risk.

## Source pool

Replacement candidates come only from the already-frozen 50-case `EXPANSION_RESERVE` in the private M2 review queue.

No new corpus discovery, prompt tuning, relationship-label assignment, or test-set outcome information is used to choose replacements.

## Deterministic selection rules

The replacement builder:

1. verifies the accepted private checkpoint containing the completed 100-case suitability review;
2. confirms exactly 78 suitable and 22 unsuitable core records;
3. evaluates all 50 reserve records;
4. excludes a reserve record when its exact-content group contains a core record already marked suitable;
5. never selects two replacement records from the same exact-content group;
6. greedily balances source-model group, template family, severity bucket, selection-reason family, discovery score, and presence of recurrence metadata;
7. preserves the complete reserve ranking, eligibility decision, exclusion reason, and selection score for auditability; and
8. generates provenance-safe private evidence packets for the selected 22 records.

Exact-content identity is only a retrieval and selection-control signal. It does not establish `DUPLICATE` ground truth.

## Human-review boundary

The 22 replacement records receive the same human suitability decision used for the first 100 records:

- `SUITABLE`
- `UNSUITABLE`
- `NEEDS_MORE_CONTEXT`

Relationship ground truth remains unassigned during this step. The labels `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, and `INSUFFICIENT_EVIDENCE` are not assigned until the project has assembled 100 suitable benchmark observations and the required historical context.

## Provenance and source integrity

For every selected replacement, the builder validates the source Git blob and commit/path linkage, copies the exact source blob into the private evidence-packet workspace, records SHA-256 provenance, and verifies that source repositories are unchanged.

The private replacement workspace contains the full deterministic reserve ranking, the 22-record review worklist, build summary, and one evidence packet per replacement candidate.
