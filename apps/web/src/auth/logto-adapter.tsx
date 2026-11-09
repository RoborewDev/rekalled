import { LogtoProvider, useHandleSignInCallback, useLogto, type LogtoConfig } from "@logto/react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AuthContext } from "./context";
import type { AuthState } from "./types";

const resource = import.meta.env.VITE_LOGTO_API_RESOURCE;

const config: LogtoConfig = {
  endpoint: import.meta.env.VITE_LOGTO_ENDPOINT,
  appId: import.meta.env.VITE_LOGTO_APP_ID,
  resources: [resource],
  scopes: ["decks:read", "decks:write", "cards:generate"],
};

const RETURN_TO_KEY = "rekalled.returnTo";

function LogtoBridge({ children }: { children: ReactNode }) {
  const logto = useLogto();
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    if (!logto.isAuthenticated) return;
    void logto.getIdTokenClaims().then((claims: Awaited<ReturnType<typeof logto.getIdTokenClaims>>) => setName(claims?.name ?? claims?.email ?? null));
  }, [logto]);

  const value = useMemo<AuthState>(
    () => ({
      status: logto.isLoading ? "loading" : logto.isAuthenticated ? "signedIn" : "signedOut",
      user: logto.isAuthenticated ? { name } : null,
      getAccessToken: async ({ forceRefresh } = {}) => {
        if (forceRefresh) await logto.clearAccessToken();
        return (await logto.getAccessToken(resource)) ?? null;
      },
      signIn: (returnTo) => {
        // Logto owns the redirect; we only remember where to land afterwards.
        sessionStorage.setItem(RETURN_TO_KEY, returnTo ?? "/");
        void logto.signIn(`${window.location.origin}/callback`);
      },
      signOut: () => void logto.signOut(window.location.origin),
    }),
    [logto, name],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function LogtoAuthProvider({ children }: { children: ReactNode }) {
  return (
    <LogtoProvider config={config}>
      <LogtoBridge>{children}</LogtoBridge>
    </LogtoProvider>
  );
}

/** Rendered by the /callback route. Finishes the code exchange, then sends the user back. */
export function SignInCallback({ onDone }: { onDone: (returnTo: string) => void }) {
  const { isLoading } = useHandleSignInCallback(() => {
    const returnTo = sessionStorage.getItem(RETURN_TO_KEY) ?? "/";
    sessionStorage.removeItem(RETURN_TO_KEY);
    onDone(returnTo);
  });
  return isLoading ? <p className="p-8 text-sm">Signing you in…</p> : null;
}
