/**
 * Single-flight gate in front of the Logto token endpoint, closing two SDK gaps that
 * together turn a routine token expiry into a permanent request storm: (full write-up:
 * docs/web/AUTH-TOKEN-FLOW.md)
 *
 * 1. `@logto/client` has no refresh-token mutex: parallel `getAccessToken` calls all
 *    reuse the same stored refresh token, but Logto rotates it — the loser replays a
 *    consumed token and Logto revokes the entire grant. Serializing every fetch (and
 *    letting concurrent callers share the in-flight one) keeps a single
 *    `POST /oidc/token` in flight, so rotation can never race itself.
 * 2. `invalid_grant` is terminal (RFC 6749 §5.2): the grant is revoked, so no retry
 *    can succeed. Once observed, the gate resolves every caller with `null` without
 *    touching the network, and calls `onSessionDead` once so the app redirects to
 *    sign-in instead of retrying forever.
 */

/** Narrow view of the underlying Logto client; injectable so tests never call Logto. */
export type LogtoTokenSource = {
  getAccessToken: (resource: string) => Promise<string | undefined>;
  clearAccessToken: () => Promise<void>;
};

export type TokenAccess = {
  getAccessToken: (options?: { forceRefresh?: boolean }) => Promise<string | null>;
  /**
   * Flag the session as dead from the outside. `@logto/react`'s per-method proxy swallows
   * errors into the provider's `error` state instead of rethrowing, so the adapter watches
   * that state and reports a swallowed `invalid_grant` here. Same effect as a rejected
   * fetch: one `onSessionDead`, then `null` for every caller without touching the network.
   */
  markSessionDead: () => void;
};

/**
 * `not_authenticated` (no ID token yet, e.g. during SSR) and network failures must not
 * be mistaken for a revoked grant, or they would bounce the user to sign-in on a
 * server error. The SDK reports `invalid_grant` either as its own `code` or on the
 * token-endpoint response body carried in `data`; accept both shapes so minor SDK
 * changes cannot resurrect the loop.
 */
export function isInvalidGrant(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  const { code, data } = error as { code?: unknown; data?: unknown };
  if (code === "oidc.invalid_grant") return true;
  return (
    typeof data === "object" &&
    data !== null &&
    (data as { error?: unknown }).error === "invalid_grant"
  );
}

export function createTokenAccess(
  source: LogtoTokenSource,
  resource: string,
  onSessionDead?: () => void,
): TokenAccess {
  let dead = false;
  let notifiedSessionDead = false;
  // Queue of token work: each op starts only after the previous one fully settled —
  // which includes the SDK writing the rotated refresh token before it resolves.
  let tail: Promise<unknown> = Promise.resolve();
  let inFlight: { forced: boolean; promise: Promise<string | null> } | null = null;

  const markSessionDead = () => {
    dead = true;
    if (!notifiedSessionDead) {
      notifiedSessionDead = true;
      onSessionDead?.();
    }
  };

  const run = async (forceRefresh: boolean): Promise<string | null> => {
    if (dead) return null;
    try {
      if (forceRefresh) await source.clearAccessToken();
      return (await source.getAccessToken(resource)) ?? null;
    } catch (error) {
      if (!isInvalidGrant(error)) throw error;
      markSessionDead();
      return null;
    }
  };

  return {
    getAccessToken: ({ forceRefresh = false } = {}) => {
      if (dead) return Promise.resolve(null);
      // Concurrent callers ride along on the in-flight fetch. A forced caller may only
      // share a forced fetch: it must clear the cached token first, and therefore run
      // after whatever is in flight settles.
      if (inFlight && (!forceRefresh || inFlight.forced)) return inFlight.promise;
      const promise = tail.then(() => run(forceRefresh));
      const stopSharing = () => {
        if (inFlight?.promise === promise) inFlight = null;
      };
      // Keep the queue usable when the op rejects; only sharing depends on this slot.
      tail = promise.then(stopSharing, stopSharing);
      inFlight = { forced: forceRefresh, promise };
      return promise;
    },
    markSessionDead,
  };
}
