# Defensive Drift — Current State Checkpoint — 2026-09-25

## Purpose

This checkpoint supersedes the September 18 public progress checkpoint for current-status reporting. Historical checkpoints remain preserved as historical evidence.

## Verified M2 progress

The 100-case benchmark suitability target is assembled and quality-reviewed.

- Original candidate review: 100 / 100 reviewed
- Suitable original cases: 78
- Unsuitable original cases: 22
- Replacement cases required: 22
- Replacement cases reviewed: 22 / 22
- Suitable replacement cases: 22
- Current suitable benchmark pool: 100 / 100

The existing historical-context evidence remains materialized and integrity-validated:

- 820 unique historical evidence records
- 1,952 case-to-context relationships
- 820 / 820 evidence hashes verified

## Remaining M2 scientific gate

The 100-case suitability pool is assembled, but benchmark v0.1 is not yet frozen.

The remaining work is:

1. complete the human context-sufficiency decisions;
2. expand evidence only where additional context is required;
3. assign the five-class relationship ground-truth labels;
4. schema-validate and freeze benchmark v0.1.

Relationship ground-truth labels remain unassigned at this checkpoint. The site must not describe M2 as complete until the adjudication and freeze gates are actually satisfied.

## M3 / M4

M3 conventional baselines and M4 model evaluation remain downstream of the benchmark freeze for final reproducible comparisons. Work that can be prepared safely in advance may proceed, but final comparison claims must use the frozen benchmark.

## Grant execution

OpenAI Cybersecurity Grant application preparation is now an active parallel workstream. The project does not need to complete every long-term engineering objective before application submission. The immediate goal is to preserve the strongest defensible preliminary evidence, complete the highest-value remaining evaluation work, and submit as soon as the proposal is sufficiently supported.

## Public-status requirement

This checkpoint materially changes the verified research state. `site/status.json` and the rendered homepage must advance with it. Future material research-state changes are not operationally complete until the public/operator status surface is reviewed and either updated or explicitly verified unchanged.
