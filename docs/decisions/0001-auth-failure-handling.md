# ADR-0001: Auth failures degrade to an error screen, never a sign-in loop

## Status

Accepted

## Date

2026-11-12

## Context

On staging (2026-11-12) every authenticated request returned 401 and the page reloaded
endlessly. Root cause: a Cloudflare bot filter in front of the Logto tenant blocked the
API's JWKS fetch — PyJWT's default `Python-urllib` user agent — so the API could not
verify any token. Three design gaps turned that one block into a loop:

1. **An outage reported itself as a client-auth failure.** `JwksKeyResolver` let
   `PyJWKClientConnectionError` (a `PyJWTError` subclass) be caught as "invalid token"
   → 401. Nothing in the logs said why; the response body was indistinguishable from a
   bad token.
2. **The web app answered every double-401 with `signIn()`.** Re-authenticating cannot
   fix a 401 the API returns for a token Logto just issued — Logto still has a valid
   session and redirects straight back, so the page reloads forever.
3. **A signed-in app unmounted on every token fetch.** `useLogto().isLoading` is true
   during every wrapped SDK call, not only the initial session check; mapping it to
   `"loading"` made `RequireAuth` swap the whole app for a spinner, aborting all
   in-flight queries and refetching them on remount.

Full mechanism: [docs/web/AUTH-TOKEN-FLOW.md](../web/AUTH-TOKEN-FLOW.md).

## Decision

**The app never auto-redirects to the provider on failure, and our outages never
masquerade as the user's fault.**

- **API:** an unreachable JWKS endpoint answers `503 "Authentication service
  unavailable"` (mapped via `KeyServiceUnavailableError`, deliberately not a
  `PyJWTError`) and logs at ERROR; every rejected token logs its reason at WARNING —
  the reason only, never the token. The JWKS client sends an explicit
  `User-Agent: rekalled-api`.
- **Web:** `auth-fetch` retries a 401 once after a forced refresh, then returns the
  response. It never calls `signIn`. The only sign-in redirect left on failure is the
  token gate's dead-grant path (`invalid_grant` is genuinely terminal, fires once).
- **Web:** a signed-in user stays signed in while the SDK is busy (`authStatus`);
  page-level query failures render the shared `ErrorState` screen after react-query's
  default bounded retries (3, exponential backoff).

## Alternatives considered

### Redirect guard (sessionStorage flag suppressing repeat `signIn` calls)

- Pros: smallest diff to the old ladder
- Cons: treats the symptom. The redirect is wrong for _any_ API-side 401, not just
  repeated ones; the flag also has to survive page loads to work at all
- Rejected: returning the 401 to react-query is simpler and ends in the error screen

### `python-jose`, following Logto's Flask sample verbatim

- Pros: matches the quick-start snippet
- Cons: the sample takes `algorithms` from the token's own header — the exact
  anti-pattern RFC 8725 §2.1 and PyJWT's docs warn about — and swallows the exception,
  which is why the sample would also have hidden this incident's cause. PyJWT with a
  pinned `ES384` allowlist is the stronger choice and was already in place
- Rejected: no gain, real losses

### Custom `shouldRetryQuery` + `ApiError` wrapper (skip retries on 4xx)

- Pros: 4xx surfaces in ~0s instead of ~7s
- Cons: the generated client throws the response body with no status, so every error
  must be rewrapped — and the wrapper contradicts the generated error types
- Rejected for now: TanStack's default retry is already bounded; revisit if the 7s
  wait on permission errors annoys users

## Consequences

- An API or Logto outage ends in a bounded number of requests (~4 per query over ~7s),
  a stable error screen with a retry button, and an API log line naming the cause.
- The Cloudflare skip rule for Logto's discovery endpoints is a **deployment
  prerequisite**, not code: if the proxy is rebuilt without it, auth breaks again
  (the explicit user agent alone may not satisfy every bot filter). See
  [Deployment setup](../deployment/PLAN.md).
- A genuine 4xx (e.g. missing scope after a role change) takes ~7s to surface because
  of retry backoff — accepted.
- `pytest` log assertions work again: alembic's `fileConfig` no longer disables
  existing `app.*` loggers (`disable_existing_loggers=False` in `migrations/env.py`).
