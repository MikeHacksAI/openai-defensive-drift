# Claude Review Prompt — M2 Context-Sufficiency Workbook Recovery

## Use now

This review is required before the M2 context-sufficiency workbook recovery is executed again.

## Artifacts

1. Canonical workbook builder
   - path: `experiments/pre-grant/m2-create-context-sufficiency-review-workbook.ps1`
   - failed builder commit: `52bd9e8becacc92c80cf9c67bbd04ef389be9988`
   - failed builder blob: `2a6e58bdcc36ba7cc4288e371f73351b5f36456d`

2. Narrow recovery runner
   - path: `experiments/pre-grant/m2-context-sufficiency-workbook-parser-repair-runner.ps1`
   - recovery runner commit: `c26719b8dfb288653027c22ae9fc3cfd6f2d58a9`
   - recovery runner blob: `a1d83564461a2ff1eed170459176feaf234f9537`

3. Observed failure

PowerShell parser preflight reported:

`Variable reference is not valid. ':' was not followed by a valid variable name character. Consider using ${} to delimit the name.`

The known defective construct is an expandable-string variable immediately followed by a colon: `$CaseIndex:`. The recovery runner is intentionally narrow: it expects exactly one occurrence, replaces it in a temporary copy with `${CaseIndex}:`, parser-validates the repaired copy, and only then executes the workbook builder.

## Exact prompt to Claude

You are an independent code reviewer for the Defensive Drift cybersecurity research project. Review the exact two PowerShell artifacts I provide; do not redesign the project or broaden scope.

The first artifact is the canonical M2 Excel context-sufficiency workbook builder. The second is a narrow recovery runner created after the canonical builder failed PowerShell parser preflight.

Observed parser failure:

`Variable reference is not valid. ':' was not followed by a valid variable name character. Consider using ${} to delimit the name.`

Known suspected cause: an expandable string uses `$CaseIndex:` where PowerShell requires `${CaseIndex}:` because the colon is adjacent to the variable token.

Focus on concrete defects that could prevent execution, corrupt the workbook, violate stated invariants, or cause another avoidable operator retry. Specifically inspect:

- PowerShell parser/syntax hazards throughout both files;
- quoting and variable interpolation, especially variables adjacent to `:` or other syntactically meaningful characters;
- Windows PowerShell / PowerShell compatibility;
- Excel COM workbook lifecycle and COM cleanup;
- hyperlink creation and expected counts;
- worksheet names and ranges;
- formulas and whether the initial Summary values should evaluate to Total=100, Reviewed=0, Remaining=100, Relationship Ground Truth Assigned=0;
- data validation for exactly `SUFFICIENT_FOR_ADJUDICATION` and `MORE_CONTEXT_REQUIRED`;
- error handling and partial-workbook cleanup;
- whether the repair runner truly limits itself to exactly one `$CaseIndex:` -> `${CaseIndex}:` change in a temporary copy;
- whether any additional parser/runtime defect is visible that the current narrow repair would miss.

Preserve these project invariants:

- private evidence checkpoint is `0c3df389b37ea948129c801276a844ecf3430b9e`;
- source evidence is read-only;
- immutable historical evidence bytes must never be normalized or rewritten;
- the workbook is only a human context-sufficiency review surface;
- no relationship ground truth may be assigned by code or by you;
- unknown stays unknown;
- `main` is the only working branch;
- do not rerun corpus discovery or evidence materialization;
- do not propose a broad rewrite if the existing design can be repaired safely.

Return exactly:

1. `PASS` or `FAIL` for executing the recovery runner after review.
2. Confirmed findings ranked `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.
3. For each confirmed defect, the smallest safe patch only.
4. Exact parser/runtime/smoke tests that must pass before operator execution.
5. A final line: `SAFE TO EXECUTE AFTER PATCHES: YES` or `SAFE TO EXECUTE AFTER PATCHES: NO`.

Do not assign Defensive Drift benchmark labels and do not inspect or request private raw evidence. Review only the public code and the failure information above.

## Return path

Bring Claude's complete response back to the primary Defensive Drift conversation. The primary assistant will reconcile the findings, make any necessary patch, validate the exact committed artifact, and then provide the next executable operator command.
