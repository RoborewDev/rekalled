import { useEffect, type ReactNode } from "react";
import { useAuth } from "./context";

export function RequireAuth({ children, returnTo }: { children: ReactNode; returnTo: string }) {
  const auth = useAuth();

  useEffect(() => {
    if (auth.status === "signedOut") auth.signIn(returnTo);
  }, [auth, returnTo]);

  if (auth.status !== "signedIn") return <p className="p-8 text-sm text-zinc-500">Loading…</p>;
  return children;
}
