# Defensive Drift — Human Adjudication Protocol

## Classification order

Every benchmark observation is evaluated against all supplied historical incidents before any model result is considered.

### `DUPLICATE`

Use only when the observation represents the same underlying security condition already captured by an existing incident and does not require an independent defensive incident record.

Similar wording alone is not sufficient.

### `RECURRENCE`

Use when substantially the same underlying security condition returns after mitigation, remediation, closure, or an apparent period of absence.

A recurrence remains independently visible to defenders and must not be silently collapsed into a resolved duplicate.

### `RELATED_BUT_DISTINCT`

Use when observations share symptoms, systems, terminology, or context but differ materially in root cause, affected component, security consequence, or required remediation.

### `NEW`

Use when no supplied historical incident adequately represents the observed security condition.

### `INSUFFICIENT_EVIDENCE`

Use when supplied artifacts cannot safely support one of the other four classifications.

Uncertainty must never be converted into `DUPLICATE`.

## Dangerous false duplicate

A dangerous false duplicate occurs when a case whose correct relationship is `NEW`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE` is treated as an already-resolved duplicate in a way that could suppress necessary defensive investigation.

## Evidence rules

1. Ground truth cites specific evidence IDs.
2. Similar language is not proof of duplication.
3. Shared symptoms are not proof of shared root cause.
4. Remediation claims require explicit evidence.
5. Unknown remediation state remains `UNKNOWN`.
6. Unsafe relationship uncertainty remains `INSUFFICIENT_EVIDENCE`.
7. Adjudicators do not infer hidden facts absent from supplied evidence.

## Workflow

1. Review observation.
2. Review historical incidents.
3. Review evidence artifacts.
4. Assign relationship.
5. Assign remediation state.
6. Assign severity.
7. Determine dangerous-false-duplicate relevance.
8. Cite evidence.
9. Record confidence.
10. Mark `PROVISIONAL`, `REVIEWED`, or `FROZEN`.

## Freeze rule

After a case enters the frozen evaluation set:

- do not change its label merely because a model performed poorly;
- document legitimate corrections;
- increment the benchmark version when a correction materially changes evaluation results.