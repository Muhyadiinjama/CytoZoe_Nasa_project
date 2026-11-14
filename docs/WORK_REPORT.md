# CytoZoe: Backend work report

**Branch:** `Mustafa` (commit `fa63ed8`) · **Date:** 14 November 2026 · **Spec:** CytoZoe Backend PRD v3
**Status:** all required milestones done, tested and pushed. Ready for PM review and merge into `main`.

---

## 1. What was wrong before

Before changing anything, I tested the PRD's claims against the existing code. Both main problems were real:

| Problem | Why it mattered | Fixed |
|---|---|---|
| **Fake data could appear as NASA data.** I changed one blood value (1.37 → 9.99), imported the file, and the app showed it as official NASA data. | A judge could break trust in the app in seconds. | ✅ |
| **The replay used the answer while calculating it.** At visit L-3, the "baseline known so far" already included L-3's own value. | Scientifically wrong; a judge could catch it. | ✅ |

---

## 2. What was built

### Trust (most important)
- Every data file's fingerprint (SHA-256) is checked against the official NASA source list. Anything changed is refused, even on a fresh install.
- Every dataset is labelled **verified NASA** or not, and only verified data is ever shown.
- Exports record which verified data each review was based on.

### Mission Health Intelligence Brief (new main feature)
- One request (`GET /api/mission/brief`) gives a reviewer the whole picture for a sample. For each result it shows:
  - what was measured;
  - what it's compared with;
  - the exact source row and column;
  - why it's flagged;
  - the limits;
  - what follow-up can be saved.
- Every number in the brief is proven identical to the evidence view and the exported report, for all 28 samples.
- No diagnosis, no "danger" levels, no AI.

### Reliability
- Health and readiness checks say exactly what's wrong (database broken, data missing, data not verified) instead of crashing.
- `npm run dev` and `npm start` refuse busy ports, report whether the app is really ready, and leave no stray processes when you quit (`q` or Ctrl+C).
- New database backup and restore tool (`scripts/backup_db.py`).

### Replay fixes
- The replay baseline uses only earlier visits.
- Replays never change saved data.
- A paused radiation replay resumes with exactly the same numbers.

---

## 3. Bugs found and fixed along the way

1. Fake data shown as NASA data (critical)
2. Replay using the current visit in its own baseline
3. **Backup restore silently restored the wrong file** if run within one second of backing up
4. On Windows, closing the app could leave hidden processes still running
5. A flaky browser test (the feature itself was fine)

---

## 4. Test results (all actually run)

| Tests | Result |
|---|---|
| Backend tests | **56 passed** (was 33) |
| Frontend unit tests | **4 passed** |
| Browser tests (full user journey) | **12 passed** |
| Start/stop launcher checks | **13 passed** |
| Speed of the new brief | ~10 ms (target: under 500 ms) |

Logs are in `docs/test-logs/`.

---

## 5. Milestones

| Milestone | Result |
|---|---|
| M0 Audit and backup | ✅ Done |
| M1 Startup and diagnostics | ✅ Done |
| M2 Trusted NASA data | ✅ Done |
| M3 Mission Health Brief | ✅ Done |
| M4 Replay and save/export loop | ✅ Done |
| M5 Extra markers / device input | ⏭️ Skipped on purpose: risky and doesn't add trust |
| M6 Release candidate | ✅ Done |
| M7 AI | ⏭️ Skipped on purpose (the PRD's default) |

---

## 6. Still to do

- [ ] **Test with Wi-Fi off on the demo laptop.** So far only checked in the browser by blocking internet requests.
- [ ] **Mac/Linux:** supported in code but only tested on Windows.
- [ ] **Connect the new Mission Brief to the screens.** This is the UI/UX step.
- [ ] **PM review and merge** of `Mustafa` into `main`.

---

## 7. Where to find everything

| File | What it is |
|---|---|
| `docs/BACKEND_RELEASE_REPORT.md` | Full technical report |
| `docs/API_CONTRACT.md` | What the UI team builds on |
| `docs/RELEASE_CHECKLIST.md` | Steps before submitting |
| `docs/examples/mission-brief-C001-L-3.json` | Real example of the new brief |
| `docs/REBUILD_BASELINE.md` | What the audit found before any changes |
