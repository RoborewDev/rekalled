# Releases and rollback

Staging deploys from `main`; production deploys from version tags. Both use the same GHCR images, with no rebuild between environments.

## Deploy staging

1. Open a PR to `main` and wait for the required checks.
2. Squash-merge it.
3. Wait for the Release workflow to finish, then check staging.

The images use `sha-<first 12 characters of the commit>`. No staging tag needs to be created manually.

## Deploy production

Choose a new version and tag the commit that passed staging:

```sh
git fetch origin
git tag -a v0.1.0 -m "Initial release" origin/main
git push origin v0.1.0
```

Replace the version and message as needed. If `main` has moved since the staging run, tag the tested commit SHA instead.

The Promote workflow checks the commit, adds the version tag to the existing images, verifies the digests match, deploys production and creates release notes. Check production health when it finishes.

Use `vMAJOR.MINOR.PATCH`; prerelease tags such as `v0.1.0-rc.1` do not trigger deployment. Never move or reuse an existing release tag.

## Roll back

Open Actions → Promote (tag -> production) → Run workflow. Select `main` and enter an earlier release version.

Both images for that version must still exist in GHCR. The workflow redeploys them without rebuilding; database changes must remain backward compatible. The first production release has no earlier application release to restore.

See [Deployment setup](PLAN.md) for configuration and [GHCR cleanup](GHCR-RETENTION.md) for image retention.
