#!/usr/bin/env node
/**
 * One-command development runner for CytoZoe.
 *
 * Usage:
 *   npm run dev              # auto-setup (if needed) + run FastAPI (:8000) & Vite (:5173) together
 *   npm run dev -- --setup   # force full setup before starting
 *   npm run setup            # run one-time setup only
 *
 * Stop with Ctrl+C, or type q + Enter. Child process trees are terminated on every OS (no orphans).
 * Network is used only during first-time setup; with dependencies and data staged it never downloads.
 */
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import http from "node:http";
import net from "node:net";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const FRONTEND_DIR = join(ROOT, "frontend");
const IS_WIN = process.platform === "win32";
const VENV_PY = IS_WIN ? join(ROOT, ".venv", "Scripts", "python.exe") : join(ROOT, ".venv", "bin", "python");
// Run Vite's JS entry with this Node binary: one real process (no cmd.exe shim) that we can terminate reliably.
const VITE_JS = join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js");
const DB_PATH = join(process.env.CYTOZOE_DATA_DIR ?? join(ROOT, "runtime"), "cytozoe.sqlite");
const DIST_INDEX = join(FRONTEND_DIR, "dist", "index.html");
const API = "http://127.0.0.1:8000";

const args = new Set(process.argv.slice(2));
const forceSetup = args.has("--setup");
const setupOnly = args.has("--setup-only");

const log = (tag, msg) => console.log(`[${tag}] ${msg}`);
const fail = (msg) => {
  console.error(`\n[dev] ✖ ${msg}\n`);
  process.exit(1);
};

function runSync(title, cmd, cmdArgs, cwd = ROOT, shell = false) {
  log("setup", title);
  const res = spawnSync(cmd, cmdArgs, { cwd, stdio: "inherit", shell });
  if (res.error?.code === "ENOENT") fail(`'${cmd}' was not found. Install it and re-run (see README "Quick start").`);
  if (res.status !== 0) fail(`Setup step failed: ${title} (exit ${res.status}). Fix the error above and re-run.`);
}

function hasBackendDeps() {
  if (!existsSync(VENV_PY)) return false;
  return spawnSync(VENV_PY, ["-c", "import fastapi, uvicorn, pandas"], { cwd: ROOT, stdio: "ignore" }).status === 0;
}

function ensureSetup() {
  const nodeMajor = Number(process.versions.node.split(".")[0]);
  if (nodeMajor < 20) fail(`Node.js ${process.versions.node} is too old; install Node.js 20 or newer.`);
  if (forceSetup || !hasBackendDeps()) {
    if (!existsSync(VENV_PY)) runSync("Creating Python virtual environment (.venv)…", IS_WIN ? "python" : "python3", ["-m", "venv", ".venv"]);
    runSync("Installing backend dependencies…", VENV_PY, ["-m", "pip", "install", "-q", "-e", "./backend[dev]"]);
  }
  if (forceSetup || !existsSync(VITE_JS)) runSync("Installing frontend dependencies (npm ci)…", "npm", ["ci"], FRONTEND_DIR, IS_WIN);
  if (forceSetup || !existsSync(DIST_INDEX)) runSync("Building frontend bundle (frontend/dist)…", "npm", ["run", "build"], FRONTEND_DIR, IS_WIN);
  if (forceSetup || !existsSync(DB_PATH)) {
    runSync("Fetching pinned NASA datasets (one-time, needs internet)…", VENV_PY, ["scripts/fetch_data.py", "--all"]);
    runSync("Verifying SHA-256 hashes and schemas…", VENV_PY, ["scripts/verify_data.py", "--strict"]);
    runSync("Importing into the local database…", VENV_PY, ["scripts/import_data.py", "--all"]);
  }
}

function getJson(url, timeoutMs = 1500) {
  return new Promise((done) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let body = "";
      res.on("data", (c) => (body += c));
      res.on("end", () => {
        try { done({ status: res.statusCode, json: JSON.parse(body) }); } catch { done({ status: res.statusCode, json: null }); }
      });
    });
    req.on("error", () => done(null));
    req.on("timeout", () => { req.destroy(); done(null); });
  });
}

function portFree(port) {
  return new Promise((done) => {
    const srv = net.createServer();
    srv.once("error", () => done(false));
    srv.once("listening", () => srv.close(() => done(true)));
    srv.listen(port, "127.0.0.1");
  });
}

/** Kill a child and all of its descendants. On Windows, signals don't reach grandchildren, so use taskkill /T. */
function killTree(child) {
  if (!child.pid || child.exitCode !== null) return;
  if (IS_WIN) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
  else {
    try { process.kill(-child.pid, "SIGTERM"); } catch { child.kill("SIGTERM"); }
  }
}

function prefixStream(stream, prefix, target) {
  let buf = "";
  stream.on("data", (chunk) => {
    buf += chunk.toString();
    const lines = buf.split(/\r?\n/);
    buf = lines.pop() ?? "";
    for (const line of lines) target.write(`[${prefix}] ${line}\n`);
  });
  stream.on("end", () => buf && target.write(`[${prefix}] ${buf}\n`));
}

async function main() {
  ensureSetup();
  if (setupOnly) return log("setup", "Setup complete. Start with: npm run dev");

  const children = [];
  let shuttingDown = false;
  const shutdown = (code = 0) => {
    if (shuttingDown) return;
    shuttingDown = true;
    log("dev", "Stopping…");
    for (const c of children) killTree(c);
    setTimeout(() => process.exit(code), 300);
  };
  process.on("SIGINT", () => shutdown(0));
  process.on("SIGTERM", () => shutdown(0));
  process.on("exit", () => children.forEach(killTree));
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (d) => { if (String(d).trim().toLowerCase() === "q") shutdown(0); });

  // Reuse port 8000 only if it is a CytoZoe backend; never hijack or kill another program.
  const existing = await getJson(`${API}/api/healthz`);
  if (existing) {
    if (existing.json?.app !== "CytoZoe") fail("Port 8000 is used by another program. Close it, then run npm run dev again.");
    log("dev", "A CytoZoe backend is already running on :8000 — reusing it.");
  } else {
    if (!(await portFree(8000))) fail("Port 8000 is busy. Close the program using it, then re-run.");
    log("dev", `Starting API at ${API} …`);
    const backend = spawn(VENV_PY, ["-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1",
      "--port", "8000", "--reload", "--reload-dir", "backend"], { cwd: ROOT, stdio: ["ignore", "pipe", "pipe"], detached: !IS_WIN });
    children.push(backend);
    prefixStream(backend.stdout, "api", process.stdout);
    prefixStream(backend.stderr, "api", process.stderr);
    backend.on("exit", (code) => { if (!shuttingDown) { log("api", `API exited (code ${code ?? 0}).`); shutdown(code || 1); } });
    let alive = false;
    for (let i = 0; i < 80 && !alive; i++) {
      alive = Boolean(await getJson(`${API}/api/healthz`));
      if (!alive) await new Promise((r) => setTimeout(r, 250));
    }
    if (!alive) { log("dev", "✖ API did not start within 20 s (see [api] lines above)."); return shutdown(1); }
  }

  // Report real readiness (DB, migrations, verified NASA data) — never claim "ready" when it is not.
  const ready = await getJson(`${API}/api/readyz`);
  if (ready?.status === 200) log("dev", "API ready: database, migrations and verified NASA datasets OK.");
  else {
    const failed = ready?.json?.checks?.find((c) => !c.ok);
    log("dev", `⚠ API is up but NOT ready: ${ready?.json?.state ?? "unknown"} — ${failed?.detail ?? "see /api/readyz"}`);
  }

  if (!(await portFree(5173))) { log("dev", "✖ Port 5173 is busy (another Vite?). Close it and re-run."); return shutdown(1); }
  log("dev", "Starting interface at http://127.0.0.1:5173 …");
  const frontend = spawn(process.execPath, [VITE_JS, "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
    { cwd: FRONTEND_DIR, stdio: ["ignore", "pipe", "pipe"], detached: !IS_WIN });
  children.push(frontend);
  prefixStream(frontend.stdout, "web", process.stdout);
  prefixStream(frontend.stderr, "web", process.stderr);
  frontend.on("exit", (code) => { if (!shuttingDown) shutdown(code ?? 0); });
  console.log("\n  ➜ Open http://127.0.0.1:5173   ·  Stop: Ctrl+C or type q + Enter\n");
}

main();
