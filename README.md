# Rekalled

A flashcard app for turning reading material into cards and reviewing them with spaced repetition. Built with TanStack Start, FastAPI and PostgreSQL.

## Quick start

Requires Docker, Python 3.13+, uv, pnpm, Vite+ (`vp`) and just.

Copy `.env.example` to `.env` and fill in the local settings, then install dependencies:

```sh
cd apps/api && uv sync --locked
cd ../web && pnpm install --frozen-lockfile
cd ../..
```

Start the database and apply migrations:

```sh
just db
just migrate
```

Run the API and web app in separate terminals:

```sh
just api     # http://localhost:8000
just web     # http://localhost:3000
```

## Useful commands

```sh
just test
just lint
just revision "add decks"
```

## Documentation

- [Product specification](docs/spec/Flashcard%20Platform%20%E2%80%94%204-day%20Prototype%20Spec.md)
- [Architecture decisions](docs/decisions/)
- [Contributing](CONTRIBUTING.md)
- [Deployment setup](docs/deployment/PLAN.md)
- [Releases and rollback](docs/deployment/TAGS.md)
