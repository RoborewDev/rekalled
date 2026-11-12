import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/about")({
  head: () => ({ meta: [{ title: "About · Rekalled" }] }),
  component: About,
});

function About() {
  return (
    <>
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-3xl px-4 py-3">
          <Link to="/" className="font-display text-xl font-semibold">Rekalled</Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="text-2xl">About</h1>
        <p className="mt-3 text-ink-soft">
          Rekalled is a beta app designed to simplify spaced repetition!
        </p>
      </main>
    </>
  );
}
