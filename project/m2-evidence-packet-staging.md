# M2 Evidence-Packet Staging

This document defines the private evidence-packet staging step that follows the M2 stratified human-review queue.

## Purpose

The 100-entry core review tier is not yet a 100-case benchmark. A queued discovery candidate must first be materialized with provenance, screened for record suitability, supplied with relevant historical context, and human-adjudicated before it can become a benchmark case.

Evidence-packet staging exists to make that process auditable without modifying the original source evidence.

## Packet scope

For each of the 100 core review entries, the staging builder creates a private packet under `openai-defensive-drift-private/adjudication-working/evidence-packets/`.

Each packet contains:

- an exact byte-for-byte private copy of the tracked source Git blob as `source-record.md`;
- `packet-manifest.json` with source repository, source path, source commit, Git blob SHA, extracted SHA-256, source-model provenance, template family, and discovery metadata;
- `packet.md` explaining the packet state, provenance, and any exact-content relationship hints;
- `adjudication-notes.md` as a blank human-review worksheet.

The top-level packet directory also contains a machine-readable packet index and a build summary.

## Trust boundary

Original source repositories remain read only.

The packet builder retrieves tracked evidence by Git blob SHA rather than copying from an arbitrary current worktree path. This preserves the exact tracked content represented by the candidate inventory and avoids Unicode-path reconstruction problems.

The builder records source-repository Git status before and after packet creation and fails if any source repository status changes.

The derived packet copy is private research material. It never replaces, renames, deletes, or normalizes the original source record.

## Ground-truth boundary

Packet creation assigns no relationship label.

Every packet begins with:

- record suitability: `NOT_REVIEWED`;
- benchmark case status: `NOT_SELECTED`;
- ground truth assigned: `NO`;
- adjudication status: `NOT_STARTED`.

A queued record may still be rejected as a benchmark observation if it is a template, runbook, policy, administrative note, duplicated artifact, incomplete fragment, or otherwise scientifically unsuitable.

## Exact-content groups

Exact-content groups are carried into packets only as retrieval/context hints.

Identical Git blob content does not prove that two records represent the same underlying incident. Exact-content identity must never automatically produce `DUPLICATE` ground truth.

## Historical-context requirement

A source record by itself is not necessarily an adjudication-ready benchmark case.

Before ground truth is assigned, the adjudicator must assemble relevant historical incidents and supporting evidence. The final decision then follows `benchmark/ground-truth/ADJUDICATION-PROTOCOL.md` and the frozen benchmark schemas.

This prevents discovery scoring, queue stratification, filename conventions, or exact-content identity from becoming hidden substitutes for human ground truth.

## Output state

Successful packet staging means the core review tier has provenance-preserving private evidence packets ready for suitability screening and historical-context assembly.

It does **not** mean:

- 100 benchmark cases have been accepted;
- any relationship labels have been assigned;
- benchmark v0.1 is frozen;
- class coverage has been satisfied.

Those gates occur only after human adjudication, schema validation, class-distribution review, and sanitization/public-release review where applicable.
