import { SignInCallback } from "#/auth";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

export const Route = createFileRoute("/callback")({ component: Callback });

function Callback() {
  const navigate = useNavigate();
  return (
    <SignInCallback
      onDone={(returnTo) => {
        // `href` handles a full path (including a query string); `replace` keeps /callback out
        // of history so Back cannot replay the code exchange.
        void navigate({ href: returnTo, replace: true }).catch(() => {
          window.location.assign("/");
        });
      }}
    />
  );
}
