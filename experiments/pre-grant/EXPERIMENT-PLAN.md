# Defensive Drift — Pre-Grant Experiment Plan

## Research question

Can AI systems reliably distinguish a genuinely new defensive-security issue from a duplicate, recurrence, related-but-distinct issue, or an observation with insufficient evidence?

## Frozen classes

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

## Evaluation sequence

1. Human ground truth
2. Exact/normalized lexical baseline
3. TF-IDF similarity baseline
4. Embedding similarity baseline
5. OpenAI model evaluation
6. Open-weight GPU evaluation where practical
7. Repeated high-risk trials
8. Failure-mode analysis

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