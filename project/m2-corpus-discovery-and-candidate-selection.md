# M2 Corpus Discovery and Candidate Selection

This document explains what Defensive Drift is doing during M2 before the benchmark is frozen, how the source-evidence corpus is assembled, how preliminary drift-evidence candidates are discovered, and how those candidates differ from the final human-adjudicated benchmark cases.

## Why this step exists

M2 is not simply a search for 100 convenient examples. Before benchmark cases are selected, Defensive Drift first establishes the broadest defensible evidence universe available from the project’s historical records.

The purpose is to reduce sampling bias and make the later benchmark-selection process auditable. A grant reviewer or research reader should be able to distinguish:

1. the evidence universe that was available;
2. the records that were algorithmically flagged as worth reviewing;
3. the records humans actually adjudicated;
4. the final cases admitted to the frozen benchmark.

A successful narrow scan is therefore a checkpoint, not proof that M2 corpus discovery is complete.

## What the corpus-completeness audit does

The M2 corpus-completeness audit attempts to establish the available source-evidence universe before benchmark selection begins.

It covers four evidence categories:

- **locally tracked Git evidence** — Markdown already tracked in locally available source repositories;
- **local untracked evidence** — Markdown present in source worktrees but not yet tracked by Git;
- **local ignored evidence** — potentially relevant user-authored Markdown that Git ignores, with generated/vendor/cache material explicitly separated or excluded;
- **GitHub-only tracked evidence** — tracked Markdown from repositories in the authoritative GitHub repository inventory that are not currently cloned under the local Git root.

Tracked/untracked status is a **provenance attribute, not an eligibility rule**. A historically valid drift record is not rejected merely because it is untracked, uses an older template, resides outside the current canonical drift directory, or originated from a different AI workflow.

Source repositories are treated as read-only evidence. Discovery and normalization outputs are written to the private research workspace, not back into the source records.

The intended flow is:

`source evidence universe → discovery candidates → normalization/linkage review → human adjudication → benchmark case selection → sanitization/public-release review → frozen benchmark`

## What “candidate” means

A **discovery candidate** is not automatically a valid incident and is not automatically one of the final benchmark cases.

At this stage, candidate means:

> A Markdown record whose filename, path, or contents contain enough drift-related signals that it should enter the review pool rather than be silently discarded.

The discovery stage is intentionally high-recall. It is designed to avoid missing plausible drift evidence, even when that means admitting records that later prove to be duplicates, administrative notes, legacy fragments, incomplete records, or otherwise unsuitable for the final benchmark.

A candidate enters review with no final benchmark relationship label implied.

## Current deterministic candidate-discovery heuristic

The discovery scanner assigns points using filename, repository-relative path, and file contents.

| Signal | Score |
|---|---:|
| filename contains `drift` | +3 |
| path is in `drift/`, `drifts/`, `drift-log/`, or `drift-logs/` | +2 |
| path is under `inbox/` | +1 |
| content contains a `Drift ID:` field | +5 |
| H1 heading mentions drift | +3 |
| content contains `Drift Log` | +3 |
| content contains `Continuance Drift` | +2 |
| content contains `Expected State` | +1 |
| content contains `Actual State` | +1 |

A Markdown record enters the discovery-candidate pool when either:

- its discovery score is **4 or greater**; or
- its filename contains `drift` and its contents also contain `drift`.

This heuristic is deterministic. It is not an LLM classification and it does not assign any of the benchmark ground-truth relationship classes.

### Examples

| Example | Approximate score | Discovery candidate? |
|---|---:|---|
| `DRIFT-...md` with a `Drift ID:` field | 3 + 5 | Yes |
| record under `drifts/` containing `Expected State` and `Actual State` | 2 + 1 + 1 | Yes |
| ordinary README that mentions the word “drift” once | usually below threshold | No |
| file under `inbox/` with no other drift signals | 1 | No |
| legacy record with a drift H1 and `Drift Log` text | 3 + 3 | Yes |

## Metadata preserved for candidates

Where evidence supports it, candidate records preserve or derive research metadata such as:

- source repository;
- source-relative path;
- tracked/untracked provenance class;
- source branch/ref;
- source commit and Git blob SHA for tracked evidence;
- content SHA-256 where available;
- repository HEAD/worktree context;
- source AI/model when explicitly supported;
- model-provenance confidence;
- inferred historical template family;
- title;
- raw Drift ID;
- raw severity;
- raw affected component;
- raw recurrence classification;
- discovery score and discovery signals.

Unknown provenance remains `UNKNOWN`; it is not guessed.

## Why a high-recall candidate pool is acceptable

The candidate-discovery heuristic is intentionally broader than the benchmark.

Its job is to answer:

> “Is this record plausible enough to deserve review?”

It is **not** intended to answer:

> “What is the correct incident relationship?”

The second question is reserved for evidence-grounded human adjudication under the frozen adjudication protocol.

This separation helps prevent the discovery algorithm from becoming hidden ground truth and reduces the risk that early similarity assumptions contaminate the benchmark labels.

## Candidate discovery versus final benchmark ground truth

The final benchmark relationship classes are:

- `NEW`
- `DUPLICATE`
- `RECURRENCE`
- `RELATED_BUT_DISTINCT`
- `INSUFFICIENT_EVIDENCE`

No candidate receives one of these labels merely because it passed the discovery threshold.

Before a record or evidence relationship becomes a benchmark case, the research process must determine whether it is suitable for adjudication, connect relevant historical evidence, evaluate remediation/state context, and apply the human adjudication protocol.

Human adjudication—not the discovery score—creates the benchmark ground truth.

## Current M2 execution checkpoint — 2026-08-30

The first local tracked-evidence pass scanned **2,968 tracked Markdown files** across the locally available source repositories and produced **1,900 preliminary discovery candidates**.

The subsequent comprehensive pass expanded the evidence-universe audit to local untracked/ignored evidence, tracked deltas, and repositories present in the authoritative GitHub inventory but absent from the local Git root.

A state-aware recovery preserved the successful local work and produced the following partial checkpoint:

- preserved local/checkpoint candidates: **1,901**;
- GitHub repository inventory: **65 repositories**;
- GitHub-only repositories requiring remote-cache coverage at that checkpoint: **40**;
- GitHub-only Markdown successfully scanned during recovery: **327**;
- additional remote drift candidates discovered: **11**;
- combined candidate records preserved: **1,912**;
- repositories correctly identified as empty/no commit tree: **3**;
- unresolved remote repository coverage failures: **1**;
- combined private-inventory SHA-256: `9afbdf814f5a4054d59f0b0536901085f3477e05e068586eda2ee1f72b8b2f12`;
- private partial-recovery commit: `e87f01dd9ee100ad69ffb89caa7d5dc7223ef02a`.

The partial result is intentionally preserved rather than discarded. However, **benchmark selection remains blocked until the remaining repository-coverage failure is repaired or explicitly and scientifically justified as an exclusion**.

This is an important research-integrity distinction: a partial corpus artifact can be useful evidence of progress without being treated as a completed corpus-completeness gate.

## What happens after corpus completeness passes

Once the evidence-universe coverage gate is satisfied, M2 moves into the much stricter benchmark-construction phase:

1. review and normalize plausible evidence relationships without altering the original source records;
2. identify duplicate, recurrence, and related-but-distinct relationships among historical evidence;
3. select cases that provide useful class, ambiguity, severity, remediation-state, and failure-mode coverage;
4. human-adjudicate every selected case under the frozen adjudication protocol;
5. validate every final case against the benchmark/ground-truth schemas;
6. perform public/private sanitization review;
7. freeze benchmark v0.1 at the scientifically justified case count.

The operational target is **100 human-adjudicated cases**, with a **150–200 case expansion range** when additional cases materially improve research coverage without weakening adjudication quality.

## Core research-integrity rule

**Discovery scoring finds records worth reviewing; human adjudication creates ground truth.**

The project must never treat a candidate score, filename convention, current template, repository location, or AI-generated similarity judgment as a substitute for adjudication evidence.
