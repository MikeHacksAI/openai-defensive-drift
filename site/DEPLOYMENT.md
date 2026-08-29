# Defensive Drift Site Deployment

Canonical public domain: `https://defensive-drift.mikehacks.ai`

Canonical source repository: `MikeHacksAI/openai-defensive-drift`

Canonical branch: `main`

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

GitHub Actions is intentionally not used for this project.

Deployment flow:

`GitHub main` → `Cloudflare Pages native Git integration` → `defensive-drift.mikehacks.ai`

## Cloudflare Pages project setup

Create a Cloudflare Pages project connected directly to the GitHub repository:

- Repository: `MikeHacksAI/openai-defensive-drift`
- Production branch: `main`
- Framework preset: `None`
- Build command: leave blank
- Build output directory: `site`

The site is static HTML/CSS/JavaScript and does not require a build step.

Cloudflare Pages should automatically deploy future commits to `main` that affect the public site source.

## Custom domain

Attach this custom domain to the Cloudflare Pages project:

`defensive-drift.mikehacks.ai`

The hostname was previously pointed at GitHub Pages during initial setup. Once the Cloudflare Pages custom domain is attached, the existing GitHub-targeted DNS record should be replaced by the DNS configuration Cloudflare Pages creates or requests.

Do not leave multiple conflicting A, AAAA, or CNAME records for `defensive-drift`.

## GitHub Actions policy

Do not add a GitHub Actions workflow for public-site deployment unless the deployment architecture is deliberately changed in the future.

The repository previously contained `.github/workflows/deploy-pages.yml`. It was removed after GitHub Actions jobs were blocked by an account billing lock and the project adopted Cloudflare Pages native Git deployment instead.

This project should not depend on paid GitHub Actions execution for routine site publishing.

## Verification checklist

After the Cloudflare Pages project and custom domain are configured:

- confirm the Cloudflare Pages deployment succeeds;
- confirm the deployed revision corresponds to the intended GitHub `main` commit;
- confirm `https://defensive-drift.mikehacks.ai` loads the research landing page;
- confirm HTTPS is valid;
- confirm CSS and JavaScript assets load correctly;
- confirm GitHub links and milestone links resolve;
- confirm no private/raw research corpus is included in the deployment;
- confirm no unmeasured research results are presented as measured findings.

## Public/private boundary

Only the `site/` directory is intended for public website deployment.

Private research working material belongs in the separate private companion repository `MikeHacksAI/openai-defensive-drift-private` or other explicitly private canonical sources. Raw drift evidence remains in its existing canonical repository and is not moved into the public site deployment.
