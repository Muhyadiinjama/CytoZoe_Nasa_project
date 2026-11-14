import { defineConfig } from "@playwright/test";
import { join } from "node:path";

// Uses the locally installed Microsoft Edge (channel "msedge"), so no browser download is needed.
// Set PW_CHANNEL=chrome (or "chromium" after `npx playwright install chromium`) on other machines.
const python = process.platform === "win32" ? join("..", ".venv", "Scripts", "python.exe") : join("..", ".venv", "bin", "python");
const channel = process.env.PW_CHANNEL ?? (process.platform === "win32" ? "msedge" : "chrome");

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  outputDir: "../test-results",
  use: {
    baseURL: "http://127.0.0.1:8010",
    channel: channel === "chromium" ? undefined : channel,
    acceptDownloads: true,
    trace: "off",
  },
  webServer: {
    command: `${python} ../scripts/e2e_server.py --port 8010 --fresh`,
    url: "http://127.0.0.1:8010/api/status",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
