# M2 Context Evidence Materialization and Sufficiency Review

## Current state

The deterministic historical-context retrieval index is complete for the 100 suitable benchmark observations.

- suitable benchmark pool: 100 observations;
- retrieved case-to-context rows: 1,952;
- cases with at least one retrieved context candidate: 100;
- cases without metadata matches: 0;
- relationship ground truth assigned: 0.

## Why this gate exists

The M2 adjudication protocol requires each observation to be evaluated against supplied historical incidents before assigning `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE`.

The retrieval index identifies potentially relevant records, but metadata similarity is not evidence by itself. The retrieved source artifacts therefore must be materialized and reviewable before relationship adjudication begins.

## Materialization design

`experiments/pre-grant/m2-materialize-context-evidence.py` materializes each unique retrieved context candidate exactly once under the private research repository.

Tracked evidence is extracted from its preserved Git blob and verified with Git object identity. If a discovery-time untracked or ignored Markdown record ever appears in the retrieval set, it is accepted only when its current bytes still match the preserved discovery SHA-256. Source repositories are read-only and their pre/post Git status is compared.

The materialized library is deduplicated by candidate identity rather than copied once per case. The 1,952 case-to-context relationships point to that evidence library through a mapping CSV.

## Private outputs

The stage writes only under `adjudication-working/context-evidence/`:

- `evidence-library/<candidate-id>/source-record.md` — exact materialized evidence;
- `evidence-library/<candidate-id>/manifest.json` — source provenance, hashes, and materialization mode;
- `evidence-library-index.csv` — one row per unique materialized context candidate;
- `case-context-map.csv` — all case-to-context retrieval relationships with evidence paths;
- `context-sufficiency-review.csv` — 100-case human-review worklist;
- `build-summary.json` — materialization and integrity counts;
- `README.md` — private-stage boundary documentation.

## Human context-sufficiency gate

Before relationship labels are assigned, each of the 100 cases is reviewed only for whether the supplied historical context is adequate to proceed.

Allowed sufficiency decisions are:

- `SUFFICIENT_FOR_ADJUDICATION`
- `MORE_CONTEXT_REQUIRED`

This gate does not assign benchmark relationship ground truth.

## Scientific boundary

Retrieval score, token overlap, exact-content identity, repository affinity, model affinity, template affinity, and timestamp ordering are retrieval aids only. None automatically establishes `DUPLICATE`, `RECURRENCE`, or any other final relationship.

Unknown facts remain unknown. Context that is inadequate for a safe relationship decision must be expanded before adjudication rather than converted into an assumed label.

## Next gate

After materialized evidence passes integrity validation, create the Excel-native 100-case context-sufficiency review workbook. Once human sufficiency review is complete, cases marked `MORE_CONTEXT_REQUIRED` receive bounded retrieval expansion; only cases with sufficient supplied context proceed to relationship/remediation/severity/dangerous-false-duplicate/confidence adjudication.
