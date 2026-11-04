#!/usr/bin/env bash
# Run the API (fastapi dev) and the web app (vp dev) together; Ctrl-C stops both.
#
# Usage: bash scripts/dev.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

(cd apps/api && exec uv run fastapi dev --port 8000) &
(cd apps/web && exec vp dev --port 3000) &
wait
