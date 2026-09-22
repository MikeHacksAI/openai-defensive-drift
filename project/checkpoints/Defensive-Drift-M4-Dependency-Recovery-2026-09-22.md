# Defensive Drift M4 Dependency-Recovery Checkpoint — 2026-09-22

## Decision

Use dependency-first recovery. Do not start, characterize, or freeze M4 model results until the M2 benchmark is frozen and the M3 evaluator and conventional baselines are complete.

The September 25 M4 date is an aggressive planning reference, not permission to bypass the acceptance criteria or dependency chain.

## Repository evidence reviewed

- Issue `#4` requires evaluation against a frozen benchmark and explicitly depends on M1, M2, and M3.
- Issue `#2` remains open. The last verified state records 100 suitable observations but `0/100` human context-sufficiency decisions and no relationship ground-truth labels.
- Issue `#3` remains open. No final frozen-benchmark baseline runs, raw predictions, aggregate metrics, or evaluator commit are present.
- `experiments/pre-grant/` contains M2 tooling and the run-manifest schema, but no M3 or M4 run directories or raw result artifacts.
- The public repository has only `main`; there is no open pull request containing unmerged evaluator or model-run work.
- The latest default-branch commit before this checkpoint is `0ae38b16a21c3e2d8a71d045a1c41b7f1610b0a3`.

## Exact M2 execution gate

The canonical public artifacts remain byte-identical to the repository identities recorded by the September 10 reconciliation:

- workbook recovery runner blob: `2733b49f7d4b250e3c2a0200365e56bdeb0f8791`;
- workbook builder blob: `2a6e58bdcc36ba7cc4288e371f73351b5f36456d`;
- authoritative private evidence checkpoint: `0c3df389b37ea948129c801276a844ecf3430b9e`.

Static inspection confirms that the recovery runner:

1. requires the authoritative private evidence checkpoint to be an ancestor of current private `HEAD`;
2. requires `adjudication-working/context-evidence` to be unchanged since that checkpoint;
3. requires both repositories to be clean;
4. verifies the exact canonical builder blob;
5. applies only the reviewed parser/UTF-8 repairs to a temporary execution copy; and
6. removes a newly generated workbook if execution or validation fails.

Static inspection also confirms that the builder reopens the saved workbook and validates the required sheets, hyperlink counts, and initial summary counts.

The repository contains the exact-artifact rereview prompt at:

`experiments/pre-grant/reviews/grok/2026-09-10-m2-exact-artifact-rereview-prompt.md`

No subsequent independent PASS/FAIL result is present. The September 10 reconciliation explicitly prohibits workbook generation until that exact-artifact review is completed and reconciled. That missing review result is therefore the first unresolved gate.

## Shortest defensible path to M4

### Gate 1 — Clear the workbook execution hold

- Obtain one fresh independent adversarial review of the exact canonical runner and builder blobs named above.
- Preserve the review result in `experiments/pre-grant/reviews/`.
- Reconcile only concrete findings. Do not redesign the workflow or alter immutable evidence.
- Require an explicit PASS before workbook generation.

### Gate 2 — Finish M2 human work

- Run the guarded recovery runner on the authorized Windows/Excel workstation against the private repository.
- Complete all 100 human context-sufficiency decisions.
- Expand evidence only for cases marked `MORE_CONTEXT_REQUIRED`.
- Perform human relationship-ground-truth adjudication under the frozen protocol.
- Validate schema, coverage, sanitization, provenance, and exclusions.
- Freeze benchmark v0.1 and record its manifest, version, case count, class distribution, validation result, and commit SHA.

### Gate 3 — Complete M3 before making AI-value claims

- Implement the shared evaluator and output validation against development fixtures if useful while human review is underway.
- Freeze thresholds and configuration before the final evaluation.
- Run exact/normalized lexical, TF-IDF, and embedding baselines only on benchmark v0.1.
- Retain manifests, machine-readable predictions, metrics, latency, and threshold-selection notes.

### Gate 4 — Execute the minimum complete M4 design

- Run one economical OpenAI configuration and one stronger-reasoning OpenAI configuration across at least 50 frozen cases.
- Record exact model snapshots/IDs, parameters, prompt/schema version, benchmark version, evaluator commit, timestamps, token usage, cost, and latency.
- Select high-risk/ambiguous cases by a predeclared rule derived from frozen labels and M3 errors, then perform at least three trials per selected configuration.
- Retain every raw structured response, including invalid/error responses; never overwrite or normalize the frozen originals.
- Hash and inventory the raw-results tree, mark it read-only, and derive metrics/failure records in a separate directory.
- Calculate every metric required by Issue `#4` and document representative security-relevant failures.

## Scope boundary

Do not add new product features, broaden the taxonomy, rewrite the protocol after observing outputs, add extra model families before the two required OpenAI configurations are complete, or treat an optional open-weight comparison as a reason to delay the core evaluation. Issue `#5` already permits a conditional-go outcome when an optional comparison cannot be completed for a defensible reason.

## M4 close rule

Issue `#4` may close only when its closing evidence names:

- the frozen benchmark version and commit;
- the evaluator commit;
- the qualifying run IDs and exact configurations;
- aggregate metrics and cost/latency summary;
- repeated-trial consistency results;
- representative failure records; and
- the immutable raw-results inventory and hashes.

Until those artifacts exist, the accurate status is **blocked by M2/M3**, not partially complete.
