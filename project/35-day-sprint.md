# Defensive Drift — 35-Day Pre-Grant Research Sprint

**Sprint start:** 2026-08-29  
**Latest grant-readiness date:** 2026-10-02  
**Execution mode:** Aggressive / gate-driven / evidence-first

## Core rule

The 35 days are a **maximum execution window**, not a schedule to fill. Every milestone begins as soon as its dependency gate is satisfied. If M1 closes today, M2 begins today. If M2 closes early, baselines begin immediately. No task waits for its originally assigned calendar date.

Every work block should produce one of four things:

1. a frozen research definition;
2. a benchmark/data artifact;
3. a reproducible experiment/result;
4. a reviewer-facing evidence artifact.

The project does not optimize for doing the minimum. It optimizes for producing the strongest defensible evidence as quickly as quality allows.

## Definition of grant-ready

By the time the package is submitted, the project should contain:

- frozen incident and ground-truth schemas;
- frozen human adjudication protocol;
- frozen metrics and dangerous-failure definitions;
- a benchmark v0.1 targeting **100 adjudicated cases**;
- expansion toward **150–200 cases** when scientifically useful and operationally fast;
- lexical, TF-IDF/similarity, and embedding baselines;
- OpenAI model evaluation;
- at least one open-weight/cloud-GPU comparison where practical;
- repeated trials on high-risk and ambiguous cases;
- dangerous false-duplicate, grounding, remediation, latency, cost, and consistency measurements;
- a failure-mode catalog;
- reproducible evaluator code and run artifacts;
- a public methodology and preliminary-results report;
- the live public research site at `https://defensive-drift.mikehacks.ai`;
- a concise preliminary-results PDF;
- a grant evidence matrix;
- reduced, expanded, and full funding scenarios.

## Scope protection

This sprint exists to create research evidence, not production SaaS polish. Do not let these block grant readiness:

- enterprise authentication;
- multi-user systems;
- mobile applications;
- elaborate dashboards;
- autonomous remediation;
- Kubernetes;
- unrelated infrastructure refactoring;
- broad model catalogs with little research value.

## M1 — Research design freeze

**Latest-acceptable date:** 2026-09-04  
**Accelerated target:** complete as early as possible, beginning on Day 1.

Required:

- `benchmark/schema/incident-schema.json`
- `benchmark/schema/ground-truth-schema.json`
- `benchmark/ground-truth/ADJUDICATION-PROTOCOL.md`
- `project/metrics.md`
- sanitization/public-release rules
- `experiments/pre-grant/EXPERIMENT-PLAN.md`
- run-manifest specification

Exit gate:

- [ ] relationship taxonomy frozen
- [ ] remediation-state vocabulary frozen
- [ ] severity scale frozen
- [ ] human adjudication rules frozen
- [ ] dangerous false-duplicate definition frozen
- [ ] evidence-grounding rubric frozen
- [ ] public/private data boundary documented
- [ ] final benchmark evaluation cannot alter methodology after seeing results

## M2 — Benchmark v0.1

**Latest-acceptable date:** 2026-09-11  
**Operational target:** 100 human-adjudicated cases  
**Immediate expansion range:** 150–200 when quality remains high

All five classes must receive meaningful coverage:

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

Process:

1. identify candidate incidents and controlled/synthetic scenarios;
2. create derived working representations only;
3. preserve canonical raw evidence unchanged;
4. adjudicate in batches;
5. schema-validate continuously;
6. run consistency review continuously;
7. freeze v0.1 when coverage, quality, validation, and reproducibility gates are satisfied.

Exit gate:

- [ ] 100-case v0.1 target reached or a documented scientific freeze decision explains another count
- [ ] 100% human-adjudicated
- [ ] 100% schema-valid
- [ ] class distribution documented
- [ ] ambiguous/high-risk cases deliberately included
- [ ] public subset sanitized
- [ ] no credentials/PII/confidential raw evidence released
- [ ] benchmark version frozen

## M3 — Conventional baselines

**Latest-acceptable date:** 2026-09-18

Required methods:

1. exact/normalized lexical matching;
2. TF-IDF or equivalent lexical similarity;
3. embedding similarity.

Development implementation may begin before M2 closes, but final head-to-head measurements must use the frozen benchmark and frozen evaluation protocol.

Every final run records:

- run ID;
- Git commit SHA;
- benchmark version;
- method/model identifier;
- timestamp;
- predictions;
- ground truth;
- precision;
- recall;
- F1;
- dangerous false-duplicate count/rate;
- grounding/remediation metrics where applicable;
- latency;
- attributable cost.

## M4 — AI evaluation

**Latest-acceptable date:** 2026-09-25

Required tracks:

**OpenAI:** at least one economical configuration and one stronger reasoning configuration, with exact model IDs preserved at run time.

**Open-weight/cloud GPU:** at least one practical comparison when infrastructure permits.

For high-risk/ambiguous cases, use repeated independent trials to measure consistency and closure-risk disagreement.

Exit gate:

- [ ] full frozen benchmark evaluated
- [ ] multiple AI configurations represented
- [ ] repeated high-risk trials complete
- [ ] raw structured outputs preserved
- [ ] cost and latency measured
- [ ] ground truth unchanged post hoc
- [ ] individual security-relevant failures cataloged

## M5 — Grant evidence package

**Latest-acceptable date:** 2026-10-02

This work runs partially in parallel. The public site is already live and should be updated only with validated, grant-relevant evidence.

Required:

- `research/preliminary-results.md`;
- figures and comparison tables;
- methodology page;
- benchmark description;
- reproducibility instructions;
- safe representative failure cases;
- preliminary-results PDF;
- completed evidence matrix;
- <=3,000-word proposal;
- <=200-word problem statement;
- funding tiers;
- formal go/no-go review.

## Daily operating rhythm

### Start of work block

Record only what matters:

- current milestone;
- top P0 tasks;
- blocker, if any;
- artifact expected from the block.

### End of work block

Record:

- completed artifact;
- measured result, if any;
- commit SHA / run ID;
- next dependency gate.

This repository is an evidence trail, not a diary.

## Priority definition

**P0:** Required to close the current gate or protect research validity.  
**P1:** Improves evidence quality but does not block the current gate.  
**P2:** Valuable after grant readiness or when there is spare capacity.

## Infrastructure principle

Azure credits and cloud-GPU spending should do double duty: directly enable benchmark storage, experiment execution, observability, reproducibility, or publication while also creating defensible cloud-workload evidence. Infrastructure work that does not advance the research is deferred.
