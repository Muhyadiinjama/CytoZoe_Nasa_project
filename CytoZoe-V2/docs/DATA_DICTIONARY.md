# Data dictionary

## OSD-575 CMP (input)
| Source column | Imported as | Notes |
|---|---|---|
| `Sample Name` | participant_id, specimen, visit, phase, relative_day | Format `{C###}_{specimen}_{L-n or R+n}`, e.g. `C001_serum_L-3`. UTF-8 BOM removed. Any other format rejects the import with line numbers. |
| `{stem}_value_{unit}` | value (float or null) | `NA`, `N/A`, blank → null. Non-numeric/non-finite → null and counted as invalid. |
| `{stem}_range_min_{unit}` / `_range_max_` | range_low / range_high | Supplied by the source per row. Missing bound → one-sided comparison. |
Stems and display units: glucose (mg/dL), sodium (mmol/L), potassium (mmol/L), creatinine (mg/dL), calcium (mg/dL).
All other columns (including race-based eGFR) are ignored. `source_row` = line number in the file (header = line 1).

## RadLab (input)
| Column | Imported as | Notes |
|---|---|---|
| `timestamp` | source_timestamp (text, as provided) + epoch_ms (arithmetic only) | No timezone stated by the source; never converted or relabelled. |
| `instrument_id` | instrument_id | Optional; DosTel1 chosen by default when several are present. |
| `absorbed_dose_rate` | rate (µGy/h) | Missing → `MISSING_VALUE`; negative/non-numeric → `INVALID_RATE`. |
Quality status: `ACCEPTED`, `DUPLICATE_CONFLICT` (same timestamp, different rates: **all** rows in the group excluded),
`DUPLICATE_IDENTICAL` (same timestamp and rate: first kept, extras not integrated), `INVALID_TIMESTAMP`, `INVALID_RATE`, `MISSING_VALUE`.

## Derived values
| Name | Definition | Rule version |
|---|---|---|
| Retrospective preflight mean | mean of all non-null L- visit values for the same participant and marker; requires n ≥ 2 | health-compare-v1 |
| Difference | value − mean | health-compare-v1 |
| % difference | 100 × (value − mean) / mean; null when mean = 0 | health-compare-v1 |
| Range status | `BELOW_SUPPLIED_LOWER_BOUND` if value < low; `ABOVE_SUPPLIED_UPPER_BOUND` if value > high; equality is inside; one bound only → `ONE_SIDED_COMPARISON`; none → `UNKNOWN`; no value → `NOT_ASSESSABLE` | health-compare-v1 |
| Interval dose | ((r_i + r_j)/2) × Δt s / 3600, µGy, for adjacent accepted readings with 0 < Δt ≤ 300 s and no excluded reading inside | radiation-integrate-v1 |
| Estimated sensor dose | sum of accepted interval doses; covered duration = sum of their Δt | radiation-integrate-v1 |

## Local records (SQLite, `runtime/cytozoe.sqlite`, never committed)
`datasets`, `health_observations`, `radiation_observations`, `findings` (evidence frozen at first review), `reviews`
(status OPEN / FOLLOW_UP_REQUESTED / REVIEWED, note ≤ 4,000 chars, optional date, version), `review_events` (append-only
history), `import_runs`. Schema in `backend/migrations/001_init.sql`.
