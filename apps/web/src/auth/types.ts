export type AuthUser = { name: string | null };

export type AuthState = {
  status: "loading" | "signedIn" | "signedOut";
  user: AuthUser | null;
  /** Null in dev mode: the API's dev bypass needs no token. */
  getAccessToken: (options?: { forceRefresh?: boolean }) => Promise<string | null>;
  signIn: (returnTo?: string) => void;
  signOut: () => void;
};
