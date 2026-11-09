import { defineConfig, devices } from "@playwright/test";

// Full loop in a real browser: dev auth (no Logto) and the fake card generator (no AI calls).
export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run fastapi run --port 8000",
      cwd: "../api",
      url: "http://localhost:8000/v1/health",
      env: { AUTH_MODE: "dev", CARD_GENERATOR: "fake" },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "pnpm dev",
      url: "http://localhost:3000",
      env: { VITE_AUTH_MODE: "dev", VITE_API_URL: "http://localhost:8000" },
      reuseExistingServer: !process.env.CI,
    },
  ],
});
