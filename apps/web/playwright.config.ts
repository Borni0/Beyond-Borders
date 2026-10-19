import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config.
 *
 * The tests below are minimal: they only require a running backend
 * (for the API to work) and a running Next.js dev server (for the
 * browser tests). `webServer` boots both automatically.
 *
 * For the unit/component coverage of business logic, see Vitest.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "list" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "cd ../../services/api && . .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/api/v1/health",
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      env: {
        DATABASE_URL: "sqlite:///./e2e_test.db",
        SECRET_KEY: "e2e-test-secret-key-please-do-not-use-32b",
        COOKIE_SECURE: "false",
        LOG_LEVEL: "WARNING",
      },
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000/api/v1",
      },
    },
  ],
});