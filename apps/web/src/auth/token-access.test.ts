import { describe, expect, it, vi } from "vite-plus/test";
import { createTokenAccess } from "./token-access";

const RESOURCE = "https://api.example";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

/** The terminal error as the SDK reports it: endpoint body on `data`, logto code on `code`. */
function invalidGrantError() {
  return Object.assign(new Error("Grant request is invalid"), {
    code: "oidc.invalid_grant",
    data: { error: "invalid_grant" },
  });
}

describe("createTokenAccess", () => {
  it("shares one source fetch across 8 concurrent callers", async () => {
    const pending = deferred<string>();
    const getAccessToken = vi.fn(() => pending.promise);
    const clearAccessToken = vi.fn(async () => {});
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE);

    const calls = Array.from({ length: 8 }, () => access.getAccessToken());
    pending.resolve("t1");

    const tokens = await Promise.all(calls);
    expect(tokens).toStrictEqual(["t1", "t1", "t1", "t1", "t1", "t1", "t1", "t1"]);
    expect(getAccessToken).toHaveBeenCalledTimes(1);
    expect(getAccessToken).toHaveBeenCalledWith(RESOURCE);
    expect(clearAccessToken).not.toHaveBeenCalled();
  });

  it("orders a forced refresh after the in-flight fetch: clear, then fetch, never mid-flight", async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const order: string[] = [];
    const getAccessToken = vi
      .fn(() => first.promise)
      .mockImplementationOnce(() => {
        order.push("fetch1");
        return first.promise;
      })
      .mockImplementationOnce(() => {
        order.push("fetch2");
        return second.promise;
      });
    const clearAccessToken = vi.fn(async () => {
      order.push("clear");
    });
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE);

    const gentle = access.getAccessToken();
    await Promise.resolve(); // let the queue start the first fetch
    expect(getAccessToken).toHaveBeenCalledTimes(1);
    const forced = access.getAccessToken({ forceRefresh: true });
    // The forced call queues behind the in-flight one; it must not clear underneath it.
    expect(clearAccessToken).not.toHaveBeenCalled();

    first.resolve("t1");
    second.resolve("t2");
    expect(await gentle).toBe("t1");
    expect(await forced).toBe("t2");

    expect(order).toStrictEqual(["fetch1", "clear", "fetch2"]);
  });

  it("shares one forced fetch across concurrent forced callers", async () => {
    const pending = deferred<string>();
    const getAccessToken = vi.fn(() => pending.promise);
    const clearAccessToken = vi.fn(async () => {});
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE);

    const calls = [
      access.getAccessToken({ forceRefresh: true }),
      access.getAccessToken({ forceRefresh: true }),
    ];
    pending.resolve("t2");

    const tokens = await Promise.all(calls);
    expect(tokens).toStrictEqual(["t2", "t2"]);
    expect(getAccessToken).toHaveBeenCalledTimes(1);
    expect(clearAccessToken).toHaveBeenCalledTimes(1);
  });

  it("treats invalid_grant as terminal: notifies once, then answers null without the source", async () => {
    const getAccessToken = vi.fn(async () => {
      throw invalidGrantError();
    });
    const clearAccessToken = vi.fn(async () => {});
    const onSessionDead = vi.fn();
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE, onSessionDead);

    expect(await access.getAccessToken()).toBeNull();
    expect(await access.getAccessToken()).toBeNull();
    // Even a forced refresh is short-circuited: no clear, no fetch, no second redirect.
    expect(await access.getAccessToken({ forceRefresh: true })).toBeNull();

    expect(onSessionDead).toHaveBeenCalledOnce();
    expect(getAccessToken).toHaveBeenCalledTimes(1);
    expect(clearAccessToken).not.toHaveBeenCalled();
  });

  it("resolves concurrent callers with null when the shared fetch hits invalid_grant", async () => {
    let reject!: (reason?: unknown) => void;
    const rejecting = new Promise<string>((_, rej) => {
      reject = rej;
    });
    const getAccessToken = vi.fn(() => rejecting);
    const clearAccessToken = vi.fn(async () => {});
    const onSessionDead = vi.fn();
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE, onSessionDead);

    const calls = Array.from({ length: 3 }, () => access.getAccessToken());
    reject(invalidGrantError());

    expect(await Promise.all(calls)).toStrictEqual([null, null, null]);
    expect(onSessionDead).toHaveBeenCalledOnce();
    expect(getAccessToken).toHaveBeenCalledTimes(1);
  });

  it("treats a data-only invalid_grant shape as terminal too", async () => {
    const getAccessToken = vi.fn(async () => {
      // The token-endpoint body may arrive without a Logto error code on the wrapper.
      throw Object.assign(new Error("unexpected_response_error"), {
        data: { error: "invalid_grant", error_description: "Grant request is invalid" },
      });
    });
    const clearAccessToken = vi.fn(async () => {});
    const onSessionDead = vi.fn();
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE, onSessionDead);

    expect(await access.getAccessToken()).toBeNull();
    expect(onSessionDead).toHaveBeenCalledOnce();
  });

  it("propagates network failures unchanged and keeps the session usable", async () => {
    const network = new Error("offline");
    const getAccessToken = vi.fn(async () => "t1").mockRejectedValueOnce(network);
    const clearAccessToken = vi.fn(async () => {});
    const onSessionDead = vi.fn();
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE, onSessionDead);

    await expect(access.getAccessToken()).rejects.toBe(network);

    expect(await access.getAccessToken()).toBe("t1");
    expect(getAccessToken).toHaveBeenCalledTimes(2);
    expect(onSessionDead).not.toHaveBeenCalled();
  });

  it("markSessionDead short-circuits without the source, even for forced refreshes", async () => {
    const getAccessToken = vi.fn(async () => "t1");
    const clearAccessToken = vi.fn(async () => {});
    const onSessionDead = vi.fn();
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE, onSessionDead);

    access.markSessionDead();

    expect(await access.getAccessToken()).toBeNull();
    expect(await access.getAccessToken({ forceRefresh: true })).toBeNull();

    expect(onSessionDead).toHaveBeenCalledOnce();
    expect(getAccessToken).not.toHaveBeenCalled();
    expect(clearAccessToken).not.toHaveBeenCalled();
  });

  it("notifies onSessionDead once when the internal and external dead paths converge", async () => {
    // The swallowed-error path in logto-adapter can land after the gate already saw the
    // rejection — or vice versa — so both must funnel into a single recovery attempt.
    const getAccessToken = vi.fn(async () => {
      throw invalidGrantError();
    });
    const clearAccessToken = vi.fn(async () => {});
    const onSessionDead = vi.fn();
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE, onSessionDead);

    expect(await access.getAccessToken()).toBeNull();
    access.markSessionDead();
    access.markSessionDead();

    expect(onSessionDead).toHaveBeenCalledOnce();
    expect(getAccessToken).toHaveBeenCalledTimes(1);
  });

  it("rethrows not_authenticated without flagging the session dead", async () => {
    const notAuthenticated = Object.assign(new Error("Not authenticated."), {
      code: "not_authenticated",
      data: "Refresh token not found",
    });
    const getAccessToken = vi.fn(async () => {
      throw notAuthenticated;
    });
    const clearAccessToken = vi.fn(async () => {});
    const onSessionDead = vi.fn();
    const access = createTokenAccess({ getAccessToken, clearAccessToken }, RESOURCE, onSessionDead);

    await expect(access.getAccessToken()).rejects.toBe(notAuthenticated);
    await expect(access.getAccessToken()).rejects.toBe(notAuthenticated);

    expect(getAccessToken).toHaveBeenCalledTimes(2);
    expect(onSessionDead).not.toHaveBeenCalled();
  });
});
