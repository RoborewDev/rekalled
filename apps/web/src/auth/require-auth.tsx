import type { ReactNode } from "react";
import { Spinner } from "#/components/spinner";
import { useAuth } from "./context";
import { SignIn } from "./sign-in";

/**
 * Gates the app behind auth. Sign-in is user-triggered: a signed-out visitor gets the
 * sign-in landing (which remembers where to return afterwards), never an auto-redirect.
 */
export function RequireAuth({ children, returnTo }: { children: ReactNode; returnTo: string }) {
  const auth = useAuth();

  if (auth.status === "loading") {
    return (
      <main className="grid min-h-svh place-items-center p-8">
        <div role="status" className="grid justify-items-center gap-3 text-sm text-ink-soft">
          <Spinner />
          Loading…
        </div>
      </main>
    );
  }
  if (auth.status === "signedOut") return <SignIn returnTo={returnTo} />;
  return children;
}
