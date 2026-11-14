// B21 launcher smoke test: real `scripts/dev.mjs` start → ready → clean teardown (no orphans), and safe port refusal.
// Usage (repo root, setup already done, ports 8000/5173 free):  node tests/launcher/launcher.test.mjs
import { spawn } from "node:child_process";
import http from "node:http";
import net from "node:net";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const get = (url) => new Promise((done) => {
  const req = http.get(url, { timeout: 1500 }, (res) => { let b = ""; res.on("data", (c) => (b += c)); res.on("end", () => done({ status: res.statusCode, body: b })); });
  req.on("error", () => done(null)); req.on("timeout", () => { req.destroy(); done(null); });
});
const portFree = (p) => new Promise((done) => {
  const s = net.createServer(); s.once("error", () => done(false)); s.once("listening", () => s.close(() => done(true))); s.listen(p, "127.0.0.1");
});
let failures = 0;
const check = (name, ok, extra = "") => { console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? `  (${extra})` : ""}`); if (!ok) failures++; };

function startDev() {
  const p = spawn(process.execPath, [join(ROOT, "scripts", "dev.mjs")], { cwd: ROOT, stdio: ["pipe", "pipe", "pipe"] });
  let out = "";
  p.stdout.on("data", (d) => (out += d)); p.stderr.on("data", (d) => (out += d));
  return { p, out: () => out, exited: new Promise((r) => p.on("exit", (c) => r(c))) };
}

// 1. Clean start → ready → q → no orphan processes.
check("ports 8000/5173 free before test", (await portFree(8000)) && (await portFree(5173)));
const run = startDev();
let web = null;
for (let i = 0; i < 120 && !web; i++) { web = await get("http://127.0.0.1:5173/"); if (!web) await sleep(500); }
check("interface answers on :5173", web?.status === 200);
const proxied = await get("http://127.0.0.1:5173/api/readyz");
check("API reachable through the dev proxy and READY", proxied?.status === 200 && JSON.parse(proxied.body).state === "READY");
check("launcher reported real readiness", /API ready: database, migrations and verified NASA datasets OK/.test(run.out()));
run.p.stdin.write("q\n");
const code = await Promise.race([run.exited, sleep(15000).then(() => "timeout")]);
check("launcher exits on 'q'", code !== "timeout", `exit ${code}`);
await sleep(1500);
check("no orphan on :8000 after teardown", await portFree(8000));
check("no orphan on :5173 after teardown", await portFree(5173));

// 2. A foreign program on :8000 must be refused, never reused or killed.
const foreign = http.createServer((_, res) => { res.writeHead(200, { "content-type": "application/json" }); res.end('{"app":"something-else"}'); });
await new Promise((r) => foreign.listen(8000, "127.0.0.1", r));
const run2 = startDev();
const code2 = await Promise.race([run2.exited, sleep(20000).then(() => "timeout")]);
check("refuses a foreign program on :8000 with exit 1", code2 === 1, `exit ${code2}`);
check("explains the port conflict", /Port 8000 is used by another program/.test(run2.out()));
const stillThere = await get("http://127.0.0.1:8000/");
check("foreign program was not killed", stillThere?.body?.includes("something-else"));
foreign.close();
if (code2 === "timeout") run2.p.kill();

// 3. `npm start` (scripts/start.mjs): one-origin production server → READY → q → no orphan.
await sleep(500);
const s = spawn(process.execPath, [join(ROOT, "scripts", "start.mjs")], { cwd: ROOT, stdio: ["pipe", "pipe", "pipe"] });
let sout = ""; s.stdout.on("data", (d) => (sout += d)); s.stderr.on("data", (d) => (sout += d));
const sExit = new Promise((r) => s.on("exit", (c) => r(c)));
let page = null;
for (let i = 0; i < 80 && !/ready →|NOT ready/.test(sout); i++) await sleep(250);
page = await get("http://127.0.0.1:8000/overview");
check("npm start serves the built interface on :8000", page?.status === 200 && page.body.includes('id="root"'));
check("npm start reports READY", /CytoZoe ready → http:\/\/127\.0\.0\.1:8000/.test(sout));
s.stdin.write("q\n");
const sCode = await Promise.race([sExit, sleep(15000).then(() => "timeout")]);
await sleep(1000);
check("npm start stops on 'q' and frees :8000", sCode !== "timeout" && (await portFree(8000)), `exit ${sCode}`);

console.log(failures ? `\n${failures} launcher check(s) FAILED` : "\nAll launcher checks passed");
process.exit(failures ? 1 : 0);
