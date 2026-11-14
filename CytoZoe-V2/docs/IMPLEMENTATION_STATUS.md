# Implementation status (PRD 24.1) — 14 Nov 2026

- [x] P0 source manifest and download/verify scripts — `data/manifests/sources.json`, `scripts/fetch_data.py` (not run here: no internet; files supplied by the team and hash-verified), `scripts/verify_data.py`
- [x] P0 OSD-575 exact data imported and examples matched — T01–T03, E2E T02/T17
- [x] P0 RadLab exact data imported and conflicts quarantined — T08/T09, E2E
- [x] P0 four usable routes with only three primary charts
- [x] P0 canonical evidence drawer and explain endpoint (verified templates)
- [x] P0 notes persist across restart and review event trail exists — T20 (pytest and E2E)
- [x] P0 export HTML, JSON (and CSV subset), separately labelled cases — T23/T24
- [x] P0 clean build, data tests, UI tests, E2E/keyboard/offline tests — `docs/TEST_REPORT.md`
- [x] P0 release README and competition docs — README, `docs/SUBMISSION.md`, `docs/DEMO_SCRIPT.md`
- [x] P1 optional local AI (Ollama) adapter — implemented and validated against a stand-in; **not tested with a real model**
- [ ] P1 guided sample replay — not built (cut first per PRD 23)
- [ ] P2 speech read-out — not built

| Requirement | Status | Notes |
|---|---|---|
| DATA-01/02/03 | done | provenance one click away (drawer Source section, Sources & quality) |
| HEAL-01..04 | done | categorical visits, no interpolation, data table |
| ENV-01/02 | done | segmented charts, conflict inspector, coverage + method beside the value |
| EVID-01 | done | three questions + free-text guard |
| REV-01/02 | done | 409 conflict keeps draft; idempotent create; history |
| OFF-01 | done in tests | manual Wi-Fi-off check still to do on demo laptop |
| UX-01 | done (Chromium) | Firefox/Safari and manual screen reader still to do |
| SEC-01 | done | loopback, host/origin checks, CSP, limits, escaping |
| QA-01 | done | 34 backend + 74 browser checks, a11y audit |
| DEMO-01 | ready | docs/DEMO_SCRIPT.md |
| Stack | substituted | FastAPI→Starlette, Vite→esbuild, Recharts→SVG (no package downloads on build machine) |
