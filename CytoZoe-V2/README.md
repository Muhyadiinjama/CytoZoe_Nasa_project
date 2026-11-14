# CytoZoe — Understand the change. Keep the evidence.

An offline-first **research demonstration** for NASA Space Apps Challenge 2026 (*Create Health Monitoring Software for
Astronauts on Space Missions*). CytoZoe turns real historical NASA biomarker samples into source-linked comparisons,
shows a **separate** ISS radiation record with its data-quality problems handled openly, and lets a reviewer save and
export traceable follow-ups without internet access.

It is **not** clinical software and **not** live astronaut monitoring. No diagnosis, health score, personal dose, ML
prediction or radiation–health link is produced. The blood and radiation records are different people, missions and dates
and are never paired.

| | |
|---|---|
| Pages | Health overview · Health trends · Radiation review · Review log |
| Charts | Blood marker by visit · Radiation dose rate · Estimated accumulated sensor dose |
| Engines | E1 ingestion and quality · E2 health comparisons · E3 radiation integration |
| Data | NASA OSDR **OSD-575** (Inspiration4 CMP, 4 people × 7 visits × 5 markers) · NASA **RadLab DosTel1**, 1 March 2022 |
| Runs at | http://127.0.0.1:8000 (loopback only) |

## Quick start

**Fastest (the zip already contains the built frontend in `frontend/dist/`; only Python needed):**
```bash
python3 -m pip install -r backend/requirements.txt
python3 scripts/import_data.py --all
python3 -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000   # → http://127.0.0.1:8000/overview
```
(Windows: same three commands with `python` / `py -3`.)

**Full developer setup** — requires **Python 3.11+** (verified on 3.13) and **Node.js 18+** (verified on 22) with npm:

### macOS / Linux
```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r backend/requirements.txt
(cd frontend && npm install)
# data: the two verified NASA files are already in data/raw/. To re-download instead:
#   python scripts/fetch_data.py --all
scripts/build_local.sh      # verifies hashes/counts, imports into SQLite, type-checks and builds the frontend
scripts/start.sh            # → open http://127.0.0.1:8000/overview
```

### Windows (PowerShell)
```powershell
py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
cd frontend; npm install; cd ..
.\scripts\build_local.ps1
.\scripts\start.ps1          # → open http://127.0.0.1:8000/overview
```

After setup the app needs **no internet**: it serves its own fonts, scripts and data from your computer. The local
service must be running (closing it stops the app; the browser keeps nothing on its own).

### Demo in 90 seconds
Overview opens on **C001 · L-3 · Preflight**. Creatinine **1.370 mg/dL** is above the source's upper bound **1.35** →
*Inspect result* → evidence (source line 2, file SHA-256, retrospective preflight mean **1.2367 (n=3)**) → *Explain this
result* → write a note → *Record follow-up* → **Review log** → *Export review packet*. Then **Radiation review**:
4 conflicting timestamps quarantined, 1,194 unambiguous rows, **296.037 µGy** estimated at the sensor over 23.75 h.
Full script: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

## Tests
```bash
python -m pytest -q backend/tests          # 34 backend tests: PRD T01–T16, API T17–T25, assistant, security
(cd frontend && npm run typecheck)         # strict TypeScript
node tests/e2e/e2e.mjs                      # 74 browser checks on the real server: journey, restart, conflict, export, offline, layouts, keyboard, AI stand-in
node tests/a11y/a11y.mjs                    # automated accessibility audit → docs/a11y/REPORT.md
scripts/smoke_test.sh                       # 10-second API smoke test
python scripts/verify_data.py --strict      # source hashes and expected counts
```
E2E and accessibility tests need Playwright with Chromium (`npm i -D playwright && npx playwright install chromium`).
Results of the last run: [docs/TEST_REPORT.md](docs/TEST_REPORT.md).

## Optional local AI wording (off by default)
Wording only, from a model already installed in [Ollama](https://docs.ollama.com/api/introduction) on the same computer:
```bash
ollama pull llama3.2:3b                      # any small instruction model
CYTOZOE_OLLAMA_MODEL=llama3.2:3b scripts/start.sh
```
The model sees only the verified explanation's facts (never notes). Its reply is rejected if it contains a number that is
not in those facts, clinical or causal wording, or an unknown source id; slower than 15 s falls back. Drafts are labelled
**"AI draft — verify against evidence"**, shown under the verified answer, and are saved only if the reviewer puts them in
a note and saves. Tested with a stand-in server; **not yet tested with a real model** — do that on the demo laptop.

## Repository
```
backend/app/            Starlette + Pydantic service: engines/ (E1-E3), services/ (store, evidence, explain, assistant, reviews, export), main.py
backend/migrations/     SQLite schema (versioned)
backend/tests/          pytest unit + integration (real files, fixtures, stand-in Ollama)
frontend/src/           React 19 + TypeScript: app/ (shell, router), pages/, components/, charts/, api/, styles/
scripts/                fetch_data, verify_data, import_data, build_local, start, smoke_test (.sh and .ps1)
data/raw/               the two NASA source files (immutable)   data/manifests/sources.json  hashes and expected counts
docs/                   PRD, sources, data dictionary, architecture, security, tests, demo, submission, limitations
tests/e2e, tests/a11y   browser tests against the running service
legacy/                 the earlier single-file prototype (kept as an offline fallback)
```

## Differences from the PRD's stack (honest list)
The build machine could not download packages, so three PRD tools were replaced by installed equivalents:
- **FastAPI → Starlette + Pydantic** (FastAPI's own foundation). Same routes, JSON contracts and error shape; no
  auto-generated OpenAPI page — endpoints are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- **Vite → esbuild** (`frontend/build.mjs`). Same output: static files served by the backend.
- **Recharts → hand-written SVG charts** (no chart library), with keyboard access and data tables.
- `@types/react` was unavailable; type-checking uses a minimal stand-in (`frontend/types/`). See its README to switch.
- SQLite access uses Python's `sqlite3` with a tracked SQL migration instead of an ORM/Alembic.
More in [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).

## Data, licences and attribution
- NASA OSDR OSD-575 (Inspiration4) comprehensive metabolic panel — study page lists **CC0-1.0**.
- NASA OSDR RadLab, DosTel1 (ISS Columbus) — public API export; **redistribution terms not separately verified**; check before
  keeping the raw file in a public repository.
- Code: MIT (team to confirm). Inter font: SIL OFL 1.1. Details: [docs/SOURCES.md](docs/SOURCES.md).
