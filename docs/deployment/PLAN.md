# Rekalled — CI/CD and deployment plan

Status: ready to implement at slice 02. Every file named here is included in this change.

The step-by-step guide to releasing (merge → staging, tag → production, rollback) is in
[`TAGS.md`](TAGS.md). This document is the design and the why; that one is the how.

## The flow in one picture

```text
worktree branch ──PR──▶ main
   │                      │
   │  ci.yml              │  release.yml (on push to main)
   │  ├ repo-lint         │  ├ ci.yml again on the merged commit (no image job)
   │  ├ api               │  ├ build rekalled-api + rekalled-web ONCE  → :sha-<12>
   │  ├ web               │  ├ pull back, smoke test, Grype scan
   │  ├ images (build,    │  └ deploy.yml  environment=staging  (API, then web)
   │  │  smoke, scan)     │
   │  └ ci-ok  ◀── required check
   │  CodeRabbit ◀── required check
   │
   │                 git tag v1.4.0 <sha on main>   (git push origin v1.4.0)
   │                      │
   │                      ▼  promote.yml
   │                      ├ tag is on main? staging deploy of that sha succeeded?
   │                      ├ registry retag  sha-<12> → v1.4.0   (same digest, no build)
   │                      ├ deploy.yml  environment=production  (API, then web)
   │                      └ GitHub release with generated notes
```

Rollback: Actions → "Promote (tag -> production)" → Run workflow → `v1.3.2`.
This re-deploys the image that already exists. Nothing is rebuilt.

## Decisions

### 1. One branch, short-lived PRs

The repo uses trunk-based development with a single long-lived branch, `main`.

- Rename `master` to `main` in GitHub settings; GitHub redirects the old name.
- Each worktree has its own branch. Open a PR to `main`, then squash-merge it.
- `develop` and `staging` branches don't exist. Your previous projects used a branch per
  environment, so the same code went through two builds. That is the parity bug you described.

### 2. Build once, promote the same image

- Each merge to `main` builds each app exactly once and pushes it as `sha-<first 12 of commit>`.
- Images live in private GHCR packages `ghcr.io/roborewdev/rekalled-api` and
  `ghcr.io/roborewdev/rekalled-web`. GitHub Actions publishes with its built-in
  `GITHUB_TOKEN`; only publishing and promotion jobs receive `packages: write`.
- Staging deploys that tag automatically.
- Production runs the same bytes. A semver tag adds a `vX.Y.Z` alias to the existing
  manifest using `docker buildx imagetools create`. The workflow then checks that both tags
  have the same digest.
- There is no `latest`, `main` or `dev` tag. Those tags are mutable, so they can't tell you
  what is actually running.
- Staging is not tag-gated. You asked whether staging needs its own tags: it doesn't. The
  commit SHA already is the staging version, and staging always runs `main`. Production is
  what gets a human-chosen version.

### 3. Separate apps, separate images, separate Coolify resources

- `rekalled-api` and `rekalled-web` each have their own Dockerfile, image, Coolify application
  and health check.
- Both are built and deployed on every merge.
  - This keeps each commit a complete matched set.
  - It avoids "which web goes with which API" bookkeeping.
  - Building only the app that changed is a later optimisation. The retag mechanism already
    supports it.
- Deploy order is API, then web. A new web may call new endpoints. The old web keeps working
  against the new API because of rule 5.

### 4. Coolify "Docker Image" applications (not Compose, not Dockerfile)

Coolify should pull a pre-built image. It should not build one.

- Rolling updates only work for single-container applications, so Compose loses zero-downtime
  replacement ([Coolify rolling updates](https://coolify.io/docs/knowledge-base/rolling-updates)).
- A repo-based compose file is read from `main` HEAD, not from the commit being promoted.
- Coolify keeps the old container serving until the new one is healthy. If the new one never
  becomes healthy, Coolify removes it and the old one stays live.
- Rolling updates are disabled if you publish a host port or set a custom container name.
  Do neither.

### 5. Migrations run at API start, under a lock, and must be expand/contract

`docker/start.sh` runs `alembic upgrade head`, then starts uvicorn.

- `migrations/env.py` takes `pg_advisory_xact_lock`, so two containers starting at once can't
  both migrate. This was tested: of two concurrent runs, one applied both revisions and the
  other found nothing to do.
- Why not blocshed's separate migration resource? Coolify's pre-deploy command runs in the
  old container, and its post-deploy command runs after the new one is already serving. The
  new container is the only place that has the new migrations before it takes traffic.
- Because the old release still serves during the rollout, every migration must be backward
  compatible.
  - Add columns as nullable or with a server default.
  - Backfill if needed.
  - Drop or rename only in a later PR, after no running code uses the old column.
- CodeRabbit enforces this rule as a blocking pre-merge check.
- A failed migration exits the container, so the health check never passes and the old
  release keeps serving.
- Phase 2 option (from blocshed): a separate migrator role that owns DDL, while the app role
  only has DML.

### 6. Parity between staging and production

- Staging runs `ENV=production`. `ENV` describes the kind of runtime, not the name of the
  deployment. That means staging exercises the production validators, for example
  `AUTH_MODE=dev` being refused.
- Settings fails fast on any missing variable. So a variable you forget in one environment
  surfaces as a failed staging deploy, which is a free parity check.
- Infisical holds the same keys in its `staging` and `prod` environments. Only the values
  differ.
- Web build-time config breaks parity. `import.meta.env.VITE_*` is inlined when the image is
  built.
  - Rule: no `VITE_*` value may differ between environments. CodeRabbit enforces it.
  - From slice 11, the Logto endpoint, app ID and API URL do differ. Plan for this at slice 11:
    expose a small runtime-config route from the Start server that reads `process.env`. That is
    presentation config, not business logic.
  - Re-check the exact Start server-route API with Context7 when slice 11 is updated.

### 7. Secrets: Infisical at runtime, Coolify holds only the bootstrap

- The API entrypoint checks for `INFISICAL_PROJECT_ID`, `INFISICAL_CLIENT_ID` and
  `INFISICAL_CLIENT_SECRET`.
- If they are set, it:
  1. logs in with Universal Auth;
  2. drops the long-lived client secret;
  3. `exec`s `infisical run -- <command>`, which injects the secrets as environment variables.
- Without them, it uses whatever Coolify set. That keeps it working before you configure
  Infisical, and keeps local `docker run` simple.
- The app never knows which source it got its secrets from. It only reads environment
  variables through `Settings`.
- Dependency flag: the Infisical CLI (v0.44.12, checksum-verified) is installed in the image.
  It is an image and infra dependency, not an app dependency. Nothing in `pyproject.toml` or
  `package.json` changed.
- The web image has no secrets. Its runtime values (from slice 11) are public config, set
  directly in Coolify.

### 8. Supply-chain hygiene

- Every action is pinned to a full commit SHA with a version comment. Dependabot bumps them
  weekly, with a 7-day cooldown.
- Workflows:
  - default to `permissions: contents: read`;
  - check out with `persist-credentials: false`;
  - never use `pull_request_target`;
  - pass user input through `env:` only.
  - actionlint and zizmor (pedantic) are clean.
- The release build doesn't use the GitHub Actions cache, so a PR can't poison a production
  image.
- Grype scans the images, not Trivy. The `aquasecurity/trivy-action` and `setup-trivy` tags
  were repointed to a credential stealer in March 2026
  ([GitHub advisory](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23),
  [Microsoft analysis](https://www.microsoft.com/en-us/security/blog/2026/03/24/detecting-investigating-defending-against-trivy-supply-chain-compromise/)).
  CodeRabbit's own sandboxed Trivy is still enabled for IaC review.
- Images are pushed with SBOM and max-mode provenance attestations.

## Files in this change and why each exists

| File                                                                      | Why                                                                                                                    |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `.github/workflows/ci.yml`                                                | Every PR gate. Also reused by `release.yml`, so merged code passes the same checks. `ci-ok` is the one required check. |
| `.github/workflows/release.yml`                                           | Main → build once → smoke test + scan the pushed image → staging.                                                      |
| `.github/workflows/promote.yml`                                           | Tag or manual → verify → retag → production → GitHub release. It is also the rollback path.                            |
| `.github/workflows/deploy.yml`                                            | One deploy implementation for both environments. Only the GitHub environment differs.                                  |
| `.github/zizmor.yml`                                                      | Disables one rule: the new `$/` self-repo syntax is rejected by actionlint 1.7.12.                                     |
| `.github/dependabot.yml`                                                  | Weekly grouped updates for actions, uv, npm and Docker base images.                                                    |
| `.github/pull_request_template.md`                                        | Reminds you of the migration and parity rules on every PR.                                                             |
| `.coderabbit.yaml`                                                        | Review rules per path, linters, blocking pre-merge checks, auto-approve. Validated against the v2 schema.              |
| `apps/api/Dockerfile`, `.dockerignore`                                    | uv multi-stage build, non-root user, `GIT_SHA` baked in, health check, Infisical CLI.                                  |
| `apps/api/docker/entrypoint.sh`                                           | Chooses the secrets source (Infisical or plain env).                                                                   |
| `apps/api/docker/start.sh`                                                | Runs migrations, then uvicorn with proxy headers for Traefik.                                                          |
| `apps/api/migrations/env.py`                                              | Advisory lock around migrations.                                                                                       |
| `apps/api/app/core/config.py`, `api/v1/health.py`, `tests/test_health.py` | `/v1/health` now reports `git_sha`, so a deploy can prove the new commit is serving. Test-first, two tests.            |
| `apps/web/Dockerfile`, `.dockerignore`                                    | pnpm build. The runtime ships only Nitro's self-contained `.output` (about 1.6 MB, no node_modules).                   |
| `apps/web/vite.config.ts`                                                 | Excludes the generated `routeTree.gen.ts` from `vp fmt`. Without this, `vp check` fails in CI on a clean checkout.     |
| `scripts/ci/smoke-images.sh`                                              | Starts both images as Coolify would: production settings, migrations, health, `/v1/me` = 401.                          |
| `scripts/deploy/coolify-deploy.sh`                                        | PATCH tag → POST deploy → poll the deployment → check health serves the expected SHA.                                  |
| `justfile`                                                                | `just images` and `just smoke` reproduce CI locally.                                                                   |

## One-time setup checklist

### GitHub (RoborewDev/rekalled)

1. Settings → General → rename the default branch `master` to `main`. Locally, run:
   `git branch -m master main && git fetch && git branch -u origin/main main && git remote set-head origin -a`
2. Settings → General → Pull requests:
   - allow squash merge only;
   - turn on "Always suggest updating branches" and "Automatically delete head branches".
3. Rules → new branch ruleset targeting `main`:
   - Require a pull request.
   - Require status checks `ci-ok` and `CodeRabbit`, and "Require branches to be up to date".
   - Require conversation resolution.
   - Block force pushes and deletion.
   - Optional: require 1 approval. CodeRabbit auto-approves, but whether a bot approval counts
     toward required reviews isn't verified here, so test it on your first PR. As a solo
     developer you can't approve your own PR, so leave approvals at 0 if the bot's doesn't count.
4. Rules → new tag ruleset targeting `v*`:
   - Restrict creation to admins (bypass list = you).
   - Block updates and deletion, so a release tag can't be moved.
5. Settings → Environments:
   - Create `staging` and `production`.
   - On `production`, set "Deployment branches and tags" to selected: tag `v*` (tag
     releases) and branch `main` (manual rollbacks run from `main`). Required reviewers
     need a public repo or a paid plan, so treat that as optional.
6. Settings → Secrets and variables → Actions:

   | Scope                  | Name                        | Kind     | Value                                            |
   | ---------------------- | --------------------------- | -------- | ------------------------------------------------ |
   | Repository             | `COOLIFY_TOKEN`             | secret   | Coolify API token with deploy and write; explicitly passed to deploy.yml |
   | Repository             | `COOLIFY_BASE_URL`          | variable | `https://coolify.example.com`                    |
   | staging and production | `COOLIFY_API_UUID`          | variable | UUID of that environment's API app               |
   | staging and production | `COOLIFY_WEB_UUID`          | variable | UUID of that environment's web app               |
   | staging and production | `API_HEALTH_URL`            | variable | `https://api.staging.example.com/v1/health`      |
   | staging and production | `WEB_URL`                   | variable | `https://staging.example.com`                    |

7. Install CodeRabbit on the repo. `.coderabbit.yaml` in the repo root configures it.

### GitHub Container Registry

1. Keep private package creation and source-repository permission inheritance enabled in
   the organisation. The first release publishes `ghcr.io/roborewdev/rekalled-api` and
   `ghcr.io/roborewdev/rekalled-web`, linked to this repository.
2. Actions uses `GITHUB_TOKEN` automatically. Do not create a publishing PAT secret.
3. For private pulls, create a PAT (classic) with `read:packages`, using an account that
   can read these organisation packages. Authorise it for SSO if required. Enter it yourself
   through Coolify's server registry login, or run `docker login ghcr.io -u roborew`
   on the deployment server as the user Coolify uses for Docker.
4. No automatic image deletion runs during deployment. Any future retention job must
   protect release versions, deployed versions, rollback candidates and attestations.

Authentication and namespace ownership follow the
[GitHub Container registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
Server login must use the deployment server's Docker user, as described in
[Coolify's registry documentation](https://coolify.io/docs/knowledge-base/docker/registry).

### Coolify

1. Create a project `rekalled` with environments `staging` and `production`.
2. In each environment, create:
   - Postgres. Use the `pgvector/pgvector:pg17` image, or a managed DB with the `vector`
     extension available.
     - Turn on scheduled backups to DO Spaces.
     - Take a manual backup before each production tag.
   - API: New resource → Docker Image →
     `ghcr.io/roborewdev/rekalled-api`, tag `sha-…` (CI overwrites it).
     - Port 8000. Domain `api.<env-domain>`.
     - Health check type **CMD**: `python /app/docker/healthcheck.py`, with interval 10,
       timeout 5, retries 3 and start period 60.
     - The check is a script in the image because Coolify rejects quotes and brackets in
       health check commands, and the slim images have no curl or wget for HTTP checks
       ([Coolify health checks](https://coolify.io/docs/knowledge-base/health-checks)).
   - Web: Docker Image → `ghcr.io/roborewdev/rekalled-web`, port 3000, domain `<env-domain>`.
     - Health check type **CMD**: `node /app/healthcheck.mjs`, with interval 10, timeout 5,
       retries 3 and start period 20.
3. Don't map host ports and don't set a custom container name. Either one disables rolling
   updates.
4. API environment variables in Coolify:
   - Bootstrap only: `INFISICAL_PROJECT_ID`, `INFISICAL_ENV` (`staging` or `prod`),
     `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, plus `INFISICAL_API_URL` if
     self-hosted.
   - Before Infisical is set up, put `ENV=production`, `AUTH_MODE=logto` and `DATABASE_URL`
     here directly.
5. Turn off Coolify's own auto-deploy and webhooks for these apps. GitHub Actions is the only
   thing that deploys.
6. Copy each app's UUID from its URL into the GitHub environment variables.

### Infisical

1. Create a project `rekalled` with environments `staging` and `prod`. Use the same keys in
   both: `ENV=production`, `AUTH_MODE=logto` and `DATABASE_URL` (the Coolify internal hostname
   of that environment's Postgres). From slice 9, add `LOGTO_*`. From slice 13, add
   `OPENAI_API_KEY`.
2. Create two machine identities with Universal Auth, one per environment, each with read
   access to only its own environment. A leaked staging credential then can't read
   production.

## Day-to-day

Commands for each of these are in [`TAGS.md`](TAGS.md).

- Feature work:
  1. `git worktree add ../rekalled-s03 -b s03-decks origin/main`
  2. Commit test-first, push, open a PR.
  3. Fix whatever `ci-ok` and CodeRabbit report.
  4. Squash-merge. Staging updates in about 5–8 minutes.
- Release:
  1. Check staging.
  2. `git tag -a v0.3.0 -m "Decks" origin/main && git push origin v0.3.0`
  3. Production updates to the same image. For a new image, the workflow refuses if that
     commit isn't green on staging. An existing version image (rollback) is redeployed
     without repeating the staging check.
- Rollback: run Promote manually with the previous version. If a migration was involved, it
  has to be backward compatible under rule 5, so the old code still runs.
- Hotfix: the same as a feature PR. There are no release branches. Main is always releasable.

## Verified here, and what wasn't

Verified in the sandbox:

- API gates are green (ruff, ruff format, mypy, 14 pytest tests).
- `alembic check` reports no drift.
- The concurrent-migration lock works.
- Simulating the runtime image without Docker worked:
  - entrypoint, migrations, then uvicorn;
  - `/v1/health` returned the injected SHA;
  - `/v1/me` returned 401;
  - the HEALTHCHECK command passed.
- Web `vp check`, test and build pass. The `.output` server, started on its own, returned 200
  to the health check command.
- `coolify-deploy.sh` worked against a mock Coolify API: success, a failed deployment and the
  wrong SHA served.
- actionlint, zizmor (pedantic), hadolint and shellcheck are clean.
- `.coderabbit.yaml` and `dependabot.yml` validate against their JSON schemas.

Not verified (no Docker or real accounts here):

- the actual `docker build` of both images;
- registry push and retag;
- Coolify API calls against a real instance;
- the Infisical login inside the container;
- whether CodeRabbit's approval satisfies a required-review rule.

The first PR and the first merge exercise all of these. Expect to fix something small.

## Follow-ups by slice

- Slice 9 (Logto): staging needs a Logto app and API resource of its own.
  - Add the `LOGTO_*` values to both Infisical environments.
  - Add placeholder values to `scripts/ci/smoke-images.sh` so the production validators pass.
- Slice 10 (root pnpm workspace, `packages/api-client`):
  - The web Docker build context becomes the repo root.
  - Update `apps/web/Dockerfile`, `ci.yml` and `release.yml` together.
  - Add the OpenAPI drift check: generate the client in CI and `git diff --exit-code`.
- Slice 11 (web auth config): replace the `VITE_*` Logto values with runtime config, as in
  rule 6.
- Slice 15 of the build guide (its CI section) is superseded by these workflows.
