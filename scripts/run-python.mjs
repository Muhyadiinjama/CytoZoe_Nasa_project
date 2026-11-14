// Run a command with the project's virtual-environment Python, on any OS.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const python = join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
if (!existsSync(python)) {
  console.error("\n✖ Python environment not found. Run the one-time setup first:  npm run setup\n");
  process.exit(1);
}
const res = spawnSync(python, process.argv.slice(2), { cwd: root, stdio: "inherit" });
process.exit(res.status ?? 1);
