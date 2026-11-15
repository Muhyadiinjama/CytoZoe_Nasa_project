import { expect, test } from "@playwright/test";
import { isolate } from "./helpers";

test("T08/ENV-01/ENV-02: radiation quality strip, conflict evidence and a participant-free review", async ({ page }) => {
  await isolate(page);
  await page.goto("/environment");
  await expect(page.getByRole("note")).toContainText("Not linked to the selected health participant.");
  // No health participant controls on this route.
  await expect(page.getByLabel("Participant (anonymised)")).toHaveCount(0);

  const strip = page.getByRole("region", { name: "Data quality summary" });
  await expect(strip).toContainText("1,192");
  await expect(strip).toContainText("6 in 3 conflict groups");

  await page.getByRole("button", { name: "Why excluded?" }).click();
  await expect(page.getByRole("region", { name: /Why were 6 records excluded/ })).toBeFocused();
  for (const t of ["04:45:00", "09:10:00", "09:15:00"]) {
    await expect(page.getByRole("heading", { name: new RegExp(t) })).toBeVisible();
  }

  await page.getByRole("button", { name: "Inspect & review conflicting readings at 09:15:00" }).click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toContainText("2.99937726837061");
  await expect(drawer).toContainText("2.698345");
  await drawer.getByRole("button", { name: "Explain this result" }).click();
  await expect(drawer).toContainText("does not take the first value, sum them or average them");
  await drawer.getByLabel(/Reviewer note/).fill("Ask the RadLab provider which DosTel1 row is authoritative.");
  await drawer.getByRole("button", { name: "Save follow-up" }).click();
  await expect(drawer.getByText(/Saved locally/)).toBeVisible();
  await page.keyboard.press("Escape");

  // Source-row explorer shows the six excluded raw rows by default.
  const explorer = page.locator("details", { hasText: "Source-row explorer" });
  await explorer.getByText(/Source-row explorer/).click();
  await expect(explorer.locator("tr.row-excluded")).toHaveCount(6);

  await page.goto("/reviews?case=environment");
  await expect(page.getByRole("cell", { name: "DosTel1 (no participant)" })).toBeVisible();
  await expect(page.getByLabel("Participant")).toHaveCount(0);
});
