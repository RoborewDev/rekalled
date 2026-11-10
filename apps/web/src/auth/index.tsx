// The rest of the app imports auth from here only. No other folder imports @logto/react.
import { useEffect, type ReactNode } from "react";
import { AuthModeProvider, useAuthMode } from "./context";
import { DevAuthProvider } from "./dev-adapter";
import { LogtoAuthProvider, SignInCallback as LogtoSignInCallback } from "./logto-adapter";
import type { AuthMode, LogtoConfigValues } from "./types";

export { useAuth } from "./context";
export { RequireAuth } from "./require-auth";
export type { AuthMode, AuthState, LogtoConfigValues } from "./types";

export function AuthProvider({
  mode,
  logto,
  children,
}: {
  mode: AuthMode;
  logto: LogtoConfigValues | null;
  children: ReactNode;
}) {
  // The web server picks the adapter at request time (lib/runtime-env.ts reads AUTH_MODE);
  // the bundle never decides this on its own.
  if (mode === "dev") {
    return (
      <AuthModeProvider mode={mode}>
        <DevAuthProvider>{children}</DevAuthProvider>
      </AuthModeProvider>
    );
  }
  if (mode === "logto") {
    if (!logto) {
      throw new Error("AUTH_MODE=logto needs LOGTO_ENDPOINT, LOGTO_APP_ID and LOGTO_API_RESOURCE");
    }
    return (
      <AuthModeProvider mode={mode}>
        <LogtoAuthProvider config={logto}>{children}</LogtoAuthProvider>
      </AuthModeProvider>
    );
  }
  // A new AuthMode must be handled here rather than silently falling back to an adapter.
  const unhandled: never = mode;
  throw new Error(`Unhandled auth mode: ${String(unhandled)}`);
}

/**
 * Finishes a sign-in redirect. Dev mode never sends the browser to Logto, so there is nothing
 * to exchange; only the Logto adapter can complete a callback.
 */
export function SignInCallback({ onDone }: { onDone: (returnTo: string) => void }) {
  const mode = useAuthMode();

  useEffect(() => {
    if (mode === "dev") onDone("/");
  }, [mode, onDone]);

  if (mode === "dev") return null;
  return <LogtoSignInCallback onDone={onDone} />;
}
