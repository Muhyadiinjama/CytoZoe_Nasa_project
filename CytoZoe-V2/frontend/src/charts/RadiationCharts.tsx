import { useMemo, useState } from 'react';
import type { EnvResponse, Pt } from '../api/contracts';
import { num } from '../lib/format';
import { useWidth } from '../lib/hooks';
import { Swatch } from './Legend';
import { C, hh, hourTicks, niceTicks } from './util';

const M = { l: 60, r: 16, t: 16, b: 46 };

function Frame({ W, H, t0, t1, yTicks, yLabel, X, Y, env, children }: {
  W: number; H: number; t0: number; t1: number; yTicks: number[]; yLabel: string; X: (t: number) => number; Y: (v: number) => number; env: EnvResponse; children: unknown;
}) {
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
      {yTicks.map((t) => <g key={t}><line x1={M.l} x2={W - M.r} y1={Y(t)} y2={Y(t)} stroke={C.grid} /><text x={M.l - 8} y={Y(t) + 4} textAnchor="end">{String(+t.toFixed(2))}</text></g>)}
      {hourTicks(t0, t1).map((t) => <g key={t}><line x1={X(t)} x2={X(t)} y1={M.t} y2={H - M.b} stroke={C.grid} /><text x={X(t)} y={H - M.b + 18} textAnchor="middle">{hh(t)}</text></g>)}
      <text x={14} y={M.t + 8} transform={`rotate(-90 14 ${M.t + 8})`} textAnchor="end">{yLabel}</text>
      <text x={(M.l + W - M.r) / 2} y={H - 6} textAnchor="middle">Source timestamp, {env.banner.date_text} (no timezone stated by the source)</text>
      {env.integration.excluded_intervals.map((iv) => (
        <rect key={iv.from_ms} x={X(iv.from_ms)} y={M.t} width={Math.max(3, X(iv.to_ms) - X(iv.from_ms))} height={H - M.t - M.b} fill={C.reviewBg} stroke={C.review} strokeWidth={0.6} />
      ))}
      {children as never}
    </svg>
  );
}

function bounds(env: EnvResponse) {
  const all = [...env.integration.rate_segments.flat(), ...env.integration.isolated_points];
  const t0 = Math.min(...all.map((p) => p.t), ...env.integration.excluded_intervals.map((i) => i.from_ms));
  const t1 = Math.max(...all.map((p) => p.t), ...env.integration.excluded_intervals.map((i) => i.to_ms));
  return { all, t0, t1 };
}

/** Chart 2: dose rate of accepted readings. Lines join only accepted intervals; excluded intervals are shaded and never bridged. */
export function RadiationRateChart({ env }: { env: EnvResponse }) {
  const [ref, w] = useWidth<HTMLDivElement>();
  const { all, t0, t1 } = useMemo(() => bounds(env), [env]);
  const pts = useMemo(() => [...all].sort((a, b) => a.t - b.t), [all]);
  const [idx, setIdx] = useState<number | null>(null);
  const W = Math.max(300, w || 800), H = 300;
  const yTicks = niceTicks(0, Math.max(...pts.map((p) => p.v)) * 1.05, 5);
  const X = (t: number) => M.l + ((t - t0) / (t1 - t0)) * (W - M.l - M.r);
  const Y = (v: number) => M.t + (1 - v / yTicks[yTicks.length - 1]) * (H - M.t - M.b);
  const cur: Pt | null = idx === null ? null : pts[idx];
  const move = (i: number) => setIdx(Math.max(0, Math.min(pts.length - 1, i)));
  return (
    <div>
      <div className="chart" ref={ref} tabIndex={0} role="group" data-testid="rate-chart"
        aria-label={`Absorbed dose rate, ${env.integration.accepted_points} accepted readings. Use left and right arrow keys, Home and End to read values. A data table follows.`}
        onKeyDown={(e: { key: string; preventDefault(): void }) => {
          const k = e.key; if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(k)) return; e.preventDefault();
          if (k === 'Home') move(0); else if (k === 'End') move(pts.length - 1); else move((idx ?? (k === 'ArrowRight' ? -1 : pts.length)) + (k === 'ArrowRight' ? 1 : -1));
        }}
        onPointerMove={(e: { clientX: number; currentTarget: HTMLElement }) => {
          const r = e.currentTarget.getBoundingClientRect(); const t = t0 + ((e.clientX - r.left - M.l) / (W - M.l - M.r)) * (t1 - t0);
          let best = 0, bd = Infinity; pts.forEach((p, i) => { const d = Math.abs(p.t - t); if (d < bd) { bd = d; best = i; } }); setIdx(best);
        }}>
        <Frame W={W} H={H} t0={t0} t1={t1} yTicks={yTicks} yLabel="µGy/hour" X={X} Y={Y} env={env}>
          {env.integration.rate_segments.map((seg, i) => <polyline key={i} points={seg.map((p) => `${X(p.t).toFixed(1)},${Y(p.v).toFixed(1)}`).join(' ')} fill="none" stroke={C.teal} strokeWidth={1.6} strokeLinejoin="round" />)}
          {env.integration.isolated_points.map((p) => <circle key={p.t} cx={X(p.t)} cy={Y(p.v)} r={2.5} fill={C.teal} />)}
          {cur ? <circle cx={X(cur.t)} cy={Y(cur.v)} r={5} fill="#fff" stroke={C.ink} strokeWidth={2} /> : null}
        </Frame>
      </div>
      <div className="readout" aria-live="polite" data-testid="rate-readout">
        {cur ? `${cur.ts} source time · ${num(cur.v, 3)} µGy/h · source line ${cur.row ?? '—'}` : 'Point at the chart, or focus it and use the arrow keys, to read a value.'}
      </div>
      <div className="legend"><span><Swatch kind="line" /> Accepted readings, joined only across accepted intervals</span><span><Swatch kind="excl" /> Excluded interval (conflict or gap): no line or dose across it</span></div>
    </div>
  );
}

/** Chart 3: estimated accumulated sensor dose over covered intervals; flat-free and discontinuous across exclusions. */
export function SensorDoseChart({ env }: { env: EnvResponse }) {
  const [ref, w] = useWidth<HTMLDivElement>();
  const { t0, t1 } = useMemo(() => bounds(env), [env]);
  const W = Math.max(300, w || 800), H = 280;
  const total = env.integration.estimated_sensor_dose_uGy;
  const yTicks = niceTicks(0, Math.max(total, 0.001) * 1.05, 5);
  const X = (t: number) => M.l + ((t - t0) / (t1 - t0)) * (W - M.l - M.r);
  const Y = (v: number) => M.t + (1 - v / yTicks[yTicks.length - 1]) * (H - M.t - M.b);
  return (
    <div>
      <div className="chart" ref={ref} role="img" data-testid="dose-chart"
        aria-label={`Estimated dose accumulated over covered intervals at the sensor: ${num(total, 3)} micrograys over ${num(env.integration.covered_seconds / 3600, 2)} hours covered. The line stops at each excluded interval. A data table follows.`}>
        <Frame W={W} H={H} t0={t0} t1={t1} yTicks={yTicks} yLabel="µGy (accumulated)" X={X} Y={Y} env={env}>
          {env.integration.dose_segments.map((seg, i) => <polyline key={i} points={seg.map((p) => `${X(p.t).toFixed(1)},${Y(p.v).toFixed(1)}`).join(' ')} fill="none" stroke={C.teal} strokeWidth={2} />)}
        </Frame>
      </div>
      <div className="legend"><span><Swatch kind="line" /> Estimated accumulated sensor dose (accepted intervals only)</span><span><Swatch kind="excl" /> Excluded interval</span></div>
    </div>
  );
}
