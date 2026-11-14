#!/usr/bin/env node
/**
 * Production / demo start: the built app on ONE origin, http://127.0.0.1:8000 (loopback only, works offline).
 *   npm start           (requires a prior `npm run setup` or `npm run build`)
 * Never downloads anything. Stop with Ctrl+C or q + Enter; the server process tree is always terminated.
 */
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import http from "node:http";
import net from "node:net";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const IS_WIN = process.platform === "win32";
const PY = IS_WIN ? join(ROOT, ".venv", "Scripts", "python.exe") : join(ROOT, ".venv", "bin", "python");
const PORT = Number(process.env.CYTOZOE_PORT ?? 8000);
const fail = (m) => { console.error(`\n[start] ✖ ${m}\n`); process.exit(1); };

if (!existsSync(PY)) fail("Python environment missing. Run once: npm run setup");
if (!existsSync(join(ROOT, "frontend", "dist", "index.html"))) fail("Interface not built. Run: npm run build");

const getJson = (url) => new Promise((done) => {
  const req = http.get(url, { timeout: 1500 }, (res) => {
    let b = ""; res.on("data", (c) => (b += c));
    res.on("end", () => { try { done({ status: res.statusCode, json: JSON.parse(b) }); } catch { done({ status: res.statusCode, json: null }); } });
  });
  req.on("error", () => done(null)); req.on("timeout", () => { req.destroy(); done(null); });
});
const portFree = (p) => new Promise((done) => {
  const s = net.createServer(); s.once("error", () => done(false)); s.once("listening", () => s.close(() => done(true))); s.listen(p, "127.0.0.1");
});

if (!(await portFree(PORT))) {
  const who = await getJson(`http://127.0.0.1:${PORT}/api/healthz`);
  fail(who?.json?.app === "CytoZoe" ? `CytoZoe is already running at http://127.0.0.1:${PORT}` : `Port ${PORT} is used by another program.`);
}

const child = spawn(PY, ["-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", String(PORT)],
  { cwd: ROOT, stdio: ["ignore", "inherit", "inherit"], env: { ...process.env, CYTOZOE_REQUIRE_FRONTEND: "1" }, detached: !IS_WIN });
const kill = () => {
  if (child.exitCode !== null) return;
  if (IS_WIN) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  else { try { process.kill(-child.pid, "SIGTERM"); } catch { child.kill(); } }
};
let stopping = false;
const stop = () => { if (stopping) return; stopping = true; kill(); setTimeout(() => process.exit(0), 300); };
process.on("SIGINT", stop); process.on("SIGTERM", stop); process.on("exit", kill);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { if (String(d).trim().toLowerCase() === "q") stop(); });
child.on("exit", (c) => { if (!stopping) { console.error(`[start] server exited (code ${c})`); process.exit(c || 1); } });

for (let i = 0; i < 80; i++) {
  if (await getJson(`http://127.0.0.1:${PORT}/api/healthz`)) break;
  await new Promise((r) => setTimeout(r, 250));
}
const ready = await getJson(`http://127.0.0.1:${PORT}/api/readyz`);
if (ready?.status === 200) console.log(`\n  ✔ CytoZoe ready → http://127.0.0.1:${PORT}   ·  Stop: Ctrl+C or q + Enter\n`);
else {
  const f = ready?.json?.checks?.find((c) => !c.ok);
  console.log(`\n  ⚠ Server is up but NOT ready (${ready?.json?.state ?? "unreachable"}): ${f?.detail ?? "see /api/readyz"}\n`);
}
