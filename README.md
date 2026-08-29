# Defensive Drift

**AI security-drift reconciliation research by MikeHacksAI**

> **Research question:** Can AI reliably distinguish a genuinely new security problem from a duplicate, recurrence, related-but-distinct issue, or an already-remediated condition while grounding its decision in evidence?

🌐 **Research site:** https://defensive-drift.mikehacks.ai  
📊 **Current phase:** M2 — Benchmark construction  
🧪 **Methodology status:** M1 research design frozen  
🔐 **Research posture:** Defensive, evidence-grounded, human-adjudicated

---

## What is Defensive Drift?

Defensive Drift is an open defensive-security research project focused on a common operational problem: security findings often reappear across logs, configuration changes, scanner output, incident records, deployment history, support conversations, and AI-assisted engineering sessions.

The hard part is not merely finding similar text. The hard part is determining whether a new observation is:

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

A poor reconciliation system can create alert fatigue by opening unnecessary duplicate incidents. More dangerously, it can suppress a genuinely new or recurring issue by incorrectly deciding that it has already been handled.

Defensive Drift is building a reproducible benchmark, evaluator, and reference pipeline for measuring that problem directly.

---

## Why this matters

Security operations produce fragmented evidence. The same underlying condition may surface through different tools and different wording, while two superficially similar findings may actually have different root causes or remediation requirements.

This creates an important AI-safety and defensive-security question:

**When should an AI system confidently reconcile an observation with historical evidence, and when should it escalate rather than collapse uncertainty into a duplicate?**

The project treats the **dangerous false-duplicate rate** as a headline safety metric. Aggregate accuracy or F1 is not sufficient if a method hides unresolved defensive issues.

---

## Research design

The benchmark evaluates each new observation against supplied historical incidents and evidence.

### Relationship classes

| Class | Meaning |
|---|---|
| `NEW` | No supplied historical incident adequately represents the observed condition. |
| `DUPLICATE` | The same underlying condition is already represented and does not require a separate incident. |
| `RECURRENCE` | A substantially similar condition returned after mitigation, remediation, closure, or apparent absence. |
| `RELATED_BUT_DISTINCT` | The observation is related to prior history but differs materially in root cause, affected component, consequence, or remediation. |
| `INSUFFICIENT_EVIDENCE` | Available evidence cannot safely support a stronger classification. |

### Remediation states

The research schema supports:

- `DETECTED`
- `ACKNOWLEDGED`
- `MITIGATED`
- `PARTIALLY_REMEDIATED`
- `REMEDIATED`
- `RECURRED`
- `UNRESOLVED`
- `UNKNOWN`

### Evaluation tracks

The planned head-to-head evaluation includes:

1. exact / normalized lexical matching;
2. TF-IDF or equivalent lexical similarity;
3. embedding similarity;
4. OpenAI model evaluation;
5. open-weight model evaluation on cloud GPU infrastructure where practical;
6. repeated trials on high-risk and ambiguous cases.

The same frozen benchmark cases will be used for final comparisons.

---

## Primary metrics

Defensive Drift tracks conventional performance metrics and security-specific failure metrics.

Key measurements include:

- duplicate precision;
- duplicate recall;
- duplicate F1;
- novel-issue recall;
- **dangerous false-duplicate rate**;
- evidence-grounding accuracy;
- unsupported remediation-claim rate;
- remediation-state accuracy;
- severity accuracy;
- confidence calibration;
- prediction consistency;
- latency per case;
- cost per case;
- human review time where feasible.

See [`project/metrics.md`](project/metrics.md) for the frozen metric definitions.

---

## Benchmark construction

The current milestone is **M2 — Benchmark v0.1**.

The operational target is **100 human-adjudicated cases for v0.1**, with an immediate **150–200 case expansion range** when additional cases improve coverage without weakening adjudication quality.

The project does not stop merely because a minimum count has been reached. Benchmark quality, class coverage, provenance, schema validity, and safe public release determine the freeze decision.

Every final benchmark case must have human ground truth and must pass the project’s schema and data-boundary requirements.

---

## Historical evidence corpus

The drift corpus is **heterogeneous and cross-model**.

`MikeHacksAI/mikehacksai-drift-records/raw/confirmed-incidents/` is the current curated **ChatGPT drift stream**. It is not the complete historical evidence universe.

Valid drift evidence may also remain in legacy `drifts/`, `inbox/`, older top-level records, and other MikeHacksAI repositories where Claude, Gemini, other AI systems, or earlier workflows originally preserved drift records.

Historical templates have changed over time. **Template conformity is not an eligibility requirement.** A legacy record remains valid evidence even if it does not match the current ChatGPT drift template.

Source AI/model, repository, path, commit/blob/hash provenance, historical template family, and parser confidence are preserved whenever evidence supports them. Unknown provenance stays `UNKNOWN`; it is not guessed.

---

## Public/private research boundary

Defensive Drift deliberately separates source evidence from public research artifacts.

### Source evidence

Operational drift evidence remains in its original source repository and path and is treated as immutable input.

Original records are **not moved, renamed, rewritten, normalized in place, or deleted** by this project.

### Private research workspace

All generated indexes and derived research work belong in `MikeHacksAI/openai-defensive-drift-private`, including:

- cross-repository source indexes;
- candidate-case references;
- normalized derived representations;
- model/source provenance metadata;
- adjudication working notes;
- deduplication and relationship analysis;
- sanitization staging;
- rejected or non-public cases;
- private experiment material.

### Public repository

This repository contains only material intended for public research distribution, including methodology, schemas, evaluator code, approved sanitized/synthetic cases, reproducibility artifacts, public results, and the research website source.

The intended flow is:

`immutable source record → private reference/index → derived private representation → human adjudication → sanitization → public-release review → approved public artifact`

See [`datasets/SANITIZATION-RULES.md`](datasets/SANITIZATION-RULES.md).

---

## Research integrity rules

Defensive Drift is designed so the evaluation cannot quietly redefine success after seeing model results.

Core rules include:

- frozen test cases are not used to tune final thresholds;
- ground truth is human-adjudicated before final model comparison;
- difficult cases are not removed merely because they hurt performance;
- exclusions require documented reasons;
- negative and inconclusive findings are preserved;
- model predictions never silently rewrite human ground truth;
- remediation claims require evidence;
- uncertainty must not be converted into `DUPLICATE` merely to force a decision;
- every experimental run records benchmark version, method/model, Git commit, run ID, parameters, cost, and latency.

The project is successful if it produces reproducible evidence about **where AI helps, where simpler methods remain competitive, and where AI creates security-relevant failure modes**. AI is not required to win every comparison.

---

## Repository map

```text
benchmark/
  schema/                     Benchmark and ground-truth schemas
  ground-truth/               Human adjudication protocol

datasets/
  sanitized/                  Approved sanitized research data
  synthetic/                  Public-safe synthetic cases
  SANITIZATION-RULES.md       Public/private release rules

experiments/
  pre-grant/                  Experiment plans, manifests, and M2 discovery tooling

evaluator/                    Evaluation implementation
research/                     Research notes and findings
reports/                      Reviewer-facing research reports
project/                      Sprint, milestones, and metrics contracts
grant/                        Grant evidence mapping and proposal support
site/                         Public research website source
```

---

## Key research artifacts

- [`benchmark/schema/incident-schema.json`](benchmark/schema/incident-schema.json) — benchmark incident representation
- [`benchmark/schema/ground-truth-schema.json`](benchmark/schema/ground-truth-schema.json) — human ground-truth representation
- [`benchmark/ground-truth/ADJUDICATION-PROTOCOL.md`](benchmark/ground-truth/ADJUDICATION-PROTOCOL.md) — classification and freeze rules
- [`project/metrics.md`](project/metrics.md) — evaluation metric contract
- [`experiments/pre-grant/EXPERIMENT-PLAN.md`](experiments/pre-grant/EXPERIMENT-PLAN.md) — experiment sequence and integrity requirements
- [`experiments/pre-grant/m2-cross-model-discovery.ps1`](experiments/pre-grant/m2-cross-model-discovery.ps1) — read-only cross-model/cross-repository source discovery
- [`experiments/pre-grant/run-manifest-schema.json`](experiments/pre-grant/run-manifest-schema.json) — reproducibility metadata
- [`datasets/SANITIZATION-RULES.md`](datasets/SANITIZATION-RULES.md) — public/private data handling
- [`project/milestones.md`](project/milestones.md) — research milestone gates
- [`project/35-day-sprint.md`](project/35-day-sprint.md) — accelerated pre-grant research plan
- [`grant/evidence-matrix.md`](grant/evidence-matrix.md) — mapping from grant claims to evidence

---

## Current status

### Completed

- public research repository established;
- public/private research boundary established;
- research site deployed at **https://defensive-drift.mikehacks.ai**;
- Cloudflare Pages deployment connected to GitHub `main`;
- M1 research design frozen;
- incident schema committed;
- ground-truth schema committed;
- human adjudication protocol committed;
- sanitization rules committed;
- experiment plan committed;
- run-manifest schema committed;
- metric contract committed;
- cross-model/multi-template source-evidence rules documented.

### In progress

- M2 cross-model and cross-repository candidate discovery;
- benchmark construction and human adjudication;
- schema validation;
- class-balance review;
- public-safe sanitization/synthetic-case preparation.

### Next

- freeze benchmark v0.1;
- run lexical, TF-IDF, and embedding baselines;
- evaluate frontier and open-weight AI approaches;
- measure failure modes, consistency, cost, and latency;
- publish preliminary results and a reviewer-facing research brief.

**No model-performance claims are published here until they have actually been measured.**

---

## Single-branch project policy

Defensive Drift is intentionally maintained as a **single-branch project**.

- `main` is the sole normal development, research, documentation, and deployment branch.
- Do not create feature, staging, repair, temporary, experiment, deployment, or assistant-specific branches for routine work.
- Local clones stay on `main` and reconcile directly with `origin/main`.
- Local ahead/behind state must be explained and reconciled directly rather than hidden behind new branches.
- A second branch is allowed only when a platform or safety requirement makes it genuinely unavoidable; any such exception must be explicit, temporary, documented before creation, and removed afterward.

---

## Website deployment

GitHub `main` is the authoritative source for the public research site.

The static site under [`site/`](site/) is hosted with **Cloudflare Pages native Git integration**:

`GitHub main → Cloudflare Pages → defensive-drift.mikehacks.ai`

The project intentionally does **not** depend on GitHub Actions for routine website deployment.

Deployment details: [`site/DEPLOYMENT.md`](site/DEPLOYMENT.md)

---

## Safety scope

Defensive Drift is a **defensive-security research project**.

It is intended to evaluate incident reconciliation, evidence grounding, defensive triage, and security-state reasoning. It does not require autonomous exploitation, credential theft, destructive actions, unauthorized access, or blind autonomous remediation.

Human and deterministic approval boundaries remain part of the research design where operational action is involved.

---

## Follow the project

- **Live research site:** https://defensive-drift.mikehacks.ai
- **Repository issues / milestones:** https://github.com/MikeHacksAI/openai-defensive-drift/issues
- **Repository:** https://github.com/MikeHacksAI/openai-defensive-drift

Defensive Drift is being developed in public as a reproducible defensive-security research project. Results — favorable, negative, or inconclusive — will be reported from measured evidence rather than assumed outcomes.
