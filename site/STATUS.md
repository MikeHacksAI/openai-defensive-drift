# Defensive Drift Live Public Status Contract

The public website is a live/near-real-time research-status surface, not a manually maintained snapshot.

## Canonical public status source

`site/status.json`

`site/app.js` loads this artifact on page load and renders the current milestone headline, detailed status, next gate, and public-safe review progress into the existing static site.

## Required propagation flow

`research gate completes` → `safe aggregate status is promoted to site/status.json` → `commit to main` → `Cloudflare Pages deploys` → `public site reflects current state`

Every material research-gate completion transaction must update `site/status.json` in the same public-repository change that records the new public checkpoint. A milestone/checkpoint must not be described as externally current if `site/status.json` still reports an earlier phase.

## Required fields

At minimum, maintain:

- active milestone and phase;
- reviewer-facing headline and detail text;
- current public-safe aggregate counts;
- next gate;
- latest-acceptable milestone date;
- last-updated timestamp; and
- public/private boundary metadata.

## Public/private boundary

Only aggregate research-progress information belongs in `site/status.json`.

Do not expose private evidence packets, raw drift records, confidential source material, case-level adjudication details, private paths, or other non-public research artifacts.

## Verification gate

A public checkpoint is not complete until:

1. `site/status.json` reflects the new checkpoint;
2. `site/app.js` can render the status artifact;
3. Cloudflare Pages has deployed the relevant `main` revision; and
4. the rendered public site matches the canonical status artifact.

The static HTML should retain sensible fallback copy so a transient JSON fetch failure does not blank the page, but `site/status.json` is authoritative for current public status.
