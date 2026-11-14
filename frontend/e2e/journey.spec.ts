import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { isolate } from "./helpers";

const NOTE = "Request repeat measurement / discuss with qualified medical staff";
const CMP_SHA = "5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9";

test("T17–T19, T23, T26–T27: C001 L-3 creatinine → evidence → explain → save → reload → export, network-isolated", async ({ page }) => {
  const external = await isolate(page);
  const t0 = Date.now();
  await page.goto("/");
  await page.getByRole("link", { name: "Launch Workspace" }).first().click();
  await expect(page).toHaveURL(/\/overview\?participant=C001&sample=L-3/);
  await expect(page.getByRole("heading", { name: "Health Overview", level: 1 })).toBeVisible();

  // Five real marker cards; creatinine flagged with text, not colour only.
  const creat = page.getByRole("article", { name: "Creatinine" });
  await expect(creat).toContainText("1.37");
  await expect(creat).toContainText("Outside supplied range · above upper bound");
  await expect(page.getByText("1 of 5 outside supplied range")).toBeVisible();

  await page.getByRole("button", { name: "Inspect result: Creatinine" }).click();
  const drawer = page.getByRole("dialog", { name: "Creatinine · C001 · L-3" });
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("1.2367 mg/dL (n = 3)");
  await expect(drawer).toContainText("Data row 1 (file line 2)");
  await expect(drawer).toContainText(CMP_SHA);

  for (const [i, q] of ["Explain this result", "How was this calculated?", "What can this dataset not tell us?"].entries()) {
    await drawer.getByRole("button", { name: q }).click();
    await expect(drawer.getByText(/deterministic template \(no language model\)/)).toHaveCount(i + 1);
  }
  // Typed question in the chat composer is routed to a verified template.
  await drawer.getByLabel("Ask a question about this result").fill("how was the baseline computed?");
  await page.keyboard.press("Enter");
  await expect(drawer.locator(".msg-user").last()).toHaveText("how was the baseline computed?");
  await expect(drawer.getByText(/Baseline: B = mean of available preflight values/).last()).toBeVisible();
  await drawer.getByRole("button", { name: "Did radiation cause this?" }).click();
  await expect(drawer).toContainText("No — the available data cannot support that claim.");
  await drawer.getByRole("button", { name: "Does this mean something is wrong?" }).click();
  await expect(drawer).toContainText("Insufficient evidence. CytoZoe does not diagnose");

  await drawer.getByLabel("Review status").selectOption("FOLLOW_UP_REQUESTED");
  await drawer.getByLabel(/Reviewer note/).fill(NOTE);
  await drawer.getByRole("button", { name: "Save follow-up" }).click();
  await expect(drawer.getByText(/Saved locally/)).toBeVisible();
  const elapsed = (Date.now() - t0) / 1000;
  test.info().annotations.push({ type: "scripted-journey-seconds", description: elapsed.toFixed(1) });

  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect(page.getByRole("button", { name: "Inspect result: Creatinine" })).toBeFocused();

  // T19: reload keeps note and status.
  await page.reload();
  await expect(page.getByRole("article", { name: "Creatinine" })).toContainText("Follow-up requested");

  // Review Log + export preview and downloads.
  await page.getByRole("link", { name: /Review Log/ }).first().click();
  // The live sidebar already lists it.
  await expect(page.getByRole("complementary").getByRole("button", { name: /Creatinine · C001 · L-3/ })).toBeVisible();
  await page.getByRole("main").getByRole("button", { name: "Creatinine · C001 · L-3", exact: true }).click();
  const rv = page.getByRole("dialog");
  await expect(rv.locator(".note-text")).toHaveText(NOTE);
  await expect(rv.getByText("Created")).toBeVisible();
  await page.keyboard.press("Escape");

  await expect(page.getByText(/Health section:.*1 review/)).toBeVisible();
  const [html] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Download HTML" }).click()]);
  const htmlText = readFileSync((await html.path())!, "utf8");
  expect(htmlText).toContain(NOTE.replace("/", "/"));
  expect(htmlText).toContain(CMP_SHA);
  expect(htmlText).toContain("has not been sent anywhere");
  const [json] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Download JSON" }).click()]);
  const packet = JSON.parse(readFileSync((await json.path())!, "utf8"));
  expect(packet.health.reviews[0].note).toBe(NOTE);
  expect(packet.health.reviews[0].evidence_snapshot.measurement.value).toBe(1.37);
  expect(packet.datasets.map((d: { sha256: string }) => d.sha256)).toContain(CMP_SHA);

  // Every route works with external network blocked.
  for (const path of ["/overview", "/health", "/environment", "/reviews"]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.getByText("Local service connected")).toBeVisible();
  }
  expect(external, `external requests attempted: ${external.join(", ")}`).toEqual([]);
});

test("Health Trends: categorical visits, URL state, inline follow-up keeps the measurement visible", async ({ page }) => {
  await isolate(page);
  await page.goto("/health?participant=C001&sample=R%2B1&marker=glucose");
  await expect(page.getByRole("tab", { name: "Glucose" })).toHaveAttribute("aria-selected", "true");
  const panel = page.getByRole("region", { name: "Evidence" });
  await expect(panel).toContainText("90");
  await expect(panel).toContainText("77.3333 mg/dL (n = 3)");
  await expect(panel).toContainText("+12.6667 mg/dL (+16.38%)");
  await expect(panel).toContainText("Within supplied range");

  await page.getByText(/Data table · 7 source values/).click();
  const rows = page.locator("table.data tbody tr button");
  await expect(rows).toHaveText(["L-92 · Preflight", "L-44 · Preflight", "L-3 · Preflight", "R+1 · Postflight", "R+45 · Postflight", "R+82 · Postflight", "R+194 · Postflight"]);
  await page.getByRole("button", { name: "Select visit R+45 · Postflight" }).click();
  await expect(page).toHaveURL(/sample=R%2B45/);

  await page.getByRole("tab", { name: "Glucose" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/marker=sodium/);
  await page.goBack();
  await expect(page).toHaveURL(/marker=glucose/);

  await page.getByRole("button", { name: "Record follow-up" }).click();
  await expect(panel.getByLabel(/Reviewer note/)).toBeFocused();
  await expect(panel.locator(".ev-big")).toBeVisible();

  // Invalid params fall back visibly to a valid selection.
  await page.goto("/health?participant=C999&sample=X&marker=bogus");
  await expect(page.getByText(/is not in this dataset/)).toBeVisible();
  await expect(page).toHaveURL(/participant=C001/);
});
