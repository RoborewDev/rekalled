# Rekalled — Releases and tags

How code gets from a merge to production. The rule in one line: **only production uses version tags. Staging deploys every time code lands on `main`.**

- Staging is automatic. There is nothing to tag by hand, and staging always runs the latest `main`.
- Production is a human decision, expressed as a `vX.Y.Z` git tag on a commit that staging has already run.

The workflows behind this are `.github/workflows/release.yml` (merge → build once → staging) and `.github/workflows/promote.yml` (tag → verify → production). The full CI/CD design, including why, is in [`PLAN.md`](PLAN.md).

## Staging: merge to main

1. Open a PR from your worktree branch to `main`.
2. Once `ci-ok` and CodeRabbit pass, squash-merge it.
3. The release workflow builds both images once, tags them `sha-<first 12 of commit>` (for example `sha-3f9c2a1b7d04`), and deploys that tag to staging.

There's nothing to tag by hand, and staging always runs the latest `main`.

## Production: push a version tag

1. Check that staging looks right. The commit you tag must already be deployed to staging successfully, or the workflow refuses.
2. Tag that commit and push the tag:

   ```bash
   git fetch origin
   git tag -a v0.3.0 -m "Decks and cards" origin/main
   git push origin v0.3.0
   ```

3. The promote workflow then:
   - checks the tag matches `vMAJOR.MINOR.PATCH` and the commit is on `main`;
   - checks that commit's staging release run succeeded (a re-run counts as its latest attempt);
   - adds `v0.3.0` as a second tag on the existing `sha-…` images, with no rebuild and the same digest;
   - deploys `v0.3.0` to production, API first, then web;
   - creates a GitHub release with generated notes.

To release an older commit that's still on `main`, tag that SHA instead of `origin/main`. Its staging deployment must have succeeded.

## Rollback

You don't push a new tag. Go to Actions → "Promote (tag -> production)" → Run workflow, and enter an earlier version such as `v0.2.1`. It redeploys that existing image without rebuilding.

## Version numbers

Use semantic versioning:

- **Patch** (`v0.3.1`): fixes.
- **Minor** (`v0.4.0`): new features.
- **Major** (`v1.0.0`): breaking changes, or the first public release.

Tags like `v1.0.0-rc.1` don't trigger a deploy — the workflow only matches `v[0-9]+.[0-9]+.[0-9]+`.

## Rules that protect tags

The setup checklist in [`PLAN.md`](PLAN.md#one-time-setup-checklist) creates a tag ruleset so only admins can create `v*` tags, and nobody can move or delete them. If a release is bad, ship a new patch version or roll back. Never re-point an existing tag.

## In the registry

Both apps use private organisation packages: `ghcr.io/roborewdev/rekalled-api` and
`ghcr.io/roborewdev/rekalled-web`. Staging and production use these same packages;
only their tags differ.

| Tag                | Created by                            | Used by    |
| ------------------ | ------------------------------------- | ---------- |
| `sha-3f9c2a1b7d04` | Every merge to `main`                 | Staging    |
| `v0.3.0`           | Your git tag, added to the same image | Production |

There's no `latest`, `main` or `staging` image tag, so a tag always tells you exactly which build is running.
