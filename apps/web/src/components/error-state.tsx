import { CloudOff } from "lucide-react";

/**
 * Page-level failure: the API is unreachable or erroring. One shared screen so every
 * route fails the same way; `onRetry` re-runs the queries that failed.
 */
export function ErrorState({ onRetry }: { onRetry?: () => void }) {
  return (
    <section role="alert" className="panel grid justify-items-center gap-4 px-8 py-12 text-center">
      <CloudOff aria-hidden="true" className="h-10 w-10 text-red" />
      <h2 className="text-xl font-semibold">Uh oh! This is embarrassing.</h2>
      <p className="max-w-md text-sm text-ink-soft">
        We seem to be having a technical difficulty. We're on it now — please come back soon.
      </p>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </section>
  );
}
