#!/usr/bin/env bash
# Run the API (fastapi dev) and the web app (vp dev) together; Ctrl-C stops both.
#
# Usage: bash scripts/dev.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

api_pid=""
web_pid=""

alive() {
  local stat
  stat="$(ps -p "$1" -o stat= 2>/dev/null)" || return 1
  [[ "$stat" != *Z* ]]
}

cleanup() {
  local status="${1:-$?}"
  trap - EXIT INT TERM
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  if [[ -n "$web_pid" ]]; then
    kill "$web_pid" 2>/dev/null || true
    wait "$web_pid" 2>/dev/null || true
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(cd apps/api && exec uv run fastapi dev --port 8000) &
api_pid=$!
(cd apps/web && exec vp dev --port 3000) &
web_pid=$!

# Wait for either server to exit, then stop the other and propagate its status.
while alive "$api_pid" && alive "$web_pid"; do
  sleep 1
done

status=0
if ! alive "$api_pid"; then
  wait "$api_pid" || status=$?
else
  wait "$web_pid" || status=$?
fi
cleanup "$status"
