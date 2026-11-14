# Release checklist (tick only with observed proof)

## Fresh setup (any OS)
- [ ] Clone → `npm run setup` completes. It uses the network only here: packages + NASA download.
- [ ] `python scripts/verify_data.py --strict` → all checks passed.
- [ ] `npm start` prints **"CytoZoe ready → http://127.0.0.1:8000"**. If it prints "NOT ready", the reason is shown.
- [ ] `http://127.0.0.1:8000/api/readyz` → `200`, `"state": "READY"`.

## Core journey (judge story)
- [ ] Health Overview → C001 · L-3 shows creatinine **1.37 mg/dL** vs supplied upper bound **1.35** (data row 1).
- [ ] `GET /api/mission/brief?participant=C001&sample=L-3` → 1 finding, baseline 1.2367 (n=3), provenance `NASA_PINNED_VERIFIED`.
- [ ] Inspect → Explain → write a note → **Save follow-up** → "Saved locally".
- [ ] Stop the server (Ctrl+C or `q`) → `npm start` → the review and its history are still there.
- [ ] Review Log → download HTML and JSON → open both: note, SHA-256, limitations and "has not been sent anywhere" are present.
- [ ] Radiation Review → replay → the conflicts at 09:15 / 09:20 / 18:25 / 18:30 appear; the final estimate is 296.04 µGy.

## Offline (on the demo laptop)
- [ ] Turn off Wi-Fi/Ethernet, then repeat the core journey with `npm start`. Everything works except the external "Study page" links.
- [ ] Browser DevTools → Network: every request goes to `127.0.0.1`.

## Data integrity & safety
- [ ] `node tests/launcher/launcher.test.mjs` → all checks pass (ports 8000/5173 must be free).
- [ ] `cd backend && python -m pytest -q` → all passed (with `data/raw/` staged).
- [ ] `python scripts/backup_db.py` → backup written (integrity ok). Restore: `python scripts/backup_db.py --restore <file>` with the server stopped.
- [ ] `git status` shows no `runtime/`, `*.sqlite`, `data/raw/*.csv`, `.env` or `node_modules`.

## Submission
- [ ] PM reviews branch `Mustafa` and merges to `main` (no force push).
- [ ] Space Apps portal: challenge, team, rules, AI disclosure, deadline in local time; submit through the Project tab.
- [ ] Demo video records a physical Wi-Fi-off segment.
