// The rest of the app imports auth from here only. No other folder imports @logto/react.
import type { ReactNode } from "react";
import { DevAuthProvider } from "./dev-adapter";
import type { AuthMode } from "./types";
import { LogtoAuthProvider } from "./logto-adapter";

export { useAuth } from "./context";
export { RequireAuth } from "./require-auth";
export type { AuthMode, AuthState } from "./types";

export const authMode = import.meta.env.VITE_AUTH_MODE === "dev" ? "dev" : "logto";

export function AuthProvider({ mode, children }: { mode: AuthMode; children: ReactNode }) {
  // Only the dev adapter exists so far. Fail loudly instead of silently signing in as the
  // dev user when the deployment asks for an adapter that is not written yet.
  if (mode !== "dev") throw new Error(`AUTH_MODE=${mode} has no auth adapter yet`);
  return authMode === "dev" ? (
    <DevAuthProvider>{children}</DevAuthProvider>
  ) : (
    <LogtoAuthProvider>{children}</LogtoAuthProvider>
  );

}
