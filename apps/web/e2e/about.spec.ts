import { expect, test } from "@playwright/test";

// /about is public: readable while signed out, with no sign-in gate.
test("about page is visible without signing in", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();

  await page.goto("/about");
  await expect(
    page.getByText("Rekalled is a beta app designed to simplify spaced repetition!"),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeHidden();
});

// /callback must stay public: gating it would dead-loop the Logto code exchange.
// In dev mode the callback immediately returns to "/", so the URL is the assertion:
// a gate would leave it stuck at /callback.
test("callback route is not gated", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/callback");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});
