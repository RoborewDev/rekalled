set dotenv-load

# Start Postgres (pgvector) in the background
db:
    docker compose up -d --wait db

# Run the API with reload on http://localhost:8000
api:
    cd apps/api && uv run fastapi dev --port 8000

# Run the web app on http://localhost:3000
web:
    cd apps/web && vp dev --port 3000

migrate:
    cd apps/api && uv run alembic upgrade head

# Create a migration from model changes: just revision "add decks"
revision message:
    cd apps/api && uv run alembic revision --autogenerate -m "{{message}}"

test-api *args:
    cd apps/api && uv run pytest {{args}}

test-web:
    cd apps/web && vp test

test: test-api test-web

lint:
    cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
    cd apps/web && vp check
