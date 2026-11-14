# CytoZoe API contract (backend v3)

Base: `http://127.0.0.1:8000` (loopback only). Machine-readable schema: **`GET /api/openapi.json`**; interactive docs: `/api/docs`.
All routes are additive over v2 — **no existing route was removed or renamed**.

## Error contract (every 4xx/5xx)
```json
{ "code": "SOURCE_HASH_MISMATCH", "message": "…human readable…", "details": { }, "request_id": "a1b2c3d4e5f6" }
```
`request_id` matches the `X-Request-ID` response header. No tracebacks, filesystem paths or note text are ever returned.

| Code | HTTP | Meaning |
|---|---|---|
| `NO_DATA` | 404 | The dataset is not imported (PRD name: `DATASET_NOT_IMPORTED`; that name is used by `/api/readyz`) |
| `NOT_FOUND` | 404 | Unknown participant / visit / evidence / review |
| `VALIDATION_ERROR` | 422 | Request failed schema validation (`details.fields`) |
| `SOURCE_HASH_MISMATCH` | 422 on import / 409 on read | The bytes are not a registered verified NASA snapshot; existing data was preserved |
| `DATASET_VERSION_CHANGE` | 409 | A different *registered* version is already loaded; replace it deliberately with the CLI |
| `VERSION_CONFLICT` | 409 | Stale review `version` (PRD name: `REVIEW_VERSION_CONFLICT`); `details.current` has the latest record |
| `CROSS_CASE_LINK_REJECTED` | 400 | An attempt to pair the health and radiation cases |
| `INVALID_MODE` · `UNSUPPORTED_MARKER` · `QUESTION_REQUIRED` · `INVALID_FINDING_ID` | 400 | Bad parameter |
| `UNKNOWN_SCHEMA` · `DATA_SCHEMA_MISMATCH` · `TOO_MANY_ROWS` · `LINE_TOO_LONG` · `BINARY_CONTENT` · `FILE_TOO_LARGE` | 413/422 | Import rejected |
| `ORIGIN_REJECTED` | 403 | Cross-site write |
| `DATABASE_UNAVAILABLE` | 503 | SQLite cannot be opened or read; see `/api/readyz` |
| `INTERNAL_ERROR` | 500 | Unexpected; saved data unchanged |

Kept v2 code names (`NO_DATA`, `VERSION_CONFLICT`) are deliberate, so the shipped frontend keeps working. The PRD's preferred names are listed alongside.

## Runtime probes
| Route | Behaviour |
|---|---|
| `GET /api/healthz` | `200 {"status":"alive","app":"CytoZoe",…}`; never touches the DB |
| `GET /api/readyz` | `200` only when the DB is reachable, migrations are current and both datasets are imported **and** verified. Otherwise `503`, with `state` = the first failing code (`DATABASE_UNAVAILABLE`, `MIGRATION_PENDING`, `DATASET_NOT_IMPORTED`, `SOURCE_HASH_MISMATCH`, `FRONTEND_NOT_BUILT` when `CYTOZOE_REQUIRE_FRONTEND=1`) and `checks[]` |
| `GET /api/status` | v2 fields **plus** `state` and `checks` (same as `readyz`) |

## Mission Health Intelligence Brief — `GET /api/mission/brief`
Query: `participant` (C001–C004), `sample` (visit label, e.g. `L-3`), `mode=historical` (the only accepted mode).
Response: **`MissionBriefV1`**. Real example: [examples/mission-brief-C001-L-3.json](examples/mission-brief-C001-L-3.json).

| Field | Content |
|---|---|
| `schema_version`, `brief_id`, `mode` (`HISTORICAL_RESEARCH`), `title`, `generated_at`, `rule_versions` | Identity and versions |
| `dataset` | id, title, provider, file, **sha256**, **provenance**, source URL, `imported_at` |
| `context` | participant, sample, visit, visit label, phase, relative day + reference ("days before launch" / "days after return") |
| `coverage` | markers considered/measured/missing; counts with two-sided, one-sided or no bounds; scope note |
| `summary` | `measured_marker_count`, `outside_supplied_range_count`, `text` (fixed wording, including the neutral no-findings sentence) |
| `findings[]` | Outside supplied bounds, in stable marker order (glucose, sodium, potassium, creatinine, calcium). **No severity ranking** |
| `other_measurements[]` · `missing_measurements[]` | Remaining measured markers; markers without a value (`status: UNKNOWN`) |
| each item | `evidence_id`, value/unit (unrounded), bounds, `status`, `baseline{value,n,available,includes_selected_sample,samples_used[]}`, `delta`, `percent_delta`, `source{file,sha256,provenance,source_row,file_line,source_column,raw_value}`, `explanation{observed,compared_with,why_flagged,limitations[],next_review_action}`, `review{id,status,version,note_present,updated_at}`, `actions{inspect_evidence, create_or_open_review{method,endpoint,finding_id,review_id}, export_packet}` |
| `quality` | provenance, validation status, parser version, parse issues, warnings |
| `dataset_limitations[]`, `case_separation`, `available_questions[]` | Honesty and guided-question IDs for `/api/explain` |

**Invariant (tested):** every number in a brief item equals the same field in `GET /api/evidence/{evidence_id}` and in the evidence snapshot frozen into exports (same unit, rule version and source hash).

## Verified explanations — `POST /api/explain`
`{evidence_id, question_id}` or `{evidence_id, message}` (typed text routed by keyword rules; never echoed). New IDs in v3: `SOURCE_LOCATION` ("Where did this number come from?") and `FOLLOW_UP_OPTIONS` ("What follow-up can be recorded?"). Existing: `EXPLAIN_RESULT`, `HOW_CALCULATED`, `LIMITATIONS`, `DIAGNOSIS_REQUEST`, `CAUSATION_REQUEST`. There is no language model.

## Replays (historical, read-only)
| Route | Notes |
|---|---|
| `GET /api/replay/health?participant=` | `mode: HISTORICAL_REPLAY`. Each frame has `baseline_context: PROSPECTIVE_PRIOR_PREFLIGHT` and `baseline_visits` — preflight visits **strictly before** the frame (no leakage). Never writes to the DB |
| `GET /api/replay/environment?speed=&start=` (SSE) | `meta` (`mode: HISTORICAL_REPLAY`, timestamp semantics), `frame` (`reading` / `excluded` events), `end`. `start` resumes with identical rows and totals. Stops when the client disconnects |
| `GET /api/events` (SSE) | `review.created`, `review.updated`, `dataset.imported`; note text is never broadcast |

## Unchanged v2 routes
`/api/datasets` (now includes `provenance`), `/api/import`, `/api/participants`, `/api/health`, `/api/health/trend`, `/api/environment`, `/api/evidence/{id}` (`source.provenance` added), `/api/reviews` (GET/POST), `/api/reviews/{id}` (GET/PATCH), `/api/export?format=json|html` (datasets include `provenance`; HTML shows it).

## Provenance classes
`NASA_PINNED_VERIFIED` (the only class the NASA endpoints serve) · `UNVERIFIED_LEGACY` (rows from before the trust gate whose hash is not registered; blocked with 409) · `RESEARCH_IMPORTED_UNVERIFIED`, `MISSION_ADAPTER_TEST` (reserved in the schema; not implemented — P1).
