# Pre-Grant External Review Artifacts

This directory stores external-model review evidence tied directly to executable pre-grant experiments.

## Structure

Use one lowercase provider directory per reviewer:

```text
experiments/pre-grant/reviews/
├── claude/
├── grok/
└── perplexity/
```

Create a provider directory only when an artifact exists for that reviewer.

## Artifact separation

Preserve reviewer output separately from Defensive Drift reconciliation.

Recommended naming:

```text
YYYY-MM-DD-<target>-review.md
YYYY-MM-DD-<target>-review-reconciliation.md
```

A reviewer-output artifact must state whether it is:

- a verbatim preserved reviewer response;
- a source-faithful reconstruction from a checkpoint/transcript; or
- a summary.

Never present a reconstruction as verbatim evidence.

The reconciliation artifact is where Defensive Drift compares reviewer claims against deterministic evidence such as exact Git blobs, commits, parser results, repository state, tests, and research/governance boundaries.

## Identity rule

For executable review gates, record the exact repository path and Git blob SHA for every reviewed artifact. When the external service does not preserve an upload hash, do not infer that the reviewed attachment was identical to the canonical repository file merely from its filename.

## Scientific boundary

External reviewers may critique implementation, failure modes, provenance controls, and test coverage. They do not assign M2 relationship ground truth or modify immutable evidence.
