import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useReducer } from "react";
import type { StudyCard } from "@rekalled/api-client";
import { getStudyQueueOptions, submitReviewMutation } from "@rekalled/api-client/query";
import { opId } from "#/lib/query-keys";
import {
  sessionReducer,
  startSession,
  currentCard,
  isFinished,
  type Rating,
} from "#/features/study/session";

type StudySearch = { deckId?: string };

export const Route = createFileRoute("/study")({
  validateSearch: (search: Record<string, unknown>): StudySearch => ({
    deckId: typeof search.deckId === "string" ? search.deckId : undefined,
  }),
  component: StudyPage,
});

function StudyPage() {
  const { deckId } = Route.useSearch();
  // The queue is a snapshot for this session: don't refetch it under the user.
  const queue = useQuery({
    ...getStudyQueueOptions({ query: { deck_id: deckId } }),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  if (queue.isPending) return <p>Loading cards…</p>;
  if (queue.isError) return <p className="text-red">Could not load the queue.</p>;
  return <Session key={deckId ?? "all"} cards={queue.data} />;
}

const RATINGS: { rating: Rating; label: string }[] = [
  { rating: 1, label: "Again" },
  { rating: 2, label: "Hard" },
  { rating: 3, label: "Good" },
  { rating: 4, label: "Easy" },
];

function Session({ cards }: { cards: StudyCard[] }) {
  const [state, dispatch] = useReducer(sessionReducer, cards, startSession);
  const card = currentCard(state);
  const queryClient = useQueryClient();
  const review = useMutation({
    ...submitReviewMutation(),
    // Scores changed: the next visit to "/" or a deck page refetches. Not the queue itself,
    // which would refetch mid-session.
    onSettled: () =>
      queryClient.invalidateQueries({ predicate: (q) => opId(q) !== "getStudyQueue" }),
  });

  const rate = (rating: Rating) => {
    if (!card) return;
    // review_id makes the POST idempotent: a retried request is not counted twice.
    review.mutate({ body: { review_id: crypto.randomUUID(), card_id: card.id, rating } });
    dispatch({ type: "rate", rating, now: new Date() });
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        dispatch({ type: "reveal" });
      } else if (state.revealed && ["1", "2", "3", "4"].includes(e.key)) {
        rate(Number(e.key) as Rating);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (isFinished(state)) {
    return (
      <div className="panel space-y-4 text-center">
        <h1 className="text-3xl">Session done</h1>
        <p>
          {state.reviewed} reviews · {state.again} marked Again
        </p>
        <Link to="/" className="btn-primary">
          Back to Study today
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-soft">
        {card!.deck_name} · {state.queue.length} left
      </p>
      <article className="panel min-h-64 space-y-6">
        <h1 className="text-2xl leading-snug">{card!.question}</h1>
        {state.revealed ? (
          <div className="space-y-3 border-t border-line pt-6">
            <p className="text-lg">{card!.answer}</p>
            {card!.source_excerpt && (
              <blockquote className="border-l-2 border-red pl-3 text-sm text-ink-soft">
                {card!.source_excerpt}
              </blockquote>
            )}
          </div>
        ) : (
          <button className="btn-primary" onClick={() => dispatch({ type: "reveal" })}>
            Show answer <kbd className="text-xs opacity-70">Space</kbd>
          </button>
        )}
      </article>
      {state.revealed && (
        <div className="grid grid-cols-4 gap-2">
          {RATINGS.map(({ rating, label }) => (
            <button key={rating} className="btn flex-col" onClick={() => rate(rating)}>
              <span>
                {label} <kbd className="hidden text-xs opacity-70 sm:inline">{rating}</kbd>
              </span>
              <span className="text-xs text-ink-soft">
                {formatDue(card!.next_due[String(rating)])}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function formatDue(iso: string | undefined): string {
  if (!iso) return "";
  const minutes = Math.round((new Date(iso).getTime() - Date.now()) / 60_000);
  if (minutes < 60) return `${Math.max(minutes, 1)}m`;
  if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h`;
  return `${Math.round(minutes / (60 * 24))}d`;
}
