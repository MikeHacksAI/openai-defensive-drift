# Defensive Drift — Current-State Checkpoint / Grant Rebaseline

**Checkpoint date:** 2026-09-18  
**Repository:** `MikeHacksAI/openai-defensive-drift`  
**Purpose:** Replace the 2026-09-10 chat handoff as the current continuation point without modifying that historical checkpoint.

## 1. Current truth

Defensive Drift remains in Grant M2. M1 is complete. The benchmark and grant research path have not advanced at the same pace as the drift-record governance and automation work.

The last verified public research state contains:

- 100 suitable benchmark observations;
- 1,952 case-to-context relationships;
- 820 unique materialized historical evidence records;
- 820/820 evidence hashes verified;
- 2 legacy non-UTF-8 records preserved byte-for-byte;
- 0/100 human context-sufficiency decisions recorded in the last verified research artifact;
- relationship ground truth still unassigned; and
- no measured model-performance results published.

The active scientific gate therefore remains human context-sufficiency review followed by relationship ground-truth adjudication.

## 2. What changed after the 2026-09-10 checkpoint

The September 10 checkpoint is now historical rather than operational. Subsequent work in the public research repository preserved and reconciled Grok review findings, documented the external-review artifact structure, and created an exact-artifact Grok rereview prompt.

Separately, `MikeHacksAI/mikehacksai-drift-records` advanced substantially in governance and automation. Canonical high-water allocation, generated-state refresh, historical canonical-number reconciliation, and GitHub-based automation progressed independently of the grant benchmark.

As of this checkpoint, the drift-number high-water repository reports:

- last assigned/reserved: `DRIFT-001424`;
- next available: `DRIFT-001425`.

This drift-governance progress is useful engineering evidence, but it does not substitute for completing Grant M2.

## 3. Corrected grant critical path

The project remains grant-first:

1. **M2 — Benchmark v0.1**
   - recover/verify the exact reviewed workbook-generation path;
   - present all 100 cases in a low-friction human review interface/workbook;
   - complete 100 context-sufficiency decisions;
   - expand context only for `MORE_CONTEXT_REQUIRED` cases;
   - complete human relationship adjudication;
   - schema-validate and freeze benchmark v0.1.

2. **M3 — Conventional baselines**
   - exact/normalized lexical matching;
   - TF-IDF or equivalent similarity;
   - embedding similarity;
   - reproducible run manifests and metrics.

3. **M4 — AI evaluation**
   - structured model interface;
   - OpenAI evaluation configurations;
   - practical open-weight comparison where feasible;
   - repeated trials on high-risk/ambiguous cases;
   - cost, latency, consistency, evidence-grounding, and failure analysis.

4. **M5 — Grant-ready evidence package**
   - methodology;
   - benchmark description;
   - preliminary measured results;
   - reproducibility instructions;
   - safe representative failure cases;
   - research brief;
   - evidence matrix;
   - application package.

## 4. Timeline correction

The original accelerated sprint dates remain useful historical planning targets, but the project must not present missed dates as if they are still future gates.

- Original M2 target: 2026-09-11 — missed.
- Original M3 target: 2026-09-18 — blocked by unfinished M2.
- Original M4 target: 2026-09-25 — retained only as an aggressive planning reference, dependent on M2/M3 completion.
- Internal submission-ready target: 2026-10-02.

The October 2 date is an internal execution target, not an asserted external grant deadline.

## 5. Automation boundary

The project should aggressively automate work that does not require human scientific judgment.

### Automate

- repository/current-state scans;
- stale-status detection;
- site-status generation and validation;
- evidence retrieval/navigation;
- hashing and provenance checks;
- schema validation;
- baseline execution;
- model-run orchestration;
- metrics calculation;
- cost/latency capture;
- failure-catalog generation;
- claim/evidence matrix checks;
- grant-draft assembly from verified artifacts;
- public-site propagation after verified research gates.

### Keep human-authoritative

- context-sufficiency decisions;
- relationship ground truth;
- adjudication corrections;
- public-release/sanitization approval;
- final grant submission approval.

No external model should silently replace human ground truth.

## 6. Perplexity dependency removed

Perplexity is not required to continue the project. External research/reviewer work may use available tools when useful, but the grant critical path must not depend on paid Perplexity credits.

Repository evidence, deterministic scripts, GitHub automation, OpenAI evaluation tooling, and human adjudication are sufficient to continue.

## 7. Public website correction

`site/status.json`, `site/index.html`, and `site/app.js` are being rebaselined with this checkpoint so the public site no longer presents the August 31 status or missed September 11/18 dates as current future milestones.

The public site must accurately say:

- M2 remains active;
- the evidence library is materialized and verified;
- human context-sufficiency review is the next scientific gate;
- M3 is blocked on benchmark freeze;
- measured model results are not yet published; and
- October 2 is an internal submission-ready target.

## 8. Immediate next execution state

After this checkpoint and site refresh, the next technical priority is to finish the M2 human-review delivery mechanism and benchmark freeze. Drift-governance/platform work may continue when useful, but it must not displace the grant critical path.

## 9. Source-of-truth rule

This file supersedes the 2026-09-10 checkpoint **only as the current continuation point**. The older checkpoint remains immutable historical evidence of project state at that time.

GitHub remains the source of truth for durable project state. Chat history is supporting context, not the canonical project record.
