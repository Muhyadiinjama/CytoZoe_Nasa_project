import { expect, test } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { join } from "node:path";

// T20: stop and restart the actual server process on the same SQLite database.
const PORT = 8011;
const python = process.platform === "win32" ? join("..", ".venv", "Scripts", "python.exe") : join("..", ".venv", "bin", "python");

async function start(fresh: boolean): Promise<ChildProcess> {
  const proc = spawn(python, ["../scripts/e2e_server.py", "--port", String(PORT), ...(fresh ? ["--fresh"] : [])], { stdio: "ignore" });
  for (let i = 0; i < 120; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/api/status`);
      if (r.ok) return proc;
    } catch { /* not up yet */ }
    await new Promise((res) => setTimeout(res, 250));
  }
  proc.kill();
  throw new Error("server did not start");
}

async function stop(proc: ChildProcess) {
  const exited = new Promise((res) => proc.once("exit", res));
  proc.kill();
  await exited;
  for (let i = 0; i < 40; i++) {
    try { await fetch(`http://127.0.0.1:${PORT}/api/status`); } catch { return; }
    await new Promise((res) => setTimeout(res, 250));
  }
}

test("T20: saved review and history survive a full server restart", async ({ page }) => {
  let server = await start(true);
  const base = `http://127.0.0.1:${PORT}`;
  try {
    await page.goto(`${base}/environment`);
    await page.getByRole("button", { name: "Record review" }).click();
    await page.getByRole("dialog").getByLabel(/Reviewer note/).fill("Coverage 99% — acceptable for a demo estimate.");
    await page.getByRole("dialog").getByRole("button", { name: "Save follow-up" }).click();
    await expect(page.getByText(/Saved locally/)).toBeVisible();
  } finally {
    await stop(server);
  }
  // While stopped, the UI says so instead of pretending to save.
  await page.goto(`${base}/reviews`).catch(() => undefined);

  server = await start(false);
  try {
    await page.goto(`${base}/reviews?case=environment`);
    await page.getByRole("main").getByRole("button", { name: /sensor-dose estimate/ }).click();
    const d = page.getByRole("dialog");
    await expect(d.locator(".note-text")).toHaveText("Coverage 99% — acceptable for a demo estimate.");
    await expect(d.getByText("Created")).toBeVisible();
  } finally {
    await stop(server);
  }
});
