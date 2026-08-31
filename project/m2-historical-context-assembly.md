# M2 Historical-Context Assembly

## Current state

Human suitability screening is complete for the 100-case benchmark pool:

- 78 suitable observations from the original 100-case core review;
- 22 suitable observations from the replacement review;
- 100 suitable observations total;
- relationship ground truth remains unassigned.

## Why this gate exists

The frozen adjudication protocol requires every benchmark observation to be evaluated against supplied historical incidents before assigning `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE`.

Similarity is retrieval assistance only. It is not ground truth.

## First-pass retrieval method

`experiments/pre-grant/m2-build-historical-context-index.py` creates a deterministic metadata-only candidate index for each of the 100 suitable observations.

Retrieval signals include:

- exact Git-blob identity;
- exact raw Drift ID identity;
- token overlap across title, path, Drift ID, and raw recurrence metadata;
- repository affinity;
- model-group affinity;
- template-family affinity;
- explicit timestamp ordering when a timestamp can be parsed from preserved metadata.

Known newer or same-time records are not supplied as historical context when both observation and candidate timestamps are explicitly available. Unknown timestamp ordering remains eligible but is marked `TEMPORAL_RELATION_UNKNOWN`.

## Scientific boundary

The retrieval pass does **not** assign relationship ground truth and does not infer hidden facts.

A retrieved record may ultimately be irrelevant, a mirror, a duplicate, a recurrence, related-but-distinct, or insufficient evidence. Human review against the preserved source evidence determines that later.

## Outputs

Private staging under `adjudication-working/historical-context/` contains:

- `suitable-pool-100.csv` — the canonical 100-observation suitability pool;
- `historical-context-candidates.csv` — deterministic retrieval candidates for each observation;
- `build-summary.json` — retrieval coverage counts and method metadata;
- `README.md` — private-stage boundary documentation.

## Next gate

After the retrieval index is built and checked, the next stage materializes the retrieved historical evidence, reviews context sufficiency, and then performs human relationship adjudication using `benchmark/ground-truth/ADJUDICATION-PROTOCOL.md`.
