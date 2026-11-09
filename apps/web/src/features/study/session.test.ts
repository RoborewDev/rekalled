import { describe, expect, it } from "vite-plus/test";
import type { StudyCard } from "@rekalled/api-client";
import { currentCard, isFinished, sessionReducer, startSession } from "./session";

const NOW = new Date("2026-11-02T09:00:00Z");
const inMinutes = (m: number) => new Date(NOW.getTime() + m * 60_000).toISOString();
const inDays = (d: number) => inMinutes(d * 24 * 60);

function card(id: string): StudyCard {
  return {
    id,
    deck_id: "d1",
    deck_name: "Deck",
    question: `Q ${id}`,
    answer: `A ${id}`,
    source_excerpt: null,
    is_new: true,
    memory_score: null,
    next_due: { "1": inMinutes(1), "2": inMinutes(6), "3": inMinutes(10), "4": inDays(8) },
  };
}

describe("study session", () => {
  it("shows the question first, then the answer", () => {
    let state = startSession([card("a")]);
    expect(state.revealed).toBe(false);

    state = sessionReducer(state, { type: "reveal" });
    expect(state.revealed).toBe(true);
  });

  it("moves on when a card is not due again this session", () => {
    let state = startSession([card("a"), card("b")]);
    state = sessionReducer(state, { type: "rate", rating: 4, now: NOW });

    expect(currentCard(state)?.id).toBe("b");
    expect(state.revealed).toBe(false);
    expect(state.reviewed).toBe(1);
  });

  it("re-queues a card that is due again within the session", () => {
    let state = startSession([card("a"), card("b")]);
    state = sessionReducer(state, { type: "rate", rating: 1, now: NOW });

    expect(state.queue.map((c) => c.id)).toEqual(["b", "a"]);
    expect(state.again).toBe(1);
  });

  it("keeps bringing a card back while it is rated Again", () => {
    let state = startSession([card("a")]);
    state = sessionReducer(state, { type: "rate", rating: 1, now: NOW });
    state = sessionReducer(state, { type: "rate", rating: 1, now: NOW });

    expect(state.queue.map((c) => c.id)).toEqual(["a"]);
    expect(state.again).toBe(2);
  });

  it("does not re-queue a reviewed card on a stale interval preview", () => {
    let state = startSession([card("a")]);
    state = sessionReducer(state, { type: "rate", rating: 1, now: NOW });
    state = sessionReducer(state, { type: "rate", rating: 3, now: NOW });

    expect(isFinished(state)).toBe(true);
  });

  it("finishes when the queue is empty", () => {
    let state = startSession([card("a")]);
    state = sessionReducer(state, { type: "rate", rating: 4, now: NOW });

    expect(isFinished(state)).toBe(true);
    expect(currentCard(state)).toBeNull();
  });
});
