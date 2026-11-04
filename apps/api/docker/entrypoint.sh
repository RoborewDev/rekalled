#!/bin/sh
# Container entrypoint: decides where secrets come from, then runs the command.
#
# If Infisical bootstrap variables are present, secrets are fetched at start-up and
# injected as environment variables for the command (and only for it). Otherwise the
# command runs with whatever the platform (Coolify) set. Either way the app reads plain
# environment variables through Settings, so it never knows which source was used.
#
# Coolify holds only the bootstrap variables; DATABASE_URL and friends live in Infisical.
# `infisical run` injects its secrets into the command's environment, overriding anything
# Coolify set, so the Infisical environment chosen by INFISICAL_ENV wins. That is why a
# wrong slug is refused here.
set -eu

log() { echo "[entrypoint] $*" >&2; }
fail() {
  log "error: $*"
  exit 1
}

# Same names as scripts/env-pull.sh and the Fidget/Blocshed entrypoints.
project_id="${INFISICAL_PROJECT_ID:-}"
client_id="${INFISICAL_CLIENT_ID:-${INFISICAL_UNIVERSAL_AUTH_CLIENT_ID:-}}"
client_secret="${INFISICAL_CLIENT_SECRET:-${INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET:-}}"
env_slug="${INFISICAL_ENV:-}"

if [ -z "${project_id}${client_id}${client_secret}${env_slug}" ]; then
  log "secrets: platform environment variables"
  exec "$@"
fi

# Partly configured is a mistake, not a request for the platform fallback: falling back
# would start the app without its secrets and fail later with a less useful error.
missing=""
[ -n "${project_id}" ] || missing="${missing} INFISICAL_PROJECT_ID"
[ -n "${client_id}" ] || missing="${missing} INFISICAL_CLIENT_ID"
[ -n "${client_secret}" ] || missing="${missing} INFISICAL_CLIENT_SECRET"
[ -n "${env_slug}" ] || missing="${missing} INFISICAL_ENV"
[ -z "${missing}" ] || fail "Infisical is partly configured; missing:${missing}"

# This image only runs in deployed environments. The dev environment's DATABASE_URL
# points at the docker-compose Postgres on localhost, so a dev slug can never work here.
case "${env_slug}" in
  dev | development | local)
    [ "${INFISICAL_ALLOW_DEV_ENV:-false}" = true ] \
      || fail "INFISICAL_ENV=${env_slug} loads local-development secrets; set it to this deployment's Infisical environment slug (e.g. staging or prod)"
    ;;
esac

domain="${INFISICAL_API_URL:-${INFISICAL_DOMAIN:-https://app.infisical.com/api}}"
export INFISICAL_DISABLE_UPDATE_CHECK=true
# The app must never see the long-lived machine identity, whichever alias set it.
unset INFISICAL_CLIENT_ID INFISICAL_CLIENT_SECRET \
  INFISICAL_UNIVERSAL_AUTH_CLIENT_ID INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET

# Exchange the machine identity for a short-lived token.
if ! token="$(infisical login --method=universal-auth \
  --client-id="${client_id}" --client-secret="${client_secret}" \
  --domain="${domain}" --silent --plain </dev/null)" || [ -z "${token}" ]; then
  fail "Infisical login failed (domain=${domain})"
fi
unset client_id client_secret
INFISICAL_TOKEN="${token}"
export INFISICAL_TOKEN

log "secrets: infisical (project=${project_id} env=${env_slug} domain=${domain})"
exec infisical run --projectId="${project_id}" --env="${env_slug}" \
  --domain="${domain}" --silent -- "$@"
