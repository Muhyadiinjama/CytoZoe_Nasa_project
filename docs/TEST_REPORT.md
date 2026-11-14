# Test report

> **Latest (backend v3, 14 Nov 2026):** 56 backend · 4 frontend unit · 12 E2E · 13 launcher checks, all passing. Details, the B01–B24 matrix and fixed defects: [BACKEND_RELEASE_REPORT.md](BACKEND_RELEASE_REPORT.md). The sections below are the earlier v1/v2 record.

**Run date:** 14 Nov 2026 · **Machine:** Windows 11 Home 10.0.26300 · Python 3.12.10 · Node 26.13.0 · Microsoft Edge (Playwright channel `msedge`) · Raw logs: [docs/test-logs/](test-logs/)

Every result below was produced by actually running the command. Nothing is estimated.

| # | Command (working dir) | Exit | Result |
|---|---|---|---|
| 1 | `python scripts/fetch_data.py --all` (repo) | 0 | Both files downloaded; hashes **match** pinned manifest |
| 2 | `python scripts/verify_data.py --strict` (repo) | 0 | 28 samples, C001–C004, 7 visits, 140/140 values; 1,202 rows, 1,198 unique timestamps, 4 conflict groups, 8 quarantined, 1,194 accepted |
| 3 | `python scripts/import_data.py --all` ×2 (repo) | 0 / 0 | First `IMPORTED`, second `ALREADY_IMPORTED` (idempotent) |
| 4 | `python -m pytest -v` (backend) | 0 | **33 passed** (incl. SSE replay totals, prospective baseline, typed-question routing, broker) |
| 5 | `npm run typecheck` (frontend) | 0 | strict TypeScript, 0 errors |
| 6 | `npx vitest run` (frontend) | 0 | **4 passed** |
| 7 | `npm run build` (frontend) | 0 | built; JS about 743 kB (219 kB gzip); Inter + Source Serif 4 bundled |
| 8 | `npx playwright test` (frontend) | 0 | **12 passed** (v2 UI; includes 3 real-time specs) |

### Real-time verification (v2)
| Check | Evidence | Status |
|---|---|---|
| Radiation replay streams all 1,194 accepted readings + 4 conflict events in source order; final cumulative and covered time equal the static E3 result | `test_environment_replay_streams_every_accepted_reading_and_matches_static_totals` | Pass |
| Stream visibly advances, shows the 09:15 conflict as it is reached, pauses and resumes from the same point | E2E `realtime.spec` | Pass |
| Timeline replay steps L-92 → R+194 and drives the Overview cards; the L-3 creatinine flag appears | E2E + `test_health_replay_uses_prospective_baseline` | Pass |
| Review saved in window A appears in window B (toast, sidebar, table) without reload | E2E live-sync spec | Pass |
| A draft open in another window is not silently rebased: 409 prompt shown, draft kept | E2E T21 (updated) | Pass |
| Typed questions route to fixed templates; injected text is never echoed | `test_typed_questions_route_to_fixed_templates_and_never_echo` | Pass |

Defects found and fixed during the v2 work:
1. **Live sync would have silently overwritten another window's save.** A tab with an unsaved draft took the newer version number, so its next save replaced the other window's change. Fix: a draft now keeps the version it was based on, so saving gets the 409 conflict prompt.
2. **The mobile menu closed by itself on Overview.** It closed on any URL query change, including the page filling in its default participant and visit. Fix: it now closes only on page change.

During development, earlier runs found real defects, which were fixed and then re-tested:
- an integer-truncating number formatter: the dose axis showed "3" for 300 (regression tests added in Python and TypeScript);
- an axe `label-content-name-mismatch` on 3 controls;
- a test bug with an unmatched byte replacement.

## PRD acceptance matrix
| Test | Evidence | Status |
|---|---|---|
| T01 counts | `test_t01_osd575_counts` | Pass |
| T02 C001 glucose 77.3333 / +12.6667 / 16.38% | `test_t02_*` (unit + API), E2E Health Trends | Pass |
| T03 C001 L-3 creatinine 1.37 > 1.35, B = 1.2366667 | `test_t03_*`, E2E journey | Pass |
| T04 equal bound within | unit + real C003 L-44 calcium 10.3 = 10.3 | Pass |
| T05 missing value/bound | unit | Pass |
| T06 n < 2 / B = 0 | unit | Pass |
| T07 out-of-order rows | unit | Pass |
| T08 RadLab 1,202 / 4 groups / 8 / 1,194 | `test_t08_radlab_quality`, E2E environment | Pass |
| T09 conflicts preserved, not averaged | unit + E2E drawer shows both raw rates | Pass |
| T10 6 µGy/h × 600 s = 1 µGy only if permitted | unit | Pass |
| T11 NaN/blank/malformed/negative | unit | Pass |
| T12 gap / conflict segments | unit + API (segments = excluded + 1) | Pass |
| T13 hash change / schema mismatch refused | API test (409 / 422 / 400) | Pass |
| T14 forced import failure keeps data + reviews | API test | Pass |
| T15 idempotent re-import | API + CLI | Pass |
| T16 cross-case join rejected | API 400 + DB CHECK constraint | Pass |
| T17 C001 L-3 → chart + evidence same source | E2E journey | Pass |
| T18 three verified questions, no diagnosis | API + E2E | Pass |
| T19 save → refresh | E2E | Pass |
| T20 stop/start server, same DB | E2E `restart.spec` (real process kill/restart) + API | Pass |
| T21 stale version → 409, draft kept | API + E2E two-tab test | Pass |
| T22 repeated create → one review | API | Pass |
| T23 export consistency, hash, URL, limitations | API + E2E downloaded HTML/JSON parsed | Pass |
| T24 HTML/formula injection escaped | API | Pass |
| T25 LLM disconnected | N/A — no LLM exists; verified templates are the only mode | Pass (by design) |
| T26 network disconnected | E2E with all non-loopback requests aborted: 4 routes, inspect, save, export | Pass (browser-level isolation; see gap below) |
| T27 zero remote requests | E2E records **0** external request attempts; bundle scan shows no CDN/analytics URLs | Pass |
| T28 keyboard & focus | E2E: skip link, drawer focus moves in, 60 Tab presses stay trapped, Escape restores focus to opener, save by keyboard | Pass (200% zoom not tested manually) |
| T29 390/768/1024/1440 px | E2E asserts no horizontal page overflow on 4 routes × 4 widths; screenshots in `docs/screenshots/` | Pass |
| T30 unavailable / no-data states | E2E | Pass |
| T31 first-run usability < 90 s | **Not measured with a human.** The scripted journey completes in seconds, which is not a valid usability measure | Not done |
| T32 citation visible | E2E: SHA-256 and data row shown in the drawer | Pass |

## Accessibility findings
| Check | Result |
|---|---|
| axe-core, tags wcag2a/2aa/21a/21aa/22aa, 4 routes + open drawer | 0 violations on the v2 design (after fixing 3 label mismatches in v1) |
| Keyboard-only core journey | Pass |
| Status not by colour alone | Text + icon on every range status and badge |
| Reduced motion | CSS `prefers-reduced-motion` disables animations; scroll falls back to `auto` |
| Chart alternatives | Each chart has an `aria-label` summary and an expandable data table of the plotted values |
| Not done | Manual NVDA/VoiceOver pass; manual 200% zoom pass; manual contrast check of hover states |

## Visual findings (from screenshots)
- The 1440 px overview shows 5 cards in one row. At 1024 px there are 3+2, at 768 px 2 columns, and at 390 px a single column with the menu button.
- The radiation rate chart (log scale by default) shows the orbital rate pattern and short high-rate passages, with dashed red markers at the 4 excluded timestamps.
- Fixed during review: the health chart's y-axis now uses 1/2/5-step ticks, the evidence label/value grid was rebalanced for narrow columns, and the integer tick labels were corrected.

## Performance (observed in server logs, local machine)
API responses took 5–16 ms for `/api/health`, `/api/health/trend`, `/api/participants` and review PATCH. Participant and visit changes render well under the 500 ms target on this machine. This is not a formal p95 benchmark.

## Offline verification: what was and wasn't done
- **Done:** Playwright aborted every request whose host was not 127.0.0.1/localhost. The full journey (all 4 routes, inspect, explain, save, reload, export) passed, with **0** external requests attempted.
- **Not done:** physically disabling Wi-Fi/Ethernet on the demo laptop. **The team must do this before the demo** (see `DEMO_SCRIPT.md`).
