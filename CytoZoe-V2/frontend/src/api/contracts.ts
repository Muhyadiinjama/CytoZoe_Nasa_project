/* Types mirroring the backend JSON (backend/app/services/*). Numbers come only from the API. */
export type RangeStatus = 'BELOW_SUPPLIED_LOWER_BOUND' | 'ABOVE_SUPPLIED_UPPER_BOUND' | 'WITHIN_SUPPLIED_RANGE' | 'ONE_SIDED_COMPARISON' | 'UNKNOWN' | 'NOT_ASSESSABLE';
export type ReviewStatus = 'OPEN' | 'FOLLOW_UP_REQUESTED' | 'REVIEWED';
export const REVIEW_STATUSES: ReviewStatus[] = ['OPEN', 'FOLLOW_UP_REQUESTED', 'REVIEWED'];

export interface Source { dataset_id: string; file_name: string; sha256: string; source_row: number | null; source_url: string; license_note: string; imported_at: string }
export interface ReviewState { id: number; status: ReviewStatus; version: number; updated_at: string }

export interface HealthEvidence {
  schema_version: string; evidence_id: string; kind: 'HEALTH_OBSERVATION'; case: 'health'; source: Source;
  context: { participant_id: string; sample_id: string; phase: 'PREFLIGHT' | 'POSTFLIGHT'; visit: string; relative_day: number };
  measurement: { marker: string; label: string; value: number | null; raw_value: string; unit: string; display_decimals: number; range_low: number | null; range_high: number | null; range_status: RangeStatus };
  comparison: { method: string; baseline: number | null; n: number; baseline_values: number[]; delta: number | null; percent_delta: number | null; rule_version: string; retrospective: boolean };
  evidence_strength: string; limitations: string[]; review_state?: ReviewState | null;
}
export interface ConflictGroup { instrument_id: string; source_timestamp: string; rows: { source_row: number; rate: number | null }[] }
export interface EnvEvidence {
  schema_version: string; evidence_id: string; kind: 'DATA_QUALITY' | 'ENV_OBSERVATION'; case: 'environment'; source: Source;
  context: { instrument_id: string; date_text: string | null; participant_id: null };
  title: string; observation: Record<string, unknown>; rule_version: string; evidence_strength: string; limitations: string[];
  review_state?: ReviewState | null;
}
export type Evidence = HealthEvidence | EnvEvidence;

export interface DatasetPublic { id: string; kind: 'HEALTH_CMP' | 'ENV_RADIATION'; title: string; file_name: string; sha256: string; source_url: string; license_note: string; imported_at: string; quality: Record<string, unknown> }
export interface Status { app_version: string; schema_version: number; db: { ok: boolean }; datasets: { id: string; kind: string; file_name: string; sha256: string }[]; assistant_mode: 'VERIFIED_ONLY' | 'VERIFIED_PLUS_LOCAL_AI_DRAFT'; assistant_model: string | null; local_only: boolean }
export interface Sample { sample_id: string; visit: string; phase: 'PREFLIGHT' | 'POSTFLIGHT'; relative_day: number; visit_order: number }
export interface Participants { dataset_id: string; markers: { id: string; label: string; unit: string; dp: number }[]; participants: { id: string; samples: Sample[] }[] }
export interface HealthResponse { dataset: DatasetPublic; sample: { participant_id: string; sample_id: string; visit: string; phase: string }; cards: HealthEvidence[]; to_review: string[]; summary: { outside: number; available: number; total: number; awaiting_follow_up: number } }
export interface TrendPoint { visit: string; phase: string; visit_order: number; sample_id: string; source_row: number; value: number | null; range_low: number | null; range_high: number | null; range_status: RangeStatus; delta: number | null; percent_delta: number | null; evidence_id: string }
export interface Trend { dataset: DatasetPublic; participant_id: string; marker: { id: string; label: string; unit: string; dp: number }; points: TrendPoint[]; baseline: { mean: number | null; n: number; values: number[] }; ranges_consistent: boolean; rule_version: string }
export interface Pt { t: number; ts: string; v: number; row?: number }
export interface Interval { from_ms: number; to_ms: number; from_ts: string; to_ts: string; from_row: number; to_row: number; dt_s: number; accepted: boolean; reason: string | null; dose_uGy: number | null; cumulative_uGy: number }
export interface EnvResponse {
  dataset: DatasetPublic; instrument: string; instruments: string[];
  banner: { location: string; instrument: string; date_text: string | null; location_note: string };
  quality: { raw_rows: number; unique_timestamps: number; conflict_groups: number; quarantined_rows: number; accepted_rows: number; first_timestamp: string; last_timestamp: string; status_counts: Record<string, number> };
  conflict_groups: ConflictGroup[];
  integration: { method: string; formula: string; max_gap_s: number; rule_version: string; unit: string; estimated_sensor_dose_uGy: number; covered_seconds: number; accepted_points: number; intervals_total: number; excluded_intervals: Interval[]; excluded_by_reason: Record<string, number>; rate_segments: Pt[][]; dose_segments: Pt[][]; isolated_points: Pt[] };
  findings: EnvEvidence[];
  table: { source_row: number; source_timestamp: string; rate: number | null; raw_rate: string; quality_status: string; interval_s: number | null; interval_reason: string | null; interval_accepted: boolean | null; cumulative_uGy: number | null }[];
  limitations: string[];
}
export interface Verified { mode: 'VERIFIED_EXPLANATION'; question_id: string; title: string; paragraphs: string[]; source_ids: string[] }
export interface AiResult { status: 'OFF' | 'DRAFT' | 'FALLBACK'; reason?: string; label?: string; model?: string; draft?: { summary: string; source_ids: string[]; limitations: string[] } }
export interface ExplainResponse { verified: Verified; ai: AiResult; assistant_mode: string }
export interface ReviewEvent { id: number; action: string; before: Record<string, unknown> | null; after: Record<string, unknown> | null; timestamp: string }
export interface Review { id: number; finding_id: string; status: ReviewStatus; note: string; follow_up_date: string | null; created_at: string; updated_at: string; version: number; evidence: Evidence; case: 'health' | 'environment'; participant_id: string | null; instrument_id: string | null; title: string; events?: ReviewEvent[] }
export interface ReviewList { total: number; items: Review[]; limit: number; offset: number }
export interface ImportReport { status: 'IMPORTED' | 'ALREADY_IMPORTED'; dataset_id: string; kind: string; file_name: string; sha256: string; quality: Record<string, unknown> }
