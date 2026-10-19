/**
 * Phase 1 happy-path e2e: register → create plan → add cost → add
 * funding → see the readiness panel update.
 *
 * Requires the dev servers (frontend on :3000, backend on :8000) to
 * be running. The Playwright config (webServer) handles startup.
 */

import { expect, test } from "@playwright/test";

test("user can create a plan, add costs and funding, see readiness", async ({
  page,
}) => {
  const email = `alice-${Date.now()}@example.com`;
  const password = "CorrectHorse-9!Battery";

  // Register
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel("Name").fill("Alice Tester");
  await page.getByLabel("Home country", { exact: false }).fill("US");
  await page.getByRole("button", { name: /create account/i }).click();
  await page.waitForURL(/\/dashboard$/);

  // Go to readiness
  await page.goto("/readiness");
  await expect(page.getByRole("heading", { name: /plans/i })).toBeVisible();

  // Create a plan
  await page.getByRole("button", { name: /new plan/i }).click();
  await page.getByLabel("Name").first().fill("MSc in Berlin");
  await page.getByLabel("Base currency").fill("USD");
  await page.getByLabel("Start date").fill("2026-09-01");
  await page.getByLabel("Duration (months)").fill("24");
  await page.getByRole("button", { name: /create plan/i }).click();

  // Wait for the editor to appear.
  await expect(page.getByText("Costs")).toBeVisible();

  // Add a cost
  await page.getByLabel("Description").last().fill("Monthly rent");
  await page.getByLabel("Amount").last().fill("900");
  await page.getByRole("button", { name: /add cost/i }).click();

  // Add a funding source
  await page.getByLabel(/^Name$/).last().fill("Family savings");
  await page.getByLabel("Amount").last().fill("30000");
  await page.getByRole("button", { name: /add funding/i }).click();

  // Wait for the readiness panel to reflect the data.
  await expect(page.getByTestId("status-chips")).toBeVisible();
});
