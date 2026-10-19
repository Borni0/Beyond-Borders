import { expect, test } from "@playwright/test";

const ALICE = {
  email: `alice-${Date.now()}@example.com`,
  password: "alice-strong-password-1234",
  name: "Alice A",
};
const BOB = {
  email: `bob-${Date.now()}@example.com`,
  password: "bob-strong-password-1234",
  name: "Bob B",
};

async function register(page: import("@playwright/test").Page, user: typeof ALICE) {
  await page.goto("/sign-up");
  await page.getByLabel(/full name/i).fill(user.name);
  await page.getByLabel(/email/i).fill(user.email);
  await page.getByLabel(/password/i).fill(user.password);
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page).toHaveURL("/dashboard");
}

test("two users have isolated sessions", async ({ browser }) => {
  const ctxA = await browser.newContext();
  const pageA = await ctxA.newPage();
  await register(pageA, ALICE);
  await expect(pageA.getByText(ALICE.email)).toBeVisible();

  const ctxB = await browser.newContext();
  const pageB = await ctxB.newPage();
  await register(pageB, BOB);
  await expect(pageB.getByText(BOB.email)).toBeVisible();

  // Alice's session is still her own.
  await pageA.reload();
  await expect(pageA.getByText(ALICE.email)).toBeVisible();
  await expect(pageA.getByText(BOB.email)).not.toBeVisible();

  await ctxA.close();
  await ctxB.close();
});
