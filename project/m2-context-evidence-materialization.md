# M2 Context Evidence Materialization and Sufficiency Review

## Current state

Historical-context evidence materialization is complete for the 100 suitable benchmark observations.

- suitable benchmark pool: 100 observations;
- retrieved case-to-context rows: 1,952;
- unique materialized historical evidence records: 820;
- evidence hashes verified: 820;
- preserved non-UTF-8 legacy records: 2;
- cases ready for human context-sufficiency review: 100;
- context-sufficiency decisions assigned: 0;
- relationship ground truth assigned: 0.

The private materialization checkpoint is `0c3df389b37ea948129c801276a844ecf3430b9e`.

## Why this gate exists

The M2 adjudication protocol requires each observation to be evaluated against supplied historical incidents before assigning `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE`.

The retrieval index identifies potentially relevant records, but metadata similarity is not evidence by itself. The retrieved source artifacts therefore must be materialized and reviewable before relationship adjudication begins.

## Terminology: suitability is not context sufficiency

These are two different human-review gates and must not be conflated.

### Suitability screening — already complete

The earlier suitability review asked whether a source record is a genuine incident/observation appropriate for inclusion in the Defensive Drift benchmark rather than a template, policy document, project administration artifact, aggregate container, non-incident, or redundant mirror.

The final 100-observation pool has already passed that gate: 78 suitable observations from the original core review plus 22 suitable replacement observations.

In ordinary project language, this is the stage that establishes that the record counts as a real benchmark drift/incident observation. It does **not** yet establish how that observation relates to historical records.

### Context-sufficiency review — current human gate

The context-sufficiency review asks a different question:

> Do we have enough relevant historical evidence in front of us to make a defensible relationship adjudication for this already-accepted observation?

Allowed decisions are:

- `SUFFICIENT_FOR_ADJUDICATION`
- `MORE_CONTEXT_REQUIRED`

`SUFFICIENT_FOR_ADJUDICATION` therefore does **not** mean "this is a true drift." That benchmark-observation suitability decision was made earlier. It means only that the supplied historical evidence is adequate to proceed to the relationship-label step.

A case can be a genuine benchmark observation while still requiring more historical context before the project can safely decide whether it is `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE`.

## Materialization design

`experiments/pre-grant/m2-materialize-context-evidence.py` materializes each unique retrieved context candidate exactly once under the private research repository.

Tracked evidence is extracted from its preserved Git blob and verified with Git object identity. If a discovery-time untracked or ignored Markdown record ever appears in the retrieval set, it is accepted only when its current bytes still match the preserved discovery SHA-256. Source repositories are read-only and their pre/post Git status is compared.

The materialized library is deduplicated by candidate identity rather than copied once per case. The 1,952 case-to-context relationships point to that evidence library through a mapping CSV.

### Text-encoding boundary

Evidence identity is byte-level, not text-encoding-level. Legacy Markdown records are not required to be valid UTF-8 when their authoritative Git object or preserved discovery hash validates successfully.

`source-record.md` therefore preserves the exact verified source bytes without transcoding. UTF-8 validity may be inspected as metadata or a presentation concern, but it must not be used to exclude otherwise-valid historical evidence or silently rewrite source bytes.

The recovery runner `experiments/pre-grant/m2-context-evidence-encoding-repair-runner.py` applies this single byte-preservation correction to the reviewed materializer without altering the authoritative source evidence.

### Validation boundary for immutable evidence

Exact historical evidence payloads are validated by provenance, Git-object identity, and cryptographic hashes. Generic code/style checks such as whitespace normalization must not require mutation of preserved `source-record.md` evidence. Generated research metadata and code may still receive syntax/style validation separately.

## Private outputs

The materialization stage writes only under `adjudication-working/context-evidence/`:

- `evidence-library/<candidate-id>/source-record.md` — exact materialized evidence;
- `evidence-library/<candidate-id>/manifest.json` — source provenance, hashes, and materialization mode;
- `evidence-library-index.csv` — one row per unique materialized context candidate;
- `case-context-map.csv` — all case-to-context retrieval relationships with evidence paths;
- `context-sufficiency-review.csv` — 100-case human-review worklist;
- `build-summary.json` — materialization and integrity counts;
- `README.md` — private-stage boundary documentation.

## Excel-native context-sufficiency review surface

`experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1` creates the operator review workbook from the verified private checkpoint.

The workbook intentionally separates the human decision surface from retrieval metadata:

- `Summary` — progress counts and plain-language gate definitions;
- `Review` — exactly 100 benchmark observations, each with a hyperlink to the current observation, a jump link to its retrieved historical context, the count of retrieved context candidates, a reviewer-notes field, and the context-sufficiency dropdown;
- `ContextEvidence` — all 1,952 retrieved relationships with rank, title, temporal relation, retrieval score/reasons, provenance metadata, and a direct hyperlink to the preserved historical evidence record.

The only editable classification at this gate is `Context Sufficiency`. Relationship ground truth remains `NO` throughout the workbook. Retrieval rank and score are displayed for navigation and auditability but are not labels and must not be treated as human ground truth.

The generated workbook is kept outside the Git repository during active review. When the human review is complete, the decision values and workbook hash are ingested into the private research repository as durable review evidence, following the same pattern used for the earlier suitability review workbooks.

## Human context-sufficiency gate

Before relationship labels are assigned, each of the 100 cases is reviewed only for whether the supplied historical context is adequate to proceed.

Allowed sufficiency decisions are:

- `SUFFICIENT_FOR_ADJUDICATION`
- `MORE_CONTEXT_REQUIRED`

This gate does not assign benchmark relationship ground truth.

## Scientific boundary

Retrieval score, token overlap, exact-content identity, repository affinity, model affinity, template affinity, and timestamp ordering are retrieval aids only. None automatically establishes `DUPLICATE`, `RECURRENCE`, or any other final relationship.

Unknown facts remain unknown. Context that is inadequate for a safe relationship decision must be expanded before adjudication rather than converted into an assumed label.

## Operator question documentation rule

When the operator asks what a research step, gate, review, metric, or workflow stage is for, the answer is part of the project methodology and must be recorded in the appropriate GitHub project documentation without requiring a separate request to document it.

The repository record should preserve the practical explanation, the scientific purpose, and any terminology distinction that affects interpretation of the benchmark. This documentation obligation applies automatically as the research workflow evolves.

## Next gate

Create and complete the Excel-native 100-case context-sufficiency review workbook. Cases marked `MORE_CONTEXT_REQUIRED` receive bounded retrieval expansion. Only cases marked `SUFFICIENT_FOR_ADJUDICATION` proceed to relationship/remediation/severity/dangerous-false-duplicate/confidence adjudication.
