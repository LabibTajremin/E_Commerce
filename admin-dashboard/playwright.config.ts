import { defineConfig, devices } from "@playwright/test";

/**
 * Runs against a fully live stack (backend + Postgres + Redis + this app's
 * dev server) — set ADMIN_DASHBOARD_BASE_URL to point at it. Not wired into
 * CI yet: same infra gap as the backend's Docker-dependent integration/e2e
 * suite (see backend/tests/integration and backend/tests/e2e).
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: process.env.ADMIN_DASHBOARD_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
