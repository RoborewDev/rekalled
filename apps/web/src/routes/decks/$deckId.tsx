import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { ActiveCardOut } from "@rekalled/api-client";
import {
  createTextSourceMutation,
  listDeckCardsOptions,
  listDecksOptions,
} from "@rekalled/api-client/query";
import { BandsBar, Score } from "#/components/score";

export const Route = createFileRoute("/decks/$deckId")({ component: DeckPage });

/** Weakest first so the cards that need work are at the top; unreviewed cards last. */
const byWeakest = (a: ActiveCardOut, b: ActiveCardOut) =>
  (a.memory_score ?? 2) - (b.memory_score ?? 2);

function DeckPage() {
  const { deckId } = Route.useParams();
  // Deck stats come from the deck list (one request on "/", cached here).
  const deck = useQuery({
    ...listDecksOptions(),
    select: (decks) => decks.find((d) => d.id === deckId),
  });
  const cards = useQuery(listDeckCardsOptions({ path: { deck_id: deckId } }));

  if (deck.isPending) return <p>Loading…</p>;
  if (!deck.data) return <p>Deck not found.</p>;
  const { stats } = deck.data;

  return (
    <div className="space-y-8">
      <section className="panel space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-3xl">{deck.data.name}</h1>
          <Score value={stats.score} size="lg" />
        </div>
        <BandsBar bands={stats.bands} />
      </section>

      <AddTextForm deckId={deckId} />

      <section className="space-y-2">
        <h2 className="text-2xl">Cards</h2>
        {cards.data?.length === 0 && (
          <p className="text-ink-soft">No cards yet. Paste some text above.</p>
        )}
        {[...(cards.data ?? [])].sort(byWeakest).map((card) => (
          <div key={card.id} className="panel flex items-start justify-between gap-4">
            <div>
              <p className="font-medium">{card.question}</p>
              <p className="text-sm text-ink-soft">{card.answer}</p>
            </div>
            <Score value={card.memory_score} />
          </div>
        ))}
      </section>
    </div>
  );
}

function AddTextForm({ deckId }: { deckId: string }) {
  const [text, setText] = useState("");
  const navigate = useNavigate();
  const create = useMutation({
    ...createTextSourceMutation(),
    onSuccess: (source) => navigate({ to: "/sources/$sourceId", params: { sourceId: source.id } }),
  });

  return (
    <form
      className="panel space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        create.mutate({ path: { deck_id: deckId }, body: { text } });
      }}
    >
      <label className="block font-semibold" htmlFor="source-text">
        Make cards from text
      </label>
      <textarea
        id="source-text"
        className="field min-h-40"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste notes, an article, a chapter…"
        required
      />
      {create.isError && <p className="text-sm text-red">Generation failed. Try again.</p>}
      <button className="btn-primary" disabled={create.isPending}>
        {create.isPending ? "Generating…" : "Generate cards"}
      </button>
    </form>
  );
}
