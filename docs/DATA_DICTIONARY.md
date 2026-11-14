# Data dictionary

## Source → stored fields: OSD-575 CMP (`health_observations`)
| Stored field | Source | Notes |
|---|---|---|
| `participant_id` | `Sample Name` prefix (`C001`…) | anonymised code; no identity inference |
| `sample_id` | `Sample Name` | e.g. `C001_serum_L-3` (BOM removed) |
| `visit`, `phase`, `relative_day`, `visit_order` | `Sample Name` suffix | L-92/L-44/L-3 = PREFLIGHT (days before launch); R+1/R+45/R+82/R+194 = POSTFLIGHT (days after return). The order is categorical; L and R use different reference points |
| `marker` | column stem | glucose, sodium, potassium, creatinine, calcium |
| `value` / `value_raw` | `{stem}_value_{unit}` | float or null; the raw text is kept |
| `range_low`, `range_high` | `{stem}_range_min_{unit}`, `{stem}_range_max_{unit}` | can differ between samples |
| `unit` / `source_unit` | unit token | `milligram_per_deciliter` → mg/dL, `millimol_per_liter` → mmol/L (display only; no conversion) |
| `source_row` | position | 1-based data row; file line = row + 1 |
| `source_column` | — | exact value column name |

## Source → stored fields: RadLab DosTel1 (`radiation_observations`)
| Stored field | Source | Notes |
|---|---|---|
| `source_timestamp` | `timestamp` | stored verbatim; no timezone conversion |
| `instrument_id` | `instrument_id` | must be `DosTel1` |
| `rate` / `rate_raw` | `absorbed_dose_rate` | µGy/hour; finite and ≥ 0, else excluded |
| `quality_status` | derived | `ACCEPTED`, `DUPLICATE_CONFLICT`, `DUPLICATE_IDENTICAL`, `INVALID_TIMESTAMP`, `INVALID_RATE`, `MISSING_VALUE` |

## Enumerations
- `RangeStatus`: `BELOW_SUPPLIED_LOWER_BOUND`, `ABOVE_SUPPLIED_UPPER_BOUND`, `WITHIN_SUPPLIED_RANGE`, `ONE_SIDED_COMPARISON`, `UNKNOWN`.
  - Precedence: a missing value → UNKNOWN; no bounds → UNKNOWN; a violated known bound wins; both bounds satisfied → WITHIN; one bound only → ONE_SIDED. A value equal to a bound counts as within it.
- `ReviewStatus`: `OPEN`, `FOLLOW_UP_REQUESTED`, `REVIEWED`. This is an administrative workflow state, not a medical status.
- `QuestionId`: `EXPLAIN_RESULT`, `HOW_CALCULATED`, `LIMITATIONS`, `DIAGNOSIS_REQUEST`, `CAUSATION_REQUEST`.
- `EvidenceStrength`:
  - `DIRECT_RESEARCH_MEASUREMENT_WITH_DESCRIPTIVE_COMPARISON`
  - `DIRECT_SENSOR_MEASUREMENT_WITH_APPROXIMATE_INTEGRATION`
  - `SOURCE_DATA_QUALITY_FINDING`

## Formulas
- Baseline `B = mean(finite preflight values)` with `n ≥ 2`. It is labelled *retrospective* because it includes L-3 even when an earlier visit is selected.
- `Δ = x − B`; `%Δ = 100·(x − B)/B` only when `B ≠ 0`. No rounding is applied before presentation.
- Sensor dose per interval: `((r_i + r_j)/2) × (t_j − t_i)/3600` µGy. An interval is included only if `0 < Δt ≤ 300 s` and no excluded event lies strictly inside it.
- Duplicate policy: identical duplicates count once; conflicting duplicates are all quarantined.
