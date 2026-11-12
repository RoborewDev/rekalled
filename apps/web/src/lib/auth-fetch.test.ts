import { describe, expect, it, vi } from "vite-plus/test";
import { createAuthFetch } from "./auth-fetch";

const ok = () => new Response("{}", { status: 200 });
const unauthorized = () => new Response("", { status: 401 });

function fakeAuth(tokens: (string | null)[]) {
  return {
    getAccessToken: vi.fn(async () => tokens.shift() ?? null),
    signIn: vi.fn(),
  };
}

describe("createAuthFetch", () => {
  it("adds the bearer token", async () => {
    const baseFetch = vi.fn<typeof fetch>(async () => ok());
    const authFetch = createAuthFetch(fakeAuth(["t1"]), baseFetch);

    await authFetch("http://test/v1/decks");

    const sent = baseFetch.mock.calls[0][0] as Request;
    expect(sent.headers.get("Authorization")).toBe("Bearer t1");
  });

  it("sends no header when there is no token (dev mode)", async () => {
    const baseFetch = vi.fn<typeof fetch>(async () => ok());
    await createAuthFetch(fakeAuth([null]), baseFetch)("http://test/v1/decks");

    expect((baseFetch.mock.calls[0][0] as Request).headers.has("Authorization")).toBe(false);
  });

  it("refreshes the token and retries once on 401, keeping the body", async () => {
    const auth = fakeAuth(["stale", "fresh"]);
    const baseFetch = vi.fn<typeof fetch>(async () => ok()).mockResolvedValueOnce(unauthorized());

    const response = await createAuthFetch(auth, baseFetch)("http://test/v1/decks", {
      method: "POST",
      body: JSON.stringify({ name: "Deck" }),
    });

    expect(response.status).toBe(200);
    expect(auth.getAccessToken).toHaveBeenLastCalledWith({ forceRefresh: true });
    const retry = baseFetch.mock.calls[1][0] as Request;
    expect(retry.headers.get("Authorization")).toBe("Bearer fresh");
    expect(await retry.text()).toBe('{"name":"Deck"}');
    expect(auth.signIn).not.toHaveBeenCalled();
  });

  it("returns a repeated 401 instead of redirecting", async () => {
    const auth = fakeAuth(["stale", "still-bad"]);
    const baseFetch = vi.fn<typeof fetch>(async () => unauthorized());

    const response = await createAuthFetch(auth, baseFetch)("http://test/v1/decks");

    expect(response.status).toBe(401);
    expect(baseFetch).toHaveBeenCalledTimes(2);
    expect(auth.signIn).not.toHaveBeenCalled();
  });
});
