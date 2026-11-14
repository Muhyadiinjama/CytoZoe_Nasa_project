// Start CytoZoe for development: FastAPI backend (auto-reload) + Vite frontend (hot reload), together.
// Usage from the repo root:  npm run dev      → open http://127.0.0.1:5173
// No extra npm packages needed. Works on Windows, macOS and Linux.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const win = process.platform === "win32";
const python = join(root, ".venv", win ? "Scripts/python.exe" : "bin/python");

function fail(msg) {
  console.error(`\n✖ ${msg}\n`);
  process.exit(1);
}
if (!existsSync(python)) fail("Python environment not found. Run the one-time setup first:  npm run setup");
if (!existsSync(join(root, "frontend", "node_modules"))) fail("Frontend packages not installed. Run:  npm run setup");
const db = join(process.env.CYTOZOE_DATA_DIR ?? join(root, "runtime"), "cytozoe.sqlite");
if (!existsSync(db)) {
  console.warn("\n⚠ No local database yet — the app will show 'No research data imported'.");
  console.warn("  Load the NASA data once with:  npm run data\n");
}

const procs = [];
function run(name, cmd, args, cwd) {
  const p = spawn(cmd, args, { cwd, stdio: ["ignore", "pipe", "pipe"], shell: false });
  const tag = name === "api" ? "\x1b[33m[api]\x1b[0m " : "\x1b[36m[web]\x1b[0m ";
  const pipe = (stream, out) => stream.on("data", (d) => String(d).split(/\r?\n/).filter(Boolean).forEach((l) => out.write(tag + l + "\n")));
  pipe(p.stdout, process.stdout);
  pipe(p.stderr, process.stderr);
  p.on("exit", (code) => {
    console.log(`${tag}stopped (exit ${code})`);
    shutdown(code ?? 0);
  });
  procs.push(p);
}
let closing = false;
function shutdown(code) {
  if (closing) return;
  closing = true;
  for (const p of procs) if (!p.killed) p.kill();
  setTimeout(() => process.exit(code), 300);
}
process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

run("api", python, ["-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000", "--reload", "--reload-dir", "backend"], root);
const viteBin = join(root, "frontend", "node_modules", "vite", "bin", "vite.js");
run("web", process.execPath, [viteBin, "--host", "127.0.0.1", "--port", "5173", "--strictPort"], join(root, "frontend"));

console.log("\n  CytoZoe dev servers starting…");
console.log("  ➜ Open  http://127.0.0.1:5173   (API on http://127.0.0.1:8000)");
console.log("  Press Ctrl+C to stop both.\n");
