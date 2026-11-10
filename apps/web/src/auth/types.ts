export type AuthUser = { name: string | null };

/** Which auth adapter the browser should use. Chosen at runtime by the web server. */
export type AuthMode = "dev" | "logto";

/** Public Logto settings, resolved by the web server at request time. */
export type LogtoConfigValues = {
  endpoint: string;
  appId: string;
  resource: string;
};

export type AuthState = {
  status: "loading" | "signedIn" | "signedOut";
  user: AuthUser | null;
  /** Null in dev mode: the API's dev bypass needs no token. */
  getAccessToken: (options?: { forceRefresh?: boolean }) => Promise<string | null>;
  signIn: (returnTo?: string) => void;
  signOut: () => void;
};
