set dotenv-load

# Make sure .env and .env.local exist: copied from the main checkout when run in
# a worktree, otherwise pulled from Infisical. No-ops when both files are present.
env-files:
    bash scripts/env-files.sh

# Install/refresh both apps' dependencies (creates apps/api/.venv, apps/web/node_modules)
install:
    cd apps/api && uv sync
    cd apps/web && pnpm install

# Start Postgres (pgvector) in the background. Compose reads .env by default only;
# .env.local must be passed explicitly — that is where env-pull.sh keeps POSTGRES_*.
db: env-files
    docker compose --env-file .env --env-file .env.local up -d --wait db

# Run the API with reload on http://localhost:8000
api: env-files
    cd apps/api && uv run fastapi dev --port 8000

# Run the web app on http://localhost:3000
web:
    cd apps/web && vp dev --port 3000

# Run the API and the web app together; Ctrl-C stops both
dev: env-files
    bash scripts/dev.sh

migrate: env-files
    cd apps/api && uv run alembic upgrade head

# Fresh worktree, one command: env files, fresh Infisical pull, deps, db,
# migrations, then both apps. Every step is idempotent, so re-running picks up
# where it left off. Note: the pull means `start` needs the infisical CLI and
# network access even in a worktree (where env-files alone would just copy).
start: install import-env db migrate dev

# Pull the latest secrets from Infisical into .env.local. env-files first so a
# fresh worktree gets the INFISICAL_* bootstrap vars in .env before pulling.
import-env: env-files
    ./scripts/env-pull.sh

# Create a migration from model changes: just revision "add decks"
revision message: env-files
    cd apps/api && uv run alembic revision --autogenerate -m "{{ message }}"

test-api *args: env-files
    cd apps/api && uv run pytest {{ args }}

test-web:
    cd apps/web && vp test

test: test-api test-web

lint:
    cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run basedpyright --project ../../pyrightconfig.json
    cd apps/web && vp check

# Regenerate the typed TS client from FastAPI's OpenAPI schema
gen-client:
    cd apps/api && uv run python -m scripts.export_openapi
    pnpm --filter @rekalled/api-client generate

# Build both production images locally with the same Dockerfiles CI uses
images:
    docker build -t rekalled-api:local --build-arg GIT_SHA=$(git rev-parse HEAD) apps/api
    docker build -t rekalled-web:local --build-arg GIT_SHA=$(git rev-parse HEAD) apps/web

# Run the CI smoke test against locally built images (see scripts/ci/smoke-local.sh
# for the throwaway-database prerequisite)
smoke: images env-files
    bash scripts/ci/smoke-local.sh
