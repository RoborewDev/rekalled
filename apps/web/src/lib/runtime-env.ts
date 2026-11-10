import type { AuthMode, LogtoConfigValues } from "#/auth/types";

export type RuntimeConfig = {
  apiUrl: string;
  authMode: AuthMode;
  /** Present only when the auth mode needs it; public values, safe to send to the browser. */
  logto: LogtoConfigValues | null;
};

const DEV_API_URL = "http://localhost:8000";

/**
 * Resolve the public runtime config from the web server's environment. Kept separate from the
 * server function so it can be unit tested without the Start compiler.
 */
export function resolveRuntimeConfig(env: Record<string, string | undefined>): RuntimeConfig {
  const dev = env.NODE_ENV !== "production";

  // Production must say where the API is; the local default only saves dev setup.
  const apiUrl = env.API_URL?.trim() || (dev ? DEV_API_URL : "");
  if (!apiUrl) throw new Error("API_URL must be set for the web server");

  // The browser auth adapter is a deployment setting too, so it is read here rather than
  // baked into the bundle. Local dev defaults to the dev adapter.
  const authMode = env.AUTH_MODE?.trim() || (dev ? "dev" : "");
  if (authMode !== "dev" && authMode !== "logto") {
    throw new Error("AUTH_MODE must be dev or logto for the web server");
  }

  const logto: LogtoConfigValues = {
    endpoint: env.LOGTO_ENDPOINT?.trim() ?? "",
    appId: env.LOGTO_APP_ID?.trim() ?? "",
    resource: env.LOGTO_API_RESOURCE?.trim() ?? "",
  };
  // The browser must never fall back to a partial tenant; fail at request time with the names.
  if (authMode === "logto" && !(logto.endpoint && logto.appId && logto.resource)) {
    throw new Error(
      "AUTH_MODE=logto needs LOGTO_ENDPOINT, LOGTO_APP_ID and LOGTO_API_RESOURCE for the web server",
    );
  }

  return { apiUrl, authMode, logto: authMode === "logto" ? logto : null };
}
