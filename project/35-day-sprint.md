# Defensive Drift — 35-Day Pre-Grant Research Sprint

**Sprint start:** 2026-08-29  
**Grant-readiness target:** 2026-10-02  
**Primary objective:** Turn Defensive Drift from a project concept into a measured, reproducible defensive-security research prototype with enough public evidence to support a credible full research-grant request.

## Operating rule

Every week must end with a measurable artifact committed to GitHub. Every experiment must produce machine-readable results. Every material claim intended for the grant application must map to evidence.

## Definition of grant-ready

By 2026-10-02, the repository should contain:

- a frozen research protocol;
- a benchmark schema and ground-truth schema;
- at least 50 human-adjudicated benchmark cases, stretch target 75;
- lexical, TF-IDF/similarity, and embedding baselines;
- OpenAI-model evaluation;
- at least one open-weight GPU-hosted comparison where practical;
- repeated trials for high-risk/ambiguous cases;
- precision, recall, F1, dangerous false-duplicate rate, evidence-grounding accuracy, remediation-state accuracy, cost, and latency measurements;
- an explicit model failure-mode catalog;
- reproducible evaluator code and machine-readable run artifacts;
- a public methodology and preliminary-results report;
- a public research site at `defensive-drift.mikehacks.ai`;
- a concise preliminary-results PDF suitable for grant-review context;
- a grant evidence matrix tying every major application claim to proof;
- budget tiers for reduced, expanded, and full research support.

## Scope boundary

This sprint is for **research evidence**, not production SaaS polish.

Do not allow these to block the October 2 gate:

- enterprise authentication;
- multi-user account systems;
- mobile applications;
- elaborate dashboards;
- autonomous remediation;
- Kubernetes;
- huge datasets;
- broad 20-model comparisons;
- unrelated infrastructure refactoring.

## Week 1 — Research design
### 2026-08-29 through 2026-09-04

**Goal:** Freeze the research question, labels, metrics, data-handling rules, and experimental protocol before model results are known.

### Daily execution

- **Aug 29 — Day 1:** Lock project scope, grant-readiness definition, milestone calendar, and experiment boundaries.
- **Aug 30:** Define incident taxonomy and benchmark case schema.
- **Aug 31:** Define ground-truth labels and adjudication protocol.
- **Sep 1:** Freeze metric definitions and dangerous-failure criteria.
- **Sep 2:** Define sanitization, privacy, confidentiality, and public-release rules.
- **Sep 3:** Write the pre-grant experiment protocol and run-manifest format.
- **Sep 4:** Review and freeze methodology v0.1.

### Required labels

At minimum:

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

Each case should also support remediation state, severity, confidence, evidence references, and relationships to historical incidents.

### Week 1 acceptance gate

- [ ] Research question frozen
- [ ] Incident schema committed
- [ ] Ground-truth schema committed
- [ ] Metrics contract committed
- [ ] Sanitization rules committed
- [ ] Experiment protocol committed
- [ ] No benchmark-result tuning has occurred before protocol freeze

## Week 2 — Benchmark v0.1
### 2026-09-05 through 2026-09-11

**Goal:** Build the human-adjudicated benchmark that all later methods will be evaluated against.

### Target distribution

| Class | Stretch target |
|---|---:|
| True duplicate | 15 |
| Recurrence | 15 |
| Related but distinct | 15 |
| New | 15 |
| Insufficient/conflicting evidence | 15 |
| **Total** | **75** |

### Daily execution

- **Sep 5–6:** Select candidate incidents; exclude unsuitable/private material; begin sanitization.
- **Sep 7–8:** Construct and adjudicate first 25 cases.
- **Sep 9:** Consistency review and schema validation.
- **Sep 10:** Complete cases 26–50.
- **Sep 11:** Stretch toward 75; freeze benchmark v0.1.

### Week 2 acceptance gate

- [ ] Minimum 50 cases
- [ ] Stretch target 75 cases
- [ ] 100% human-adjudicated ground truth
- [ ] 100% schema-valid cases
- [ ] 0 credentials in public artifacts
- [ ] 0 PII in public artifacts
- [ ] 0 confidential/private raw evidence unintentionally released
- [ ] Benchmark version identifier recorded

## Week 3 — Non-AI baselines
### 2026-09-12 through 2026-09-18

**Goal:** Establish reproducible conventional baselines before evaluating LLMs.

### Required methods

1. Exact/normalized lexical matching
2. TF-IDF or equivalent lexical-similarity baseline
3. Embedding similarity

### Daily execution

- **Sep 12:** Implement evaluator framework and run-manifest schema.
- **Sep 13:** Exact/normalized lexical baseline.
- **Sep 14:** TF-IDF/similarity baseline.
- **Sep 15:** Embedding baseline.
- **Sep 16:** Tune thresholds only on explicitly designated development cases.
- **Sep 17:** Run frozen evaluation.
- **Sep 18:** Verify, document, and commit baseline results.

### Every run records

- run ID;
- Git commit SHA;
- benchmark version;
- method/model;
- timestamp;
- case count;
- predictions;
- ground truth;
- precision;
- recall;
- F1;
- false-positive count;
- false-negative count;
- dangerous false-duplicate count/rate;
- latency;
- cost where applicable.

### Week 3 acceptance gate

- [ ] All three baseline classes implemented
- [ ] Frozen benchmark used for final comparison
- [ ] Machine-readable predictions retained
- [ ] Reproducible summary metrics generated
- [ ] No qualitative-only conclusions

## Week 4 — AI evaluation
### 2026-09-19 through 2026-09-25

**Goal:** Compare frontier and practical open-weight AI approaches against the frozen benchmark and conventional baselines.

### Required tracks

**Track A — OpenAI**

Evaluate at least one economical configuration and one stronger reasoning configuration. Record exact model identifiers and parameters at run time rather than hard-coding assumptions in the methodology.

**Track B — Open-weight / cloud GPU**

Where practical, run at least one open-weight model using the cloud-GPU infrastructure selected for the project.

### Daily execution

- **Sep 19–20:** Implement structured model interface and response-validation path.
- **Sep 21:** First OpenAI evaluation run.
- **Sep 22:** Second OpenAI model/configuration run.
- **Sep 23:** Open-weight GPU baseline.
- **Sep 24:** Repeated trials on high-risk and ambiguous cases.
- **Sep 25:** Freeze raw AI results and failure records.

### Repetition target

For high-risk cases, run at least three independent trials per selected model/configuration to measure consistency.

### Week 4 acceptance gate

- [ ] >=50 benchmark cases evaluated
- [ ] >=3 overall evaluation approaches represented
- [ ] Repeated trials performed on high-risk cases
- [ ] Raw outputs stored in machine-readable form
- [ ] Cost measured
- [ ] Latency measured
- [ ] Ground truth not modified post hoc to improve model scores
- [ ] Interesting failures captured individually

## Week 5 — Grant evidence package
### 2026-09-26 through 2026-10-02

**Goal:** Stop expanding scope and convert the experiment into reviewer-ready evidence.

### Daily execution

- **Sep 26:** Verify aggregate results and data integrity.
- **Sep 27:** Draft `research/preliminary-results.md`.
- **Sep 28:** Generate final research figures and tables.
- **Sep 29:** Publish minimum viable `defensive-drift.mikehacks.ai` research site.
- **Sep 30:** Produce concise preliminary-results PDF.
- **Oct 1:** Rewrite the grant application using measured evidence.
- **Oct 2:** Run formal grant-readiness go/no-go review.

### Required public evidence

- project overview;
- methodology;
- benchmark description;
- preliminary results;
- reproducibility instructions;
- selected safe failure examples;
- GitHub source;
- research brief PDF.

## October 2 grant-readiness scorecard

### Benchmark
- [ ] >=50 adjudicated cases
- [ ] Stretch: >=75 cases
- [ ] Schema published
- [ ] Dataset card published
- [ ] Sanitization audit complete

### Baselines
- [ ] Lexical baseline
- [ ] TF-IDF/similarity baseline
- [ ] Embedding baseline
- [ ] Reproducible results

### AI evaluation
- [ ] OpenAI evaluation
- [ ] Open-weight GPU evaluation or documented reason omitted
- [ ] Repeated trials
- [ ] Cost measured
- [ ] Latency measured

### Research findings
- [ ] Duplicate precision
- [ ] Duplicate recall
- [ ] F1
- [ ] Novel-issue recall
- [ ] Dangerous false-duplicate rate
- [ ] Evidence-grounding accuracy
- [ ] Remediation-state accuracy
- [ ] Failure catalog

### Public artifacts
- [ ] GitHub repository organized
- [ ] Methodology published
- [ ] Preliminary results published
- [ ] Public sanitized dataset/subset where safe
- [ ] Research website live
- [ ] Research brief PDF live

### Grant package
- [ ] Proposal <=3,000 words
- [ ] Problem statement <=200 words
- [ ] Project timeline
- [ ] Reduced funding tier
- [ ] Expanded funding tier
- [ ] Full funding tier
- [ ] Full-research-grant request justified
- [ ] Evidence matrix complete

## Daily operating rhythm

### Start of day

Update the active milestone issue with:

- today's three highest-priority tasks;
- blockers;
- target artifact;
- yesterday's measured progress.

### End of day

Record:

- completed work;
- measured result;
- artifact paths;
- run IDs / commit SHAs;
- blockers;
- next-day target.

Keep daily updates concise. This repository is an evidence trail, not a diary.

## Priority definition

**P0:** Failure to complete the task threatens the 2026-10-02 grant-readiness target.  
**P1:** Important to evidence quality but can slip without blocking the grant-readiness gate.  
**P2:** Valuable after the pre-grant sprint or when spare capacity exists.

## Infrastructure principle

Azure and cloud-GPU work should support the same research outputs whenever possible. Infrastructure work is justified during this sprint only when it directly enables benchmark storage, experiment execution, observability, reproducibility, result publication, or public research access.
