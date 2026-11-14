# Known limitations (14 Nov 2026)

## Scope (by design)
- Two historical case studies only (OSD-575 blood panel; one RadLab DosTel1 day). No live sensors, no heart rate, blood
  pressure, sleep, mood, bone or muscle data (PRD 0.4 forbids invented vitals).
- Descriptive comparisons only. Four participants cannot validate anything clinically.
- Radiation numbers are sensor readings at one ISS location: not personal, organ or effective dose, not a risk estimate.

## Stack substitutions (build machine had no package downloads)
- Starlette + Pydantic instead of FastAPI: no auto-generated OpenAPI/Swagger page.
- esbuild instead of Vite; hand-written SVG charts instead of Recharts.
- React types: minimal stand-in in `frontend/types/`; real `@types/react` not yet run (see `frontend/types/README.md`).
- `sqlite3` + SQL migration file instead of an ORM/Alembic. No `package-lock.json` (could not be generated offline):
  run `npm install` once with internet and commit the lockfile.

## Not verified here
- Optional AI wording with a **real** Ollama model (only a stand-in server was tested).
- Browsers other than Chromium 153 (Firefox, Safari); manual NVDA / VoiceOver pass (script in `docs/a11y/`).
- 200% browser zoom specifically (reflow at 320 px, which is stricter, passes).
- `pip install -e ./backend` (pyproject) — the `requirements.txt` route is the tested one.
- Performance on the team's demo laptop (here: participant/sample changes and API reads well under 100 ms).
- The official challenge Resources/Details tabs, rules, AI-disclosure requirements and project form (needs the logged-in portal).
- RadLab redistribution terms (decide before keeping `data/raw/radlab_dostel1_2022_03_01.csv` in a public repo).

## Smaller items
- Evidence deep links (`?evidence=`) are not implemented (PRD: optional).
- No guided sample replay or speech read-out (P1/P2; deliberately cut).
- The radiation data table renders all 1,202 rows when opened (fine here; could be paged).
- Review notes are required to save (a consistent rule chosen from PRD 15.5's two options).
