# M2 Evidence-Packet Staging

This document defines the private evidence-packet staging step that follows the M2 stratified human-review queue.

## Purpose

The 100-entry core review tier is not yet a 100-case benchmark. A queued discovery candidate must first be materialized with provenance, screened for record suitability, supplied with relevant historical context, and human-adjudicated before it can become a benchmark case.

Evidence-packet staging exists to make that process auditable without modifying the original source evidence.

## Packet scope

For each of the 100 core review entries, the staging builder creates a private packet under `openai-defensive-drift-private/adjudication-working/evidence-packets/`.

Each packet contains:

- an exact byte-for-byte private copy of the tracked source Git blob as `source-record.md`;
- `packet-manifest.json` with source repository, source path, source commit, Git blob SHA, Git-blob SHA-256, discovery-source SHA-256 when available, explicit hash semantics, source-model provenance, template family, and discovery metadata;
- `packet.md` explaining the packet state, provenance, hash semantics, and any exact-content relationship hints;
- `adjudication-notes.md` as a blank human-review worksheet.

The top-level packet directory also contains a machine-readable packet index and a build summary.

## Trust boundary

Original source repositories remain read only.

The packet builder retrieves tracked evidence by Git blob SHA rather than copying from an arbitrary current worktree path. It validates Git object identity and, when a source commit is available, validates the commit/path/blob relationship before creating any packet output.

The builder records source-repository Git status before and after packet creation and fails if any source repository status changes.

The derived packet copy is private research material. It never replaces, renames, deletes, or normalizes the original source record.

## Provenance hash semantics

Git-blob bytes and local worktree bytes are distinct provenance layers and must not be treated as byte-identical by assumption.

For locally discovered tracked evidence, `source_sha256` in the M2 inventory represents the discovery-time worktree bytes. On Windows, Git line-ending normalization can make that worktree use CRLF while the corresponding tracked Git blob uses LF. The worktree SHA-256 and Git-blob SHA-256 can therefore differ while both legitimately identify the same tracked source state at different layers.

Evidence packets preserve these identities separately:

- `git_blob_sha`: Git object identity;
- `git_blob_sha256`: SHA-256 of the exact bytes copied into `source-record.md`;
- `discovery_source_sha256`: discovery-time source/worktree SHA-256 when recorded;
- `discovery_source_sha256_semantics`: explicit description of what that discovery hash represents.

The packet builder does not weaken provenance by ignoring mismatches. Instead, it validates Git blob identity through Git object hashing and commit/path linkage while preserving the discovery/worktree hash as a separate provenance fact.

## Transaction boundary

Packet construction is transaction-safe.

1. All 100 core source records complete read-only provenance preflight before packet output is created.
2. Packet artifacts are generated under a builder-owned temporary directory.
3. Every temporary packet must contain all required artifacts and exact source-copy hash validation must pass.
4. Source repository status is checked again before promotion.
5. Only after all checks pass is the temporary directory atomically promoted to the canonical `evidence-packets/` path.
6. A failed build removes only the builder-owned temporary directory. An existing canonical packet workspace is never overwritten or silently deleted.

This prevents a failed provenance check from leaving a partial canonical adjudication workspace.

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
