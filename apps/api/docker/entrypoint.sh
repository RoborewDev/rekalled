#!/bin/sh
# Container entrypoint: decides where secrets come from, then runs the command.
#
# If Infisical bootstrap variables are present, secrets are fetched at start-up and
# injected as environment variables for the command (and only for it). Otherwise the
# command runs with whatever the platform (Coolify) set. Either way the app reads plain
# environment variables through Settings, so it never knows which source was used.
set -eu

if [ -n "${INFISICAL_PROJECT_ID:-}" ] \
  && [ -n "${INFISICAL_CLIENT_ID:-}" ] && [ -n "${INFISICAL_CLIENT_SECRET:-}" ]; then
  domain="${INFISICAL_API_URL:-https://app.infisical.com/api}"
  export INFISICAL_DISABLE_UPDATE_CHECK=true
  # Exchange the machine identity for a short-lived token, then drop the long-lived
  # client secret from this process so the app never sees it.
  INFISICAL_TOKEN="$(infisical login --method=universal-auth \
    --client-id="${INFISICAL_CLIENT_ID}" --client-secret="${INFISICAL_CLIENT_SECRET}" \
    --domain="${domain}" --silent --plain </dev/null)"
  export INFISICAL_TOKEN
  unset INFISICAL_CLIENT_ID INFISICAL_CLIENT_SECRET
  echo "[entrypoint] secrets: infisical (env=${INFISICAL_ENV:?set INFISICAL_ENV})" >&2
  exec infisical run --projectId="${INFISICAL_PROJECT_ID}" --env="${INFISICAL_ENV}" \
    --domain="${domain}" --silent -- "$@"
fi

echo "[entrypoint] secrets: platform environment variables" >&2
exec "$@"
