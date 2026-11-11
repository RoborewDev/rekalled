export type LogtoTokenSource = {
  getAccessToken: (resource: string) => Promise<string | undefined>;
  clearAccessToken: () => Promise<void>;
};

export type TokenAccess = {
  getAccessToken: (options?: { forceRefresh?: boolean }) => Promise<string | null>;
  /** For `invalid_grant` errors the react hook swallows into provider state instead of rethrowing. */
  markSessionDead: () => void;
};

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

/**
 * Single-flight `getAccessToken`: concurrent callers share one refresh POST, and an
 * `invalid_grant` marks the session dead — `null` for every caller, `onSessionDead`
 * exactly once. Design: docs/web/AUTH-TOKEN-FLOW.md.
 */
export function createTokenAccess(
  source: LogtoTokenSource,
  resource: string,
  onSessionDead?: () => void,
): TokenAccess {
  let dead = false;
  let notifiedSessionDead = false;
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
      if (forceRefresh) {
        await source.clearAccessToken();
        // The session may have been flagged dead while the clear was pending; recovery
        // has already started, so no token work may follow it.
        if (dead) return null;
      }
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
      if (inFlight && (!forceRefresh || inFlight.forced)) return inFlight.promise;
      const promise = tail.then(() => run(forceRefresh));
      const stopSharing = () => {
        if (inFlight?.promise === promise) inFlight = null;
      };
      tail = promise.then(stopSharing, stopSharing);
      inFlight = { forced: forceRefresh, promise };
      return promise;
    },
    markSessionDead,
  };
}
