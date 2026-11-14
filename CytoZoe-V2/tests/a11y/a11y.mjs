// Automated accessibility audit of the running app. Run: node tests/a11y/a11y.mjs  (starts its own server)
// Checks: accessible names, duplicate ids, heading order, landmarks, text contrast (WCAG AA), 24 px targets, reflow at 320 px.
// Saves the accessibility tree per view to docs/a11y/*.aria.yaml. NOT a substitute for a real screen-reader pass.
import { createRequire } from 'node:module';
import { spawn, execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const pw = require('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const out = path.join(ROOT, 'docs', 'a11y'); mkdirSync(out, { recursive: true });
const findings = []; let checks = 0;
const issue = (where, what) => findings.push(`- **${where}**: ${what}`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const AUDIT = () => {
  const vis = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && !el.closest('[inert],[aria-hidden="true"]'); };
  const nameOf = el => {
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label').trim();
    if (el.getAttribute('aria-labelledby')) return el.getAttribute('aria-labelledby').split(/\s+/).map(i => (document.getElementById(i) || {}).textContent || '').join(' ').trim();
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l && l.textContent.trim()) return l.textContent.trim(); }
    const pl = el.closest('label'); if (pl && pl.textContent.trim()) return pl.textContent.trim();
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) return (el.getAttribute('title') || '').trim();
    return (el.textContent || el.getAttribute('title') || '').trim();
  };
  const res = { unnamed: [], dupIds: [], headings: [], contrast: [], small: [], landmarks: {}, imgs: [] };
  document.querySelectorAll('button, a[href], input, select, textarea, [role=button], [role=tab], [tabindex]:not([tabindex="-1"])').forEach(el => {
    if (!vis(el) && el.type !== 'file') return;
    if (!nameOf(el)) res.unnamed.push(el.outerHTML.slice(0, 120));
    const r = el.getBoundingClientRect();
    if (vis(el) && (r.width < 24 || r.height < 24) && !el.closest('svg')) res.small.push(`${el.tagName} "${nameOf(el).slice(0, 40)}" ${Math.round(r.width)}x${Math.round(r.height)}`);
  });
  const ids = {}; document.querySelectorAll('[id]').forEach(e => { ids[e.id] = (ids[e.id] || 0) + 1; });
  res.dupIds = Object.keys(ids).filter(k => ids[k] > 1);
  res.headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(h => !h.closest('[inert],[aria-hidden="true"]') && vis(h)).map(h => +h.tagName[1]);
  res.landmarks = { main: document.querySelectorAll('main').length, nav: document.querySelectorAll('nav').length };
  document.querySelectorAll('svg[role=img], [role=img]').forEach(e => { if (!e.getAttribute('aria-label')) res.imgs.push(e.outerHTML.slice(0, 80)); });
  const parse = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const blend = (fg, bg) => ({ r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1 });
  const bgOf = el => {
    const stack = []; let e = el;
    while (e && e.nodeType === 1) {
      if (e.tagName === 'svg' || e.closest && e.closest('svg') && e.tagName !== 'svg') { /* svg shapes: use the card behind */ }
      const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { stack.push(c); if (c.a >= 1) break; }
      e = e.parentElement;
    }
    let bg = { r: 255, g: 255, b: 255, a: 1 }; for (let i = stack.length - 1; i >= 0; i--) bg = blend(stack[i], bg); return bg;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const n = walker.currentNode; if (!n.textContent.trim()) continue;
    const el = n.parentElement; if (!el || seen.has(el) || !vis(el) || el.closest('script,style,title,option')) continue; seen.add(el);
    const cs = getComputedStyle(el);
    let fg = parse(el.closest('svg') ? (cs.fill && cs.fill !== 'none' ? cs.fill : cs.color) : cs.color); if (!fg) continue;
    const op = parseFloat(cs.opacity); if (op < 1) fg.a *= op;
    const bg = bgOf(el); const f = blend(fg, bg);
    const L1 = lum(f), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const size = parseFloat(cs.fontSize), bold = +cs.fontWeight >= 700;
    const need = (size >= 24 || (bold && size >= 18.66)) ? 3 : 4.5;
    if (ratio < need) res.contrast.push(`"${n.textContent.trim().slice(0, 40)}" ${ratio.toFixed(2)}:1 (needs ${need}) ${cs.color} on rgb(${Math.round(bg.r)},${Math.round(bg.g)},${Math.round(bg.b)})`);
  }
  return res;
};

(async () => {
  const PY = process.env.PYTHON || 'python3', PORT = 8831, B = `http://127.0.0.1:${PORT}`;
  const data = mkdtempSync(path.join(tmpdir(), 'cz-a11y-'));
  execFileSync(PY, ['scripts/import_data.py', '--all'], { cwd: ROOT, env: { ...process.env, CYTOZOE_DATA_DIR: data } });
  const srv = spawn(PY, ['-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', String(PORT), '--log-level', 'warning'], { cwd: ROOT, env: { ...process.env, CYTOZOE_DATA_DIR: data }, stdio: 'ignore' });
  for (let i = 0; i < 80; i++) { try { if ((await fetch(B + '/api/status')).ok) break; } catch { /* starting */ } await sleep(150); }
  const browser = await pw[process.env.CZ_BROWSER || 'chromium'].launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce' });
  const views = [
    ['overview', '/overview', null], ['health-trends', '/health?participant=C001&sample=L-3&marker=creatinine', null], ['radiation', '/environment', null], ['review-log', '/reviews', null],
    ['evidence-drawer', '/overview', async () => { await page.getByRole('button', { name: 'Inspect Creatinine result' }).first().click(); await page.locator('.drawer').getByRole('button', { name: 'Explain this result' }).click(); await page.waitForSelector('[data-testid=answer] .answer'); }],
    ['sources-drawer', '/overview', async () => { await page.getByRole('button', { name: 'Sources and data quality' }).click(); await page.waitForSelector('.drawer .kv'); }],
    ['why-excluded-drawer', '/environment', async () => { await page.getByRole('button', { name: 'Why excluded?' }).click(); }],
    ['review-log-detail', '/reviews', async () => {
      const h = await (await fetch(B + '/api/health?participant=C001&sample=L-3')).json();
      const id = h.cards.find((c) => c.measurement.marker === 'creatinine').evidence_id;
      await fetch(B + '/api/reviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ evidence_id: id }) });
      await page.reload(); await page.getByRole('button', { name: /Creatinine C001 L-3/ }).click(); await page.waitForSelector('#rl-note');
      await page.getByRole('button', { name: 'Export review packet' }).click(); }],
  ];
  for (const [name, url, act] of views) {
    await page.goto(B + url); await page.waitForTimeout(500); if (act) { await act(); await page.waitForTimeout(300); }
    const r = await page.evaluate(AUDIT);
    checks += 6;
    r.unnamed.forEach((x) => issue(name, 'control without accessible name: `' + x + '`'));
    r.dupIds.forEach((x) => issue(name, 'duplicate id `' + x + '`'));
    r.imgs.forEach((x) => issue(name, 'image role without label: `' + x + '`'));
    r.contrast.forEach((x) => issue(name, 'low contrast ' + x));
    r.small.forEach((x) => issue(name, 'target smaller than 24x24 px: ' + x));
    if (!name.includes('drawer')) {
      if (r.headings.filter((h) => h === 1).length !== 1) issue(name, 'page should have exactly one h1');
      for (let i = 1; i < r.headings.length; i++) if (r.headings[i] > r.headings[i - 1] + 1) issue(name, `heading level skips from h${r.headings[i - 1]} to h${r.headings[i]}`);
      if (r.landmarks.main !== 1 || r.landmarks.nav < 1) issue(name, 'missing main or nav landmark');
    }
    writeFileSync(path.join(out, name + '.aria.yaml'), await page.locator(name.includes('drawer') ? '.drawer' : 'body').ariaSnapshot());
  }
  await page.setViewportSize({ width: 320, height: 640 });
  for (const r of ['/overview', '/health', '/environment', '/reviews']) {
    await page.goto(B + r); await page.waitForTimeout(400); checks++;
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) issue('reflow', `horizontal scrolling at 320 px on ${r}`);
  }
  const bname = (process.env.CZ_BROWSER || 'chromium') + ' ' + browser.version();
  await browser.close(); srv.kill();
  const report = [`# Automated accessibility audit (v2 app)`, ``, `Run ${new Date().toISOString()} · ${bname} · ${checks} check groups · ${findings.length} issue(s)`, ``,
    findings.length ? findings.join('\n') : 'No issues found by the automated checks.', ``,
    `Keyboard behaviour (skip link, drawer focus trap/return, tabs, chart keys) is covered by tests/e2e/e2e.mjs (T28).`,
    `Accessibility trees are saved here as *.aria.yaml. A manual pass with NVDA or VoiceOver is still required: see SCREEN_READER_SCRIPT.md.`].join('\n');
  writeFileSync(path.join(out, 'REPORT.md'), report);
  console.log(report);
  process.exit(findings.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
