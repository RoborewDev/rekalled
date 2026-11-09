# Spec — Rekalled: 4-day build

**Status:** ready-for-agent
**Tracker:** local markdown (`.scratch/prototype/`)
**Product name:** Rekalled (rekalled.app)
**Revision 2 (2 Nov 2026):** Studying with FSRS is now in scope and is the primary job of the app. Checking AI drafts is no longer called "review"; "review" now means rating a Card while studying. There is one draft-check screen (the checklist). The build order is in `BUILD-GUIDE.md`.
**Revision 3 (2 Nov 2026):** The LLM client is now [Pydantic AI](https://pydantic.dev/docs/ai/overview/) (`pydantic-ai-slim[openai]`), with every model call routed through [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/). This replaces the Vercel `ai` Python package and Vercel AI Gateway. The gateway shows cost, limits and traces for each call in Logfire. Frontend AI integrations aren't used.

## Problem Statement

I learn from articles, docs and notes, but turning that material into flash cards by hand is slow, so most of it is never reviewed and is forgotten. Existing tools either make me write every card myself, or generate cards I can't trace back to where they came from and can't quickly correct. I also want a place to keep my own notes and find them again later by meaning, not just by exact words.

Separately, I'm using this project to practise product design and production-grade full-stack engineering for interviews. So the architecture has to be clean, explainable and tested, not just working.

## Solution

A web app whose home screen is **Study today**: the Cards that are due, one button to start, and a **Memory score** that shows how much I'm likely to remember right now. I study one Card at a time: I see the question, reveal the answer, and rate how well I remembered it (Again, Hard, Good or Easy). The FSRS scheduler, running in FastAPI, uses that rating to decide when I see the Card next. Every Card has its own Memory score, and each Deck's score is the average of its studied Cards.

To get Cards, I create a **Deck**, paste text into it as a **Source**, and an LLM turns that Source into **Draft Cards**. I check the drafts quickly: every draft is kept by default, and I can edit or untick any of them before saving. Saved Cards stay linked to the Source and to the exact passage they came from. I can browse, edit and delete Cards in a Deck. I sign in with a hosted identity provider, and my data is visible only to me.

The 4-day build delivers the architecture, the paste → generate → check → save flow, and studying with FSRS scheduling and Memory scores. URL/PDF import, Notes with semantic recall, the PWA, and deployment are designed for but not built.

## Domain Glossary

- **User**: a person who signs in. A User is also a tenant: each User sees only their own data.
- **Deck**: a named group of Cards owned by one User.
- **Source**: a piece of material added to a Deck that Cards are generated from. In the prototype, only pasted text. Each Source belongs to exactly one Deck.
- **Card**: a question and answer pair. Belongs to exactly one Deck, and optionally to one Source.
- **Source excerpt**: the passage of a Source that a Card was generated from.
- **Draft Card**: a Card the LLM generated that hasn't been checked yet.
- **Draft check**: the step where the User keeps, edits or drops Draft Cards before saving them. Not called "review".
- **Active Card**: a Card that was kept at the draft check. Only Active Cards are studied.
- **Generation**: one LLM run that turns a Source into Draft Cards.
- **New Card**: an Active Card that has never been studied (`last_review_at` is null).
- **Due Card**: a studied Card whose `due_at` is now or in the past.
- **Study session**: one pass through the study queue: Due Cards first (oldest due first), then up to 10 New Cards.
- **Review**: one rating of one Card during a Study session. Ratings are Again (1), Hard (2), Good (3) and Easy (4). Each Review is stored in `review_logs`.
- **Memory score**: FSRS retrievability, the predicted chance that the User would recall a Card right now, shown as a percentage. A Deck's Memory score is the mean over its studied Cards. New Cards have no score and are counted separately.
- **Scheduler**: the FSRS algorithm (the `fsrs` Python package) that turns a Review into the Card's next due date.
- **Note** (roadmap): free text written by the User and retrieved later by meaning.

## User Stories

1. As a User, I want to sign in through a hosted sign-in page, so that I never create a password inside this app.
2. As a User, I want to be returned to the page I was trying to open after signing in, so that sign-in doesn't lose my place.
3. As a User, I want to sign out, so that nobody else using my browser can see my Decks.
4. As a User, I want my session to stay valid without signing in again every few minutes, so that work isn't interrupted.
5. As a User, I want to see my profile (display name and permissions), so that I know which account I'm using.
6. As a User, I want to create a Deck with a name, so that I can group related Cards.
7. As a User, I want to see a list of my Decks with Card counts, so that I can choose one to work on.
8. As a User, I want to rename a Deck, so that its name stays accurate.
9. As a User, I want to delete a Deck, so that I can remove material I no longer need.
10. As a User, I want to paste text into a Deck as a new Source, so that I can generate Cards from it.
11. As a User, I want to give a Source an optional title, so that I can recognise it later.
12. As a User, I want to be told clearly when my pasted text is too long, so that I know to split it.
13. As a User, I want the LLM to decide how many Cards to make, within a sensible maximum, so that short and long texts both get suitable coverage.
14. As a User, I want to see a clear loading state while Cards are generated, so that I know the app is working.
15. As a User, I want generated Cards saved as drafts straight away, so that refreshing the page doesn't lose LLM output.
16. As a User, I want every Draft Card kept by default, so that the draft check is fast when the output is good.
17. As a User, I want to untick a Draft Card to drop it, so that I can reject poor Cards with one click.
18. As a User, I want to edit a Draft Card's question and answer before saving, so that I can fix small errors.
19. As a User, I want to see the Source excerpt under each Draft Card, so that I can check it against the original text.
20. As a User, I want to save the whole draft check in one action, so that kept Cards become Active and dropped Cards are deleted together.
21. As a User, I want to come back later to a Source whose drafts I haven't checked, so that I can finish checking them.
22. As a User, I want a clear error if Generation fails, and the option to retry, so that a temporary model problem doesn't lose my Source.
23. As a User, I want to see all Active Cards in a Deck, so that I know what I've built.
24. As a User, I want to edit an Active Card, so that I can improve it later.
25. As a User, I want to delete an Active Card, so that I can remove Cards that aren't useful.
26. As a User, I want to see which Source a Card came from, so that I can trust and check it.
27. As a User, I want edits and deletes to update the screen at once, so that the app feels fast.
28. As a User, I want to be sure that no other User can see or change my Decks, Sources or Cards, so that my material stays private.
29. As a developer, I want a dev auth bypass that only works in development, so that I can run the app locally without Logto.
30. As a developer, I want the app to refuse to start if the bypass is turned on outside development, so that it can never ship to production by mistake.
31. As a developer, I want a typed TypeScript API client generated from FastAPI's OpenAPI spec, so that the frontend and backend contracts can't silently drift.
32. As a developer, I want CI to fail when the generated client is out of date, so that contract drift is caught before merging.
33. As a developer, I want the LLM behind a single `CardGenerator` interface with a fake version, so that tests are fast and free and don't depend on the network.
34. As a developer, I want the app runnable locally with one command, so that setup is trivial for me and for reviewers.
35. As a developer, I want CI to run linting, type checks, unit tests, API tests and one E2E test on every pull request, so that `main` always works.
36. As a developer, I want the identity provider behind a frontend wrapper and a backend auth module, so that moving from Logto Cloud to self-hosted Logto, or another OIDC provider, is a config change plus one adapter.
37. As a developer, I want FSRS state stored on the Card row and every Review appended to `review_logs`, so that scheduling is cheap to query and the history can later be used to tune FSRS parameters.
38. As a developer, I want a `user_entitlements` table and scope checks, so that usage limits and billing have a ready place to plug in.
39. As an interviewer reading the repo, I want ADRs explaining the key decisions, so that I can follow the reasoning behind the architecture.
40. As a User, I want Study today to be the first screen after signing in, so that studying is the obvious thing to do.
41. As a User, I want to see how many Cards are due and how many are new, with an estimate of the time it will take, so that I can decide to start.
42. As a User, I want to study all my Decks at once or one Deck, so that I can focus when I need to.
43. As a User, I want to see a question, try to answer it in my head, then reveal the answer, so that I practise recall rather than recognition.
44. As a User, I want to see the Source excerpt with the answer, so that I can check my understanding against the original text.
45. As a User, I want to rate each Card Again, Hard, Good or Easy using buttons or the keys 1 to 4, so that studying is fast.
46. As a User, I want each rating button to show when I'd see the Card next, so that I understand what the rating does.
47. As a User, I want a Card I rate Again to come back later in the same session, so that I relearn it while it's fresh.
48. As a User, I want each answer saved as soon as I give it, and a repeated submission to have no effect, so that leaving early or a flaky network never loses or doubles progress.
49. As a User, I want a Memory score for every Card and every Deck, so that I can see what I'm likely to forget.
50. As a User, I want each Deck's Cards split into strong (90% or more), fading, weak (under 75%) and new, so that I can see the shape of what I know.
51. As a User, I want an overall Memory score, the number of Reviews today, and a 7-day forecast of Due Cards on Study today, so that I can see my progress and plan ahead.
52. As a User, I want a summary at the end of a session showing my Memory score before and after, so that studying feels rewarding.
53. As a User, I want to be told when nothing is due and when the next Card will be, so that I don't study too early.
54. As a User, I want newly saved Cards to be offered for study straight away, so that I start learning while the material is fresh.

## Implementation Decisions

### Architecture (fixed by the developer)

- **Frontend:** TanStack Start (Router + Query) as a thin presentation layer. Start server functions contain no business logic, and Start never connects to the database.
- **Backend:** FastAPI is the only owner of data and business logic. Logic lives in plain Python service modules, called by thin REST routes.
- **API:** REST, versioned under `/v1`. FastAPI's OpenAPI spec is the contract. A TypeScript client is generated from it with `@hey-api/openapi-ts` into a workspace package.
- **Streaming:** SSE is reserved for the future RAG `/ask` feature. Card Generation in the prototype is a normal request and response, not streamed.
- **GraphQL:** not part of the core. It gets added only for read-heavy, relationship-heavy screens that meet the documented triggers.
- **Data:** one Postgres database with pgvector, and one schema managed by Alembic. Uses SQLAlchemy 2 (async) and Pydantic v2.
- **Single origin:** in development, the Start dev server proxies `/v1/*` to FastAPI. In production, the reverse proxy does the same.

### Repository layout

- A monorepo:
  - `apps/web`: TanStack Start, using pnpm.
  - `apps/api`: FastAPI, managed with uv, with a flat `app/` package (`apps/api/app/`).
  - `packages/api-client`: the generated TypeScript client. It's a separate package because a React Native (Expo) app is the planned second consumer. Auth stays out of it; each app adds its token through the client's config.
- pnpm workspaces for the TypeScript side, and uv for Python.
- A root `justfile` for commands that span both sides: `just dev`, `just gen-client`, `just test`, `just lint`.
- Docker Compose runs Postgres with pgvector. The api and web containers are optional for local dev and required for E2E.

### Identity and tenancy

- Identity is delegated to **Logto** (Logto Cloud first, self-hosted Logto OSS possible later). The full auth task brief from the grilling session is ticket 03's source of truth, with the amendments below.
- A tenant is a User. A local `users` table is created just in time on a User's first request, keyed by `(auth_provider, auth_subject)`. Every owned table has an `owner_id` foreign key to `users.id`, which is our own UUID, never Logto's ID.
- The single FastAPI dependency `get_current_user` identifies the caller. Requesting another User's resources returns 404.
- **Amendments to the auth brief, agreed during grilling:**
  - Logto signs JWTs with EC keys (ES384) by default ([Logto signing keys](https://docs.logto.io/developers/signing-keys)). Restrict validation to the algorithm the tenant's JWKS publishes, which is expected to be ES384. Test keys are EC P-384 pairs, not RSA.
  - Check the access token's `at+jwt` `typ` header and the `client_id` claim, so ID tokens can't be used as access tokens ([Logto changelog](https://blog.logto.io/changelogs/2026-august)).
  - The Logto application type is **Single page app**.
  - A default `user` role is set in the Logto Console (Roles → General), so no Management API call is needed ([Logto RBAC](https://docs.logto.io/authorization/role-based-access-control)).
  - The SDK always requests `offline_access` and refreshes tokens itself ([Logto React quick start](https://docs.logto.io/quick-starts/react)). No extra refresh configuration is needed.
  - Scopes are `decks:read`, `decks:write` and `cards:generate`. Studying uses `decks:read` for reading and `decks:write` for Reviews. `admin:users` and the admin role are deferred.
  - `users.email` and `users.display_name` stay nullable and are not filled in the prototype. `/v1/me` returns them as null, and the profile page reads the display name from the SDK's ID token claims. Before writing the user-creation code, decode one real access token to confirm which claims Logto includes.
  - The dev bypass uses a fixed subject `dev|local`, goes through the same just-in-time user creation, gets every scope, and can be overridden with an `X-Dev-User` header for manual multi-user testing. It only works when `ENV=development`.
  - E2E tests use a `FakeAuthAdapter` behind the `src/auth/` wrapper (`VITE_AUTH_MODE=fake`). The backend validates its tokens against a static test JWKS served in CI. The real Logto flow is covered by a manual smoke checklist in the README.
  - The concurrent-first-request test is deferred, but the `INSERT … ON CONFLICT DO NOTHING` then `SELECT` pattern is still used.

### Schema (shape, not DDL)

- **users:** `id`, `auth_provider`, `auth_subject` (unique together), `email` (nullable), `display_name` (nullable), timestamps.
- **user_entitlements:** `user_id`, `feature`, `limit`, `updated_at`. A placeholder only, with no logic.
- **decks:** `id`, `owner_id`, `name`, timestamps.
- **sources:** `id`, `owner_id`, `deck_id`, `kind` (`text` now, with `url` and `pdf` reserved), `title` (nullable), `content` (the extracted text), timestamps.
- **cards:**
  - Identity and ownership: `id`, `owner_id`, `deck_id`, `source_id` (nullable, so hand-written Cards are possible later).
  - Content: `card_type` (`basic` now), `question`, `answer`, `source_excerpt` (nullable).
  - Lifecycle: `status` (`draft` or `active`).
  - FSRS columns, mirroring the `fsrs` package's `Card` (all null while a Card is a draft):
    - `fsrs_state` (smallint: 1 Learning, 2 Review, 3 Relearning) and `fsrs_step` (smallint, nullable).
    - `stability` and `difficulty` (floats, null until the first Review).
    - `due_at` (timestamptz) and `last_review_at` (timestamptz, null for New Cards).
    - `reps` and `lapses` (ints, our own counters for display; not part of FSRS).
  - When a draft becomes Active: `fsrs_state = 1`, `fsrs_step = 0`, `due_at = now()`, the others null, and the counters at 0.
  - Timestamps.
  - An index on `(owner_id, due_at)` for the study queue.
- **review_logs** (append-only):
  - `id`: a UUID generated by the client. It is the primary key, which makes `POST /v1/reviews` idempotent.
  - `owner_id`, `card_id` (cascade on Card delete), `rating` (1–4), `reviewed_at`.
  - A snapshot of the Card's FSRS state after the Review (`fsrs_state`, `stability`, `difficulty`, `due_at`), for debugging and future parameter tuning.
  - An index on `(owner_id, reviewed_at)` for "Reviews today".
- The first migration also runs `CREATE EXTENSION IF NOT EXISTS vector`, so Notes can be added later without touching the database image.

### Modules

- **CardGenerator** (deep module, at the external seam):
  - Interface: `generate(text, *, max_cards) -> list[CardDraft]`, where each `CardDraft` has `question`, `answer` and `source_excerpt`.
  - Two adapters:
    - **LlmCardGenerator** uses a [Pydantic AI](https://pydantic.dev/docs/ai/overview/) `Agent` with `output_type` set to a Pydantic model, so the output is validated, and invalid output is sent back to the model for one retry (`retries={"output": 1}`). Calls go through [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/). The model is a Pydantic AI model string from config (`AI_MODEL`, default `gateway/openai:gpt-5.4-mini`).
    - **`app/llm.py`** is the only module that knows about gateway credentials. It builds models with `infer_model` and a provider factory that maps the `gateway/` prefix to `gateway_provider(upstream, api_key=...)`. It passes the key from `Settings` (`PYDANTIC_AI_GATEWAY_API_KEY`) explicitly, because pydantic-settings reads `.env` into `Settings`, not into `os.environ`. The key's region (`pylf_v1_<region>_...`) picks the gateway URL.
    - **FakeCardGenerator** is deterministic, for tests and E2E.
  - Hides: prompt construction, splitting text into chunks, enforcing the card limit, retries, and turning invalid model output into a domain error.
- **Generation service**:
  - Interface: `create_source_and_generate(user, deck_id, text, title) -> Source with Draft Cards`.
  - Enforces the text limit (about 20k characters, set in config) and the card limit (about 20, set in config).
  - Saves the Source before calling the generator, so a failed Generation keeps the Source and can be retried.
- **Draft commit service**:
  - Interface: `commit_drafts(user, source_id, kept: [{card_id, question, answer}]) -> list[Card]`.
  - In one transaction: kept drafts get their edits, become `active` and get their initial FSRS state; the other drafts for that Source are deleted.
  - Running it again is harmless.
- **Scheduler** (deep module, the only code that imports `fsrs`):
  - Interface: `review(card_state, rating, now) -> card_state`, `preview(card_state, now) -> {rating: next_due_at}`, `retrievability(card_state, now) -> float | None`.
  - Hides: mapping our columns to and from `fsrs.Card`, the UTC-only rule of py-fsrs, and the scheduler settings (desired retention 0.9, fuzzing on in the app and off in tests).
  - Pure functions with no database access, so worked-example unit tests are easy.
- **Study service**:
  - `get_queue(user, deck_id | None, new_limit=10) -> list[StudyCard]`: Due Cards ordered by `due_at`, then New Cards in creation order. Each StudyCard includes the next-due preview for all four ratings, so the client never runs FSRS.
  - `submit_review(user, review_id, card_id, rating) -> Card`: in one transaction, inserts into `review_logs` with `ON CONFLICT (id) DO NOTHING`. If the row already existed, it returns the Card unchanged. Otherwise it locks the Card row (`SELECT … FOR UPDATE`), applies the Scheduler and saves the new state.
  - `summary(user) -> {score, due, new, studied, reviews_today, forecast_7d}` and `deck_stats(user, deck_id) -> {score, due, new, total, bands}`. Scores are computed when they are read, never stored, because retrievability changes with time. Python over the rows is fine at prototype scale; a SQL version can come later.
  - "Today" is the UTC day in the prototype.
- **Deck and Card services**: CRUD, always filtered by `owner_id`.
- **Auth module** (`auth/`): config, JWT validation, `get_auth_info`, `get_current_user`, `require_scope`. This is the only code that knows about Logto.
- **Frontend `src/auth/`**: `useAuth()`, `<RequireAuth>`, and two adapters, `LogtoAuthAdapter` and `FakeAuthAdapter`. No other frontend code imports `@logto/react`.
- **Frontend study screens**: Study today, the Study session and the Deck page, as in the prototype. Keyboard: Space reveals the answer, 1–4 rate it. Each rating is sent with a `crypto.randomUUID()` `review_id`.
- **Frontend API layer**: the generated client plus a fetch wrapper that attaches the Bearer token, retries once on a 401 after forcing a token refresh, and then redirects to sign-in. Private data is loaded with TanStack Query, client-side only. Protected routes don't render on the server.

### API contract (prototype)

| Method               | Path                             | Scope            | Notes                                                                                                                               |
| -------------------- | -------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| GET                  | `/v1/me`                         | any              | id, email, display_name, scopes                                                                                                     |
| GET / POST           | `/v1/decks`                      | read / write     | list with Card counts and `stats` (score, due, new, total, bands); create                                                           |
| GET / PATCH / DELETE | `/v1/decks/{id}`                 | read / write     | 404 if not the owner                                                                                                                |
| POST                 | `/v1/decks/{id}/sources`         | `cards:generate` | body `{title?, text}`; creates the Source and runs Generation; returns the Source plus Draft Cards; 413/422 if the text is too long |
| GET                  | `/v1/sources/{id}`               | read             | Source plus its Draft and Active Cards                                                                                              |
| POST                 | `/v1/sources/{id}/generate`      | `cards:generate` | retry Generation for a Source with no drafts                                                                                        |
| POST                 | `/v1/sources/{id}/drafts/commit` | write            | commits the draft check in one request                                                                                              |
| GET                  | `/v1/decks/{id}/cards`           | read             | Active Cards, each with `memory_score`, `due_at`, `reps` and `lapses`                                                               |
| GET                  | `/v1/study/queue?deck_id=`       | read             | the study queue, each Card with `next_due` previews for ratings 1–4                                                                 |
| POST                 | `/v1/reviews`                    | write            | body `{review_id, card_id, rating}`; idempotent on `review_id`; returns the updated Card with its new `memory_score`                |
| GET                  | `/v1/study/summary`              | read             | overall score, due, new, studied, Reviews today, 7-day forecast                                                                     |
| PATCH / DELETE       | `/v1/cards/{id}`                 | write            | edit or delete a Card                                                                                                               |

### CI (GitHub Actions)

- On each pull request:
  - Linting and type checks: ruff and mypy for Python; eslint and tsc for TypeScript.
  - pytest against a Postgres service container.
  - The client drift check (regenerate the client and `git diff --exit-code`).
  - Vitest.
  - One Playwright test against the Compose stack, with the fake generator and fake auth.
- Real LLM calls and real Logto never run in CI.
- Deployment (GitHub Actions to DigitalOcean) is out of scope for this work.

## Testing Decisions

- **What a good test is:** it tests behaviour through public interfaces only. A test should survive a refactor that doesn't change behaviour. No mocking of internal collaborators. Expected values come from fixtures and worked examples, not from re-running the code's own logic.
- **Agreed seams:**
  1. **FastAPI HTTP routes:** the main backend seam. pytest with `httpx.AsyncClient`, a real Postgres database, `FakeCardGenerator` injected through a FastAPI dependency override, and EC-signed test JWTs checked against a mocked JWKS. Covers:
     - Auth cases from the brief, amended to EC keys: valid, expired, wrong issuer, wrong audience, tampered signature, unknown `kid`, wrong `typ`, missing scope (403), missing header (401).
     - Just-in-time user creation and reuse.
     - Isolation between users (404).
     - The dev bypass being refused outside development.
     - Deck CRUD.
     - Generation creating a Source plus drafts, including the text-limit error.
     - Generation failure keeping the Source.
     - Committing drafts (kept → active with initial FSRS state, dropped → deleted, edits applied, repeat commit harmless).
     - The study queue: Due before New, the New-Card limit, a Deck filter, and other Users' Cards never appearing.
     - Reviews: the Card's state changes, a repeated `review_id` changes nothing, a rating outside 1–4 gives 422, and another User's Card gives 404.
     - Deck stats and the summary, with times controlled through an injectable clock.
     - Card edit and delete.
  2. **Scheduler:** unit tests with fuzzing off and fixed UTC times. They check that a New Card rated Good moves through the short learning steps and then graduates to Review, Again on a Review Card moves it to Relearning, Easy gives a later due date than Good, and retrievability is 1.0 straight after a Review and falls over time. Expected values come from py-fsrs runs written down once as fixtures.
  3. **CardGenerator output parsing:** unit tests showing that badly formed or over-limit model output becomes a domain error, and valid output becomes `CardDraft`s.
  4. **Frontend auth wrapper and API layer:** Vitest plus React Testing Library. Covers attaching the token, retrying once on 401 then redirecting, and `<RequireAuth>` redirecting when signed out.
  5. **End to end:** one Playwright journey: sign in (fake adapter) → create a Deck → paste text → check drafts (edit one, drop one) → save → study the new Cards (reveal, rate) → see the Deck's Memory score → sign out.
- **Prior art:** none yet (new repository). These tests become the patterns later tests follow.
- **LLM adapter tests:** `FunctionModel` from Pydantic AI's [testing tools](https://pydantic.dev/docs/ai/guides/testing/) scripts the model's replies, and `models.ALLOW_MODEL_REQUESTS = False` in `conftest.py` stops any test from reaching a real model.
- **Model quality:** a manual script runs the real `LlmCardGenerator` against sample texts. It isn't run in CI.

## Out of Scope

- URL and PDF import (planned: `trafilatura` for URLs, `pypdf` for PDFs, behind `extract(input) -> SourceText`).
- Background Generation jobs and SSE progress updates.
- Tuning FSRS parameters per User (the optimizer), per-User time zones and daily limits, undoing a Review, and card burying or suspending.
- Draft-check variants B (split view) and C (one at a time) from the prototype.
- Notes, embeddings, hybrid search and the RAG `/ask` feature.
- Card types other than basic.
- PWA, offline sync, web push and mobile apps.
- The admin role, `admin:users`, and the concurrent-first-request test.
- Billing and entitlement logic.
- GraphQL.
- Deployment and hosting.
- Calling models from the browser. Pydantic AI's frontend integrations (for example the Vercel AI SDK UI adapter) aren't used; the web app only talks to `/v1`.

## Further Notes

- Pydantic AI is `pydantic-ai-slim[openai]>=2.64.0`. The `openai` extra brings in the OpenAI SDK, which the gateway uses for OpenAI models; this is an approved exception to the rule of adding no dependencies beyond `@logto/react` and `PyJWT[crypto]`. Pydantic AI needs Python 3.11 or later; the project pins 3.13.
- Pydantic AI imports stay in `app/llm.py` and the adapters (`LlmCardGenerator`, and later `LlmEmbedder` and `LlmAnswerer`). Routes and services only see the Protocols. Switching provider is a model-string change (`gateway/anthropic:...`, or `openai:...` without the gateway).
- Retry naming: some docs show `output_retries=`. In 2.64 the Agent takes `retries={"output": N}`. Check against the installed version.
- FSRS uses the official [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) package (`fsrs` on PyPI), pinned. It works only with UTC datetimes, and `review_card` returns the new Card and a ReviewLog. It is the only backend dependency added beyond the earlier list.
- ADRs to write (final ticket):
  1. Delegate identity to an OIDC provider (Logto), with FastAPI validating JWTs. Alternatives considered: Better Auth, Clerk, FastAPI Users. Includes the migration plan from Cloud to self-hosted OSS.
  2. FastAPI is the only owner of data and logic, and Start is a thin layer.
  3. REST is the default, with GraphQL only when its triggers are met.
  4. FSRS scheduling runs only on the server, using py-fsrs, with idempotent Reviews keyed by a client UUID. Alternatives considered: SM-2, and running ts-fsrs in the browser.
