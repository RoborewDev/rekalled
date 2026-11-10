import { describe, expect, it } from "vite-plus/test";
import { resolveRuntimeConfig } from "./runtime-env";

describe("resolveRuntimeConfig", () => {
  it("defaults to the local API and dev adapter outside production", () => {
    expect(resolveRuntimeConfig({ NODE_ENV: "development" })).toEqual({
      apiUrl: "http://localhost:8000",
      authMode: "dev",
      logto: null,
    });
  });

  it("reads the API, auth mode and Logto settings from the environment", () => {
    expect(
      resolveRuntimeConfig({
        NODE_ENV: "production",
        API_URL: "https://api.rekalled.app",
        AUTH_MODE: "logto",
        LOGTO_ENDPOINT: "https://tenant.logto.app",
        LOGTO_APP_ID: "app-id",
        LOGTO_API_RESOURCE: "https://api.rekalled.app",
      }),
    ).toEqual({
      apiUrl: "https://api.rekalled.app",
      authMode: "logto",
      logto: {
        endpoint: "https://tenant.logto.app",
        appId: "app-id",
        resource: "https://api.rekalled.app",
      },
    });
  });

  it("requires API_URL in production", () => {
    expect(() => resolveRuntimeConfig({ NODE_ENV: "production", AUTH_MODE: "logto" })).toThrow(
      "API_URL must be set",
    );
  });

  it("requires AUTH_MODE in production", () => {
    expect(() =>
      resolveRuntimeConfig({ NODE_ENV: "production", API_URL: "https://api.rekalled.app" }),
    ).toThrow("AUTH_MODE must be dev or logto");
  });

  it("requires the public Logto settings when AUTH_MODE is logto", () => {
    expect(() =>
      resolveRuntimeConfig({
        NODE_ENV: "production",
        API_URL: "https://api.rekalled.app",
        AUTH_MODE: "logto",
      }),
    ).toThrow("LOGTO_ENDPOINT");
  });

  it("refuses an auth mode that has no adapter", () => {
    expect(() =>
      resolveRuntimeConfig({
        NODE_ENV: "production",
        API_URL: "https://api.rekalled.app",
        AUTH_MODE: "magic",
      }),
    ).toThrow("AUTH_MODE must be dev or logto");
  });
});
