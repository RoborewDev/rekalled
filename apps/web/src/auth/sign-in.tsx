import { LogIn } from "lucide-react";
import { useState } from "react";
import { Spinner } from "#/components/spinner";
import { useAuth, useAuthMode } from "./context";

/**
 * The landing a signed-out visitor sees (prototype: viewSignIn). Sign-in is always
 * user-triggered from here — the app never auto-redirects to the provider.
 */
export function SignIn({ returnTo }: { returnTo: string }) {
  const auth = useAuth();
  const mode = useAuthMode();
  // Only the hosted flow leaves the page; dev mode signs in without a redirect, so the
  // overlay would only flash. If the Logto redirect never happens, a reload clears it.
  const [redirecting, setRedirecting] = useState(false);

  const hosted = mode === "logto";

  const startSignIn = () => {
    if (hosted) setRedirecting(true);
    auth.signIn(returnTo);
  };

  return (
    <main className="grid min-h-svh place-items-center p-8">
      <div className="relative w-full max-w-110 overflow-hidden rounded-lg border border-line bg-card px-8 py-10 shadow-md">
        <span aria-hidden="true" className="absolute inset-y-0 left-12 w-px bg-red/50" />
        <div className="pl-8">
          <div className="font-display text-2xl font-bold leading-tight tracking-tight">
            Re<span className="text-red">k</span>alled
          </div>
          <p className="mb-8 mt-3 text-sm text-ink-soft">
            Turn what you read into flash cards, then study them just before you'd forget. Every
            card stays tied to where it came from.
          </p>
          <button
            type="button"
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-3 text-sm font-medium text-paper transition hover:bg-ink/90 disabled:opacity-50"
            onClick={startSignIn}
            disabled={redirecting}
          >
            <LogIn aria-hidden="true" size={16} />
            {hosted ? "Continue with Logto" : "Sign in"}
          </button>
          <small className="mt-4 block text-xs text-ink-soft">
            {hosted
              ? "Hosted sign-in · OIDC + PKCE · no passwords stored here"
              : "Dev mode · signs in without a provider"}
          </small>
        </div>
      </div>
      {redirecting && (
        <div
          role="status"
          className="fixed inset-0 z-50 grid place-items-center bg-paper/90 text-sm text-ink-soft"
        >
          <div className="grid justify-items-center gap-3">
            <Spinner />
            Redirecting to Logto…
          </div>
        </div>
      )}
    </main>
  );
}
