import type { Trend } from '../api/contracts';
import { isOutside, num } from '../lib/format';
import { useWidth } from '../lib/hooks';
import { Swatch } from './Legend';
import { C, niceTicks } from './util';

/** Chart 1: actual sample visits (categorical, not to time scale), measured dots, dashed retrospective preflight mean,
 *  supplied range band only when every sample has the same bounds (otherwise per-sample whiskers). No interpolation. */
export function HealthVisitChart({ trend, selected, onSelect }: { trend: Trend; selected: string; onSelect: (visit: string) => void }) {
  const [ref, w] = useWidth<HTMLDivElement>();
  const W = Math.max(280, w || 640), H = W < 520 ? 300 : 340, m = { l: 60, r: 20, t: 22, b: 52 };
  const pts = trend.points, dp = trend.marker.dp + 1;
  const vals = pts.filter((p) => p.value !== null).map((p) => p.value as number);
  let lo = Math.min(...vals), hi = Math.max(...vals);
  pts.forEach((p) => { if (p.range_low !== null) lo = Math.min(lo, p.range_low); if (p.range_high !== null) hi = Math.max(hi, p.range_high); });
  if (trend.baseline.mean !== null) { lo = Math.min(lo, trend.baseline.mean); hi = Math.max(hi, trend.baseline.mean); }
  const pad = (hi - lo) * 0.12 || Math.abs(hi) * 0.1 || 1; lo -= pad; hi += pad;
  const X = (i: number) => m.l + (pts.length === 1 ? (W - m.l - m.r) / 2 : (i * (W - m.l - m.r)) / (pts.length - 1));
  const Y = (v: number) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  const p0 = pts.find((p) => p.value !== null);
  const firstPost = pts.findIndex((p) => p.phase === 'POSTFLIGHT');
  const tickDp = trend.marker.dp > 0 ? Math.min(trend.marker.dp + 1, 2) : 0;
  return (
    <div>
      <div className="chart" ref={ref}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="group" aria-label={`${trend.marker.label} in ${trend.marker.unit} by actual visit for ${trend.participant_id}. Each dot is a real sample; use Tab and Enter to select one. A table with every value follows.`}>
          {niceTicks(lo, hi, 5).map((t) => <g key={t}><line x1={m.l} x2={W - m.r} y1={Y(t)} y2={Y(t)} stroke={C.grid} /><text x={m.l - 8} y={Y(t) + 4} textAnchor="end">{t.toFixed(tickDp)}</text></g>)}
          <text x={14} y={m.t + 8} transform={`rotate(-90 14 ${m.t + 8})`} textAnchor="end">{trend.marker.label} ({trend.marker.unit})</text>
          {trend.ranges_consistent && p0 && p0.range_low !== null && p0.range_high !== null
            ? <rect x={m.l} y={Y(p0.range_high)} width={W - m.l - m.r} height={Y(p0.range_low) - Y(p0.range_high)} fill={C.band} />
            : pts.map((p, i) => (p.range_low !== null && p.range_high !== null ? (
              <g key={'w' + i} stroke={C.ctrl} strokeWidth={2}>
                <line x1={X(i)} x2={X(i)} y1={Y(p.range_low)} y2={Y(p.range_high)} />
                <line x1={X(i) - 5} x2={X(i) + 5} y1={Y(p.range_low)} y2={Y(p.range_low)} />
                <line x1={X(i) - 5} x2={X(i) + 5} y1={Y(p.range_high)} y2={Y(p.range_high)} />
              </g>) : null))}
          {trend.baseline.mean !== null ? <g>
            <line x1={m.l} x2={W - m.r} y1={Y(trend.baseline.mean)} y2={Y(trend.baseline.mean)} stroke={C.base} strokeWidth={2} strokeDasharray="6 5" />
          </g> : null}
          {firstPost > 0 ? (() => { const xb = (X(firstPost - 1) + X(firstPost)) / 2; return <g>
            <line x1={xb} x2={xb} y1={m.t} y2={H - m.b} stroke={C.ctrl} strokeDasharray="2 4" />
            <text x={xb - 6} y={H - m.b - 6} textAnchor="end">Before launch</text><text x={xb + 6} y={H - m.b - 6}>After return</text>
          </g>; })() : null}
          {pts.map((p, i) => {
            const sel = p.visit === selected, out = isOutside(p.range_status);
            return <g key={p.visit}>
              <text x={X(i)} y={H - m.b + 20} textAnchor="middle" fontWeight={sel ? 700 : 400} style={sel ? { fill: C.ink } : undefined}>{p.visit}</text>
              {p.value === null ? <text x={X(i)} y={H - m.b - 22} textAnchor="middle">no value</text> : (
                <g className="pt" tabIndex={0} role="button" aria-pressed={sel}
                  aria-label={`${p.visit}: ${num(p.value, dp)} ${trend.marker.unit}, ${out ? 'outside supplied range' : 'not outside supplied range'}${sel ? ', selected' : ''}`}
                  style={{ cursor: 'pointer' }} onClick={() => onSelect(p.visit)}
                  onKeyDown={(e: { key: string; preventDefault(): void }) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(p.visit); } }}>
                  {sel ? <circle cx={X(i)} cy={Y(p.value)} r={13} fill="none" stroke={C.teal} strokeWidth={2} /> : null}
                  {out ? <path d={`M${X(i)} ${Y(p.value) - 9} L${X(i) + 9} ${Y(p.value)} L${X(i)} ${Y(p.value) + 9} L${X(i) - 9} ${Y(p.value)} Z`} fill={C.review} stroke="#fff" strokeWidth={2} />
                    : <circle cx={X(i)} cy={Y(p.value)} r={7} fill={C.teal} stroke="#fff" strokeWidth={2} />}
                  <circle cx={X(i)} cy={Y(p.value)} r={18} fill="transparent" />
                  <title>{`${p.visit}: ${num(p.value, dp)} ${trend.marker.unit}`}</title>
                </g>)}
            </g>;
          })}
        </svg>
      </div>
      <div className="legend">
        <span><Swatch kind="dot" /> Measured sample</span><span><Swatch kind="diamond" /> Measured, outside supplied range</span>
        <span><Swatch kind="dash" /> Calculated retrospective preflight mean{trend.baseline.mean !== null ? ` ${num(trend.baseline.mean, dp)} (n=${trend.baseline.n})` : ' (not available)'}</span>
        <span><Swatch kind="band" /> {trend.ranges_consistent ? 'Supplied range (source)' : 'Supplied range per sample (source)'}</span>
      </div>
    </div>
  );
}
