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

## Public/private research boundary

Defensive Drift deliberately separates source evidence from public research artifacts.

### Canonical raw evidence

Operational source evidence remains in its existing canonical private location and is treated as immutable input.

Original raw records are **not moved, renamed, rewritten, or deleted** by this project.

### Private research workspace

Private derived work may include:

- source indexes;
- candidate-case references;
- adjudication working notes;
- sanitization staging;
- rejected or non-public cases;
- private experiment material.

### Public repository

This repository contains only material intended for public research distribution, including methodology, schemas, evaluator code, approved sanitized/synthetic cases, reproducibility artifacts, public results, and the research website source.

The intended flow is:

`canonical raw source → derived private working representation → human adjudication → sanitization → public-release review → approved public artifact`

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
  pre-grant/                  Frozen experiment plan and run manifest

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
- metric contract committed.

### In progress

- M2 candidate-case inventory;
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
