// One-time setup on any OS: Python venv + backend deps, frontend deps + build, NASA data fetch/verify/import.
// Usage from the repo root:  npm run setup
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const win = process.platform === "win32";
const venvPython = join(root, ".venv", win ? "Scripts/python.exe" : "bin/python");

function step(title, cmd, args, cwd = root) {
  console.log(`\n▶ ${title}`);
  const r = spawnSync(cmd, args, { cwd, stdio: "inherit", shell: win && cmd === "npm" });
  if (r.status !== 0) {
    console.error(`\n✖ Failed: ${title}`);
    process.exit(r.status ?? 1);
  }
}

if (!existsSync(venvPython)) {
  const sysPython = win ? "python" : "python3";
  step("Create Python virtual environment (.venv)", sysPython, ["-m", "venv", ".venv"]);
}
step("Install backend packages", venvPython, ["-m", "pip", "install", "-q", "-e", "./backend[dev]"]);
step("Install frontend packages", "npm", ["ci"], join(root, "frontend"));
step("Build the interface", "npm", ["run", "build"], join(root, "frontend"));
step("Download NASA source files (one time)", venvPython, ["scripts/fetch_data.py", "--all"]);
step("Verify SHA-256 and schemas", venvPython, ["scripts/verify_data.py", "--strict"]);
step("Import into the local database", venvPython, ["scripts/import_data.py", "--all"]);
console.log("\n✔ Setup complete.\n  Development:  npm run dev    → http://127.0.0.1:5173\n  Demo/offline: npm start      → http://127.0.0.1:8000\n");
