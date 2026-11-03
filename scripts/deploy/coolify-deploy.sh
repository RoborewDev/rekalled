#!/usr/bin/env bash
# Point one Coolify "Docker Image" application at an image tag, deploy it, wait for the
# result, and (optionally) prove the new container is serving the expected commit.
#
# Usage: coolify-deploy.sh <app-uuid> <image-tag> [health-url] [expected-sha]
# Env:   COOLIFY_BASE_URL (e.g. https://coolify.example.com), COOLIFY_TOKEN (deploy + write)
#
# Coolify API: PATCH /api/v1/applications/{uuid}, POST /api/v1/deploy?uuid=,
#              GET /api/v1/deployments/{deployment_uuid}
set -euo pipefail

app_uuid="${1:?app uuid}"
image_tag="${2:?image tag}"
health_url="${3:-}"
expected_sha="${4:-}"
: "${COOLIFY_BASE_URL:?}" "${COOLIFY_TOKEN:?}"

# An expected SHA can only be checked through the health URL: reject a missing URL up front,
# before anything is deployed, not after the API is already serving unverified.
if [ -n "$expected_sha" ] && [ -z "$health_url" ]; then
  echo "::error::expected-sha was given but no health URL was: the served commit cannot be verified" >&2
  exit 1
fi

api="${COOLIFY_BASE_URL%/}/api/v1"
timeout_s="${DEPLOY_TIMEOUT_SECONDS:-900}"

coolify() { # method path [json-body]
  local args=(-fsS --retry 3 --retry-all-errors -X "$1" "${api}$2"
    -H "Authorization: Bearer ${COOLIFY_TOKEN}" -H "Accept: application/json")
  if [ $# -ge 3 ]; then args+=(-H "Content-Type: application/json" --data "$3"); fi
  curl "${args[@]}"
}

echo "::group::Point ${app_uuid} at tag ${image_tag}"
coolify PATCH "/applications/${app_uuid}" \
  "$(jq -nc --arg t "$image_tag" '{docker_registry_image_tag: $t}')" >/dev/null
echo "::endgroup::"

deployment_uuid="$(coolify POST "/deploy?uuid=${app_uuid}&force=false" \
  | jq -er '.deployments[0].deployment_uuid')"
echo "Coolify deployment ${deployment_uuid} queued"

deadline=$(( $(date +%s) + timeout_s ))
status=""
while :; do
  status="$(coolify GET "/deployments/${deployment_uuid}" | jq -r '.status')"
  case "$status" in
    finished) echo "Coolify deployment finished"; break ;;
    failed|cancelled*|error)
      echo "::error::Coolify deployment ${deployment_uuid} ended with status ${status}"
      coolify GET "/deployments/${deployment_uuid}" | jq -r '.logs // empty' | tail -c 4000 || true
      exit 1 ;;
  esac
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "::error::Timed out after ${timeout_s}s waiting for ${deployment_uuid} (last: ${status})"
    exit 1
  fi
  sleep "${POLL_SECONDS:-10}"
done

# Coolify "finished" means the new container passed its healthcheck. The public check
# below proves the proxy now routes to it, and for the API that it runs the right commit.
if [ -n "$health_url" ]; then
  for _ in $(seq 1 30); do
    if body="$(curl -fsS --max-time 5 "$health_url" 2>/dev/null)"; then
      if [ -z "$expected_sha" ]; then echo "Healthy: ${health_url}"; exit 0; fi
      served="$(jq -r '.git_sha // empty' <<<"$body" 2>/dev/null || true)"
      if [ "$served" = "$expected_sha" ]; then
        echo "Healthy and serving ${served}"; exit 0
      fi
      echo "Serving ${served:-unknown}, waiting for ${expected_sha}..."
    fi
    sleep 5
  done
  echo "::error::${health_url} did not report the expected release"
  exit 1
fi
