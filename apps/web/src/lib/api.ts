import { client } from "@rekalled/api-client/client";
import type { AuthState } from "#/auth/types";
import { createAuthFetch } from "./auth-fetch";

/** Point the generated client at the API (VITE_API_URL) with auth attached. */
export function configureApi(auth: Pick<AuthState, "getAccessToken" | "signIn">) {
  client.setConfig({ baseUrl: import.meta.env.VITE_API_URL, fetch: createAuthFetch(auth) });
}
