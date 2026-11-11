import { LogtoProvider, useHandleSignInCallback, useLogto, type LogtoConfig } from "@logto/react";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AuthContext } from "./context";
import { createTokenAccess, isInvalidGrant, type TokenAccess } from "./token-access";
import type { AuthState, LogtoConfigValues } from "./types";

const RETURN_TO_KEY = "rekalled.returnTo";

/** Only same-origin paths are safe to hand back to the router after sign-in. */
function sanitizeReturnTo(value: string | null | undefined): string {
  // Browsers treat a backslash like a slash, so "/\evil.example" would leave the origin too.
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return "/";
  }
  // The callback route is a redirect target, not a landing page: returning there after
  // sign-in would re-enter the code exchange with no code to exchange.
  if (value === "/callback") return "/";
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

  // The SDK does not dedupe signIn: an overlapping second call overwrites the first
  // attempt's state and PKCE verifier in storage, so the callback's validation would fail.
  // Extra callers while one is pending ride along; once an attempt settles (the page did
  // not navigate), a later call can retry.
  const signInInFlight = useRef<Promise<void> | null>(null);
  const signIn = useCallback(
    (returnTo?: string) => {
      if (signInInFlight.current) return;
      // Logto owns the redirect; we only remember where to land afterwards.
      sessionStorage.setItem(RETURN_TO_KEY, sanitizeReturnTo(returnTo));
      const attempt = logto.signIn(`${window.location.origin}/callback`);
      signInInFlight.current = attempt;
      void attempt.finally(() => {
        if (signInInFlight.current === attempt) signInInFlight.current = null;
      });
    },
    [logto],
  );

  const access = useRef<TokenAccess | null>(null);
  if (access.current === null) {
    access.current = createTokenAccess(
      {
        getAccessToken: (apiResource) => logto.getAccessToken(apiResource),
        clearAccessToken: () => logto.clearAccessToken(),
      },
      resource,
      () => {
        if (typeof window === "undefined") return;
        signIn(window.location.pathname);
      },
    );
  }
  const tokenAccess = access.current;

  const { error } = logto;
  useEffect(() => {
    // On the callback route an `invalid_grant` is the (stale) authorization-code exchange,
    // which SignInCallback handles with its own error screen — not a dead refresh grant.
    if (window.location.pathname === "/callback") return;
    if (error && isInvalidGrant(error)) tokenAccess.markSessionDead();
  }, [error, tokenAccess]);

  const value = useMemo<AuthState>(
    () => ({
      status: logto.isLoading ? "loading" : logto.isAuthenticated ? "signedIn" : "signedOut",
      user: logto.isAuthenticated ? { name } : null,
      getAccessToken: (options) => tokenAccess.getAccessToken(options),
      signIn,
      signOut: () => void logto.signOut(window.location.origin),
    }),
    [logto, name, resource, signIn, tokenAccess],
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
