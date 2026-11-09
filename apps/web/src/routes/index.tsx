import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  createDeckMutation,
  getStudySummaryOptions,
  listDecksOptions,
  listDecksQueryKey,
} from "@rekalled/api-client/query"
import { BandsBar, Score } from "#/components/score";

export const Route = createFileRoute("/")({ component: StudyToday });

function StudyToday() {
  const summary = useQuery(getStudySummaryOptions());
  const decks = useQuery(listDecksOptions());

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
              <h3 className="text-lg font-semibold hover:underline">{deck.name}</h3>
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
  const create = useMutation({
    ...createDeckMutation(),
    onSuccess: () => {
      setName("");
      return queryClient.invalidateQueries({ queryKey: listDecksQueryKey() });
    },
  });

  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate({ body: { name } });
      }}
    >
      <input
        className="field"
        placeholder="New deck name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <button className="btn" disabled={create.isPending}>
        Create
      </button>
    </form>
  );
}
