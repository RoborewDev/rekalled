import { expect, test } from "@playwright/test";

// The whole API is unreachable: after bounded retries the shared error screen must
// appear, and requests must stop — no redirect loop, no endless refetching.
test("an API outage shows the error screen and stops fetching", async ({ page }) => {
  let aborted = 0;
  await page.route("**/v1/**", (route) => {
    aborted += 1;
    return route.abort();
  });

  await page.goto("/");
  await expect(page.getByText("Uh oh! This is embarrassing.")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(/technical difficulty/)).toBeVisible();

  // Bounded: once the error state is reached, the request count must settle.
  const settled = aborted;
  await page.waitForTimeout(1_500);
  expect(aborted).toBe(settled);
});
