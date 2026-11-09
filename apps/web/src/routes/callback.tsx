import { SignInCallback } from "#/auth/logto-adapter";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

export const Route = createFileRoute("/callback")({ component: Callback });

function Callback() {
  const navigate = useNavigate();
  return <SignInCallback onDone={(returnTo) => void navigate({ to: returnTo })} />;
}
