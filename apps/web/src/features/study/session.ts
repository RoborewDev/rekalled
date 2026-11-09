import type { StudyCard } from "@rekalled/api-client";

export type Rating = 1 | 2 | 3 | 4;

/** A card rated Again/Hard comes back in the same session if it is due within this window. */
export const LEARN_AHEAD_MS = 20 * 60 * 1000;

export type SessionState = {
  queue: StudyCard[];
  revealed: boolean;
  reviewed: number;
  again: number;
};

export type SessionAction = { type: "reveal" } | { type: "rate"; rating: Rating; now: Date };

export function startSession(cards: StudyCard[]): SessionState {
  return { queue: cards, revealed: false, reviewed: 0, again: 0 };
}

export function currentCard(state: SessionState): StudyCard | null {
  return state.queue[0] ?? null;
}

export function isFinished(state: SessionState): boolean {
  return state.queue.length === 0;
}

export function sessionReducer(state: SessionState, action: SessionAction): SessionState {
  const [card, ...rest] = state.queue;
  if (!card) return state;

  switch (action.type) {
    case "reveal":
      return { ...state, revealed: true };

    case "rate": {
      const dueIso = card.next_due[String(action.rating)];
      const comesBack =
        dueIso !== undefined && new Date(dueIso).getTime() - action.now.getTime() <= LEARN_AHEAD_MS;
      // The interval previews are stale once a card has been reviewed, so drop them.
      const queue = comesBack ? [...rest, { ...card, next_due: {} }] : rest;
      return {
        queue,
        revealed: false,
        reviewed: state.reviewed + 1,
        again: state.again + (action.rating === 1 ? 1 : 0),
      };
    }
  }
}
