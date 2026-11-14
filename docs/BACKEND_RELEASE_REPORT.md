# Backend release report — PRD v3 (14 Nov 2026)

Branch **`Mustafa`**, for PM review before merging to `main`. Machine: Windows 11 · Python 3.12.10 · Node 26.13.0 · Microsoft Edge. Logs: [test-logs/](test-logs/).
Status: **competition-ready research prototype backend.** This is not clinical, flight or live-monitoring software.

## Milestones
| Milestone | Decision | Evidence |
|---|---|---|
| M0 Baseline & audit | **GO** | [REBUILD_BASELINE.md](REBUILD_BASELINE.md); DB backed up; 33/33 baseline tests; 9 audit findings (A1–A9) |
| M1 Startup & diagnostics | **GO** | `/api/healthz`, `/api/readyz`, `state` in `/api/status`, `request_id` in errors, typed 503 on DB failure; launchers hardened; 13/13 launcher checks |
| M2 Provenance & import integrity | **GO** | Trust gate closes A1; `provenance` column (migration 0002) + reconcile; read-side guard; row/line caps; 6 new security tests |
| M3 Mission Health Intelligence Brief | **GO** | `GET /api/mission/brief` → `MissionBriefV1` (in OpenAPI); 7 tests incl. brief = evidence = export, all 28 samples |
| M4 Replay & action loop | **GO** | Leakage A2 fixed; replays proven read-only; SSE resume/disconnect; full brief → review → restart → export journey test |
| M5 Extra analytes / adapter (P1) | **SKIPPED** | Not needed for P0; risk without trust gain. `RESEARCH_IMPORTED_UNVERIFIED` / `MISSION_ADAPTER_TEST` are reserved in the schema only |
| M6 Release candidate | **GO** | All suites green (below); backup/restore verified (after fixing a real defect); latency measured |
| M7 Local AI (P2) | **SKIPPED** (PRD default) | No model; verified templates only |

## Final test results (actually run)
| Suite | Command | Result |
|---|---|---|
| Data verification | `python scripts/verify_data.py --strict` | pass — hashes and counts match |
| Backend | `cd backend && python -m pytest -v` | **56 passed** (33 baseline + 23 new) |
| Frontend types | `npm run typecheck` | 0 errors |
| Frontend unit | `npx vitest run` | **4 passed** |
| Build | `npm run build` | ok |
| Browser E2E (Edge) | `npx playwright test` | **12 passed** (network-isolated journey: 0 external requests) |
| Launchers | `node tests/launcher/launcher.test.mjs` | **13/13** (start, ready, `q` teardown, no orphans on :8000/:5173, foreign-port refusal, `npm start`) |
| Backup/restore + latency | release check (`test-logs/release_checks.txt`) | restore verified; brief warm latency median **9.7 ms**, p95 14.3 ms, n=28 (in-process TestClient on this laptop; not a network benchmark) |

No test was skipped while the pinned raw files were staged. When `data/raw/` is empty, the real-data tests skip with an explicit message; they are never counted as passed.

## PRD B-matrix
| ID | Status | Test |
|---|---|---|
| B01 | ✅ | `verify_data.py --strict`, `test_t01`, `test_t08` |
| B02 / B03 | ✅ | `test_t03…`, `test_fixture_a_…`, `test_t02…`, `test_fixture_b_…` (+16.3793%) |
| B04 / B05 / B06 | ✅ | `test_t04`, `test_t05`, `test_t06`, `test_trend_bounds…`, brief missing/no-bound edge case |
| B07 / B08 | ✅ | `test_t08_radlab_quality`, `test_t10`, `test_t12`; 296.04 µGy over 23 h 44 min 49 s unchanged |
| B09 | ✅ | `test_t13_t14_t15…`, `test_b09_radlab…` |
| **B10** | ✅ | `test_b10_first_import_of_wrong_hash_is_rejected_on_empty_db` |
| B11 | ✅ | `test_b11_registered_new_version…` (rollback + frozen evidence) |
| B12 | ✅ | `test_t16_cross_case…` (API + DB CHECK) |
| B13 / B14 | ✅ | `test_b13_brief_evidence_and_export_agree`, `test_fixture_b_and_b14…` |
| B15 / B16 | ✅ | `test_health_replay_uses_prospective_baseline`, `test_b15_b16_replays_are_read_only`, `test_b16_radiation_resume…`, `test_b16_…disconnect` |
| B17 | ✅ | `test_t19_t21_t22…`, E2E T21 two-tab conflict |
| B18 / B19 | ✅ | `test_critical_journey_…`, E2E `restart.spec` (real process kill/restart), `test_t23_t24…` |
| B20 | ✅ | `test_runtime.py` (corrupt DB → liveness 200, readiness 503, typed 503) |
| B21 | ✅ (Windows) | launcher test 13/13; macOS/Linux not run on this machine |
| B22 | ✅ browser-level / ⏳ physical | E2E aborts all non-loopback requests: 0 attempted. **Physical Wi-Fi-off run is still for the team** |
| B23 | ✅ | `test_b23_abuse_cases`, `test_t24` (HTML/formula injection) |
| B24 | ✅ | All v2 routes unchanged; v2 E2E suite green; brief in OpenAPI |

## Defects found and fixed in this release
1. **A1 (critical):** a tampered but schema-valid CMP file was imported and served as NASA data on an empty DB (demonstrated with C001 creatinine changed to 9.99). Fixed by the manifest hash gate, the provenance class and the read guard.
2. **A2:** the replay baseline included the replayed sample. Now it uses strictly earlier preflight visits (L-3: 1.17, n=2).
3. **Backup restore silently restored the wrong file** when run within the same second as the backup: the safety copy overwrote it. Fixed with unique filenames and a regression test.
4. **Launcher:** possible orphaned Vite/uvicorn processes on Windows; any :8000 responder was "reused"; a busy :5173 drifted silently. All fixed and tested.
5. E2E live-sync test race (counted rows before the table loaded). Test fixed; the feature was fine.

## Changed files
- **Backend:** `app/main.py`, `app/api/routes.py`, `app/schemas.py` (new), `app/engines/quality.py`, `app/services/{importer,health_service,environment_service,export,explain,live,runtime (new),mission_brief (new)}.py`, `migrations/0002_provenance.sql` (new).
- **Tests:** `tests/conftest.py`, `tests/integration/{test_api,test_live}.py` (assertions updated only where the PRD changed the contract: `request_id`, `SOURCE_HASH_MISMATCH`, prospective baseline, `HISTORICAL_REPLAY`), new `test_runtime.py`, `test_provenance.py`, `test_mission_brief.py`, `test_replay_and_loop.py`, `test_backup.py`.
- **Launch / ops:** `scripts/dev.mjs`, `scripts/start.mjs` (new), `scripts/backup_db.py` (new), `tests/launcher/launcher.test.mjs` (new), `package.json`, `frontend/vite.config.ts` (`strictPort`).
- **Frontend (compat only):** `frontend/src/api/contracts.ts` types; `frontend/e2e/realtime.spec.ts` race fix. **No UI redesign.**
- **Data / docs:** `data/manifests/sources.json` (`accepted_sha256`), docs listed below.

## Source hashes (verified this run)
OSD-575 CMP `5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9` · RadLab DosTel1 `d3f64e7f483c3ae2f08bb5e6633bae5091e661a988c434205ce6bb78c050f7e1`

## Remaining limitations and risks
- A physical offline run on the **demo laptop** has not been done; it is listed in the checklist.
- macOS/Linux launcher behaviour is implemented (process-group kill) but **not tested** here.
- Only 5 of 19 CMP analytes are served (M5 skipped). The adapter / unverified research namespace is reserved, not implemented.
- The frontend does not yet use `/api/mission/brief`; that is the UI milestone.
- The audit trail is not tamper-proof. There is no authentication (single-user loopback tool).
- PRD error names `DATASET_NOT_IMPORTED` / `REVIEW_VERSION_CONFLICT` map to the kept v2 codes `NO_DATA` / `VERSION_CONFLICT` for frontend compatibility (documented in API_CONTRACT.md).

## Handoff to the UI/UX milestone
- Contract: [API_CONTRACT.md](API_CONTRACT.md) and `GET /api/openapi.json`. Real example brief: [examples/mission-brief-C001-L-3.json](examples/mission-brief-C001-L-3.json).
- Loading and error states the UI must render: `readyz.state` values, typed error codes, `HISTORICAL_REPLAY` labels, the no-findings sentence, missing/unknown markers, and the `SOURCE_HASH_MISMATCH` block.
- Actions are data, not booleans: `actions.inspect_evidence`, `actions.create_or_open_review.{method,endpoint}`, `actions.export_packet`.
