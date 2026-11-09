// The rest of the app imports auth from here only. No other folder imports @logto/react.
import type { ReactNode } from "react";
import { DevAuthProvider } from "./dev-adapter";

export { useAuth } from "./context";
export { RequireAuth } from "./require-auth";
export type { AuthState } from "./types";

export function AuthProvider({ children }: { children: ReactNode }) {
  return <DevAuthProvider>{children}</DevAuthProvider>;
}
