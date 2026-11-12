import { useMemo, useState, type ReactNode } from "react";
import { AuthContext } from "./context";
import type { AuthState } from "./types";

// Persists the signed-out choice so the landing survives reloads, like a real session.
const DEV_SIGNED_OUT_KEY = "rekalled.dev-signed-out";

function readSignedOut(): boolean {
  try {
    return localStorage.getItem(DEV_SIGNED_OUT_KEY) === "1";
  } catch {
    // Storage unavailable (private mode): start signed in.
    return false;
  }
}

function persistSignedOut(signedOut: boolean) {
  try {
    if (signedOut) localStorage.setItem(DEV_SIGNED_OUT_KEY, "1");
    else localStorage.removeItem(DEV_SIGNED_OUT_KEY);
  } catch {
    // Storage unavailable: dev auth then forgets the choice between reloads.
  }
}

/**
 * Signs in and out locally so the landing page and the sign-out flow can be exercised
 * without a Logto tenant. Pairs with AUTH_MODE=dev on the API (no token is sent).
 */
export function DevAuthProvider({ children }: { children: ReactNode }) {
  const [signedOut, setSignedOut] = useState(readSignedOut);

  const value = useMemo<AuthState>(
    () => ({
      status: signedOut ? "signedOut" : "signedIn",
      user: signedOut ? null : { name: "Dev user" },
      getAccessToken: async () => null,
      // returnTo is moot in dev: sign-in never leaves the page, so the user is already back.
      signIn: async () => {
        persistSignedOut(false);
        setSignedOut(false);
      },
      signOut: () => {
        persistSignedOut(true);
        setSignedOut(true);
      },
    }),
    [signedOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
