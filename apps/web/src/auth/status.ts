import type { AuthState } from "./types";

/**
 * Logto's `isLoading` is true during every SDK call (`getAccessToken`, `clearAccessToken`,
 * …), not only the initial session check. A signed-in user therefore stays signed in while
 * the SDK is busy: mapping `isLoading` straight to "loading" unmounted the whole app on
 * every token refresh.
 */
export function authStatus(logto: {
  isLoading: boolean;
  isAuthenticated: boolean;
}): AuthState["status"] {
  if (logto.isAuthenticated) return "signedIn";
  return logto.isLoading ? "loading" : "signedOut";
}
