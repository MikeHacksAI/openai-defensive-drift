# M2 Stratified Human-Review Queue Selection

## Purpose

After corpus completeness and candidate-universe profiling pass, Defensive Drift constructs a human-review queue before assigning any benchmark ground truth.

The queue is not intended to mirror the raw prevalence of source repositories or model providers. It is an evaluation-review instrument designed to expose the benchmark-development process to diverse evidence conditions and reduce domination by the largest source corpus.

## Queue size

The initial review queue contains **150 candidates**:

- ranks **1–100**: core human-adjudication tier;
- ranks **101–150**: expansion/replacement reserve.

The reserve supports replacement of unusable cases, class-balance correction after human adjudication, and the planned 150–200-case expansion path when additional cases improve scientific coverage.

## Deterministic selection inputs

Queue construction may use only discovery/provenance metadata that existed before ground-truth adjudication, including:

- source repository;
- source model/provenance;
- template family;
- discovery score;
- presence of explicit severity metadata;
- presence of explicit recurrence metadata;
- presence of a Drift ID;
- exact-content identity group membership;
- deterministic candidate ID hashing for tie-breaking.

It does **not** use model predictions or final benchmark relationship labels.

## Stratification priorities

1. **Cross-repository coverage.** Candidates outside the dominant source repository receive deliberate priority so the benchmark-development queue is not effectively a single-repository sample.
2. **Rare model provenance.** Rare source-model groups receive minimum representation where available.
3. **Template diversity.** Legacy, current-canonical, current-variant, and unstructured candidates receive minimum representation where available.
4. **Recurrence evidence.** Candidates with explicit recurrence metadata receive deliberate priority because recurrence-versus-duplicate reasoning is a core research question.
5. **Discovery-score spread.** Remaining slots are filled with a diversity-aware deterministic ranking rather than a top-score-only rule.
6. **Exact-content repetition control.** Exact-content group membership is preserved as context, but no exact-content group may contribute more than two queued candidates.

## Exact-content relationship rule

Exact-content identity is never an automatic `DUPLICATE` label.

Identical content may reflect copies, migrations, reused templates, repeated records, or genuine repeated evidence. Human adjudication must still establish the relevant incident relationship using the frozen adjudication protocol.

## Auditability

Queue generation produces:

- `review-queue.csv` — ordered human worklist with blank adjudication fields;
- `selection-audit.csv` — all discovery candidates with selected/not-selected status and selection reasons;
- `queue-summary.md` — measured queue composition and selection-policy summary;
- `README.md` — workspace usage notes.

No discovery candidate is deleted from the source inventory when the queue is created.

## Ground-truth boundary

Queue construction assigns **zero** values for the final benchmark relationship classes:

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

The queue only establishes review order. Human adjudication under `benchmark/ground-truth/ADJUDICATION-PROTOCOL.md` creates ground truth.

## Interpretation of benchmark metrics

Because rare sources and provenance types are deliberately oversampled, aggregate benchmark scores must be interpreted as performance on the frozen Defensive Drift evaluation set, not as estimates of real-world drift prevalence in the underlying operational corpus.
