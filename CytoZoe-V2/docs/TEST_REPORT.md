# Test report — CytoZoe v2 (run 2026-11-14, build container)

Environment: Linux container, Python 3.13.18, Node 22.23.4, Chromium 153.0.8010.12 (Playwright 1.63). **Not** the team's
demo laptop: re-run `scripts/build_local.sh` and the commands below there before the demo.
Full logs with commands and exit codes: `docs/test-logs/`.

| # | Command (repo root) | Result | Exit |
|---|---|---|---|
| 1 | `python3 scripts/verify_data.py --strict` | both SHA-256 match the PRD; 28 rows, C001–C004, 7 visits, 140 values, BOM; 1,202 rows, 1,198 unique timestamps, 4 conflict groups (09:15, 09:20, 18:25, 18:30), 8 quarantined, 1,194 accepted | 0 |
| 2 | `python3 -m pytest -q backend/tests` | **34 passed** (T01–T16 engine/store; T17–T25 API; local-AI stand-in ×6; security; environment payload) | 0 |
| 3 | `cd frontend && npx tsc --noEmit -p tsconfig.json` | 0 errors, strict mode (React types via local stand-in, see KNOWN_LIMITATIONS) | 0 |
| 4 | `cd frontend && node build.mjs` | dist/ built (main.js ≈250 KB, main.css ≈12 KB, Inter fonts) | 0 |
| 5 | `scripts/smoke_test.sh` | PASS | 0 |
| 6 | `node tests/e2e/e2e.mjs` | **74 passed, 0 failed** | 0 |
| 7 | `node tests/a11y/a11y.mjs` | 2026-11-14T06:47:05.372Z · chromium 153.0.8010.12 · 52 check groups · 0 issue(s) | 0 |
| 8 | latency probe (`docs/test-logs/08-performance.log`) | all reads p95 ≤ 12 ms; export p95 ≈ 3 ms (targets: 300 ms / 3 s) | — |

## PRD acceptance (section 9 and 20)
| Case | Evidence |
|---|---|
| 1 Import counts / radiation quality | verify_data; T01, T08 |
| 2 C001 glucose 77.3333; R+1 90, +12.6667, ≈16.38 %, inside 65–99, no alarm | T02 (pytest + E2E) |
| 3 C001 L-3 creatinine 1.37 > 1.35, baseline 1.2366667, preflight label | T03 (pytest), T17 (E2E) |
| 4 6 µGy/h × 600 s = 1 µGy only when gap allows; excluded at 300 s | T10 |
| 5 Bounds, missing values, zero baseline, irregular/conflict/gap, source change, no cross-case join | T04–T07, T09, T11–T16 |
| 6 E2E C001 L-3 → inspect → explain → save → reload/**restart** → export; offline; LLM off | T17–T20, T23, T25, T27 |
| 7 Keyboard, status without colour, data tables, 390/768/1024/1440 | T28, T29, a11y audit |
| 8 Assistant: diagnosis / "did radiation cause this?" → insufficient evidence; notes cannot inject; AI cannot change numbers or write reviews | T18, T23, AI-01 |

**Offline (T26/T27):** every browser request in the E2E journey is checked; any request to a host other than
127.0.0.1/localhost is blocked and recorded — **0 recorded**. The build container itself has no general internet access.
Still to do on the demo laptop: the PRD 17.4 manual check with Wi-Fi off.

## Browser E2E checks (from the last run)
```
PASS T17 C001 L-3 creatinine 1.370 flagged outside supplied range (text + icon)
PASS T17 card shows retrospective preflight mean 1.237 (n=3)
PASS T17 no live/health-score/sent-to-Earth/healthy wording
PASS T17 evidence order Observed → Compared with → Source → Limits → Follow-up
PASS T17 source line 2 shown
PASS T17 full source SHA-256 shown
PASS T18 “Explain this result” gives a verified, non-diagnostic answer
PASS T18 “How was this calculated?” gives a verified, non-diagnostic answer
PASS T18 “What can this dataset not tell us?” gives a verified, non-diagnostic answer
PASS T18 answer area populated
PASS T18 “Did radiation cause this?” → Not enough evidence
PASS T22 double-click on save: exactly one review, one update, no false conflict
PASS T28 Escape closes drawer and returns focus to opener
PASS T19 saved status shows on card after refresh
PASS T17 trend chart has 7 actual visit points
PASS T17 chart and evidence panel agree
PASS T19 saved note shown on trend evidence panel
PASS T28 chart point selectable with keyboard (URL now sample=L-92)
PASS URL Back restores previous sample selection
PASS T28 marker tabs: ArrowRight moves to Calcium and keeps focus
PASS T02 C001 R+1 glucose 90 vs 77.3333: +12.6667 (+16.38%), within range, no alarm
PASS URL bad URL params fall back to a visible real selection
PASS ENV separation banner
PASS T08 quality strip 1202 / 8 excluded / 1194
PASS T16 sensor dose shown; no health participant controls on this page
PASS T09 conflict inspector lists the 4 timestamps with both rows
PASS T28 rate chart readable with arrow keys
PASS ENV environment review saved (no participant id)
PASS T20 after server restart all 3 reviews are listed
PASS T20 note and history intact after restart
PASS T24 injected note does not execute in the page
PASS REV case filter; participant filter hidden for environment
PASS REV status filter works
PASS T21 stale save returns conflict and keeps the draft
PASS T21 after loading the newer version, the draft saves
PASS T23 preview shows notes (escaped text), hash
PASS T23 JSON export: separate health (2) and environment (1) sections
PASS T23 exported notes match database; sources and version present
PASS T24 HTML export escapes note markup
PASS T24 CSV export neutralises formula-like cells
PASS EXP export confirms a local download (no transmission wording)
PASS T25 no model: verified explanations work, AI clearly off
PASS T27 zero requests to non-loopback hosts during the journey
PASS T29 /overview at 390px: no horizontal page scroll
PASS T29 /health at 390px: no horizontal page scroll
PASS T29 /environment at 390px: no horizontal page scroll
PASS T29 /reviews at 390px: no horizontal page scroll
PASS T29 /overview at 768px: no horizontal page scroll
PASS T29 /health at 768px: no horizontal page scroll
PASS T29 /environment at 768px: no horizontal page scroll
PASS T29 /reviews at 768px: no horizontal page scroll
PASS T29 /overview at 1024px: no horizontal page scroll
PASS T29 /health at 1024px: no horizontal page scroll
PASS T29 /environment at 1024px: no horizontal page scroll
PASS T29 /reviews at 1024px: no horizontal page scroll
PASS T29 /overview at 1440px: no horizontal page scroll
PASS T29 /health at 1440px: no horizontal page scroll
PASS T29 /environment at 1440px: no horizontal page scroll
PASS T29 /reviews at 1440px: no horizontal page scroll
PASS T29 phone: menu button opens navigation
PASS T28 first Tab stop is the skip link
PASS T28 skip link moves focus to the page title
PASS T28 drawer opened by keyboard gets focus
PASS T28 focus trapped in drawer; background inert
PASS T30 bad import shows column diagnostic; last good data kept
PASS T30 data still shown after failed import
PASS T30 empty database: clear no-data state with importer, nothing fabricated
PASS T30 importing the real file from the browser populates the page
PASS T30 service stopped while open: clear “Local service unavailable” message, no fake saves
PASS QA no console errors (ignored expected network errors: 1)
PASS AI-01 draft labelled “AI draft — verify against evidence”, verified facts shown beside it
PASS AI-01 draft goes into the note box only; not saved/exported until Save
PASS AI-01 draft with invented number / clinical wording rejected → verified answer only
PASS AI-01 model receives only evidence facts, never reviewer notes
```

## Not covered by these runs
Real Ollama model; Firefox/Safari; manual screen reader; 200 % zoom by hand; first-run usability timing with a real user
(PRD T31 — record the actual time, do not estimate); fresh-machine install from the README.
