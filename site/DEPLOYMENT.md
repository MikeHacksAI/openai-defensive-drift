# Defensive Drift Site Deployment

Canonical public domain: `https://defensive-drift.mikehacks.ai`

Canonical source repository: `MikeHacksAI/openai-defensive-drift`

Canonical branch: `main`

Canonical Cloudflare Pages project: `openai-defensive-drift-v2`

Canonical Pages hostname: `https://openai-defensive-drift-v2.pages.dev`

Site source directory: `site/`

## Branch policy

Defensive Drift is a **single-branch project**.

- `main` is the sole normal development, research, documentation, and deployment branch.
- Do not create feature, staging, repair, temporary, experiment, deployment, or assistant-specific branches for routine work.
- Local clones should remain checked out on `main` and reconcile directly with `origin/main`.
- Before state-changing local work, verify the local branch is `main`, inspect the worktree, fetch `origin`, and fast-forward from `origin/main` when the tree is clean.
- Do not use branch churn as a workaround for local ahead/behind state. Resolve and explain the actual Git state instead.
- A second branch is permitted only when a platform or safety requirement makes it genuinely unavoidable. That exception must be explicit, temporary, documented before creation, and removed after the requirement ends.

This policy applies to the public repository and should also be followed by the private Defensive Drift companion repository.

## Deployment architecture

GitHub `main` is the authoritative source for the public research site.

Cloudflare Pages is the deployment and hosting platform.

GitHub Actions is intentionally not used for this site deployment.

Deployment flow:

`MikeHacksAI/openai-defensive-drift` `main` → Cloudflare Pages project `openai-defensive-drift-v2` → `openai-defensive-drift-v2.pages.dev` → `defensive-drift.mikehacks.ai`

## Current Cloudflare Pages configuration

The canonical Pages project is configured as follows:

- Pages project: `openai-defensive-drift-v2`
- Repository: `MikeHacksAI/openai-defensive-drift`
- Production branch: `main`
- Framework preset: `None`
- Build command: blank
- Build output directory: `site`
- Root directory: blank
- Custom domain: `defensive-drift.mikehacks.ai`

The site is static HTML/CSS/JavaScript and does not require a build step.

## DNS

The production DNS record is:

- Type: `CNAME`
- Name: `defensive-drift.mikehacks.ai`
- Target: `openai-defensive-drift-v2.pages.dev`
- Proxy status: Proxied

Cloudflare Pages owns the custom-domain association. Do not treat the DNS record alone as sufficient proof of the active Pages project; verify the custom domain under the Pages project's **Custom domains** configuration when auditing deployment state.

## 2026-09-18 GitHub-organization migration

The original Cloudflare Pages project named `openai-defensive-drift` remained connected to the former GitHub repository identity:

`MikeHacksAI-Admin/openai-defensive-drift`

After the GitHub account was converted/migrated to the `MikeHacksAI` organization, that old Pages project no longer represented the canonical source repository used for active development.

A replacement Pages project was therefore created and verified before production cutover:

- replacement Pages project: `openai-defensive-drift-v2`
- canonical GitHub repository: `MikeHacksAI/openai-defensive-drift`
- production branch: `main`
- build output: `site`
- verification hostname: `openai-defensive-drift-v2.pages.dev`

The replacement site was visually verified before the production hostname moved. The production CNAME and Pages custom-domain association were then changed to the v2 project, and `defensive-drift.mikehacks.ai` resolved successfully after cutover.

The legacy `openai-defensive-drift` Pages project should be retained temporarily as rollback/history evidence until the v2 deployment path has demonstrated normal ongoing automatic deployments. It must not regain ownership of the production custom domain unless an explicit rollback is performed.

## Production-change safety rule

For future Pages migrations or repairs, direct live-state evidence outranks stale deployment documentation.

Before changing a production Pages association, record and verify:

1. existing Pages project name;
2. connected GitHub owner/repository;
3. production branch;
4. deployed/known-good Pages hostname;
5. build output directory;
6. current custom-domain association;
7. current DNS target; and
8. the proposed replacement project's independent `pages.dev` result.

A replacement project must be verified independently before the live custom domain is moved.

## GitHub Actions policy

Do not add a GitHub Actions workflow for public-site deployment unless the deployment architecture is deliberately changed in the future.

The repository previously contained `.github/workflows/deploy-pages.yml`. It was removed after GitHub Actions jobs were blocked by an account billing lock and the project adopted Cloudflare Pages native Git deployment instead.

This project should not depend on paid GitHub Actions execution for routine site publishing.

## Verification checklist

After a deployment or production-domain change:

- confirm the Cloudflare Pages deployment succeeds;
- confirm the Pages project is connected to `MikeHacksAI/openai-defensive-drift`;
- confirm production branch is `main`;
- confirm the deployed revision corresponds to the intended GitHub `main` commit;
- confirm `https://openai-defensive-drift-v2.pages.dev` loads the intended site;
- confirm `https://defensive-drift.mikehacks.ai` loads the same intended site;
- confirm HTTPS is valid;
- confirm CSS and JavaScript assets load correctly;
- confirm GitHub links and milestone links resolve;
- confirm `MikeHacksAI` in the footer links to `https://mikehacks.ai`;
- confirm no private/raw research corpus is included in the deployment;
- confirm no unmeasured research results are presented as measured findings.

## Public/private boundary

Only the `site/` directory is intended for public website deployment.

Private research working material belongs in the separate private companion repository `MikeHacksAI/openai-defensive-drift-private` or other explicitly private canonical sources. Raw drift evidence remains in its existing canonical repository and is not moved into the public site deployment.
