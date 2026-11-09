// The rest of the app imports auth from here only. No other folder imports @logto/react.
import type { ReactNode } from "react";
import { DevAuthProvider } from "./dev-adapter";
import type { AuthMode } from "./types";
import { LogtoAuthProvider } from "./logto-adapter";

export { useAuth } from "./context";
export { RequireAuth } from "./require-auth";
export type { AuthMode, AuthState } from "./types";

export function AuthProvider({ mode, children }: { mode: AuthMode; children: ReactNode }) {
  // The web server picks the adapter at request time (lib/runtime-env.ts reads AUTH_MODE);
  // the bundle never decides this on its own.
  return mode === "dev" ? (
    <DevAuthProvider>{children}</DevAuthProvider>
  ) : (
    <LogtoAuthProvider>{children}</LogtoAuthProvider>
  );
}
