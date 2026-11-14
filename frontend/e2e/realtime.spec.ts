import { expect, test } from "@playwright/test";
import { isolate } from "./helpers";

test("Radiation replay streams real readings in real time, surfaces conflicts, and pauses", async ({ page }) => {
  await isolate(page);
  await page.goto("/environment");
  const live = page.getByRole("region", { name: "Replay the day in real time" });
  await expect(live.getByText("Replay · recorded 1 March 2022 · not live")).toBeVisible();
  await live.getByLabel("Replay speed").selectOption("3600");
  await live.getByRole("button", { name: "Start replay" }).click();

  const clock = live.locator(".stat").filter({ hasText: "Source clock" }).locator(".stat-value");
  await expect(clock).not.toHaveText("—");
  const first = await clock.textContent();
  await page.waitForTimeout(1500);
  expect(await clock.textContent()).not.toBe(first); // values are advancing in real time

  // At 3600× the 09:15 conflict is reached after ~9 s of wall time.
  await expect(live.getByText(/Conflicting readings at 09:15:00/)).toBeVisible({ timeout: 20_000 });
  await live.getByRole("button", { name: "Pause replay" }).click();
  const paused = await clock.textContent();
  await page.waitForTimeout(1200);
  expect(await clock.textContent()).toBe(paused);

  // Resume continues from the same point rather than restarting.
  await live.getByRole("button", { name: "Resume replay" }).click();
  await page.waitForTimeout(800);
  expect((await clock.textContent())! >= paused!).toBe(true);
});

test("Health timeline replay drives the overview visit by visit", async ({ page }) => {
  await isolate(page);
  await page.goto("/overview?participant=C001&sample=R%2B194");
  const panel = page.getByRole("region", { name: "Replay C001's mission timeline" });
  await panel.getByLabel("Replay pace").selectOption("900");
  await panel.getByRole("button", { name: "Play timeline replay" }).click();
  await expect(page).toHaveURL(/sample=L-92/);
  await expect(page).toHaveURL(/sample=L-3/, { timeout: 10_000 });
  await expect(panel.getByText(/Creatinine 1.37 mg\/dL is above the supplied upper bound 1.35/)).toBeVisible();
  await expect(page.getByRole("article", { name: "Creatinine" })).toContainText("1.37");
  await expect(page).toHaveURL(/sample=R%2B194/, { timeout: 15_000 });
  await expect(panel.getByText("7 / 7 visits")).toBeVisible();
});

test("Live sync: a review saved in one window appears instantly in another", async ({ browser }) => {
  const ctx = await browser.newContext();
  const a = await ctx.newPage();
  const b = await ctx.newPage();
  await b.goto("/reviews");
  await expect(b.getByText("Live sync on")).toBeVisible();
  // Wait until the review list has finished loading (table caption or empty state) before counting rows.
  await b.locator("main table.data caption, main .empty").first().waitFor();
  const before = await b.locator("main table.data tbody tr").count();

  await a.goto("/overview?participant=C003&sample=R%2B1");
  await a.getByRole("button", { name: "Inspect result: Glucose" }).click();
  await a.getByRole("dialog").getByLabel(/Reviewer note/).fill("Live sync check from window A");
  await a.getByRole("dialog").getByRole("button", { name: "Save follow-up" }).click();
  await expect(a.getByRole("dialog").getByText(/Saved locally/)).toBeVisible();

  // Window B updates without a reload: toast, sidebar and table.
  await expect(b.getByText(/New review in another window: Glucose · C003 · R\+1/)).toBeVisible();
  await expect(b.getByRole("complementary").getByRole("button", { name: /Glucose · C003 · R\+1/ })).toBeVisible();
  await expect(b.locator("main table.data tbody tr")).toHaveCount(before + 1);
  await ctx.close();
});
