#!/bin/sh
# Start the API: apply migrations, then replace this shell with the server process.
#
# Migrations run here, inside the new container, before it reports healthy. Coolify keeps
# the old container serving until then, so migrations must be backward compatible with the
# previous release (expand/contract). env.py takes an advisory lock, so two containers
# starting together cannot run them twice.
set -eu

if [ "${MIGRATE_ON_START:-true}" = "true" ]; then
  alembic upgrade head
fi

# --proxy-headers: trust X-Forwarded-* from Traefik (Coolify's proxy) for scheme and client
# IP. The container port is only reachable on Coolify's Docker network, not the internet.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips="*" --no-server-header
