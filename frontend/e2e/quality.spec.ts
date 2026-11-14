import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { isolate } from "./helpers";

const ROUTES = [
  ["overview", "/overview?participant=C001&sample=L-3"],
  ["health", "/health?participant=C001&sample=L-3&marker=creatinine"],
  ["environment", "/environment"],
  ["reviews", "/reviews"],
] as const;

test("T28/UX-01: automated axe checks on all four routes and the drawer (WCAG 2.x A/AA rules)", async ({ page }) => {
  await isolate(page);
  const findings: string[] = [];
  for (const [, path] of ROUTES) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    await page.waitForLoadState("networkidle");
    const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
    for (const v of r.violations) findings.push(`${path}: ${v.id} (${v.impact}) × ${v.nodes.length} — ${v.nodes[0]?.target.join(" ")}`);
  }
  await page.goto("/overview?participant=C001&sample=L-3");
  await page.getByRole("button", { name: "Inspect result: Creatinine" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Explain this result" }).click();
  const d = await new AxeBuilder({ page }).include(".drawer").withTags(["wcag2a", "wcag2aa"]).analyze();
  for (const v of d.violations) findings.push(`drawer: ${v.id} (${v.impact}) × ${v.nodes.length}`);
  expect(findings, findings.join("\n")).toEqual([]);
});

test("T28: keyboard-only core journey with focus trap and focus restore", async ({ page }) => {
  await isolate(page);
  await page.goto("/overview?participant=C002&sample=R%2B45");
  // Skip link is the first tab stop.
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  const inspect = page.getByRole("button", { name: "Inspect result: Glucose" });
  await inspect.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { level: 2 })).toBeFocused();
  for (let i = 0; i < 60; i++) {
    await page.keyboard.press("Tab");
    const inside = await page.evaluate(() => !!document.activeElement?.closest(".drawer"));
    expect(inside).toBe(true);
  }
  await dialog.getByLabel(/Reviewer note/).focus();
  await page.keyboard.type("Keyboard-only note");
  // Tab forward (through the date field's own sub-fields) until the Save button has focus.
  const save = dialog.getByRole("button", { name: "Save follow-up" });
  for (let i = 0; i < 8 && !(await save.evaluate((el) => el === document.activeElement)); i++) await page.keyboard.press("Tab");
  await expect(save).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(dialog.getByText(/Saved locally/)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(inspect).toBeFocused();
});

test("T29: responsive layouts at 390/768/1024/1440 px without horizontal page scroll", async ({ page }) => {
  await isolate(page);
  mkdirSync("../docs/screenshots", { recursive: true });
  for (const width of [390, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [name, path] of ROUTES) {
      await page.goto(path);
      await expect(page.locator("h1")).toBeVisible();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(250);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${name} @ ${width}px overflows by ${overflow}px`).toBeLessThanOrEqual(0);
      await page.screenshot({ path: `../docs/screenshots/${name}-${width}.png`, fullPage: true });
    }
  }
  // Mobile menu works.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/overview");
  await page.getByRole("button", { name: "Open navigation menu" }).click();
  await page.getByRole("link", { name: /Radiation Review/ }).click();
  await expect(page.getByRole("heading", { name: "Radiation Review", level: 1 })).toBeVisible();
});

test("T30: service-unavailable and no-data states never fabricate content", async ({ page }) => {
  await page.route("**/api/status", (r) => r.abort("connectionrefused"));
  await page.goto("/overview");
  await expect(page.getByRole("heading", { name: "Local service unavailable" })).toBeVisible();
  await expect(page.locator(".metric")).toHaveCount(0);
  await page.unroute("**/api/status");
  await page.route("**/api/status", async (r) => {
    const res = await r.fetch();
    const body = await res.json();
    await r.fulfill({ json: { ...body, ready: { health: false, environment: false } } });
  });
  await page.goto("/overview");
  await expect(page.getByRole("heading", { name: "No research data imported yet" })).toBeVisible();
});

test("T21: stale second tab gets a 409 conflict and keeps its draft", async ({ browser }) => {
  const ctx = await browser.newContext();
  const a = await ctx.newPage();
  const b = await ctx.newPage();
  const url = "/health?participant=C004&sample=R%2B45&marker=potassium";
  await a.goto(url);
  await a.getByRole("button", { name: "Record follow-up" }).click();
  await a.getByLabel(/Reviewer note/).fill("First version");
  await a.getByRole("button", { name: "Save follow-up" }).click();
  await expect(a.getByText(/Saved locally/)).toBeVisible();

  await b.goto(url);
  await b.getByRole("button", { name: "Update follow-up" }).click();
  // B starts a draft; A then saves. Live sync must not silently rebase B's draft.
  await b.getByLabel(/Reviewer note/).fill("Stale draft from tab B");
  await a.getByLabel(/Reviewer note/).fill("Second version from tab A");
  await a.getByRole("button", { name: "Save changes" }).click();
  await expect(a.getByText(/Saved locally/)).toBeVisible();
  await expect(b.getByText(/in another window/)).toBeVisible();

  await b.getByRole("button", { name: "Save changes" }).click();
  await expect(b.getByText(/changed elsewhere/)).toBeVisible();
  await expect(b.getByLabel(/Reviewer note/)).toHaveValue("Stale draft from tab B");
  await b.getByRole("button", { name: "Keep my draft, then save again" }).click();
  await b.getByRole("button", { name: "Save changes" }).click();
  await expect(b.getByText(/Saved locally/)).toBeVisible();
  await ctx.close();
});
