import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { CardOut } from "@rekalled/api-client";
import { commitDraftsMutation, getSourceOptions } from "@rekalled/api-client/query";

export const Route = createFileRoute("/sources/$sourceId")({ component: DraftCheck });

type Draft = { keep: boolean; question: string; answer: string };

const toDraft = (card: CardOut): Draft => ({
  keep: true,
  question: card.question,
  answer: card.answer,
});

function DraftCheck() {
  const { sourceId } = Route.useParams();
  const source = useQuery(getSourceOptions({ path: { source_id: sourceId } }));

  if (source.isPending) return <p>Loading drafts…</p>;
  if (source.isError) return <p className="text-red">Could not load this source.</p>;
  const drafts = source.data.cards.filter((c) => c.status === "draft");
  return <DraftForm deckId={source.data.deck_id} sourceId={sourceId} drafts={drafts} />;
}

function DraftForm({
  deckId,
  sourceId,
  drafts,
}: {
  deckId: string;
  sourceId: string;
  drafts: CardOut[];
}) {
  const [edits, setEdits] = useState<Record<string, Draft>>(() =>
    Object.fromEntries(drafts.map((d) => [d.id, toDraft(d)])),
  );
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const commit = useMutation({
    ...commitDraftsMutation(),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      await navigate({ to: "/decks/$deckId", params: { deckId } });
    },
  });

  const update = (draft: CardOut, patch: Partial<Draft>) =>
    setEdits((e) => ({
      ...e,
      [draft.id]: { ...toDraft(draft), ...e[draft.id], ...patch },
    }));
  const kept = drafts
    .map((draft) => [draft.id, edits[draft.id] ?? toDraft(draft)] as const)
    .filter(([, d]) => d.keep);

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        commit.mutate({
          path: { source_id: sourceId },
          body: {
            kept: kept.map(([card_id, d]) => ({ card_id, question: d.question, answer: d.answer })),
          },
        });
      }}
    >
      <h1 className="text-3xl">Check the drafts</h1>
      <p className="text-ink-soft">
        Untick anything wrong or trivial. Edit wording before it goes into the deck.
      </p>
      {drafts.map((draft, index) => {
        const d = edits[draft.id] ?? toDraft(draft);
        return (
          <fieldset key={draft.id} className={`panel space-y-2 ${d.keep ? "" : "opacity-50"}`}>
            <legend className="sr-only">Card {index + 1}</legend>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={d.keep}
                onChange={(e) => update(draft, { keep: e.target.checked })}
              />
              Keep
            </label>
            <input
              className="field font-medium"
              value={d.question}
              onChange={(e) => update(draft, { question: e.target.value })}
              aria-label="Question"
            />
            <textarea
              className="field"
              value={d.answer}
              onChange={(e) => update(draft, { answer: e.target.value })}
              aria-label="Answer"
            />
            {draft.source_excerpt && (
              <p className="text-xs text-ink-soft">“{draft.source_excerpt}”</p>
            )}
          </fieldset>
        );
      })}
      {commit.isError && (
        <p role="alert" className="text-sm text-red">
          Could not add the cards. Try again.
        </p>
      )}
      <button
        type="submit"
        className="btn-primary"
        disabled={commit.isPending || kept.length === 0}
      >
        Add {kept.length} cards to deck
      </button>
    </form>
  );
}
