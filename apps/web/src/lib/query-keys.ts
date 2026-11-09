import type { Query } from "@tanstack/react-query";

// Generated query keys are [{ _id: "listDecks", ...options }], not ["listDecks"]:
// compare the operation id, never the key object itself.
export const opId = (q: Pick<Query, "queryKey">): string | undefined =>
  (q.queryKey[0] as { _id?: string } | undefined)?._id;
