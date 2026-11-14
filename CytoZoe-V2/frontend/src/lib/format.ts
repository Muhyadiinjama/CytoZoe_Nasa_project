import type { RangeStatus, ReviewStatus } from '../api/contracts';

export const num = (v: number | null | undefined, dp: number) => (v === null || v === undefined ? 'n/a' : v.toFixed(dp));
export const signed = (v: number | null | undefined, dp: number) =>
  v === null || v === undefined ? 'n/a' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(dp)}`;
export const when = (iso: string | null | undefined) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
};
export const statusLabel = (s: ReviewStatus) => ({ OPEN: 'Open', FOLLOW_UP_REQUESTED: 'Follow-up requested', REVIEWED: 'Reviewed' })[s];
export const isOutside = (s: RangeStatus) => s === 'ABOVE_SUPPLIED_UPPER_BOUND' || s === 'BELOW_SUPPLIED_LOWER_BOUND';
export const rangeText = (s: RangeStatus) => ({
  ABOVE_SUPPLIED_UPPER_BOUND: 'Outside supplied range (above)',
  BELOW_SUPPLIED_LOWER_BOUND: 'Outside supplied range (below)',
  WITHIN_SUPPLIED_RANGE: 'Within supplied range',
  ONE_SIDED_COMPARISON: 'Within the one supplied bound',
  UNKNOWN: 'No supplied range to compare',
  NOT_ASSESSABLE: 'Not assessable (no value)',
})[s];
export const visitLabel = (visit: string) => `${visit} · ${visit.startsWith('L') ? 'Preflight' : 'After return'}`;
export const bound = (v: number | null, missing: string) => (v === null ? missing : String(v));
export const reasonText = (r: string | null) => ({
  CONFLICT_INSIDE: 'conflicting timestamp inside', GAP_OVER_LIMIT: 'gap over 300 s', INVALID_READING_INSIDE: 'invalid reading inside',
  NON_POSITIVE_INTERVAL: 'non-positive interval',
} as Record<string, string>)[r ?? ''] ?? (r ?? '');
