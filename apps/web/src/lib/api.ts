import { client } from "@rekalled/api-client/client";
import type { AuthState } from "#/auth/types";
import { createAuthFetch } from "./auth-fetch";

/** Point the generated client at the API with auth attached. */
export function configureApi(apiUrl: string, auth: Pick<AuthState, "getAccessToken" | "signIn">) {
  client.setConfig({ baseUrl: apiUrl, fetch: createAuthFetch(auth) });
}
