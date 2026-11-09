#!/usr/bin/env bash
# Start the API and web images exactly as Coolify will (production settings, migrations on
# start) and check they become healthy. Needs Postgres with pgvector on localhost:5432.
#
# Usage: smoke-images.sh <api-image> <web-image> <expected-sha>
# Env:   SMOKE_DATABASE_URL to use another database (default: the CI Postgres service)
set -euo pipefail
api_image="${1:?}"; web_image="${2:?}"; expected_sha="${3:?}"

cleanup() {
  docker logs rekalled-api-smoke 2>&1 | tail -50 || true
  docker rm -f rekalled-api-smoke rekalled-web-smoke >/dev/null 2>&1 || true
}
trap cleanup EXIT

# ENV=production on purpose: staging and production run the same validators. The LOGTO_*
# and CORS_ORIGINS values are non-empty placeholders: Settings requires the former in logto
# mode and refuses localhost origins in production, but the JWKS client only fetches keys
# when a token arrives, and this smoke test never sends one.
docker run -d --name rekalled-api-smoke --network host \
  -e ENV=production -e AUTH_MODE=logto -e PORT=8000 \
  -e LOGTO_ENDPOINT=https://logto-smoke.invalid \
  -e LOGTO_API_RESOURCE=https://api-smoke.invalid \
  -e LOGTO_APP_ID=smoke-app-id \
  -e CORS_ORIGINS='["https://web-smoke.invalid"]' \
  -e PYDANTIC_AI_GATEWAY_API_KEY=pylf_v1_eu_smoke-not-a-real-key \
  -e DATABASE_URL="${SMOKE_DATABASE_URL:-postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/rekalled_smoke}" \
  "$api_image" >/dev/null
# The web server reads its API origin at runtime, so set one as Coolify would.
docker run -d --name rekalled-web-smoke --network host \
  -e PORT=3000 -e API_URL=http://127.0.0.1:8000 "$web_image" >/dev/null

wait_healthy() { # container
  for _ in $(seq 1 30); do
    state="$(docker inspect -f '{{.State.Health.Status}}' "$1" 2>/dev/null || echo missing)"
    [ "$state" = healthy ] && { echo "$1 healthy"; return 0; }
    [ "$state" = missing ] && break
    sleep 3
  done
  echo "::error::$1 did not become healthy (state: ${state:-unknown})"; return 1
}
wait_healthy rekalled-api-smoke
wait_healthy rekalled-web-smoke

served="$(curl -fsS http://127.0.0.1:8000/v1/health | jq -r .git_sha)"
[ "$served" = "$expected_sha" ] || { echo "::error::image reports ${served}, expected ${expected_sha}"; exit 1; }
# Auth is enforced in the production image: no token means 401, never a dev user.
code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/v1/me)"
[ "$code" = 401 ] || { echo "::error::/v1/me returned ${code} without a token, expected 401"; exit 1; }
curl -fsS -o /dev/null http://127.0.0.1:3000/
echo "Smoke test passed for ${expected_sha}"
