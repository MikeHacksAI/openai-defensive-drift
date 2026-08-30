# M2 Core Evidence-Packet Checkpoint — 2026-08-30

## Status

The 100-entry M2 core human-review tier has been materialized into provenance-preserving private evidence packets.

Private checkpoint:

- repository: `MikeHacksAI/openai-defensive-drift-private`
- commit: `3c70b67baca2a1be227d4b41389eb8997ba28100`
- core packets: **100**
- source-record copies: **100**
- source repositories read: **16**
- packets with exact-content hints: **79**
- ground-truth labels assigned: **0**
- source repositories modified: **0**
- transaction mode: `READ_ONLY_PREFLIGHT_THEN_ATOMIC_PROMOTION`

## Provenance result

The packet builder preserves two byte identities separately when both exist:

1. discovery/worktree SHA-256 — the bytes observed in the local worktree during discovery; and
2. Git-blob SHA-256 — the normalized tracked bytes addressed by the recorded Git blob SHA.

These hashes may legitimately differ because Git line-ending normalization can represent a Windows CRLF worktree file as an LF Git blob. A mismatch between those two layers is therefore not treated as corruption when commit/path/blob linkage and the Git object identity are valid.

`M2C-001898` is the regression case that established this distinction. Its CRLF discovery hash and LF Git-blob hash are both retained and independently verified.

## Ground-truth boundary

Packet staging does not make a benchmark decision. Every packet remains:

- record suitability: `NOT_REVIEWED`
- benchmark case status: `NOT_SELECTED`
- ground truth assigned: `NO`

The next M2 gate is human suitability screening followed by historical-context assembly and human adjudication.

## Source-evidence boundary

All original source repositories remained read only. Packet copies are derived private research artifacts. No original evidence record was moved, renamed, normalized, rewritten, or deleted.
