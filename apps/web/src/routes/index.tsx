import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  createDeckMutation,
  getStudySummaryOptions,
  listDecksOptions,
  listDecksQueryKey,
} from "@rekalled/api-client/query";
import { BandsBar, Score } from "#/components/score";

export const Route = createFileRoute("/")({ component: StudyToday });

function StudyToday() {
  const summary = useQuery(getStudySummaryOptions());
  const decks = useQuery(listDecksOptions());

  // A failed request looks like an empty account otherwise: no due cards and no decks.
  if (summary.isError || decks.isError) {
    return (
      <p role="alert" className="text-sm text-red">
        Could not load your study data. Reload the page to try again.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <section className="panel flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-ink-soft">Overall memory</p>
          <Score value={summary.data?.score ?? null} size="lg" />
        </div>
        <div className="text-sm">
          <p>
            <strong>{summary.data?.due ?? 0}</strong> due ·{" "}
            <strong>{summary.data?.new ?? 0}</strong> new
          </p>
          <p className="text-ink-soft">{summary.data?.reviews_today ?? 0} reviews today</p>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl">Decks</h2>
        {decks.data?.map((deck) => (
          <div key={deck.id} className="panel space-y-3">
            <div className="flex items-center justify-between gap-4">
              <Link
                to="/decks/$deckId"
                params={{ deckId: deck.id }}
                className="text-lg font-semibold hover:underline"
              >
                {deck.name}
              </Link>
              <Score value={deck.stats.score} />
            </div>
            <BandsBar bands={deck.stats.bands} />
            <div className="flex items-center justify-between text-sm">
              <span className="text-ink-soft">
                {deck.stats.due} due · {deck.stats.new} new · {deck.stats.total} cards
              </span>
            </div>
          </div>
        ))}
        <NewDeckForm />
      </section>
    </div>
  );
}

function NewDeckForm() {
  const [name, setName] = useState("");
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const create = useMutation({
    ...createDeckMutation(),
    onSuccess: async (deck) => {
      await queryClient.invalidateQueries({ queryKey: listDecksQueryKey() });
      await navigate({ to: "/decks/$deckId", params: { deckId: deck.id } });
    },
  });

  return (
    <div className="space-y-2">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate({ body: { name } });
        }}
      >
        <input
          className="field"
          name="name"
          aria-label="New deck name"
          placeholder="New deck name"
          value={name}
          onChange={(e) => {
            if (create.isError) create.reset();
            setName(e.target.value);
          }}
          required
        />
        <button type="submit" className="btn" disabled={create.isPending}>
          Create
        </button>
      </form>
      {create.isError && (
        <p role="alert" className="text-sm text-red">
          Could not create the deck. Try again.
        </p>
      )}
    </div>
  );
}
