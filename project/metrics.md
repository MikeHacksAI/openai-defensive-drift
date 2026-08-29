# Defensive Drift — Metrics Contract

This document defines the evaluation metrics for the pre-grant sprint. Metric definitions should be frozen before final benchmark evaluation so the project does not optimize its success criteria after seeing results.

## Primary classification task

For each new observation, the system must classify its relationship to historical incidents as one of:

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

## Primary metrics

### 1. Duplicate precision

Of all cases predicted `DUPLICATE`, what fraction are actually duplicates according to human ground truth?

**Why it matters:** Low precision can hide genuinely new or unresolved security issues by incorrectly collapsing them into prior records.

### 2. Duplicate recall

Of all true duplicate cases, what fraction does the method correctly identify?

**Why it matters:** Low recall creates duplicate tickets, alert fatigue, and fragmented security history.

### 3. Duplicate F1

Harmonic mean of duplicate precision and recall.

**Purpose:** Useful summary statistic, but never reported alone.

### 4. Novel-issue recall

Of all ground-truth `NEW` and `RELATED_BUT_DISTINCT` cases that require separate review, what fraction are not incorrectly collapsed into previous incidents?

### 5. Dangerous false-duplicate rate

A **dangerous false duplicate** occurs when a case that is `NEW`, `RECURRENCE`, `RELATED_BUT_DISTINCT`, or `INSUFFICIENT_EVIDENCE` is incorrectly classified as a resolved/closed duplicate in a way that could suppress needed defensive investigation.

Report:

- raw count;
- percentage of all evaluated cases;
- percentage of all non-duplicate cases;
- case IDs and failure notes.

This is a headline safety metric and must not be hidden behind aggregate F1.

## Evidence-quality metrics

### 6. Evidence-grounding accuracy

A prediction is grounded only when the cited supporting evidence actually exists in the provided case artifacts and materially supports the model's conclusion.

Score each case as:

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `UNSUPPORTED`

Report strict supported accuracy and the full distribution.

### 7. Unsupported remediation claim rate

Percentage of cases where a method/model asserts that remediation occurred, or describes a remediation action as completed, without evidence in the provided artifacts.

This is tracked separately from general evidence grounding because fabricated remediation state is particularly dangerous.

### 8. Remediation-state accuracy

Ground-truth remediation states should include, where applicable:

- `DETECTED`
- `ACKNOWLEDGED`
- `MITIGATED`
- `PARTIALLY_REMEDIATED`
- `REMEDIATED`
- `RECURRED`
- `UNRESOLVED`
- `UNKNOWN`

Report overall accuracy plus a confusion matrix when sample size supports it.

## Severity and confidence metrics

### 9. Severity accuracy

Compare predicted severity with human-adjudicated severity using the project's frozen severity scale.

Report:

- exact-match accuracy;
- one-level-off rate;
- materially dangerous under-classification count.

### 10. Confidence calibration

Where models emit confidence scores, compare confidence with empirical correctness.

At minimum report outcomes in confidence buckets, such as:

- 0–49%
- 50–69%
- 70–84%
- 85–94%
- 95–100%

Do not treat self-reported confidence as trustworthy without calibration evidence.

## Operational metrics

### 11. Latency per case

Record end-to-end processing latency for each method/model.

Report:

- median;
- p90;
- p95 where sample size supports it.

### 12. Cost per case

For paid API or cloud inference, record attributable inference cost per case and aggregate cost per benchmark run.

For cloud-GPU workloads, document the calculation method, including hourly rental rate and measured run duration.

### 13. Human review time

For a defined subset, record human adjudication/review time with and without machine assistance where feasible.

Primary question: does the method reduce human review effort without increasing dangerous false negatives?

## Repeated-trial metrics

### 14. Prediction consistency

For cases evaluated repeatedly with identical inputs/configuration, calculate the proportion of trials that return the same relationship classification.

### 15. High-risk disagreement rate

Percentage of repeated trials where the model alternates between a safe escalation class and `DUPLICATE` or another closure-like determination.

These cases should be prioritized in the failure catalog.

## Baseline comparison requirements

Every model comparison must include the same frozen benchmark cases and preserve:

- benchmark version;
- evaluation code commit SHA;
- method/model identifier;
- model configuration/parameters;
- timestamp;
- run ID.

Comparisons across mismatched benchmark versions must be explicitly labeled and must not be presented as head-to-head results.

## Minimum result table

Every final approach should have a row containing at least:

| Method | Cases | Duplicate Precision | Duplicate Recall | F1 | Novel Recall | Dangerous False-Duplicate Rate | Grounding Accuracy | Remediation Accuracy | Median Latency | Cost/Case |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

No values should be populated until measured.

## Statistical honesty rules

1. Never replace missing measurements with estimates in result tables without clearly labeling them as estimates.
2. Never remove difficult cases from the final benchmark solely because they hurt model performance.
3. Any excluded case must have a documented exclusion reason.
4. Thresholds may be tuned only on designated development cases; final test cases stay frozen.
5. Do not claim statistical significance unless the analysis actually supports it.
6. Preserve negative and inconclusive results.
7. Report security-relevant failure counts alongside aggregate averages.

## Grant-facing success criteria

The pre-grant sprint does **not** require GPT or any AI method to outperform every baseline.

The research is successful if it produces a reproducible answer to questions such as:

- Where does AI materially outperform conventional matching?
- Where does it fail despite higher semantic capability?
- Which failure modes are security-relevant?
- Can a cascade reduce inference cost without materially increasing dangerous false duplicates?
- How much human review remains necessary?

A rigorous negative result is valid grant evidence if it exposes an important unsolved defensive-security problem.
