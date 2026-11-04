#!/usr/bin/env bash
# Run the CI smoke test (ci/smoke-images.sh) against locally built images
# (rekalled-api:local, rekalled-web:local). Uses the local Postgres from
# docker-compose: needs a throwaway database, create it first, e.g.
# `docker compose exec db createdb -U postgres rekalled_smoke`
#
# Usage: bash scripts/ci/smoke-local.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# POSTGRES_* live in .env.local after env-pull.sh; source both so .env.local wins.
set -a
# shellcheck disable=SC1091
source .env
# shellcheck disable=SC1091
source .env.local
set +a

SMOKE_DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:${POSTGRES_HOST_PORT:-5433}/rekalled_smoke" \
  bash scripts/ci/smoke-images.sh rekalled-api:local rekalled-web:local "$(git rev-parse HEAD)"
