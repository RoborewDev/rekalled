import { defineConfig, devices } from "@playwright/test";

// Ports are overridable so e2e can run beside a dev server that already holds the defaults
// (e.g. E2E_WEB_PORT=3100 E2E_API_PORT=8100 pnpm e2e). Defaults match `just dev`.
const apiPort = process.env.E2E_API_PORT ?? "8000";
const webPort = process.env.E2E_WEB_PORT ?? "3000";
const webOrigin = `http://localhost:${webPort}`;

// Full loop in a real browser: dev auth (no Logto) and the fake card generator (no AI calls).
export default defineConfig({
  testDir: "e2e",
  // CI uploads playwright-report; the default list reporter does not write one.
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: { baseURL: webOrigin, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run fastapi run --port ${apiPort}`,
      cwd: "../api",
      url: `http://localhost:${apiPort}/v1/health`,
      // The API must allow the web origin in CORS; pydantic-settings parses lists as JSON.
      env: { AUTH_MODE: "dev", CARD_GENERATOR: "fake", CORS_ORIGINS: JSON.stringify([webOrigin]) },
      // Reusing a running `just dev` server would ignore the env above and hit a real model.
      reuseExistingServer: false,
    },
    {
      command: `pnpm exec vp dev --port ${webPort}`,
      url: webOrigin,
      // The web server reads AUTH_MODE and API_URL at request time (lib/runtime-env.ts).
      env: { AUTH_MODE: "dev", API_URL: `http://localhost:${apiPort}` },
      // Reusing a running `just dev-logto` server would serve Logto auth instead of dev auth.
      reuseExistingServer: false,
    },
  ],
});
