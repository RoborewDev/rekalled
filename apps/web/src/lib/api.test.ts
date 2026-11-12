import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { client } from "@rekalled/api-client/client";
import { configureApi } from "./api";

const initialConfig = client.getConfig();

afterEach(() => {
  client.setConfig(initialConfig);
  vi.unstubAllGlobals();
});

describe("configureApi", () => {
  it("points the generated client at the runtime API origin", () => {
    configureApi("https://api.example.test", {
      getAccessToken: async () => null,
    });

    expect(client.getConfig().baseUrl).toBe("https://api.example.test");
  });

  it("routes requests through the auth fetch", async () => {
    const getAccessToken = vi.fn(async () => "token-1");
    const baseFetch = vi.fn<typeof fetch>(async () => Response.json({}));
    vi.stubGlobal("fetch", baseFetch);

    configureApi("https://api.example.test", { getAccessToken });
    await client.get({ url: "/v1/me" });

    expect(getAccessToken).toHaveBeenCalledOnce();
    const sent = baseFetch.mock.calls[0][0] as Request;
    expect(sent.url).toBe("https://api.example.test/v1/me");
    expect(sent.headers.get("Authorization")).toBe("Bearer token-1");
  });
});
