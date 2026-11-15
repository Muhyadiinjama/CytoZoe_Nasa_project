import {
  CartesianGrid, ComposedChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis,
} from "recharts";
import type { HealthTrend, TrendPoint } from "../api/contracts";
import { fmt, RANGE_TEXT, rangeText, signed } from "../lib/format";

const DATA = "#2F5A7A";
const REVIEW = "#9A4B08";
const BASELINE = "#6B6760";

export type ChartMode = "absolute" | "delta";

interface ChartPoint extends TrendPoint {
  x: string; shownValue: number | null; shownLow: number | null; shownHigh: number | null;
}
interface DotProps { cx?: number; cy?: number; payload?: ChartPoint }

/** Round axis bounds to a 1/2/5 × 10^k step so tick labels are readable values. */
export function niceScale(lo: number, hi: number, target = 5): { domain: [number, number]; ticks: number[] } {
  const span = hi - lo || Math.abs(hi) || 1;
  const raw = (span * 1.2) / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const start = Math.floor((lo - span * 0.08) / step) * step;
  const end = Math.ceil((hi + span * 0.08) / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= end + step / 2; v += step) ticks.push(Number(v.toFixed(6)));
  return { domain: [ticks[0], ticks[ticks.length - 1]], ticks };
}

/**
 * Chart 1 — actual sample visits (categorical, not equally spaced in time) × marker value.
 * Dots only: no interpolation or smoothed curve between sparse blood draws.
 */
export function HealthVisitChart({ trend, selectedVisit, onSelect, mode = "absolute" }: {
  trend: HealthTrend; selectedVisit: string; onSelect: (visit: string) => void; mode?: ChartMode;
}) {
  const pts = trend.points;
  const isDelta = mode === "delta" && trend.baseline.available && trend.baseline.value !== null;
  const shown = (p: TrendPoint) => isDelta
    ? { value: p.delta, low: p.range_low_delta, high: p.range_high_delta }
    : { value: p.value, low: p.range_low, high: p.range_high };
  const nums = pts.flatMap((p) => { const s = shown(p); return [s.value, s.low, s.high]; })
    .concat(isDelta ? [0] : [trend.baseline.value])
    .filter((v): v is number => v !== null && Number.isFinite(v));
  const lo = nums.length ? Math.min(...nums) : 0;
  const hi = nums.length ? Math.max(...nums) : 1;
  const { domain, ticks } = niceScale(lo === hi ? lo - 1 : lo, hi === lo ? hi + 1 : hi);
  const data: ChartPoint[] = pts.map((p) => {
    const s = shown(p);
    return { ...p, x: p.visit, shownValue: s.value, shownLow: s.low, shownHigh: s.high };
  });
  const band = isDelta
    ? (pts.find((p) => p.range_low_delta !== null && p.range_high_delta !== null) ?? null)
    : null;
  const bandLow = isDelta ? band?.range_low_delta ?? null : trend.range_low;
  const bandHigh = isDelta ? band?.range_high_delta ?? null : trend.range_high;
  const reference = isDelta ? 0 : trend.baseline.value;

  const Dot = ({ cx, cy, payload }: DotProps) => {
    if (cx === undefined || cy === undefined || !payload || payload.shownValue === null) return <g />;
    const selected = payload.visit === selectedVisit;
    const flagged = payload.needs_review;
    return (
      <g style={{ cursor: "pointer" }} onClick={() => onSelect(payload.visit)}>
        {selected ? <circle cx={cx} cy={cy} r={10} fill="none" stroke={DATA} strokeWidth={2} /> : null}
        <circle cx={cx} cy={cy} r={flagged ? 6.5 : 5.5} fill={flagged ? "#FFFFFF" : DATA} stroke={flagged ? REVIEW : DATA} strokeWidth={flagged ? 2.5 : 1.5} />
      </g>
    );
  };
  const BoundTick = ({ cx, cy }: DotProps) => (cx === undefined || cy === undefined ? <g /> : <line x1={cx - 14} x2={cx + 14} y1={cy} y2={cy} stroke="#8A8478" strokeWidth={2} />);
  const MeanLabel = ({ viewBox }: { viewBox?: { x: number; y: number; width: number; height: number } }) => {
    if (!viewBox) return <g />;
    const text = isDelta ? "Baseline" : "Preflight mean";
    const x = viewBox.x + viewBox.width + 8;
    const y = viewBox.y + 4;
    const width = text.length * 6.1 + 10;
    return (
      <g>
        <title>{isDelta ? "Baseline reference, change = 0" : `Preflight mean, n = ${trend.baseline.n}`}</title>
        <rect x={x} y={y - 13} width={width} height={16} rx={4} fill="#FFFFFF" fillOpacity={0.92} />
        <text x={x + 5} y={y} textAnchor="start" fill={BASELINE} fontSize={11}>{text}</text>
      </g>
    );
  };
  const selectedPoint = pts.find((p) => p.visit === selectedVisit);
  const selectedSummary = selectedPoint && selectedPoint.value !== null
    ? `${selectedPoint.visit_label}: ${fmt(selectedPoint.value)} ${trend.unit}, ${RANGE_TEXT[selectedPoint.range_status]}`
    : "No selected value";

  return (
    <div className="chart-box" role="img"
      aria-label={`${trend.marker_name} for ${trend.participant_id} across ${pts.length} historical visits in ${trend.unit}. ${selectedSummary}${isDelta ? ". Shown as change from the retrospective preflight mean" : ""}. Full values are in the data table below the chart.`}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 24, right: 104, bottom: 40, left: 8 }} accessibilityLayer={false}>
          <CartesianGrid stroke="#EEEAE1" vertical={false} />
          {trend.bounds_consistent && bandLow !== null && bandHigh !== null ? (
            <ReferenceArea y1={bandLow} y2={bandHigh} fill="#F3EFE7" fillOpacity={0.6} stroke="none" ifOverflow="extendDomain" />
          ) : null}
          <XAxis dataKey="x" type="category" tick={{ fill: "#625E57", fontSize: 13 }} tickLine={false} axisLine={{ stroke: "#E7E2D7" }} tickMargin={8} padding={{ left: 10, right: 10 }}
            label={{ value: "Visit", position: "insideBottom", offset: -20, fill: "#625E57", fontSize: 12 }} />
          <YAxis domain={domain} ticks={ticks} interval={0} tick={{ fill: "#625E57", fontSize: 13 }} tickLine={false} axisLine={false} width={64} tickMargin={6}
            tickFormatter={(v: number) => fmt(v, 2)}
            label={{ value: isDelta ? `${trend.marker_name} change from preflight mean (${trend.unit})` : `${trend.marker_name} (${trend.unit})`,
              angle: -90, position: "insideLeft", offset: 8, fill: "#625E57", fontSize: 12, style: { textAnchor: "middle" } }} />
          {reference !== null ? (
            <ReferenceLine y={reference} stroke={BASELINE} strokeDasharray="6 5" strokeWidth={1.8} label={<MeanLabel />} />
          ) : null}
          <ReferenceLine x="R+1" stroke="#D5CEC0" strokeDasharray="2 4"
            label={{ value: "Return", position: "insideTop", fill: "#8A8478", fontSize: 11 }} />
          {!trend.bounds_consistent ? (
            <>
              <Scatter dataKey="shownLow" shape={BoundTick} isAnimationActive={false} legendType="none" name="Supplied lower bound" />
              <Scatter dataKey="shownHigh" shape={BoundTick} isAnimationActive={false} legendType="none" name="Supplied upper bound" />
            </>
          ) : null}
          <Scatter dataKey="shownValue" shape={Dot} isAnimationActive={false} name={trend.marker_name} />
          <Tooltip cursor={{ fill: "rgba(47,90,122,0.06)" }} content={({ active, payload }) => {
            const p = active && payload?.length ? (payload[0].payload as ChartPoint) : null;
            if (!p) return null;
            return (
              <div className="chart-tooltip">
                <strong>{p.visit_label}</strong>
                {p.value === null ? "No value" : `${fmt(p.value)} ${trend.unit}`}
                {isDelta && p.delta !== null ? (
                  <div className="meta tabular">Δ {signed(p.delta)} {trend.unit}{p.percent_delta !== null ? ` (${signed(p.percent_delta, 1)}%)` : ""}</div>
                ) : null}
                <div className="meta">{RANGE_TEXT[p.range_status]} · {rangeText(p.range_low, p.range_high, trend.unit)}</div>
              </div>
            );
          }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HealthChartLegend({ trend, mode = "absolute" }: { trend: HealthTrend; mode?: ChartMode }) {
  return (
    <div className="chart-legend health-legend" aria-hidden="true">
      <span className="legend-item"><span className="legend-swatch dot" />Measured sample</span>
      <span className="legend-item"><span className="legend-swatch flag" />Outside supplied range</span>
      <span className="legend-item"><span className="legend-swatch dashed" />{mode === "delta" ? "Baseline (Δ = 0)" : "Preflight mean"}</span>
      {trend.bounds_consistent
        ? <span className="legend-item"><span className="legend-swatch band" />Supplied range</span>
        : <span className="legend-item"><span className="legend-swatch" style={{ borderTop: "2px solid #8A8478" }} />Supplied bounds per visit</span>}
    </div>
  );
}
