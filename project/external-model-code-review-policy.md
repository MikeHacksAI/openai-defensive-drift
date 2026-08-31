# External Model Code Review Policy

## Purpose

Defensive Drift may use additional AI systems as independent reviewers of implementation work, especially where parser, runtime, provenance, or evidence-integrity defects could create operator burden or invalidate a research step.

External-model review is a review layer, not an execution authority. Parser/linter checks, deterministic tests, repository state validation, cryptographic hashes, and human acceptance remain authoritative.

## Recommended reviewer roles

### Claude — primary independent code reviewer

Use Claude as the first external reviewer for substantial PowerShell and Python revisions, especially:

- parser and quoting/interpolation hazards;
- Windows PowerShell / PowerShell compatibility;
- Excel COM automation;
- exception and cleanup paths;
- transactional file generation;
- Git/path handling;
- edge cases that are difficult to catch from a happy-path read.

Preferred request: review the exact committed script, identify concrete defects, propose the smallest safe patch, and specify tests that would prove the patch.

### Grok — adversarial second reviewer

Use Grok as a second-opinion reviewer for:

- hidden assumptions;
- brittle preconditions;
- failure-mode analysis;
- unnecessary complexity;
- operator-experience problems;
- places where the code may technically run but violate the research or governance contract.

Grok is particularly useful as a deliberately independent reviewer after another model has already authored or reviewed a change.

### Perplexity — documentation and external-compatibility verifier

Use Perplexity primarily when a code revision depends on current external documentation or platform behavior, such as:

- PowerShell / .NET / Excel COM documentation;
- Git behavior;
- Cloudflare, Azure, GitHub, or API contracts;
- current version-specific limitations;
- source-backed verification of a technical assumption.

Perplexity is not the default code patch author. Its strongest role in this workflow is source-backed confirmation of external facts that the code depends on.

## Review tiers

### Tier 1 — small/local change

Examples: one-line message correction, documentation-only edit, non-executable metadata.

Required: local validation appropriate to the artifact. External-model review optional.

### Tier 2 — substantial executable revision

Examples: PowerShell or Python workflow scripts, workbook builders, Git automation, corpus tooling.

Required before operator execution:

1. exact committed artifact parser/syntax validation;
2. deterministic local validation or dry-run where feasible;
3. one independent model review, preferably Claude or Grok;
4. assistant reconciliation of reviewer findings before handing the command to the operator.

### Tier 3 — research-integrity / provenance critical

Examples: evidence materialization, source-corpus handling, hash/provenance logic, adjudication data transformations, benchmark freeze tooling.

Required before operator execution:

1. exact committed artifact validation;
2. focused regression tests for known failure modes;
3. at least one independent code reviewer;
4. a second independent reviewer when the change modifies evidence identity, provenance, inclusion/exclusion, or ground-truth boundaries;
5. explicit confirmation that no reviewer suggestion changes immutable source evidence or silently changes research methodology.

## Data boundary

Do not send private raw evidence, unsanitized operational records, private adjudication decisions, secrets, credentials, or sensitive user data to external model providers merely for code review.

Prefer reviewing public scripts, schemas, synthetic fixtures, redacted stack traces, and minimal reproductions. If a private artifact is necessary to diagnose a defect, first reduce it to the smallest sanitized reproduction that preserves the failure.

## Current M2 application

The Excel-native context-sufficiency workbook builder qualifies as Tier 2 because it is executable PowerShell with Excel COM automation and directly controls the human-review surface.

Before the repaired workbook builder is handed back to the operator, it should receive:

- exact PowerShell parser validation;
- a local smoke test against the current 100-case / 1,952-row inputs where feasible;
- one independent model review focused on PowerShell interpolation, COM cleanup, hyperlink counts, validation lists, and workbook formulas.

The historical evidence materialization tooling is Tier 3 because provenance and byte identity are research-critical.

## Scientific boundary

No external model reviewer assigns Defensive Drift benchmark ground truth. Human adjudication remains authoritative. External models may critique code, retrieval logic, test coverage, or methodology clarity, but they must not convert retrieval similarity into `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE` labels.
