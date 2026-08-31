# External Model Code Review Policy

## Purpose

Defensive Drift may use additional AI systems as independent reviewers of implementation work, especially where parser, runtime, provenance, or evidence-integrity defects could create operator burden or invalidate a research step.

External-model review is a review layer, not an execution authority. Parser/linter checks, deterministic tests, repository state validation, cryptographic hashes, and human acceptance remain authoritative.

## Assistant orchestration obligation

The operator should not have to decide when to involve another AI reviewer or invent the review prompt.

When an external review gate is appropriate, the primary assistant must explicitly tell the operator:

1. **which model to use**;
2. **why that model is being used at that exact step**;
3. **exactly what artifact(s) to provide**;
4. **a complete copy/paste prompt** for that reviewer;
5. **what output to bring back** to the Defensive Drift conversation;
6. whether a second reviewer is required after the first review.

The primary assistant remains responsible for reconciling reviewer feedback with the project methodology and deterministic validation gates. The operator is not expected to translate vague reviewer suggestions into code changes.

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

## Exact reviewer prompts

### Claude — executable-code review prompt

Use this template when the assistant identifies a Tier 2 or Tier 3 executable review gate:

> You are an independent code reviewer for the Defensive Drift cybersecurity research project. Review the exact artifacts I provide; do not redesign the project or broaden scope. Focus on concrete defects that could prevent execution, corrupt output, violate stated invariants, or create avoidable operator retries. Check parser/syntax hazards, quoting/interpolation, error handling, cleanup, filesystem/Git path handling, PowerShell version compatibility where relevant, and runtime edge cases. For Excel COM code, also inspect workbook lifecycle, COM cleanup, hyperlinks, formulas, data validation, and failure recovery. Preserve these invariants: source evidence is read-only; immutable evidence bytes must never be normalized or rewritten; no relationship ground truth may be assigned by code or by you; unknown stays unknown; `main` is the only working branch. Return: (1) PASS/FAIL, (2) concrete findings ranked by severity, (3) the smallest safe patch for each confirmed defect, and (4) exact tests that should pass before operator execution. Do not provide speculative rewrites when the existing implementation is adequate.

The assistant must append the exact repository path, commit SHA, blob SHA, relevant failure output, and any narrowly related repair runner to this prompt before handing it to the operator.

### Grok — adversarial review prompt

Use after the primary code review when a second independent perspective is warranted:

> Act as an adversarial implementation reviewer for Defensive Drift. Assume the code has already received a conventional review. Look specifically for hidden assumptions, brittle preconditions, false-success paths, destructive behavior, state-recovery failures, operator retry traps, and places where implementation behavior could diverge from the research/governance contract. Do not assign benchmark ground truth and do not recommend changing immutable evidence. Return only concrete, reproducible concerns with a severity, why the existing tests would or would not catch them, and the smallest additional test or patch needed. If no material issue remains, say PASS and explain the strongest failure modes you checked.

### Perplexity — external-behavior verification prompt

Use only when implementation correctness depends on current external platform/documentation behavior:

> Verify the following technical assumptions using current authoritative documentation. Prefer first-party sources. For each assumption, state VERIFIED, CONTRADICTED, or VERSION-DEPENDENT; cite the source; identify the relevant version/platform boundary; and explain what implementation change, if any, follows. Do not redesign the code and do not infer behavior that the documentation does not establish. Assumptions to verify: [assistant inserts the exact assumptions].

## Data boundary

Do not send private raw evidence, unsanitized operational records, private adjudication decisions, secrets, credentials, or sensitive user data to external model providers merely for code review.

Prefer reviewing public scripts, schemas, synthetic fixtures, redacted stack traces, and minimal reproductions. If a private artifact is necessary to diagnose a defect, first reduce it to the smallest sanitized reproduction that preserves the failure.

## Current M2 application

The Excel-native context-sufficiency workbook builder qualifies as Tier 2 because it is executable PowerShell with Excel COM automation and directly controls the human-review surface.

The current workbook-builder recovery therefore requires **Claude now, before the repaired builder is executed again**. Claude should review both:

- `experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1` at the known failed blob;
- `experiments/pre-grant/m2-context-sufficiency-workbook-parser-repair-runner.ps1` at its exact current blob;
- the observed parser error showing the invalid variable reference adjacent to `:`.

After Claude's findings are reconciled:

- use Grok only if Claude identifies a substantive patch beyond the narrow parser repair, or if the primary assistant determines that an adversarial second pass is warranted because of repeated execution failures;
- use Perplexity only if a remaining question depends on documented Excel COM or PowerShell behavior rather than on code logic visible in the artifacts.

Before the repaired workbook builder is handed back to the operator, it must receive:

- exact PowerShell parser validation;
- a local smoke test against the current 100-case / 1,952-row inputs where feasible;
- the required independent model review;
- assistant reconciliation of all confirmed findings.

The historical evidence materialization tooling is Tier 3 because provenance and byte identity are research-critical.

## Scientific boundary

No external model reviewer assigns Defensive Drift benchmark ground truth. Human adjudication remains authoritative. External models may critique code, retrieval logic, test coverage, or methodology clarity, but they must not convert retrieval similarity into `NEW`, `DUPLICATE`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE` labels.
