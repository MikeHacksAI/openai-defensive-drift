# Defensive Drift — Grant Evidence Matrix

**Purpose:** Tie every substantive grant claim to a reproducible artifact, measured result, or clearly identified planned deliverable.

This matrix should be updated continuously during the 35-day sprint. Claims without evidence should not be promoted into the final application as established facts.

## Status legend

- `PLANNED` — work not yet completed
- `IN_PROGRESS` — artifact exists but evidence is incomplete
- `MEASURED` — result exists and has been checked
- `PUBLIC` — evidence is safely available to reviewers/public
- `BLOCKED` — cannot currently be substantiated

## Core evidence matrix

| Grant claim / question | Required evidence | Repository / public artifact | Status |
|---|---|---|---|
| Defensive Drift addresses a concrete reconciliation problem | Existing incident/drift workflow plus benchmark motivation | `research/methodology.md`, sanitized case examples | PLANNED |
| The project has begun before grant submission | Dated commits, sprint plan, benchmark and experiment artifacts | Git history; `project/35-day-sprint.md` | IN_PROGRESS |
| Research scope is intentionally focused | Frozen protocol and explicit scope exclusions | `project/35-day-sprint.md`, experiment plan | IN_PROGRESS |
| We created a new defensive-security benchmark | Versioned benchmark manifest and schema-valid cases | `benchmark/` | PLANNED |
| Ground truth is human adjudicated | Per-case adjudication records and process | `benchmark/ground-truth/`, adjudication protocol | PLANNED |
| Public data is sanitized and appropriate to release | Dataset card, sanitization rules, audit record | `datasets/DATASET-CARD.md` | PLANNED |
| Conventional methods have meaningful limitations | Lexical/TF-IDF/embedding results | `experiments/pre-grant/*`, results table | PLANNED |
| Frontier AI can be compared fairly to non-AI methods | Same frozen benchmark, same scoring contract | `project/metrics.md`, run manifests | IN_PROGRESS |
| Current AI has measurable security-relevant failure modes | Individual failures plus aggregate rates | `experiments/pre-grant/failures/` | PLANNED |
| False duplicate classification is a meaningful safety risk | Ground-truth examples and dangerous false-duplicate metric | failure catalog; `project/metrics.md` | IN_PROGRESS |
| AI evidence grounding can be measured | Grounding rubric and scored results | metrics contract; evaluation outputs | IN_PROGRESS |
| Unsupported remediation claims can be detected | Dedicated metric and failure examples | metrics contract; failure catalog | IN_PROGRESS |
| Model confidence may not equal reliability | Repeated trials / calibration analysis | AI experiment results | PLANNED |
| Results are reproducible | Evaluator code, benchmark version, run ID, commit SHA, model config | `evaluator/`, run manifests | PLANNED |
| The project measures operational practicality | Cost/case and latency/case results | experiment manifests and result tables | PLANNED |
| The project compares open and hosted approaches | OpenAI runs plus cloud-GPU/open-weight baseline | `experiments/pre-grant/openai/`, open-model results | PLANNED |
| Existing Azure resources reduce infrastructure funding needs | Azure workload/deployment documentation and measured usage | `docs/` / deployment notes | PLANNED |
| Requested direct funding buys dedicated research execution | Timeboxed work plan mapped to deliverables | budget + sprint plan | PLANNED |
| Requested API credits are tied to specific evaluation work | Estimated/actual inference plan and run volumes | budget + experiment plan | PLANNED |
| Reduced funding can still produce useful output | Scoped lower funding tier | `grant/budget.md` | PLANNED |
| Expanded funding materially increases public value | Expanded benchmark/review/reproducibility scope | `grant/budget.md` | PLANNED |
| Results will be shared for maximal public benefit | Public repo, research site, methodology, safe benchmark subset, PDF | `defensive-drift.mikehacks.ai`, GitHub | PLANNED |
| The proposal remains strictly defensive | Safety boundary and dataset/test environment rules | methodology / safety section | PLANNED |
| The applicant is positioned to execute | Existing working artifacts, reproducible experiments, infrastructure deployment | Git history, site, benchmark, results | PLANNED |

## Evidence required before making quantitative claims

Any grant sentence of the form:

> “Method X improved metric Y by Z%.”

must map to all of the following:

- [ ] benchmark version
- [ ] test-case count
- [ ] ground-truth version
- [ ] evaluator commit SHA
- [ ] run ID
- [ ] exact method/model identifier
- [ ] raw predictions retained
- [ ] aggregate metric calculation retained
- [ ] limitations noted

## High-value preliminary findings to look for

These are **research questions, not assumed outcomes**.

- Does lexical matching miss semantically equivalent incidents described with different terminology?
- Do embeddings incorrectly merge similar symptoms with different root causes?
- Does a frontier model reduce duplicate-detection errors?
- Does a frontier model introduce unsupported remediation statements?
- Are false duplicate classifications concentrated in specific categories?
- Does model accuracy degrade as historical context grows?
- Are model confidence scores calibrated to actual correctness?
- Can an inexpensive first-pass method plus frontier escalation preserve accuracy at lower cost?
- Can open-weight GPU inference approach hosted-model quality for selected cases?

Negative, mixed, and inconclusive findings remain valid evidence.

## Grant budget evidence

Before final submission, `grant/budget.md` should map each requested dollar/resource category to a deliverable.

Suggested structure to validate, not yet final:

| Support level | Direct funding | API credits/resources | Measurable output |
|---|---:|---:|---|
| Reduced pilot | TBD | TBD | Smaller benchmark + baselines + public report |
| Expanded research | TBD | TBD | Larger benchmark + broader AI evaluation + reference pipeline |
| Full research program | TBD | TBD | Six-month research program, expanded benchmark, reproducibility tooling, public release |

Do not lock exact grant amounts here until the budget is reviewed against the current program terms and the actual pre-grant cost measurements.

## Reviewer-path test

By the October 2 gate, a reviewer should be able to move through this chain without taking our claims on faith:

1. Read the project problem statement.
2. Inspect the methodology.
3. Inspect the benchmark description and schema.
4. See how ground truth was defined.
5. See conventional baseline results.
6. See AI model results.
7. Inspect selected failure cases.
8. Reproduce or understand the evaluation procedure.
9. See actual cost/latency data.
10. Understand exactly what additional grant funding would enable.

If any major link in this chain is missing, the evidence matrix should show it as unfinished rather than hiding the gap.

## Final application rule

**Measured claims cite measured evidence. Planned work is labeled planned. Aspirations are never presented as completed results.**
