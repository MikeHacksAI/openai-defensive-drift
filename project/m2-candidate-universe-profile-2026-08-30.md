# M2 Candidate-Universe Profile — 2026-08-30

This checkpoint records the measured composition of the completed Defensive Drift M2 discovery-candidate universe before human benchmark adjudication begins.

## Source checkpoint

- Candidate inventory: **1,914 records**
- Candidate inventory SHA-256: `44bd45ab2895b0195bbbe9d54e110a25f51356b5b880166cdc264bbae50fd016`
- Private candidate-profile commit: `e8830bdf57b3d4cdede8d62a99e721a6ef7a34eb`
- Ground-truth labels assigned during profiling: **0**
- Candidate records deleted during profiling: **0**

## Integrity profile

- Unique `combined_candidate_id` values: **1,914**
- Candidates with explicit Drift ID: **811**
- Candidates with explicit severity metadata: **1,133**
- Candidates with explicit recurrence metadata: **275**
- Candidates with non-`UNKNOWN` model provenance: **1,113**
- Exact-content identity groups containing more than one candidate: **402**
- Candidate memberships inside those exact-content groups: **976**

Exact-content identity is a relationship hint only. It does not automatically establish benchmark ground truth and no record is deleted merely because another candidate has identical content.

## Repository skew

The candidate universe is highly concentrated in the canonical drift-records repository:

| Repository | Candidates |
|---|---:|
| `mikehacksai-drift-records` | 1,864 |
| `ai-collaboration-governance` | 29 |
| `cloud-mounts-project` | 4 |
| `mikehacksai-engineering-standards` | 4 |
| `logseq-restructure` | 2 |
| twelve additional repositories | 1 each |

This means a naive top-N or simple random queue could still produce a benchmark dominated by one operational source. The human-review queue therefore uses deliberate stratification. This is appropriate because Defensive Drift is constructing an evaluation benchmark, not estimating the real-world prevalence of drift types across MikeHacksAI repositories.

## Model provenance

| Source model | Candidates |
|---|---:|
| ChatGPT | 860 |
| `UNKNOWN` | 801 |
| GitHub Copilot | 93 |
| Gemini | 88 |
| ChatGPT/OpenAI | 56 |
| Claude | 8 |
| `OTHER_EXPLICIT` | 8 |

The review queue must preserve rare model provenance rather than allowing the largest provider/model groups to crowd it out.

## Template families

| Template family | Candidates |
|---|---:|
| `LEGACY_PARTIAL` | 1,044 |
| `LEGACY_STRUCTURED` | 529 |
| `CHATGPT_CURRENT_CANONICAL` | 276 |
| `UNSTRUCTURED_CANDIDATE` | 64 |
| `CURRENT_STRUCTURED_VARIANT` | 1 |

Historical template conformity remains a provenance characteristic rather than an eligibility rule.

## Recurrence metadata

Only **275/1,914** candidates contain explicit recurrence metadata. Because the benchmark must distinguish `RECURRENCE` from `DUPLICATE`, explicit recurrence evidence receives deliberate review priority without being treated as ground truth.

## Exact-content groups

The profile found **402** exact-content groups covering **976** candidate memberships. Some groups are large, including groups with 29 and 27 members.

These groups are useful for finding repeated evidence and historical relationships, but a benchmark queue must prevent copied or repeated content from consuming the review budget. Queue construction therefore caps repeated exact-content representation and records group membership as context only.

## Review-queue implication

The next M2 artifact is a stratified human-adjudication queue:

- **100 core review candidates**;
- **50 expansion/replacement reserve candidates**;
- cross-repository and rare-provenance oversampling;
- template-family diversity;
- recurrence-evidence prioritization;
- bounded exact-content repetition;
- deterministic, auditable selection;
- no automatic assignment of `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE`.

Human adjudication under `benchmark/ground-truth/ADJUDICATION-PROTOCOL.md` remains the only mechanism that creates benchmark relationship ground truth.
