# Contributing (Team CytoZoe)

- `main` must always run. Branch from the latest `main`; small pull requests; never force-push `main`.
- Branch owners (PRD section 11): docs/pitch (PM), feat/data-quality (Data), feat/analysis (Analysis),
  feat/health-ui (Frontend, owns shared UI components and `frontend/src/styles/`),
  feat/reviews-environment (Integration, owns API/schema changes), feat/evidence-assistant (QA + assistant).
- Announce changes to shared files (`backend/app/services/evidence.py`, `frontend/src/api/contracts.ts`, styles) first.
- Before every PR: `python -m pytest -q backend/tests`, `cd frontend && npm run typecheck && npm run build`, `node tests/e2e/e2e.mjs`.
- Never commit `runtime/`, `.sqlite` files, `.env`, or invented data. New datasets enter only through a validated adapter in
  `backend/app/engines/ingest.py` with tests.
- Calculations live only in the backend engines; the frontend displays API values and never recomputes them.
