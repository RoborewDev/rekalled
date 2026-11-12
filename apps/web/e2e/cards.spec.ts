import { expect, test, type Page } from "@playwright/test";

const TEXT =
  "The mitochondria produce most of the cell's energy. " +
  "Ribosomes build proteins from amino acids. " +
  "The nucleus stores the cell's DNA.";

/** Create a deck with the three biology cards and wait for the deck page. */
async function createDeckWithCards(page: Page, deckName: string) {
  await page.goto("/");
  await page.getByPlaceholder("New deck name").fill(deckName);
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("heading", { name: deckName })).toBeVisible();

  await page.getByLabel("Make cards from text").fill(TEXT);
  await page.getByRole("button", { name: "Generate cards" }).click();
  await expect(page.getByRole("heading", { name: "Check the drafts" })).toBeVisible();
  await page.getByRole("button", { name: "Add 3 cards to deck" }).click();
  await expect(page.getByRole("heading", { name: deckName })).toBeVisible();
}

test("edit a card from the deck page", async ({ page }) => {
  const deckName = `Editing ${Date.now()}`;
  await createDeckWithCards(page, deckName);

  const mitochondria = page.getByRole("listitem").filter({ hasText: "mitochondria" });
  await expect(mitochondria).toBeVisible();

  // Cancel discards the changes; the card keeps its wording.
  await mitochondria.getByRole("button", { name: "Edit card" }).click();
  // Entering edit mode moves focus into the form.
  await expect(mitochondria.getByLabel("Question")).toBeFocused();
  await mitochondria.getByLabel("Question").fill("Discarded question?");
  await mitochondria.getByRole("button", { name: "Cancel" }).click();
  await expect(mitochondria.getByText("What does the text say about")).toBeVisible();
  // Leaving edit mode returns focus to the row's Edit button.
  await expect(mitochondria.getByRole("button", { name: "Edit card" })).toBeFocused();

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
  await createDeckWithCards(page, deckName);

  const ribosomes = page.getByRole("listitem").filter({ hasText: "Ribosomes" });
  await ribosomes.getByRole("button", { name: "Delete card" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Ribosomes")).toBeVisible();

  // Escape dismisses without deleting, and focus returns to the Delete button.
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(ribosomes).toBeVisible();
  await expect(ribosomes.getByRole("button", { name: "Delete card" })).toBeFocused();

  // The Close (X) button dismisses without deleting.
  await ribosomes.getByRole("button", { name: "Delete card" }).click();
  await dialog.getByRole("button", { name: "Close" }).click();
  await expect(dialog).toBeHidden();
  await expect(ribosomes).toBeVisible();

  // Clicking the scrim dismisses without deleting.
  await ribosomes.getByRole("button", { name: "Delete card" }).click();
  await page.mouse.click(5, 5);
  await expect(dialog).toBeHidden();
  await expect(ribosomes).toBeVisible();

  // Cancel dismisses without deleting, and focus returns to the Delete button.
  await ribosomes.getByRole("button", { name: "Delete card" }).click();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(ribosomes).toBeVisible();
  await expect(ribosomes.getByRole("button", { name: "Delete card" })).toBeFocused();

  // Confirm deletes only that card.
  await ribosomes.getByRole("button", { name: "Delete card" }).click();
  await dialog.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(ribosomes).toHaveCount(0);
  await expect(page.getByRole("listitem")).toHaveCount(2);
  // The deleted row's controls are gone; focus lands on a surviving control.
  await expect(page.getByLabel("Make cards from text")).toBeFocused();
});

test("cancel is unavailable while a save is pending", async ({ page }) => {
  const deckName = `Pending save ${Date.now()}`;
  await createDeckWithCards(page, deckName);

  // Hold the PATCH open so the save stays pending until released.
  let releaseSave: (() => void) | undefined;
  await page.route("**/v1/cards/*", async (route) => {
    if (route.request().method() === "PATCH") {
      await new Promise<void>((resolve) => {
        releaseSave = resolve;
      });
    }
    await route.continue();
  });

  const mitochondria = page.getByRole("listitem").filter({ hasText: "mitochondria" });
  await mitochondria.getByRole("button", { name: "Edit card" }).click();
  await mitochondria.getByLabel("Question").fill("Held question?");
  await mitochondria.getByRole("button", { name: "Save" }).click();

  // Cancel must not close the form while the save is in flight.
  await expect(mitochondria.getByRole("button", { name: "Cancel" })).toBeDisabled();

  // Once the save settles, the new wording is there.
  releaseSave?.();
  await expect(mitochondria.getByText("Held question?")).toBeVisible();
});

test("the delete dialog cannot be dismissed while deletion is pending", async ({ page }) => {
  const deckName = `Pending delete ${Date.now()}`;
  await createDeckWithCards(page, deckName);

  // Hold the DELETE open so the dialog stays pending until released.
  let releaseDelete: (() => void) | undefined;
  await page.route("**/v1/cards/*", async (route) => {
    if (route.request().method() === "DELETE") {
      await new Promise<void>((resolve) => {
        releaseDelete = resolve;
      });
    }
    await route.continue();
  });

  const ribosomes = page.getByRole("listitem").filter({ hasText: "Ribosomes" });
  await ribosomes.getByRole("button", { name: "Delete card" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Delete", exact: true }).click();

  // While the DELETE is in flight, every dismissal path is refused.
  await expect(dialog.getByRole("button", { name: "Cancel" })).toBeDisabled();
  await expect(dialog.getByRole("button", { name: "Close" })).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeVisible();
  await page.mouse.click(5, 5);
  await expect(dialog).toBeVisible();

  // Once it settles, the card is gone.
  releaseDelete?.();
  await expect(ribosomes).toHaveCount(0);
  await expect(page.getByRole("listitem")).toHaveCount(2);
});
