# Contributing

Use short-lived branches from `main`, keep PRs focused and squash-merge once checks pass. See the [README](README.md) for local setup.

## Make a change

For behaviour changes, use red → green → refactor:

1. Write one test, confirm it fails for the intended reason and commit it.
2. Add the minimum implementation to pass it, then run the suite.
3. Refactor with tests green and run lint and type checks.

Use the [product specification](docs/spec/Flashcard%20Platform%20%E2%80%94%204-day%20Prototype%20Spec.md) for the detailed behaviour and testing decisions.

## Test through public interfaces

- **API:** HTTP routes with real PostgreSQL, test JWTs and the fake generator.
- **Scheduler:** fixed UTC times and recorded fixtures.
- **Generator:** output parsing with scripted `FunctionModel` replies.
- **Frontend:** auth and API wrappers.
- **End to end:** the main study journey with fake auth and generation.

Use deterministic fakes and an injectable clock, not mocks of internal collaborators. Keep expected values in fixtures or worked examples rather than computing them with the code under test. Never call real model providers or Logto in tests.

## Check before opening a PR

```sh
just lint
just test
```

For image, API startup or deployment changes, also run:

```sh
just images
just smoke
```

The smoke test needs a throwaway database; see the `justfile`.

## Keep these boundaries

- FastAPI owns data and business logic; TanStack Start stays a presentation layer.
- Keep Logto integration in `auth/`, model-provider code in its adapters and FSRS imports in the Scheduler. The web app's token-refresh gate is documented in [docs/web/AUTH-TOKEN-FLOW.md](docs/web/AUTH-TOKEN-FLOW.md).
- Use expand/contract migrations. Create them with `just revision "message"` and check the advisory lock if changing migration startup.
- Keep environment-specific web settings at runtime, not in `VITE_*` build values.
- When a generated API client is present, regenerate it with API contract changes.
- Discuss new dependencies before adding them.
- Keep Actions pinned and permissions minimal. Pass untrusted workflow input through environment variables, not directly into shell scripts.
- The repo is LF-only: `.gitattributes` forces LF for scripts, Dockerfiles and the justfile, and CI fails on CRLF in any tracked file. Don't set `core.autocrlf=true` (it rewrote the worktree to CRLF once and broke the deploy scripts).

See [Deployment setup](docs/deployment/PLAN.md) for deployment configuration and [Releases and rollback](docs/deployment/TAGS.md) for release commands.

## Submit the PR

Follow the PR template and include what changed, how it was tested and any deployment notes. Include the failing-test-first evidence for behaviour changes; explain any skipped tests, suppressions or weakened checks.

Wait for `ci-ok` and CodeRabbit, resolve conversations and push review fixes as new commits before squash-merging.
