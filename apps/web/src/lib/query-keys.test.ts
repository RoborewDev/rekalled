import { describe, expect, it } from "vite-plus/test";
import { getStudyQueueQueryKey, listDecksQueryKey } from "@rekalled/api-client/query";
import { opId } from "./query-keys";

describe("opId", () => {
  it("reads the operation id from a generated query key", () => {
    expect(opId({ queryKey: getStudyQueueQueryKey() })).toBe("getStudyQueue");
    expect(opId({ queryKey: listDecksQueryKey() })).toBe("listDecks");
  });

  it("is undefined for a hand-written key", () => {
    expect(opId({ queryKey: ["something"] })).toBeUndefined();
  });
});
