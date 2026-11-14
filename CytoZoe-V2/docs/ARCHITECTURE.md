# Architecture

```
data/raw/*.csv ──E1 ingest/quality──► SQLite (runtime/) ──E2 health / E3 radiation──► evidence objects
                                                                                   │
                     React UI (4 routes, 3 charts, drawer) ◄── JSON over 127.0.0.1 ──┤── verified templates ─(optional)─► local Ollama (loopback)
                                │                                                  │
                                └── reviews (versioned, audited) ──► export JSON / HTML / CSV (local download)
```
One local process (uvicorn) serves both the built frontend and `/api`. Calculations exist only in `backend/app/engines`;
the frontend never recomputes numbers.

## API (all JSON errors are `{code, message, details}`)
| Method and path | Purpose |
|---|---|
| GET `/api/status` | version, schema, DB status, active datasets, assistant mode |
| GET `/api/datasets` | source metadata, hashes, quality reports |
| POST `/api/import?kind=HEALTH_CMP\|ENV_RADIATION&file_name=x.csv` (body: CSV bytes) | atomic, idempotent-by-hash import; 422 with diagnostics on schema problems; 413 over 10 MB |
| GET `/api/participants` | participant codes and ordered actual samples |
| GET `/api/health?participant=C001&sample=L-3` | five evidence objects + review state + summary |
| GET `/api/health/trend?participant=C001&marker=creatinine` | actual visits, baseline, ranges |
| GET `/api/environment?instrument=DosTel1` | quality, conflicts, segmented rate/dose series, exclusions, findings, table |
| POST `/api/explain` `{evidence_id, question_id: EXPLAIN\|HOW_CALCULATED\|LIMITS\|FREE_TEXT, free_text?}` | verified explanation (+ optional AI draft); no side effects |
| GET `/api/reviews?case=&status=&participant=&limit=&offset=` | saved reviews |
| POST `/api/reviews` `{evidence_id}` | idempotent create (201 new, 200 existing) |
| GET / PATCH `/api/reviews/{id}` `{version, status?, note?, follow_up_date?, clear_follow_up_date?}` | detail with history / versioned update (409 on stale version) |
| GET `/api/export?format=json\|html\|csv` | review packet download |

## Frontend
`app/router.ts` (URL state: `/overview?participant=&sample=`, `/health?…&marker=`, `/environment?instrument=`,
`/reviews?case=&status=&participant=`), `app/App.tsx` (boot / service-unavailable states, shell), `pages/*`,
`components/*` (Drawer with focus trap, EvidencePanel, ReviewForm, Assistant, ImportPanel, States),
`charts/*` (SVG), `styles/tokens.css` (PRD 5.1 palette) + `globals.css`.

## Evidence ids
`osd575:{sha12}:{sample_id}:{marker}:{rule}` and `radlab:{sha12}:{instrument}:{quality|peak}:{rule}` — stable for the same
source bytes and rule version. The first saved review freezes the evidence object, so later imports never rewrite past reports.
