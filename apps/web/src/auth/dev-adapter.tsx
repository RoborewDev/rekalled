import type { ReactNode } from "react";
import { AuthContext } from "./context";
import type { AuthState } from "./types";

// Always signed in, never sends a token. Pairs with AUTH_MODE=dev on the API.
const devAuth: AuthState = {
  status: "signedIn",
  user: { name: "Dev user" },
  getAccessToken: async () => null,
  signIn: () => { },
  signOut: () => { },
};

export function DevAuthProvider({ children }: { children: ReactNode }) {
  return <AuthContext.Provider value={devAuth}>{children}</AuthContext.Provider>;
}
