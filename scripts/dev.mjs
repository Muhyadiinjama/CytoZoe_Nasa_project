#!/usr/bin/env node
/**
 * One-command development runner for CytoZoe.
 *
 * Usage:
 *   npm run dev              # auto-setup (if needed) + run FastAPI (:8000) & Vite (:5173) together
 *   npm run dev -- --setup   # force full setup before starting
 *   npm run setup            # run one-time setup only
 */
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import http from "node:http";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const FRONTEND_DIR = join(ROOT, "frontend");
const IS_WIN = process.platform === "win32";
const VENV_PY = IS_WIN
  ? join(ROOT, ".venv", "Scripts", "python.exe")
  : join(ROOT, ".venv", "bin", "python");
const VITE_BIN = join(
  FRONTEND_DIR,
  "node_modules",
  ".bin",
  IS_WIN ? "vite.cmd" : "vite"
);
const DB_PATH = join(ROOT, "runtime", "cytozoe.sqlite");
const DIST_INDEX = join(FRONTEND_DIR, "dist", "index.html");

const args = new Set(process.argv.slice(2));
const forceSetup = args.has("--setup");
const setupOnly = args.has("--setup-only");

function log(tag, msg) {
  console.log(`[${tag}] ${msg}`);
}

function runSync(cmd, cmdArgs, cwd = ROOT, shell = false) {
  const res = spawnSync(cmd, cmdArgs, {
    cwd,
    stdio: "inherit",
    shell,
  });
  if (res.status !== 0) {
    process.exit(res.status ?? 1);
  }
}

function hasBackendDeps() {
  if (!existsSync(VENV_PY)) return false;
  const check = spawnSync(VENV_PY, ["-c", "import fastapi, uvicorn, pandas"], {
    cwd: ROOT,
    stdio: "ignore",
  });
  return check.status === 0;
}

function ensureSetup() {
  // 1. Python venv + backend package
  if (forceSetup || !hasBackendDeps()) {
    if (!existsSync(VENV_PY)) {
      log("setup", "Creating Python virtual environment (.venv)...");
      const sysPy = IS_WIN ? "python" : "python3";
      runSync(sysPy, ["-m", "venv", ".venv"]);
    }
    log("setup", "Installing backend dependencies...");
    runSync(VENV_PY, ["-m", "pip", "install", "--upgrade", "pip"]);
    runSync(VENV_PY, ["-m", "pip", "install", "-e", "./backend[dev]"]);
  }

  // 2. Frontend node_modules
  if (forceSetup || !existsSync(VITE_BIN)) {
    log("setup", "Installing frontend dependencies (npm ci)...");
    runSync("npm", ["ci"], FRONTEND_DIR, IS_WIN);
  }

  // 3. Frontend initial build so http://127.0.0.1:8000 also works out of the box
  if (forceSetup || !existsSync(DIST_INDEX)) {
    log("setup", "Building frontend bundle (frontend/dist)...");
    runSync("npm", ["run", "build"], FRONTEND_DIR, IS_WIN);
  }

  // 4. NASA datasets + SQLite import
  if (forceSetup || !existsSync(DB_PATH)) {
    log("setup", "Fetching, verifying, and importing pinned NASA datasets...");
    runSync(VENV_PY, ["scripts/fetch_data.py", "--all"]);
    runSync(VENV_PY, ["scripts/verify_data.py", "--strict"]);
    runSync(VENV_PY, ["scripts/import_data.py", "--all"]);
  }
}

function checkPortReady(url, timeoutMs = 1500) {
  return new Promise((resolveReady) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      res.resume();
      resolveReady(res.statusCode === 200);
    });
    req.on("error", () => resolveReady(false));
    req.on("timeout", () => {
      req.destroy();
      resolveReady(false);
    });
  });
}

async function waitForBackend(url, maxWaitMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    if (await checkPortReady(url)) return true;
    await new Promise((r) => setTimeout(r, 250));
  }
  return false;
}

function prefixStream(stream, prefix, target) {
  let buf = "";
  stream.on("data", (chunk) => {
    buf += chunk.toString();
    const lines = buf.split(/\r?\n/);
    buf = lines.pop() ?? "";
    for (const line of lines) {
      target.write(`[${prefix}] ${line}\n`);
    }
  });
  stream.on("end", () => {
    if (buf.length > 0) {
      target.write(`[${prefix}] ${buf}\n`);
    }
  });
}

async function main() {
  ensureSetup();
  if (setupOnly) {
    log("setup", "Setup complete.");
    return;
  }

  const children = [];
  let shuttingDown = false;

  const shutdown = (code = 0) => {
    if (shuttingDown) return;
    shuttingDown = true;
    for (const child of children) {
      if (!child.killed) {
        child.kill("SIGTERM");
      }
    }
    setTimeout(() => process.exit(code), 200);
  };

  process.on("SIGINT", () => shutdown(0));
  process.on("SIGTERM", () => shutdown(0));

  const apiAlreadyUp = await checkPortReady("http://127.0.0.1:8000/api/status");
  if (apiAlreadyUp) {
    log("dev", "Backend already running at http://127.0.0.1:8000 — reusing it.");
  } else {
    log("dev", "Starting FastAPI backend at http://127.0.0.1:8000 ...");
    const backend = spawn(
      VENV_PY,
      [
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        "backend",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload",
      ],
      { cwd: ROOT, stdio: ["ignore", "pipe", "pipe"] }
    );
    children.push(backend);
    prefixStream(backend.stdout, "api", process.stdout);
    prefixStream(backend.stderr, "api", process.stderr);
    backend.on("exit", (code) => {
      if (!shuttingDown) {
        log("api", `Backend exited (code ${code ?? 0}). Stopping dev runner.`);
        shutdown(code ?? 1);
      }
    });

    const ready = await waitForBackend("http://127.0.0.1:8000/api/status");
    if (!ready) {
      log("dev", "Backend failed to become ready on http://127.0.0.1:8000");
      shutdown(1);
      return;
    }
  }

  log("dev", "Starting Vite dev server at http://127.0.0.1:5173 ...");
  const frontend = spawn(VITE_BIN, [], {
    cwd: FRONTEND_DIR,
    stdio: ["inherit", "pipe", "pipe"],
    shell: IS_WIN,
  });
  children.push(frontend);
  prefixStream(frontend.stdout, "web", process.stdout);
  prefixStream(frontend.stderr, "web", process.stderr);
  frontend.on("exit", (code) => {
    if (!shuttingDown) {
      shutdown(code ?? 0);
    }
  });
}

main();
