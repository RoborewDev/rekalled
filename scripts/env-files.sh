#!/usr/bin/env bash
# Make sure .env and .env.local exist at the repo root.
#
# In a worktree, copy them from the main checkout (instant, offline); otherwise
# pull secrets with env-pull.sh. No-ops when both files are already present.
#
# Usage: bash scripts/env-files.sh
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

has_secrets() {
  [[ -f "$1" ]] && grep -qE '^[A-Za-z_][A-Za-z0-9_]*=' "$1"
}

if [[ -f .env ]] && has_secrets .env.local; then
  exit 0
fi

main="$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')"

if [[ ! -f .env ]]; then
  if [[ ! -f "$main/.env" ]]; then
    echo "No .env here or in the main checkout ($main) — see .env.example." >&2
    exit 1
  fi
  cp "$main/.env" .env
  chmod 600 .env
  echo "Copied .env from $main"
fi

if ! has_secrets .env.local; then
  if [[ "$main" != "$REPO_ROOT" ]] && has_secrets "$main/.env.local"; then
    cp "$main/.env.local" .env.local
    chmod 600 .env.local
    echo "Copied .env.local from $main"
  else
    # The main checkout has no pulled secrets either — pull them now.
    bash scripts/env-pull.sh
  fi
fi
