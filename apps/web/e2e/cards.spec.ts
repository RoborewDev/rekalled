import { expect, test } from "@playwright/test";

const TEXT =
  "The mitochondria produce most of the cell's energy. " +
  "Ribosomes build proteins from amino acids. " +
  "The nucleus stores the cell's DNA.";

test("edit a card from the deck page", async ({ page }) => {
  const deckName = `Editing ${Date.now()}`;
  await page.goto("/");
  await page.getByPlaceholder("New deck name").fill(deckName);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: deckName })).toBeVisible();

  await page.getByLabel("Make cards from text").fill(TEXT);
  await page.getByRole("button", { name: "Generate cards" }).click();
  await expect(page.getByRole("heading", { name: "Check the drafts" })).toBeVisible();
  await page.getByRole("button", { name: "Add 3 cards to deck" }).click();
  await expect(page.getByRole("heading", { name: deckName })).toBeVisible();

  const mitochondria = page.getByRole("listitem").filter({ hasText: "mitochondria" });
  await expect(mitochondria).toBeVisible();

  // Cancel discards the changes; the card keeps its wording.
  await mitochondria.getByRole("button", { name: "Edit card" }).click();
  await mitochondria.getByLabel("Question").fill("Discarded question?");
  await mitochondria.getByRole("button", { name: "Cancel" }).click();
  await expect(mitochondria.getByText("What does the text say about")).toBeVisible();

  // Save persists the new wording.
  await mitochondria.getByRole("button", { name: "Edit card" }).click();
  await mitochondria.getByLabel("Question").fill("Where is most of a cell's energy made?");
  await mitochondria.getByLabel("Answer").fill("The mitochondria.");
  await mitochondria.getByRole("button", { name: "Save" }).click();
  await expect(mitochondria.getByText("Where is most of a cell's energy made?")).toBeVisible();
  await expect(mitochondria.getByText("The mitochondria.")).toBeVisible();
});

test("deleting a card asks for confirmation", async ({ page }) => {
  const deckName = `Deleting ${Date.now()}`;
  await page.goto("/");
  await page.getByPlaceholder("New deck name").fill(deckName);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: deckName })).toBeVisible();

  await page.getByLabel("Make cards from text").fill(TEXT);
  await page.getByRole("button", { name: "Generate cards" }).click();
  await expect(page.getByRole("heading", { name: "Check the drafts" })).toBeVisible();
  await page.getByRole("button", { name: "Add 3 cards to deck" }).click();
  await expect(page.getByRole("heading", { name: deckName })).toBeVisible();

  const ribosomes = page.getByRole("listitem").filter({ hasText: "Ribosomes" });
  await ribosomes.getByRole("button", { name: "Delete card" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Ribosomes")).toBeVisible();

  // Escape dismisses without deleting.
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(ribosomes).toBeVisible();

  // Cancel dismisses without deleting.
  await ribosomes.getByRole("button", { name: "Delete card" }).click();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(ribosomes).toBeVisible();

  // Confirm deletes only that card.
  await ribosomes.getByRole("button", { name: "Delete card" }).click();
  await dialog.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(ribosomes).toHaveCount(0);
  await expect(page.getByRole("listitem")).toHaveCount(2);
});
