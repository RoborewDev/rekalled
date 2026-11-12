import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import type { ActiveCardOut } from "@rekalled/api-client";
import {
  createTextSourceMutation,
  deleteCardMutation,
  listDeckCardsOptions,
  listDecksOptions,
  updateCardMutation,
} from "@rekalled/api-client/query";
import { BandsBar, Score } from "#/components/score";
import { ConfirmDialog } from "#/components/confirm-dialog";
import { ErrorState } from "#/components/error-state";

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
  if (deck.isError) {
    return (
      <ErrorState
        onRetry={() => {
          void deck.refetch();
          void cards.refetch();
        }}
      />
    );
  }
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
        <Link to="/study" search={{ deckId }} className="btn-primary">
          Study {stats.due + stats.new} cards
        </Link>
      </section>

      <AddTextForm deckId={deckId} />

      <section className="space-y-2">
        <h2 className="text-2xl">Cards</h2>
        {cards.isError && <ErrorState onRetry={() => void cards.refetch()} />}
        {cards.data?.length === 0 && (
          <p className="text-ink-soft">No cards yet. Paste some text above.</p>
        )}
        <ul role="list" className="space-y-2">
          {[...(cards.data ?? [])].sort(byWeakest).map((card) => (
            <CardRow key={card.id} card={card} />
          ))}
        </ul>
      </section>
    </div>
  );
}

/** One card in the deck: question and answer, with inline edit and delete. */
function CardRow({ card }: { card: ActiveCardOut }) {
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (editing) return <EditCard card={card} onDone={() => setEditing(false)} />;
  return (
    <li className="panel flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="font-medium">{card.question}</p>
        <p className="text-sm text-ink-soft">{card.answer}</p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Score value={card.memory_score} />
        <button
          type="button"
          className="btn-icon"
          aria-label="Edit card"
          title="Edit"
          onClick={() => setEditing(true)}
        >
          <Pencil aria-hidden="true" size={16} />
        </button>
        <button
          type="button"
          className="btn-icon"
          aria-label="Delete card"
          title="Delete"
          onClick={() => setConfirmingDelete(true)}
        >
          <Trash2 aria-hidden="true" size={16} />
        </button>
      </div>
      {confirmingDelete && <DeleteCard card={card} onDismiss={() => setConfirmingDelete(false)} />}
    </li>
  );
}

/** Inline edit form that replaces the card's row while open. */
function EditCard({ card, onDone }: { card: ActiveCardOut; onDone: () => void }) {
  const [question, setQuestion] = useState(card.question);
  const [answer, setAnswer] = useState(card.answer);
  const queryClient = useQueryClient();
  const save = useMutation({
    ...updateCardMutation(),
    onSuccess: () => {
      onDone();
      void queryClient.invalidateQueries();
    },
  });
  // The API rejects blank questions and answers, so keep Save disabled.
  const incomplete = question.trim() === "" || answer.trim() === "";

  return (
    <li className="panel">
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (incomplete) return;
          save.mutate({
            path: { card_id: card.id },
            body: { question: question.trim(), answer: answer.trim() },
          });
        }}
      >
        <div className="space-y-1">
          <label className="block text-sm font-medium" htmlFor={`question-${card.id}`}>
            Question
          </label>
          <input
            id={`question-${card.id}`}
            className="field font-medium"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <label className="block text-sm font-medium" htmlFor={`answer-${card.id}`}>
            Answer
          </label>
          <textarea
            id={`answer-${card.id}`}
            className="field"
            rows={3}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
        </div>
        {save.isError && (
          <p role="alert" className="text-sm text-red">
            Could not save the card. Try again.
          </p>
        )}
        <div className="flex gap-2">
          <button type="submit" className="btn-primary" disabled={incomplete || save.isPending}>
            {save.isPending ? "Saving…" : "Save"}
          </button>
          <button type="button" className="btn-outline" onClick={onDone}>
            Cancel
          </button>
        </div>
      </form>
    </li>
  );
}

/** Modal confirmation before deleting: once the card is gone there is no undo. */
function DeleteCard({ card, onDismiss }: { card: ActiveCardOut; onDismiss: () => void }) {
  const queryClient = useQueryClient();
  const del = useMutation({
    ...deleteCardMutation(),
    onSuccess: () => {
      onDismiss();
      void queryClient.invalidateQueries();
    },
  });

  return (
    <ConfirmDialog
      title="Delete this card?"
      confirmLabel="Delete"
      pending={del.isPending}
      onDismiss={onDismiss}
      onConfirm={() => del.mutate({ path: { card_id: card.id } })}
    >
      <p className="font-medium text-ink">“{card.question}”</p>
      <p>The card will be removed from this deck. This cannot be undone.</p>
      {del.isError && (
        <p role="alert" className="text-red">
          Could not delete the card. Try again.
        </p>
      )}
    </ConfirmDialog>
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
      {create.isError && (
        <p role="alert" className="text-sm text-red">
          Generation failed. Try again.
        </p>
      )}
      <button type="submit" className="btn-primary" disabled={create.isPending}>
        {create.isPending ? "Generating…" : "Generate cards"}
      </button>
    </form>
  );
}
