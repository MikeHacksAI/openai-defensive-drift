# Defensive Drift — Sanitization and Public Release Rules

## Immutable source rule

Canonical raw evidence is never moved, renamed, rewritten, deleted, or converted in place.

Research processing uses copies or derived representations only.

## Data flow

Canonical private source
→ derived private working copy
→ human adjudication
→ sanitization review
→ public-release review
→ approved public artifact

## Never publish

- passwords;
- API keys;
- tokens;
- cookies;
- session identifiers;
- private keys;
- recovery codes;
- personally identifiable information;
- private email addresses unless explicitly intended for publication;
- unnecessary private network topology;
- secret-bearing configuration;
- confidential third-party records;
- raw private provider/AI chat exports;
- evidence without redistribution rights.

## Release states

- `PRIVATE_ONLY`
- `SANITIZATION_PENDING`
- `PUBLIC_APPROVED`
- `PUBLIC_SYNTHETIC`

## Public approval requirements

1. Remove credentials and secrets.
2. Remove unnecessary personal identifiers.
3. Generalize sensitive hostnames/IPs where needed.
4. Preserve the technical relationship needed for research.
5. Verify sanitization did not alter ground truth.
6. Record sanitization notes.
7. Perform final human review.

If safe sanitization would materially change the security meaning, keep the source case private and create a synthetic public analogue.