# Defensive Drift — Milestones

This file is the authoritative milestone model for the pre-grant sprint.

## Execution rule

The dates below are **latest-acceptable completion dates, not pacing targets**. Defensive Drift runs milestone-to-milestone continuously. The moment an exit gate is satisfied, the next milestone begins. Work is never delayed simply because its originally scheduled calendar date has not arrived.

The project optimizes for **quality + speed + measurable evidence**. It does not stop at an arbitrary minimum count when additional high-quality evidence can be produced quickly.

---

## M1 — Research Design Frozen

**Latest-acceptable date:** 2026-09-04  
**Current execution target:** complete as early as possible, beginning 2026-08-29  
**Purpose:** Prevent post-hoc methodology changes after seeing model results.

### Required outputs

- `benchmark/schema/incident-schema.json`
- `benchmark/schema/ground-truth-schema.json`
- `benchmark/ground-truth/ADJUDICATION-PROTOCOL.md`
- `project/metrics.md`
- dataset sanitization/public-release rules
- `experiments/pre-grant/EXPERIMENT-PLAN.md`
- run-manifest specification

### Exit criteria

- [ ] Incident relationship taxonomy frozen
- [ ] Ground-truth labels frozen
- [ ] Human adjudication rules frozen
- [ ] Dangerous failure definitions frozen
- [ ] Evaluation metrics frozen
- [ ] Public/private data boundary documented
- [ ] Experiment protocol frozen before final benchmark/model evaluation

### Acceleration rule

As soon as these artifacts are complete and internally consistent, M2 starts immediately. Do not wait until September 4.

---

## M2 — Benchmark v0.1 Frozen

**Latest-acceptable date:** 2026-09-11  
**Purpose:** Produce a human-adjudicated evaluation set that can support reproducible comparisons.

### Operational target

- **100 adjudicated cases for benchmark v0.1**
- **150–200 case expansion range** when additional cases improve class coverage, ambiguity coverage, or failure-mode diversity without sacrificing adjudication quality

These are working research targets, not a floor/ceiling game. Freeze decisions are based on scientific usefulness, coverage, validation, and readiness for reproducible comparison.

### Corpus completeness gate

M2 may not begin benchmark candidate selection or freeze from a partial convenience sample.

The detailed rationale, candidate-discovery heuristic, candidate-versus-ground-truth distinction, provenance model, and current M2 execution checkpoint are documented in [`project/m2-corpus-discovery-and-candidate-selection.md`](m2-corpus-discovery-and-candidate-selection.md).

The completed gate review and explicit v0.1 evidence-universe scope are documented in [`project/m2-corpus-completeness-gate-review-2026-08-30.md`](m2-corpus-completeness-gate-review-2026-08-30.md).

The evidence universe must be explicitly inventoried before case selection:

1. **GitHub-wide tracked evidence:** enumerate the authoritative MikeHacksAI repository estate and inspect in-scope tracked Markdown evidence across repositories, not only repositories that happen to be cloned locally.
2. **Local untracked evidence:** inspect untracked Markdown under local Git worktrees because historically valid drift records may exist before commit or outside the current tracked set.
3. **Provenance separation:** tracked and untracked records remain distinguishable. Tracked records preserve repository, branch/ref, commit, blob/path, and content hash where available. Untracked records preserve repository/worktree, relative path, content hash, size, and filesystem provenance while explicitly recording that no Git commit/blob provenance exists.
4. **Explicit exclusions:** archived, empty, unavailable, intentionally excluded, or technically blocked repositories must be listed with reasons. Silence is not an exclusion policy.
5. **Coverage matrix:** the private research workspace must contain a machine-readable repository/evidence coverage report showing what was scanned, what was not, and why.
6. **No source mutation:** corpus discovery is read-only against source repositories and worktrees. Generated indexes, normalization, adjudication, deduplication analysis, and derived benchmark material belong only in `openai-defensive-drift-private`.

A successful narrow scan is evidence of progress, not proof that corpus discovery is complete.

### Required class coverage

Meaningful representation across:

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

### Required outputs

- authoritative repository-universe manifest
- repository/evidence coverage matrix
- combined provenance-aware tracked + untracked candidate inventory
- benchmark manifest
- case folders/artifacts
- ground-truth records
- adjudication notes
- schema validation report
- sanitization audit for any public subset

### Exit criteria

- [x] Authoritative GitHub repository universe inventoried
- [x] GitHub-wide tracked evidence coverage complete or every exclusion/blocker explicitly documented
- [x] Local untracked Markdown evidence audited across available local source worktrees
- [x] Combined tracked + untracked candidate inventory produced with provenance class preserved
- [x] No benchmark candidate selection/freeze occurred from a knowingly partial corpus
- [ ] 100-case v0.1 operational target reached or a documented scientific reason supports freezing at a different count
- [ ] 100% human-adjudicated
- [ ] 100% schema-valid
- [ ] Class distribution documented
- [ ] Ambiguous/high-risk cases deliberately represented
- [ ] No credentials/PII/confidential raw data in public artifacts
- [ ] Benchmark version identifier frozen

### Source-evidence rule

Canonical raw drift evidence is immutable. Benchmark development uses derived copies/references only. No original drift record is moved, renamed, rewritten, or deleted. The evidence universe is not limited to `raw/confirmed-incidents/`; valid historical drift evidence may exist across repositories, `/inbox` locations, other AI-model collections, and older template families.

---

## M3 — Conventional Baselines Complete

**Latest-acceptable date:** 2026-09-18  
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

### Acceleration rule

Baseline implementation may begin on development cases before the full benchmark freezes, but final comparison runs must use the frozen benchmark and frozen thresholds/protocol.

---

## M4 — AI Evaluation Complete

**Latest-acceptable date:** 2026-09-25  
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

- [ ] Full frozen benchmark evaluated
- [ ] At least one economical and one stronger OpenAI configuration evaluated
- [ ] Open-weight GPU comparison completed or omission explicitly justified
- [ ] Repeated trials completed for high-risk/ambiguous subset
- [ ] Model identifiers/configuration preserved
- [ ] Interesting security failure modes documented
- [ ] No ground-truth rewriting to improve scores

---

## M5 — Grant Ready

**Latest-acceptable date:** 2026-10-02  
**Purpose:** Convert research into a reviewer-ready, publicly verifiable grant package.

The public site at `https://defensive-drift.mikehacks.ai` is already live and should evolve continuously as validated public artifacts become available.

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

1. Dates are latest-acceptable gates, not reasons to slow down.
2. Close milestones as soon as acceptance criteria are demonstrably satisfied.
3. Begin the next milestone immediately after the previous gate closes.
4. Parallelize work only when it cannot contaminate frozen methodology or ground truth.
5. Never trade case quality, data safety, methodological integrity, or corpus completeness for raw speed.
6. Never stop merely because a prior minimum count has been reached.
7. All quantitative claims must be traceable to a benchmark version, run ID, and Git commit.
8. If a milestone threatens the latest-acceptable date, cut optional scope before moving the date.
9. Grant-critical evidence-completeness work already identified as in scope must not be deferred as “later” without a concrete blocker or explicit operator approval.
10. A successful script run is not equivalent to a satisfied milestone gate; the gate must be evaluated against all documented acceptance criteria.
