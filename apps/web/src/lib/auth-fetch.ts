import type { AuthState } from "#/auth/types";

type Auth = Pick<AuthState, "getAccessToken">;

/**
 * fetch that adds the Bearer token. On a 401 it forces one token refresh and retries once,
 * then returns whatever the API answered. It never redirects: a dead session recovers
 * through the token gate, and any other 401 surfaces as a query error.
 */
export function createAuthFetch(auth: Auth, baseFetch: typeof fetch = fetch): typeof fetch {
  return async (input, init) => {
    const original = new Request(input, init);

    const send = async (forceRefresh: boolean) => {
      const request = original.clone();
      const token = await auth.getAccessToken({ forceRefresh });
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      return baseFetch(request);
    };

    const first = await send(false);
    if (first.status !== 401) return first;
    return send(true);
  };
}
