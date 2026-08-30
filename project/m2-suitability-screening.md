# M2 Human Suitability Screening

## Purpose

The 100 core evidence packets are a human-review queue, not automatically 100 benchmark cases. High-recall discovery intentionally admitted plausible drift evidence as well as templates, runbooks, standards, README files, project documentation, checkpoints, aggregate drift logs, and other artifacts that may be useful for provenance but unsuitable as benchmark observations.

Suitability screening determines whether each queued packet can serve as a scientifically useful benchmark observation before historical-context assembly and relationship adjudication begin.

## Human-only decision boundary

The screening tool may calculate deterministic navigation hints from file paths and titles, but it must not decide record suitability.

Every initialized row begins with:

- `screening_status = NOT_REVIEWED`
- blank `record_suitability`
- blank rejection reason
- blank reviewer notes
- no relationship label
- no ground truth

The human reviewer records one of:

- `SUITABLE`
- `UNSUITABLE`
- `NEEDS_MORE_CONTEXT`

Suggested rejection-reason vocabulary includes:

- `TEMPLATE_OR_BLANK_FORM`
- `RUNBOOK_OR_POLICY`
- `PROJECT_ADMIN_DOC`
- `DUPLICATE_ARTIFACT_NOT_OBSERVATION`
- `INCOMPLETE_FRAGMENT`
- `NOT_SECURITY_RELEVANT`
- `OTHER`

These reasons describe benchmark-observation suitability only. They do not assign `DUPLICATE`, `NEW`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE` ground truth.

## Deterministic artifact hints

For review efficiency, the initializer may emit non-decisional hints such as:

- `INCIDENT_PATH`
- `TEMPLATE_PATH`
- `RUNBOOK_PATH`
- `README_PATH`
- `STANDARD_POLICY_PATH`
- `PROJECT_DOC_PATH`
- `CHECKPOINT_HANDOFF_PATH`
- `CHAT_HISTORY_RECORD`
- `DRIFT_LOG_CONTAINER`
- `UNKNOWN`

Hint precedence is deliberately conservative: templates, runbooks, standards, and project documents are detected before generic drift/incident filename patterns so the word `drift` alone cannot make an artifact look incident-like.

## Output

Private screening state belongs under:

`openai-defensive-drift-private/adjudication-working/suitability-screening/`

The initializer creates:

- `screening-worklist.csv` — one row per core packet;
- `screening-summary.json` — machine-readable counts;
- `screening-summary.md` — human-readable review summary;
- `README.md` — field vocabulary and workflow notes.

The initializer is transactional: all 100 packet manifests and source copies are validated before the canonical screening directory is promoted into place.

## After screening

Unsuitable records remain in the audit trail and are not deleted. Replacement observations, when needed, come from the 50-entry expansion reserve and retain their original queue/provenance identities.

Suitable records proceed to historical-context assembly. Only after the relevant historical incidents and supporting evidence are assembled does the human adjudication protocol assign relationship ground truth.
