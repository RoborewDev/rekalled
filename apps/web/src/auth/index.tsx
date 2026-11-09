// The rest of the app imports auth from here only. No other folder imports @logto/react.
import type { ReactNode } from "react";
import { DevAuthProvider } from "./dev-adapter";

export { useAuth } from "./context";
export { RequireAuth } from "./require-auth";
export type { AuthState } from "./types";

export function AuthProvider({ children }: { children: ReactNode }) {
  // Only the dev adapter exists so far. Fail loudly instead of silently signing in as the
  // dev user when a build asks for an adapter that is not written yet.
  const mode = import.meta.env.VITE_AUTH_MODE ?? "dev";
  if (mode !== "dev") throw new Error(`VITE_AUTH_MODE=${mode} has no auth adapter yet`);
  return <DevAuthProvider>{children}</DevAuthProvider>;
}
