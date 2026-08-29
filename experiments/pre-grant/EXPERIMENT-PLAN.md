# Defensive Drift — Pre-Grant Experiment Plan

## Research question

Can AI systems reliably distinguish a genuinely new defensive-security issue from a duplicate, recurrence, related-but-distinct issue, or an observation with insufficient evidence?

## Frozen classes

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

## Source evidence corpus

The historical drift corpus is heterogeneous and cross-model.

`MikeHacksAI/mikehacksai-drift-records/raw/confirmed-incidents/` is the current curated **ChatGPT drift stream**. It is not the complete historical evidence universe.

Valid historical drift evidence may also exist:

- elsewhere in `mikehacksai-drift-records`, including legacy `drifts/`, `inbox/`, and older top-level records;
- inside other MikeHacksAI repositories where model-specific drift records were originally preserved;
- in records created by Claude, Gemini, other AI systems, or older workflows;
- in historical formats that predate the current canonical drift template.

Evidence validity is independent of template conformity. A historical record must not be excluded merely because it does not match the current ChatGPT template.

### Source-preservation rule

M2 discovery is read-only against every source repository. Defensive Drift must never move, rename, rewrite, normalize in place, delete, or commit changes to source drift records.

All generated indexes, normalization, adjudication, deduplication analysis, relationship metadata, and benchmark-case representations belong in `MikeHacksAI/openai-defensive-drift-private`.

For each discovered source record, preserve as much of the following provenance as evidence supports:

- source repository;
- source-relative path;
- source branch and commit SHA;
- Git blob SHA when tracked;
- read-copy SHA-256;
- source AI/model when explicitly known;
- raw model-provenance text when present;
- historical template family / parser disposition;
- discovery signals and confidence.

Unknown provenance remains `UNKNOWN`; it is never guessed.

### Template heterogeneity rule

The current ChatGPT schema is a normalization target, not an ingestion requirement.

Discovery must retain:

- current-template records;
- legacy structured records;
- partially structured records;
- free-form drift records that are still valid evidence.

Legacy material is normalized only as a **derived private representation**, while the source record remains untouched.

## Evaluation sequence

1. Cross-model, cross-repository drift evidence discovery
2. Private normalization and provenance capture
3. Human ground truth
4. Exact/normalized lexical baseline
5. TF-IDF similarity baseline
6. Embedding similarity baseline
7. OpenAI model evaluation
8. Open-weight GPU evaluation where practical
9. Repeated high-risk trials
10. Failure-mode analysis

## Split discipline

Development cases may be used for threshold or prompt development.

Frozen test cases may not be used to tune thresholds or prompts.

## Required AI output

- relationship
- matched incident IDs
- remediation state
- severity
- confidence
- cited evidence IDs
- reasoning summary
- escalation recommendation

## Headline safety metric

Dangerous false-duplicate rate.

Aggregate F1 must never hide dangerous false duplicates.

## Repetition

High-risk and ambiguous cases receive repeated identical-input trials for selected AI configurations.

## Required run provenance

Every run preserves:

- run ID
- benchmark version
- Git commit SHA
- method/model ID
- parameters
- timestamp
- case IDs
- raw predictions
- ground truth
- cost
- latency

## Success definition

The experiment succeeds when it produces reproducible evidence showing where AI helps, where simpler methods remain competitive, which failures matter defensively, and what level of human review remains necessary.

AI is not required to win every comparison.