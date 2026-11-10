# Deployment setup

Use this guide for the one-time GitHub and Coolify setup. For routine deployments, see [Releases and rollback](TAGS.md).

## How deployment works

- **Pull requests:** run lint, tests, image smoke tests and security checks.
- **Merge to `main`:** build the API and web images, publish them to GHCR as `sha-<12>`, then deploy staging.
- **Push a `vX.Y.Z` tag:** promote the staging-tested images to production without rebuilding.
- **Deploy order:** API first, then web. Coolify pulls prebuilt images; it does not build them.

The workflows are in `.github/workflows/`: `ci.yml`, `release.yml`, `promote.yml` and the reusable `deploy.yml`.

## Configure GitHub

1. Use `main` as the default branch and squash-merge short-lived PRs.
2. Protect `main`: require PRs, `ci-ok`, CodeRabbit and resolved conversations; block force pushes and deletion.
3. Protect `v*` tags against changes and deletion. Limit tag creation to release maintainers.
4. Create the `staging` and `production` environments. Allow production deployments from `v*` tags and `main` for manual rollbacks. Add approval rules if supported and useful.
5. Add the settings below.

| Scope            | Name               | Type     |
| ---------------- | ------------------ | -------- |
| Repository       | `COOLIFY_TOKEN`    | Secret   |
| Repository       | `COOLIFY_BASE_URL` | Variable |
| Each environment | `COOLIFY_API_UUID` | Variable |
| Each environment | `COOLIFY_WEB_UUID` | Variable |
| Each environment | `API_HEALTH_URL`   | Variable |
| Each environment | `WEB_URL`          | Variable |

Use the same variable names in both environments, with the matching app UUIDs and URLs. `API_HEALTH_URL` ends in `/v1/health`.

The Coolify API token must support application updates, deployment and status polling. It is intentionally shared by staging and production; two same-team tokens would not by themselves isolate the environments ([Coolify permissions](https://coolify.io/docs/api-reference/permissions)).

## Connect GHCR

Images are stored in two private organisation packages:

```text
ghcr.io/roborewdev/rekalled-api
ghcr.io/roborewdev/rekalled-web
```

1. Allow private package creation and source-repository permission inheritance in the organisation.
2. Let Actions publish using its built-in `GITHUB_TOKEN`. No publishing PAT is needed.
3. Create a PAT (classic) with `read:packages` from an account with access to the packages. Authorise organisation SSO if required.
4. In Coolify, open Integrations → Registries, find the deployment server's `ghcr.io` entry and select Log In.
5. Enter the GitHub username and PAT, then confirm the registry test passes.

The registry login is shared by apps on that server. Do not put the PAT in application environment variables ([GitHub registry authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry), [Coolify registry setup](https://coolify.io/docs/knowledge-base/docker/registry)).

## Configure Coolify

Create API and web Docker Image applications in both `staging` and `production`. Reuse existing applications if they are already configured.

| Setting                      | API                                 | Web                               |
| ---------------------------- | ----------------------------------- | --------------------------------- |
| Image                        | `ghcr.io/roborewdev/rekalled-api`   | `ghcr.io/roborewdev/rekalled-web` |
| Port                         | `8000`                              | `3000`                            |
| Health check type            | CMD                                 | CMD                               |
| Health check command         | `python /app/docker/healthcheck.py` | `node /app/healthcheck.mjs`       |
| Interval / timeout / retries | 10s / 5s / 3                        | 10s / 5s / 3                      |
| Start period                 | 60s                                 | 20s                               |

- Set each app's domain and configure DNS and HTTPS.
- Leave the image tag separate from the image name. Actions sets it before deploying.
- Disable automatic deployments and app deployment webhooks.
- Do not publish host ports or set custom container names; these prevent rolling updates ([Coolify rolling updates](https://coolify.io/docs/knowledge-base/rolling-updates)).
- Copy the app UUIDs and public health URLs into the matching GitHub environment.

## Configure runtime settings

Use separate databases and Infisical environments for staging and production. Keep the same setting names in both, with different values.

On each app (API and web), set the Infisical bootstrap variables:

```text
INFISICAL_API_URL
INFISICAL_PROJECT_ID
INFISICAL_ENV
INFISICAL_CLIENT_ID
INFISICAL_CLIENT_SECRET
```

Keep credentials runtime-only, not build-time. Both images use the Infisical CLI to load settings when they start.

`INFISICAL_ENV` is the Infisical environment slug for that app: `staging` on staging and `prod` on production. Never use `dev`. Its `DATABASE_URL` points at the docker-compose Postgres on localhost. `infisical run` injects its values into the command's environment, overriding anything set in Coolify. The entrypoint therefore refuses `dev`, `development` and `local` and stops the container with a clear error. It also stops when the bootstrap variables are only partly set, or when login fails. Its first log line, `[entrypoint] secrets: infisical (project=… env=… domain=…)`, shows which environment loaded. The `INFISICAL_UNIVERSAL_AUTH_CLIENT_ID`/`_SECRET` and `INFISICAL_DOMAIN` aliases from `scripts/env-pull.sh` are also accepted.

`DATABASE_URL` may be pasted as the provider gives it, such as `postgresql://…?sslmode=require` from DigitalOcean. Settings rewrites it for asyncpg as `postgresql+asyncpg://…?ssl=require`.

In Infisical, set `ENV=production`, `AUTH_MODE=logto` and the environment's `DATABASE_URL`, plus the authentication and AI settings required by the implemented features. Use an identity with access only to its own environment.

The web app uses the same bootstrap variables and the same entrypoint pattern as the API: with them present it logs in and wraps the server in `infisical run`, injecting the environment's values as plain environment variables; without them the server runs with whatever the platform set. A wrong or `dev` slug is refused, a partly-set bootstrap fails, and a failed login stops the container with a clear error instead of serving requests without configuration.

In Infisical, each environment the web app deploys to needs `API_URL` (that environment's public API origin, for example `https://api-staging.rekalled.app` on staging), `AUTH_MODE` (the same value the API uses) and — with `AUTH_MODE=logto` — `LOGTO_ENDPOINT`, `LOGTO_APP_ID` and `LOGTO_API_RESOURCE` (the same public values the API uses). The server validates all of them at start-up via a Nitro plugin, so a missing value crashes the container before it listens and Coolify shows it unhealthy; the old failure mode — a healthy container whose pages could not load their config — can no longer hide behind the `/` health check. The promoted image still needs no rebuild and no `VITE_*` value for any of this.

Keep secrets out of the web image. Any public configuration that differs between environments must be supplied at runtime, not baked into `VITE_*` build settings. Note that `infisical run` injects every secret the machine identity can read, so the web server's process also holds the environment's database and AI keys today; when convenient, give the web app its own machine identity (or a web/ folder path in Infisical) with access to only the values above.

In Infisical, also set `CORS_ORIGINS` to a JSON list of the web app's public origin, such as `["https://app.rekalled.app"]`. The API refuses to start in production when the list is empty, contains `*`, or contains a localhost or scheme-less entry.

## Migrations and checks

- API startup runs `alembic upgrade head` under a PostgreSQL advisory lock.
- Use expand/contract migrations so the previous application version can still run during deployment and rollback.
- Enable database backups and take a backup before a production release.
- After deployment, check the API's `/v1/health` reports the expected commit SHA and open the web app.
- Keep action pins, image scans, SBOM and provenance checks enabled.

## Image maintenance

No automatic package deletion runs during deployment. Review the [GHCR cleanup guide](GHCR-RETENTION.md) before the first production release, then monthly or when storage needs attention.
