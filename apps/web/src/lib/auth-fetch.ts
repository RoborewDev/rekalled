import type { AuthState } from "#/auth/types";

type Auth = Pick<AuthState, "getAccessToken" | "signIn">;

/**
 * fetch that adds the Bearer token. On a 401 it forces a token refresh and retries once;
 * if that also fails, it sends the user to sign in.
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

    const second = await send(true);
    if (second.status === 401) auth.signIn(globalThis.location?.pathname);
    return second;
  };
}
