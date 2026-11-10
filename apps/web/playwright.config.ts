import { defineConfig, devices } from "@playwright/test";

// Full loop in a real browser: dev auth (no Logto) and the fake card generator (no AI calls).
export default defineConfig({
  testDir: "e2e",
  // CI uploads playwright-report; the default list reporter does not write one.
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run fastapi run --port 8000",
      cwd: "../api",
      url: "http://localhost:8000/v1/health",
      env: { AUTH_MODE: "dev", CARD_GENERATOR: "fake" },
      // Reusing a running `just dev` server would ignore the env above and hit a real model.
      reuseExistingServer: false,
    },
    {
      command: "pnpm dev",
      url: "http://localhost:3000",
      // The web server reads AUTH_MODE and API_URL at request time (lib/runtime-env.ts).
      env: { AUTH_MODE: "dev", API_URL: "http://localhost:8000" },
      // Reusing a running `just dev-logto` server would serve Logto auth instead of dev auth.
      reuseExistingServer: false,
    },
  ],
});
