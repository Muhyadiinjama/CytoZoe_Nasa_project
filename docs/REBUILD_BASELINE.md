# Backend rebuild baseline (M0) — 14 Nov 2026

Specification: `CytoZoe_Backend_PRD_v3_Claude_Code.md` (team-supplied). Work branch: **`Mustafa`**. The PM reviews and merges to `main`.

## Repository state before changes
| Item | Observed |
|---|---|
| Branch / HEAD | `Mustafa` @ `fe03837` (merge of `main` incl. `330d107` "fix how to run code"); in sync with `origin/Mustafa`; `main` is fully contained |
| Working tree | clean |
| Stack | FastAPI 0.162.7 · Pydantic 2.14.3 · pandas 3.1.1 · SQLite (WAL, `PRAGMA user_version` migrations) · React 19 / TypeScript 7 / Vite 8 / Recharts 3 |
| Launchers | root `npm run dev` → `scripts/dev.mjs` (teammate version: auto-setup, reuses a backend on :8000); `npm start` → uvicorn on :8000; `scripts/start.ps1/.sh` |
| Migrations | `backend/migrations/0001_initial.sql` |
| Source manifest | `data/manifests/sources.json` — OSD-575 CMP `5eb1e7f0…09d9`, RadLab DosTel1 `d3f64e7f…f7e1` |
| Local DB | `runtime/cytozoe.sqlite`; backed up with SQLite's backup API to `runtime/backups/cytozoe-20261114T090804Z.sqlite` (integrity ok, 0 reviews) |

## Baseline commands (actually run)
| Command | Result |
|---|---|
| `python scripts/fetch_data.py --all` | both files downloaded; hashes match the manifest |
| `python scripts/verify_data.py --strict` | OK — 28 samples, C001–C004, 7 visits, 140 values; 1,202 rows, 4 conflict groups |
| `cd backend && python -m pytest -q` | **33 passed** |

## Audit findings
| # | Finding | Evidence | Severity | Milestone |
|---|---|---|---|---|
| A1 | **The first import of a schema-valid but hash-mismatched CMP file is accepted and served as NASA OSDR data.** The importer only refused changed bytes when a dataset was already loaded. | Probe: C001 L-3 creatinine changed to 9.99 → `IMPORTED`, `matches_pinned=False`, evidence served with provider "NASA Open Science Data Repository" and value 9.99 | **Critical** (trust) | M2 |
| A2 | **Replay temporal leakage:** the health replay "prospective" baseline at L-3 included L-3 itself (n=3, 1.2367) | Probe output | High (scientific) | M4 |
| A3 | No liveness/readiness probes; `/api/status` has no single readiness state; a DB failure surfaces as a generic 500 | Code read: `routes.py`, `main.py` | Medium | M1 |
| A4 | Error bodies lack a `request_id`; the ID exists only in a response header | `main.py` | Low | M1 |
| A5 | Launcher on Windows: Vite is spawned through `shell: true`, so `child.kill()` ends `cmd.exe` and can orphan Vite. uvicorn `--reload` also has a reloader + worker pair. Any HTTP 200 on `:8000/api/status` is "reused", even if it is a different app | `scripts/dev.mjs` | Medium | M1 |
| A6 | Vite port is not strict, so a busy :5173 silently moves to another port and the printed URL is wrong | `frontend/vite.config.ts` | Low | M1 |
| A7 | SSE radiation replay does not check for client disconnect between batches | `services/live.py` | Low | M4 |
| A8 | No single brief endpoint: the UI assembles summary state from several calls | routes | Feature gap | M3 |
| A9 | Upload row count is unbounded (only a 10 MB size cap) | `engines/quality.py` | Low | M2 |

## Preserved invariants (must stay green)
- PRD fixtures: C001 L-3 creatinine 1.37 > 1.35, B = 1.2366667 (n=3); C001 R+1 glucose B = 77.3333, Δ = +12.6667, +16.38%.
- RadLab: 1,202 raw / 1,198 unique / 4 groups / 8 quarantined / 1,194 accepted; 296.04 µGy over 23 h 44 min 49 s.
- Stable evidence IDs (`osd575-cmp:<sample>:<marker>`, `radlab-dostel1:*`), review optimistic locking (409), audit events, frozen evidence, escaped exports, cross-case rejection.

## Scope decision
Implement M0 → M1 → M2 → M3 → M4 → M6. **M5 (extra analytes / adapter) and M7 (AI) are skipped**, as the PRD allows: they add demo risk without improving core trust.
