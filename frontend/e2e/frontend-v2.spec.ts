import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { isolate } from "./helpers";

const fmt = (v: number, d = 4) => { const s = v.toFixed(d); return s.includes(".") ? s.replace(/\.?0+$/, "") : s; };

test("F6 landing: local imagery, no API calls, credits, accessible, CTA opens the workspace", async ({ page }) => {
  const external = await isolate(page);
  const api: string[] = [];
  const media: { url: string; type: string; status: number }[] = [];
  page.on("request", (r) => { if (new URL(r.url()).pathname.startsWith("/api/")) api.push(r.url()); });
  page.on("response", (r) => { if (new URL(r.url()).pathname.startsWith("/media/")) media.push({ url: r.url(), type: r.headers()["content-type"] ?? "", status: r.status() }); });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Understand the change. Keep the evidence.");
  await expect(page.getByText("Independent research prototype").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Photo & data credits" })).toBeVisible();
  await expect(page.getByText(/Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center/)).toBeVisible();
  await expect(page.getByText(/Not affiliated with or endorsed by NASA/)).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(media.length).toBeGreaterThan(0);
  for (const m of media) {
    expect(m.status, m.url).toBe(200);
    expect(m.type, m.url).toMatch(/^image\/(avif|webp)/);
  }
  const hero = page.locator(".l-hero-media img");
  expect(await hero.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes[0]?.target.join(" ")}`)).toEqual([]);
  expect(api, "the introduction must not call the API").toEqual([]);

  await page.getByRole("link", { name: "Explore the system" }).click();
  await expect(page).toHaveURL(/#how$/);
  await page.getByRole("link", { name: "Launch Workspace" }).first().click();
  await expect(page.getByRole("heading", { name: "Health Overview", level: 1 })).toBeVisible();
  expect(external).toEqual([]);
});

test("F2 Mission Brief renders exactly the backend payload for all 28 samples", async ({ page, request }) => {
  await isolate(page);
  const participants = await (await request.get("/api/participants")).json() as { participant_id: string; samples: { visit: string }[] }[];
  let samples = 0;
  for (const p of participants) {
    for (const s of p.samples) {
      const brief = await (await request.get(`/api/mission/brief?participant=${p.participant_id}&sample=${encodeURIComponent(s.visit)}&mode=historical`)).json();
      await page.goto(`/overview?participant=${p.participant_id}&sample=${encodeURIComponent(s.visit)}`);
      const panel = page.getByRole("region", { name: new RegExp(`${p.participant_id} · ${s.visit.replace(/[+]/g, "[+]")}`) });
      await expect(panel.locator(".brief-summary")).toHaveText(brief.summary.text);
      await expect(panel.locator(".brief-item")).toHaveCount(brief.findings.length);
      for (const f of brief.findings) {
        const ev = await (await request.get(`/api/evidence/${encodeURIComponent(f.evidence_id)}`)).json();
        expect(f.value).toBe(ev.measurement.value);               // brief == evidence (same number, unrounded)
        expect(f.source.source_row).toBe(ev.source.source_row);
        const item = panel.locator(".brief-item").filter({ hasText: f.marker_name });
        await expect(item.locator(".brief-value")).toContainText(fmt(f.value));
        await expect(item).toContainText(f.explanation.compared_with);
        await expect(item).toContainText(`Data row ${f.source.source_row} (file line ${f.source.file_line})`);
        await expect(item).toContainText(f.source.source_column);
      }
      await expect(panel.locator(".brief-table tbody tr")).toHaveCount(brief.other_measurements.length);
      await expect(panel).toContainText(brief.dataset.sha256);
      samples++;
    }
  }
  expect(samples).toBe(28);
});

test("F2 brief follow-up opens the shared evidence drawer on the note field", async ({ page }) => {
  await isolate(page);
  await page.goto("/overview?participant=C001&sample=L-3");
  const panel = page.getByRole("region", { name: /Mission Health Intelligence Brief|C001 · L-3/ });
  await expect(panel.getByText("Verified NASA snapshot")).toBeVisible();
  await panel.getByRole("button", { name: "Record follow-up: Creatinine (Mission Brief)" }).click();
  const drawer = page.getByRole("dialog", { name: "Creatinine · C001 · L-3" });
  await expect(drawer.getByLabel(/Reviewer note/)).toBeFocused();
  await expect(drawer).toContainText("Verified NASA snapshot (SHA-256 matches the registered manifest)");
  await page.keyboard.press("Escape");
  await expect(panel.getByRole("button", { name: "Record follow-up: Creatinine (Mission Brief)" })).toBeFocused();
});

test("F3 Health Trends separates the retrospective and the replay (prior-visits-only) baselines", async ({ page }) => {
  await isolate(page);
  await page.goto("/health?participant=C001&sample=L-3&marker=creatinine");
  const card = page.getByRole("region", { name: /Baseline comparison/ });
  const retro = card.locator(".baseline-tile").first();
  const prior = card.locator(".baseline-tile.replay");
  await expect(retro).toContainText("1.2367 mg/dL");
  await expect(retro).toContainText("n = 3 · L-92, L-44, L-3");
  await expect(prior).toContainText("1.17 mg/dL");
  await expect(prior).toContainText("n = 2 · L-92, L-44");
  await expect(card).toContainText("retrospective mean includes the visit's own value");
  // First visit: nothing is known before it, so nothing is shown.
  await page.goto("/health?participant=C001&sample=L-92&marker=creatinine");
  await expect(prior).toContainText("Not available");
  await expect(prior).toContainText("no earlier preflight visit");
});
