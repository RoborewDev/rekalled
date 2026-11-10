import { LogtoProvider, useHandleSignInCallback, useLogto, type LogtoConfig } from "@logto/react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AuthContext } from "./context";
import type { AuthState, LogtoConfigValues } from "./types";

const RETURN_TO_KEY = "rekalled.returnTo";

/** Only same-origin paths are safe to hand back to the router after sign-in. */
function sanitizeReturnTo(value: string | null | undefined): string {
  // Browsers treat a backslash like a slash, so "/\evil.example" would leave the origin too.
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return "/";
  }
  return value;
}

function LogtoBridge({ resource, children }: { resource: string; children: ReactNode }) {
  const logto = useLogto();
  const [name, setName] = useState<string | null>(null);

  // `logto` may keep its identity across renders, so depend on the auth state it reports.
  // The `active` flag drops a claim fetch that resolves after sign-out or unmount.
  useEffect(() => {
    if (!logto.isAuthenticated) {
      setName(null);
      return;
    }
    let active = true;
    logto
      .getIdTokenClaims()
      .then((claims) => {
        if (active) setName(claims?.name ?? claims?.email ?? null);
      })
      .catch(() => {
        if (active) setName(null);
      });
    return () => {
      active = false;
    };
  }, [logto.isAuthenticated]);

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
        sessionStorage.setItem(RETURN_TO_KEY, sanitizeReturnTo(returnTo));
        void logto.signIn(`${window.location.origin}/callback`);
      },
      signOut: () => void logto.signOut(window.location.origin),
    }),
    [logto, name, resource],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function LogtoAuthProvider({
  config: values,
  children,
}: {
  config: LogtoConfigValues;
  children: ReactNode;
}) {
  const config = useMemo<LogtoConfig>(
    () => ({
      endpoint: values.endpoint,
      appId: values.appId,
      resources: [values.resource],
      scopes: ["decks:read", "decks:write", "cards:generate"],
    }),
    [values.endpoint, values.appId, values.resource],
  );
  return (
    <LogtoProvider config={config}>
      <LogtoBridge resource={values.resource}>{children}</LogtoBridge>
    </LogtoProvider>
  );
}

/** Rendered by the /callback route. Finishes the code exchange, then sends the user back. */
export function SignInCallback({ onDone }: { onDone: (returnTo: string) => void }) {
  const { isLoading, error } = useHandleSignInCallback(() => {
    const returnTo = sanitizeReturnTo(sessionStorage.getItem(RETURN_TO_KEY));
    sessionStorage.removeItem(RETURN_TO_KEY);
    onDone(returnTo);
  });

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <p role="alert" className="text-sm text-red">
          We could not complete sign-in. Please try again.
        </p>
        <a className="underline" href="/">
          Back to sign in
        </a>
      </main>
    );
  }
  return isLoading ? <p className="p-8 text-sm">Signing you in…</p> : null;
}
