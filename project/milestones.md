# Defensive Drift — Milestones

This file is the authoritative milestone calendar for the 35-day pre-grant sprint.

## M1 — Research Design Frozen

**Deadline:** 2026-09-04  
**Purpose:** Prevent post-hoc methodology changes after seeing model results.

### Required outputs

- `benchmark/schema/incident-schema.json`
- `benchmark/schema/ground-truth-schema.json`
- `project/metrics.md`
- dataset sanitization/public-release rules
- `experiments/pre-grant/EXPERIMENT-PLAN.md`
- run-manifest specification

### Exit criteria

- [ ] Incident relationship taxonomy frozen
- [ ] Ground-truth labels frozen
- [ ] Dangerous failure definitions frozen
- [ ] Evaluation metrics frozen
- [ ] Public/private data boundary documented
- [ ] Experiment protocol frozen before final benchmark/model evaluation

### Failure condition

If M1 is late, model evaluation dates do **not** move automatically. Reduce nonessential scope instead.

---

## M2 — Benchmark v0.1 Frozen

**Deadline:** 2026-09-11  
**Purpose:** Produce a human-adjudicated evaluation set that can support reproducible comparisons.

### Minimum target

- 50 adjudicated cases

### Stretch target

- 75 adjudicated cases

### Required outputs

- benchmark manifest
- case folders/artifacts
- ground-truth records
- adjudication notes
- schema validation report
- sanitization audit for any public subset

### Exit criteria

- [ ] >=50 cases
- [ ] 100% human-adjudicated
- [ ] 100% schema-valid
- [ ] Class distribution documented
- [ ] No credentials/PII/confidential raw data in public artifacts
- [ ] Benchmark version identifier frozen

### Failure condition

If fewer than 50 high-quality cases are ready, do not inflate the dataset with weak cases. Document the shortfall and proceed with a smaller but defensible benchmark only after explicit review.

---

## M3 — Conventional Baselines Complete

**Deadline:** 2026-09-18  
**Purpose:** Establish what simpler approaches can already accomplish before attributing value to LLMs.

### Required methods

- exact/normalized lexical matching
- TF-IDF or equivalent lexical similarity
- embedding similarity

### Required outputs

- evaluator framework
- machine-readable predictions
- run manifests
- aggregate metrics
- threshold-selection notes
- baseline comparison table

### Exit criteria

- [ ] All three baseline classes run
- [ ] Frozen benchmark used for final comparison
- [ ] Precision/recall/F1 calculated
- [ ] Dangerous false-duplicate count/rate calculated
- [ ] Latency recorded
- [ ] Reproduction command/process documented

---

## M4 — AI Evaluation Complete

**Deadline:** 2026-09-25  
**Purpose:** Measure frontier/open-model performance, cost, consistency, and security-relevant failure modes.

### Required outputs

- OpenAI evaluation runs
- open-weight/cloud-GPU evaluation where practical
- repeated high-risk-case trials
- raw structured model outputs
- model/run manifests
- cost and latency measurements
- individual failure records

### Exit criteria

- [ ] >=50 benchmark cases evaluated
- [ ] At least one economical and one stronger OpenAI configuration evaluated
- [ ] Open-weight GPU comparison completed or omission explicitly justified
- [ ] Repeated trials completed for high-risk/ambiguous subset
- [ ] Model identifiers/configuration preserved
- [ ] Interesting security failure modes documented
- [ ] No ground-truth rewriting to improve scores

---

## M5 — Grant Ready

**Deadline:** 2026-10-02  
**Purpose:** Convert research into a reviewer-ready, publicly verifiable grant package.

### Required outputs

- `research/preliminary-results.md`
- final figures/tables
- public research site at `defensive-drift.mikehacks.ai`
- preliminary-results PDF
- completed `grant/evidence-matrix.md`
- grant application draft
- budget tiers
- formal go/no-go review

### Exit criteria

- [ ] Core experimental results verified
- [ ] Public methodology available
- [ ] Public benchmark description available
- [ ] Safe representative failures published
- [ ] Reproducibility instructions published
- [ ] Proposal <=3,000 words
- [ ] Problem statement <=200 words
- [ ] Full research-grant request justified with measurable evidence
- [ ] Every major application claim mapped to an artifact or measured result

---

# Milestone discipline

1. Dates are fixed planning constraints, not estimates to be casually moved.
2. If a milestone is at risk, reduce optional scope before changing the deadline.
3. Every milestone closes only after its acceptance criteria are demonstrably satisfied.
4. A milestone may be marked complete with documented limitations; it may not be marked complete based on intention.
5. All quantitative claims must be traceable to a benchmark version, run ID, and Git commit.
