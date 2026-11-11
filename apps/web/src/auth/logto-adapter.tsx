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

  const signIn = useCallback(
    (returnTo?: string) => {
      // Logto owns the redirect; we only remember where to land afterwards.
      sessionStorage.setItem(RETURN_TO_KEY, sanitizeReturnTo(returnTo));
      void logto.signIn(`${window.location.origin}/callback`);
    },
    [logto],
  );

  // One token gate per bridge, in a ref so it survives the AuthState memo below (design:
  // docs/web/AUTH-TOKEN-FLOW.md). The SDK's hook methods are identity-stable and `signIn`
  // reads the location at call time, so the first-render captures stay correct. Serialization
  // here is what keeps parallel react-query fetches from replaying one refresh token and
  // bricking the grant.
  const access = useRef<TokenAccess | null>(null);
  if (access.current === null) {
    access.current = createTokenAccess(
      {
        getAccessToken: (apiResource) => logto.getAccessToken(apiResource),
        clearAccessToken: () => logto.clearAccessToken(),
      },
      resource,
      () => {
        // Mirror the double-401 recovery in auth-fetch: the grant is unrecoverable, so
        // let Logto's signIn clear the dead tokens and take the user to sign in.
        if (typeof window === "undefined") return;
        signIn(window.location.pathname);
      },
    );
  }
  const tokenAccess = access.current;

  // `useLogto`'s proxy swallows errors into the provider's `error` state instead of
  // rethrowing, so a terminal `invalid_grant` surfaces there rather than as a rejection.
  // Every access-token POST goes through the gate, so an `invalid_grant`-shaped error in
  // that state can only come from one of our serialized refreshes — flag it dead there.
  const { error } = logto;
  useEffect(() => {
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
