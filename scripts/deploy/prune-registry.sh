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

# Command substitution, not a process substitution: a curl or jq failure then stops the
# script under set -e instead of silently pruning nothing. Page through the API so a
# repository with more than one page of tags is pruned too.
all=""
page=1
while :; do
  body="$(curl -fsS "${auth[@]}" "${base}?page=${page}&per_page=200")"
  page_tags="$(jq -r '.tags[] | select(.tag | startswith("sha-")) | [.updated_at, .tag] | @tsv' <<<"$body")"
  all="${all}${page_tags}"$'\n'
  [ "$(jq -r '.tags | length' <<<"$body")" -lt 200 ] && break
  page=$((page + 1))
done

# Newest first by updated_at (ISO timestamps sort lexically); keep the newest <keep>.
mapfile -t old < <(printf '%s' "$all" | LC_ALL=C sort -r | awk -v keep="$keep" 'NR > keep { print $2 }')

for tag in "${old[@]}"; do
  echo "Deleting ${repo}:${tag}"
  curl -fsS -X DELETE "${auth[@]}" "${base}/${tag}" >/dev/null
done
echo "${repo}: kept ${keep} newest sha- tags, deleted ${#old[@]}"
