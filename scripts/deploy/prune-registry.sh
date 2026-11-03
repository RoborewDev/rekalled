#!/usr/bin/env bash
# Delete all but the newest <keep> sha-* tags of one DOCR repository.
# vX.Y.Z tags are never touched; a release shares its manifest with its sha- tag, so
# deleting the sha- tag later does not remove the production image.
# Storage is only reclaimed after a registry garbage collection (run it manually or on a
# schedule outside deploy hours: it makes the registry read-only while it runs).
#
# Usage: prune-registry.sh <repository> <keep>
# Env:   DIGITALOCEAN_ACCESS_TOKEN, DO_REGISTRY_NAME
set -euo pipefail
repo="${1:?repository}"; keep="${2:?keep count}"
: "${DIGITALOCEAN_ACCESS_TOKEN:?}" "${DO_REGISTRY_NAME:?}"
base="https://api.digitalocean.com/v2/registry/${DO_REGISTRY_NAME}/repositories/${repo}/tags"
auth=(-H "Authorization: Bearer ${DIGITALOCEAN_ACCESS_TOKEN}")

mapfile -t old < <(curl -fsS "${auth[@]}" "${base}?per_page=200" \
  | jq -r --argjson keep "$keep" \
      '[.tags[] | select(.tag | startswith("sha-"))] | sort_by(.updated_at) | reverse
       | .[$keep:] | .[].tag')

for tag in "${old[@]}"; do
  echo "Deleting ${repo}:${tag}"
  curl -fsS -X DELETE "${auth[@]}" "${base}/${tag}" >/dev/null
done
echo "${repo}: kept ${keep} newest sha- tags, deleted ${#old[@]}"
