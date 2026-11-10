import { createContext, useContext, type ReactNode } from "react";
import type { AuthMode, AuthState } from "./types";

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside <AuthProvider>");
  return auth;
}

// The adapter is picked at runtime, but routes that are shared by every mode (the callback
// route) still need to know which one is active. Only src/auth may decide that.
const AuthModeContext = createContext<AuthMode | null>(null);

export function AuthModeProvider({ mode, children }: { mode: AuthMode; children: ReactNode }) {
  return <AuthModeContext.Provider value={mode}>{children}</AuthModeContext.Provider>;
}

export function useAuthMode(): AuthMode {
  const mode = useContext(AuthModeContext);
  if (!mode) throw new Error("useAuthMode must be used inside <AuthProvider>");
  return mode;
}
