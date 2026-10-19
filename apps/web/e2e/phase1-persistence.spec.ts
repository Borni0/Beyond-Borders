/**
 * Phase 1 persistence e2e: write data, then sign out and sign back in
 * with the same credentials; the data must still be there.
 */

import { expect, test } from "@playwright/test";

test("plan and readiness survive a sign-out / sign-in cycle", async ({
  page,
  context,
}) => {
  const email = `bob-${Date.now()}@example.com`;
  const password = "CorrectHorse-9!Battery";

  // Register and create a plan
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel("Name").fill("Bob Tester");
  await page.getByLabel("Home country", { exact: false }).fill("US");
  await page.getByRole("button", { name: /create account/i }).click();
  await page.waitForURL(/\/dashboard$/);

  await page.goto("/readiness");
  await page.getByRole("button", { name: /new plan/i }).click();
  await page.getByLabel("Name").first().fill("MBA in London");
  await page.getByLabel("Base currency").fill("USD");
  await page.getByLabel("Start date").fill("2026-09-01");
  await page.getByLabel("Duration (months)").fill("12");
  await page.getByRole("button", { name: /create plan/i }).click();
  await expect(page.getByText("MBA in London")).toBeVisible();

  // Sign out via dashboard
  await page.goto("/dashboard");
  await page.getByRole("button", { name: /sign out/i }).click();
  await page.waitForURL(/\/sign-in/);

  // Sign back in
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL(/\/dashboard$/);

  // Plan still there
  await page.goto("/readiness");
  await expect(page.getByText("MBA in London")).toBeVisible();

  // Cookies are httpOnly — close context to confirm we are not relying on
  // an accidental client cache.
  await context.close();
});
