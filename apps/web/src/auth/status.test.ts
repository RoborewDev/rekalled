import { describe, expect, it } from "vite-plus/test";
import { authStatus } from "./status";

describe("authStatus", () => {
  it("stays signed in while the SDK is busy with a token call", () => {
    expect(authStatus({ isAuthenticated: true, isLoading: true })).toBe("signedIn");
  });

  it("is loading until the first session check settles", () => {
    expect(authStatus({ isAuthenticated: false, isLoading: true })).toBe("loading");
  });

  it("is signed out once the check settles without a session", () => {
    expect(authStatus({ isAuthenticated: false, isLoading: false })).toBe("signedOut");
  });
});
