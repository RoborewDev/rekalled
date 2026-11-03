# Contributing to Rekalled

Patches are welcome. This project is deliberately strict about how changes are made: every contribution is **test-driven**, tested through public interfaces only, and keeps `main` always releasable. If you follow this document, CI and review will be quick.

Read these first if you're doing anything non-trivial:

- [`docs/spec/Flashcard Platform — 4-day Prototype Spec.md`](docs/spec/Flashcard%20Platform%20—%204-day%20Prototype%20Spec.md) — the product and its testing decisions
- [`docs/deployment/PLAN.md`](docs/deployment/PLAN.md) — the CI/CD rules your change must not break

## Ground rules

- **Trunk-based, short-lived PRs.** Branch from `main`, open a PR, keep it small and short-lived. Squash-merge is the only merge style. There are no `develop`/`staging` branches and no release branches — `main` is always releasable.
- **Required checks:** `ci-ok` and CodeRabbit must pass, and conversations must be resolved before merge. Don't force-push over review feedback; push fixes as new commits and let the squash merge clean up history.
- **Don't weaken the bar.** A PR that silences a check — skipping a test, adding an ignore/disable suppression, relaxing a threshold, deleting an assertion — needs to justify it explicitly in the PR description, or it will be rejected.
- **No new dependencies** without discussion. The backend dependency list is deliberately tiny; anything new must earn its place.

## Strict TDD — how every change is made

Every behaviour change follows red → green → refactor. A PR that arrives with implementation but no failing-test-first evidence will be asked to start over, because the tests are the point: they're what makes refactors safe and the architecture explainable.

### The loop

1. **Red.** Write exactly one failing test that expresses the behaviour you want. Run it and watch it fail for the reason you expect — a test that fails by accident (import error, wrong fixture) is not red, it's noise. Commit the test.
2. **Green.** Write the _minimum_ code to pass it. Resist implementing anything the test doesn't demand. Run the whole suite, not just your test.
3. **Refactor.** Clean up under green. The suite staying green is your proof the refactor preserved behaviour. `just lint` and type checks must pass too.

Repeat until the feature is done. A PR reads as a sequence of test+implementation commits (they'll be squashed on merge), or as one well-described pair — but the tests must exist and must be the spec for the change.

### What a good test is here

These rules are fixed by the spec's Testing Decisions. They are not stylistic preferences:

- **Test behaviour through public interfaces only.** A test should survive any refactor that doesn't change behaviour. If your test breaks when you rename an internal function, the test was wrong.
- **No mocking of internal collaborators.** Don't monkey-patch services or stub functions inside the app. Use the agreed seams and the provided fakes (below).
- **Expected values come from fixtures and worked examples, written down once** — never from re-running the code's own logic. If a Scheduler test asserts "Good on a New Card gives due_at = X", that X was captured from a real py-fsrs run once and hardcoded. Computing the expected value with the code under test proves nothing.
- **Never test the LLM or Logto for real.** No network in tests, ever. `conftest.py` sets `models.ALLOW_MODEL_REQUESTS = False`, so this is enforced, not just asked.

### The only seams you may test through

1. **FastAPI HTTP routes** (`httpx.AsyncClient`, real Postgres, `FakeCardGenerator` injected via dependency override, EC-signed test JWTs against a mocked JWKS). This is the main backend seam — auth cases, tenancy isolation (404s), CRUD, generation, draft commits, the study queue, idempotent reviews, stats with an injectable clock.
2. **Scheduler** — pure unit tests, fuzzing off, fixed UTC times, expected values from recorded py-fsrs fixtures.
3. **CardGenerator output parsing** — malformed or over-limit model output becomes a domain error; valid output becomes `CardDraft`s. Script the model with Pydantic AI's `FunctionModel`.
4. **Frontend auth wrapper and API layer** — Vitest + React Testing Library: token attachment, single 401 retry then redirect, `<RequireAuth>`.
5. **End to end** — the one Playwright journey (sign in → deck → paste → check drafts → save → study → memory score → sign out) with the fake generator and `FakeAuthAdapter`.

If you find yourself wanting to test somewhere else, that's a signal to either move the test to a seam or ask whether the code is in the wrong place.

### Fakes, not mocks

These are the spec's agreed fakes (each lands with its build slice):

- `FakeCardGenerator` — deterministic generation for tests and E2E.
- `FakeAuthAdapter` (behind `src/auth/`) — auth for E2E; the backend checks its tokens against a static test JWKS.
- `FunctionModel` — scripts LLM replies for adapter tests.
- The injectable clock — for anything time-dependent.

If your change needs a new fake, add it at the same seam as the existing ones and keep it deterministic.

## Rules your change must not break

These come from the deployment plan. CI and CodeRabbit enforce them as blocking checks; knowing them up front saves a round-trip:

- **Migrations must be expand/contract.** The old release keeps serving while a new one rolls out, so every migration must be backward compatible: add columns nullable or with a server default, backfill separately, and drop/rename only in a later PR once no running code uses the old shape. Generate with `just revision "message"`; test the lock behaviour if you touch `migrations/env.py`.
- **No `VITE_*` value may differ between environments.** Build-time config is inlined into the image and breaks staging/production parity. Runtime config that varies goes through the Start server's runtime-config route, not `import.meta.env`.
- **The generated client must not drift.** When the API contract changes, regenerate the client in the same PR (`just gen-client`, once the `packages/api-client` workspace lands — until then, this doesn't apply). CI regenerates and fails the PR on `git diff --exit-code`.
- **Keep the module boundaries.** Routes and services only see Protocols — Pydantic AI imports stay in `app/llm.py` and the adapters, `fsrs` is imported only by the Scheduler module, Logto only by `auth/`, and `@logto/react` only by the frontend `src/auth/` wrapper. A PR that leaks a provider or vendor into the wrong layer will be asked to move it.
- **Security posture is not negotiable:** actions pinned to full commit SHAs, `permissions: contents: read` defaults, no `pull_request_target`, user input through `env:` only.

## Practical checklist for a PR

Before you push, from the repo root:

```sh
just lint     # ruff + ruff format + mypy; eslint + tsc (vp check)
just test     # pytest against your running docker Postgres, then vitest
```

And for anything touching the API surface, Docker files or deploy scripts:

```sh
just images   # build both images exactly as CI does
just smoke    # smoke test them (needs a throwaway DB, see justfile)
```

Your PR should:

- [ ] Contain the failing tests, written first, and the minimum implementation that passes them
- [ ] Test only through the five seams, with no internal mocking and no network
- [ ] Use fixture/worked-example expected values, not values computed by the code under test
- [ ] Keep migrations expand/contract (or make none)
- [ ] Regenerate the API client if the contract changed
- [ ] Leave `just lint` and `just test` green locally, and CI (`ci-ok`) green on the PR
- [ ] Not weaken any check, skip any test, or add a suppression without justification
- [ ] Follow the PR template — it reminds you of the migration and parity rules

## Getting set up

```sh
git clone https://github.com/RoborewDev/rekalled
cd rekalled
cp .env.example .env
just db && just migrate
just api &  # or a separate terminal
just web
```

The dev auth bypass means you don't need Logto locally. If anything in this document is unclear or seems wrong, open an issue rather than guessing — the docs are the contract, and improvements to them are contributions too.
