# Defensive Drift Site Deployment

Canonical public domain: `https://defensive-drift.mikehacks.ai`

Site source: `site/`

Deployment workflow: `.github/workflows/deploy-pages.yml`

## Hosting

The initial public research site is deployed with GitHub Pages from the `site/` directory through GitHub Actions.

## One-time GitHub Pages setup

In `MikeHacksAI/openai-defensive-drift`:

1. Open **Settings**.
2. Open **Pages** under Code and automation.
3. Under **Build and deployment → Source**, select **GitHub Actions**.
4. Under **Custom domain**, enter `defensive-drift.mikehacks.ai` and save.
5. Enable **Enforce HTTPS** after GitHub provisions the certificate.

The repository contains `site/CNAME` for documentation/artifact continuity, but GitHub requires the custom domain to be configured in repository Pages settings (or its Pages API) as well.

## Cloudflare DNS

Create a DNS record in the `mikehacks.ai` zone:

- Type: `CNAME`
- Name: `defensive-drift`
- Target: `mikehacksai.github.io`
- Proxy status during initial GitHub validation: `DNS only`

Do not create a second conflicting A/AAAA/CNAME record for `defensive-drift`.

## Verification

After GitHub Pages is enabled and DNS has propagated:

- confirm the Pages workflow completes successfully;
- confirm `https://defensive-drift.mikehacks.ai` loads the research landing page;
- confirm HTTPS is valid;
- confirm CSS and JavaScript assets load from the custom domain;
- confirm GitHub links and milestone links resolve;
- confirm no unmeasured research results are shown as measured findings.

## Updating the site

Any push to `main` that changes `site/**` automatically triggers `.github/workflows/deploy-pages.yml`.

The deployment artifact contains only the `site/` directory, not the private/raw research corpus.
