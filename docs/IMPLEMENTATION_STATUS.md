# Implementation status (14 Nov 2026)

## P0 ledger
- [x] P0 source manifest and download/verify scripts (`data/manifests/sources.json`, `scripts/fetch_data.py`, `verify_data.py`, `import_data.py`)
- [x] P0 OSD-575 exact data imported and examples matched (T01–T04)
- [x] P0 RadLab exact data imported and conflicts quarantined (T08–T12)
- [x] P0 four usable routes with only three primary charts
- [x] P0 canonical evidence drawer and explain endpoints (Verified explanation)
- [x] P0 notes persist across restart and the review event trail exists (T19–T22)
- [x] P0 export of both HTML and JSON, with separately labelled cases (T23–T24)
- [x] P0 clean build, data tests, UI tests, E2E/keyboard tests; offline via network isolation (physical Wi-Fi-off test still to do)
- [x] P0 release README and required competition docs
- [ ] P1 optional AI: **not implemented** (no local model available; the deterministic templates are complete)

## Requirements register
| ID | Status | Notes |
|---|---|---|
| DATA-01 | Done | 28 samples / 140 values, hash-verified |
| DATA-02 | Done | 1,192 raw rows retained; 6 quarantined |
| DATA-03 | Done | Drawer shows dataset, file, data row, file line, column, raw value, SHA-256, licence, URL |
| HEAL-01 | Done | 4 participants, 7 categorical visits, URL state |
| HEAL-02 | Done | 5 cards with values, units, range status, Δ |
| HEAL-03 | Done | n shown; not computed when n < 2 |
| HEAL-04 | Done | Dots only; per-visit bounds when they differ; data table |
| ENV-01 | Done | Segmented lines, conflict markers, source-clock label, row explorer |
| ENV-02 | Done | Coverage and method beside the value; "Estimated dose over covered intervals at sensor" |
| EVID-01 | Done | 5 questions (3 primary + 2 boundary) |
| REV-01 | Done | Real process restart test, 409 conflicts, audit events |
| REV-02 | Done | Escaped self-contained HTML + JSON |
| OFF-01 | Done (browser-isolation proof) | Physical offline test pending on the demo laptop |
| UX-01 | Done | 4 widths, keyboard, focus restore, axe 0 violations |
| SEC-01 | Done | Loopback, host/origin guard, CSP, upload limits, no secrets |
| QA-01 | Done | Logs in `docs/test-logs/` |
| DEMO-01 | Ready | `docs/DEMO_SCRIPT.md` |
| EVID-02 | Done | Mission timeline replay (Overview) + SSE radiation replay stream (Radiation Review); only true recorded data, labelled "not live" |
| LIVE-01 (added) | Done | SSE live sync of reviews across windows, sidebar recent reviews, toasts; drafts never silently rebased |
| UX-02 (added) | Done | v2 visual redesign (calm workspace, serif headings, conversational assistant), replacing the PRD §5 palette at the team's request |
| AI-01 | Not started | P1; needs Ollama + a tested model |
| ACCESS-02 | Not started | P2 |

## Data handling decision
The raw NASA CSVs were downloaded, verified, imported and tested, and then **removed from `data/raw/`** at the team's request. The working database `runtime/cytozoe.sqlite` keeps the imported records, so the app runs without them. Re-create the files any time with `python scripts/fetch_data.py --all`; the pinned SHA-256 values prove they are byte-identical. The real-data tests are skipped (not faked) while the files are absent.
