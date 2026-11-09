import { LogtoProvider, useHandleSignInCallback, useLogto, type LogtoConfig } from "@logto/react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AuthContext } from "./context";
import type { AuthState } from "./types";

const RETURN_TO_KEY = "rekalled.returnTo";

/**
 * Read the Logto tenant config from the VITE_* values baked at build time (Vite loads the
 * repo-root .env files via envDir in vite.config.ts). Missing values used to surface as an
 * opaque "Invalid URL" from inside the SDK; fail here with the actual names instead.
 */
function resolveLogtoConfig(): { config: LogtoConfig; resource: string } {
  const endpoint = import.meta.env.VITE_LOGTO_ENDPOINT;
  const appId = import.meta.env.VITE_LOGTO_APP_ID;
  const resource = import.meta.env.VITE_LOGTO_API_RESOURCE;
  if (!endpoint || !appId || !resource) {
    throw new Error(
      "Logto auth needs VITE_LOGTO_ENDPOINT, VITE_LOGTO_APP_ID and VITE_LOGTO_API_RESOURCE. " +
        "Set them in .env.local at the repo root and restart the dev server.",
    );
  }
  return {
    config: {
      endpoint,
      appId,
      resources: [resource],
      scopes: ["decks:read", "decks:write", "cards:generate"],
    },
    resource,
  };
}

function LogtoBridge({ resource, children }: { resource: string; children: ReactNode }) {
  const logto = useLogto();
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    if (!logto.isAuthenticated) return;
    void logto
      .getIdTokenClaims()
      .then((claims: Awaited<ReturnType<typeof logto.getIdTokenClaims>>) =>
        setName(claims?.name ?? claims?.email ?? null),
      );
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
    [logto, name, resource],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function LogtoAuthProvider({ children }: { children: ReactNode }) {
  const { config, resource } = useMemo(resolveLogtoConfig, []);
  return (
    <LogtoProvider config={config}>
      <LogtoBridge resource={resource}>{children}</LogtoBridge>
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
