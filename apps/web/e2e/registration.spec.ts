import { expect, test } from "@playwright/test";

const TEST_EMAIL = `e2e-${Date.now()}@example.com`;
const TEST_PASSWORD = "e2e-strong-password-1234";

test.describe("Registration", () => {
  test("user can register, see their email on the dashboard, and sign out", async ({
    page,
  }) => {
    await page.goto("/sign-up");
    await page.getByLabel(/full name/i).fill("E2E User");
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page).toHaveURL("/dashboard");
    await expect(page.getByText(TEST_EMAIL)).toBeVisible();

    // Sign out lands back on sign-in.
    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page).toHaveURL(/\/sign-in/);
  });

  test("dashboard redirects unauthenticated users to sign-in", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/sign-in/);
  });
});
