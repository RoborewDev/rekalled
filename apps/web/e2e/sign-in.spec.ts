import { expect, test } from "@playwright/test";

// The prototype flow: a signed-out visitor sees the sign-in card instead of being
// auto-redirected to the identity provider, and signing out returns them to it.
test("sign out shows the sign-in landing; sign in returns to the app", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Decks" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();

  // The landing replaces the app shell: card copy, no header user, no deck form.
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await expect(page.getByText("Turn what you read into flash cards")).toBeVisible();
  await expect(page.getByText("Dev user")).toBeHidden();
  await expect(page.getByLabel("New deck name")).toBeHidden();

  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Decks" })).toBeVisible();
  await expect(page.getByText("Dev user")).toBeVisible();
});
