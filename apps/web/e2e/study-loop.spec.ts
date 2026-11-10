import { expect, test } from "@playwright/test";

const TEXT =
  "The mitochondria produce most of the cell's energy. " +
  "Ribosomes build proteins from amino acids. " +
  "The nucleus stores the cell's DNA.";

test("paste text, keep the good drafts, study them", async ({ page }) => {
  const deckName = `Biology ${Date.now()}`;

  await page.goto("/");
  await page.getByPlaceholder("New deck name").fill(deckName);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: deckName })).toBeVisible();

  await page.getByLabel("Make cards from text").fill(TEXT);
  await page.getByRole("button", { name: "Generate cards" }).click();

  await expect(page.getByRole("heading", { name: "Check the drafts" })).toBeVisible();
  await expect(page.getByLabel("Keep")).toHaveCount(3);
  await page.getByLabel("Keep").nth(2).uncheck();
  await page.getByRole("button", { name: "Add 2 cards to deck" }).click();

  await expect(page.getByRole("heading", { name: deckName })).toBeVisible();
  await page.getByRole("link", { name: "Study 2 cards" }).click();

  for (const left of ["2 left", "1 left"]) {
    await expect(page.getByText(left)).toBeVisible();
    await page.keyboard.press("Space");
    await expect(page.getByRole("button", { name: /Easy/ })).toBeVisible();
    await page.keyboard.press("4"); // Easy: due in days, so it leaves the session
  }
  await expect(page.getByRole("heading", { name: "Session done" })).toBeVisible();
  await expect(page.getByText("2 reviews")).toBeVisible();

  await page.getByRole("link", { name: "Back to Study today" }).click();
  await expect(page.getByText(`${deckName}`)).toBeVisible();
});
