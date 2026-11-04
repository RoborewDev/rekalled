# GHCR cleanup

The project maintainer reviews image storage before the first production release, then monthly or when storage needs attention. Cleanup is manual; deployment workflows do not delete images.

Apply this to both `rekalled-api` and `rekalled-web` packages.

## Keep

- Every release version (`v*`).
- Images currently deployed in staging or production, plus any other rollback candidates.
- The newest 15 SHA versions and anything published in the last 30 days.
- Untagged versions, platform manifests, attestations and OCI referrers.

## Clean up

1. Check package storage and note the deployed API/web tags and digests in Coolify.
2. Identify SHA-only versions older than 30 days and outside the newest 15.
3. Exclude everything protected above. If a version's dependencies or purpose are unclear, keep it.
4. With no deployment running, recheck the candidates and delete only confirmed unused versions in GitHub's package settings.
5. Note the cleanup date and removed versions. Confirm the retained release images still resolve.

Deleting a package version removes all its tags. Untagged versions may be required by another image or its metadata, so do not bulk-delete them ([GitHub package-version API](https://docs.github.com/en/rest/packages/packages?apiVersion=2022-11-28#delete-package-version-for-an-organization)).

Use the normal GitHub account for manual cleanup. Do not add deletion permissions to CI or to Coolify's read-only registry token.
