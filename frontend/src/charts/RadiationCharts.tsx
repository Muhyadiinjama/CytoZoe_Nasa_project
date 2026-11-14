import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EnvironmentView, EnvPoint } from "../api/contracts";
import { clock, fmt, timeOnly } from "../lib/format";

const DATA = "#1F4E79";
const ERROR = "#B42318";
const TICKS = Array.from({ length: 9 }, (_, i) => i * 10800);

function axisProps() {
  return {
    type: "number" as const, dataKey: "t", domain: [0, 86400] as [number, number], ticks: TICKS,
    tickFormatter: (v: number) => clock(v), tick: { fill: "#53697D", fontSize: 12 }, tickLine: false,
    axisLine: { stroke: "#DDE5EB" }, allowDuplicatedCategory: false,
  };
}

function Tip({ active, payload, kind }: { active?: boolean; payload?: { payload: EnvPoint }[]; kind: "rate" | "dose" }) {
  const p = active && payload?.length ? payload[0].payload : null;
  if (!p) return null;
  return (
    <div className="chart-tooltip">
      <strong>{timeOnly(p.ts)} <span className="meta">source clock</span></strong>
      {kind === "rate" ? `${fmt(p.rate, 3)} µGy/hour` : `${fmt(p.cumulative, 3)} µGy accumulated`}
      <div className="meta">Data row {p.source_row}</div>
    </div>
  );
}

/** Chart 2 — absorbed dose rate vs source timestamp; one line per accepted segment, never bridged. */
export function RadiationRateChart({ env, logScale }: { env: EnvironmentView; logScale: boolean }) {
  return (
    <div className="chart-box tall" role="img"
      aria-label={`DosTel1 absorbed dose rate in µGy per hour across 1 March 2022, drawn as ${env.segments.length} separate segments broken at ${env.quality.conflict_groups.length} excluded conflict timestamps. Values are in the data table below.`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart margin={{ top: 12, right: 16, bottom: 28, left: 8 }} accessibilityLayer={false}>
          <CartesianGrid stroke="#E6ECF1" vertical={false} />
          <XAxis {...axisProps()} label={{ value: "Source timestamp, 1 March 2022 (as exported; no timezone)", position: "insideBottom", offset: -18, fill: "#53697D", fontSize: 12 }} />
          <YAxis scale={logScale ? "log" : "linear"} domain={logScale ? [1, 1000] : [0, "auto"]} allowDataOverflow={logScale}
            ticks={logScale ? [1, 3, 10, 30, 100, 300, 1000] : undefined}
            tick={{ fill: "#53697D", fontSize: 12 }} tickLine={false} axisLine={false} width={64} tickFormatter={(v: number) => fmt(v, 1)}
            label={{ value: "Absorbed dose rate (µGy/hour)", angle: -90, position: "insideLeft", offset: 4, fill: "#53697D", fontSize: 12, style: { textAnchor: "middle" } }} />
          {env.quality.conflict_groups.map((g) => (
            <ReferenceLine key={g.timestamp} x={g.t} stroke={ERROR} strokeDasharray="3 3" strokeWidth={1.4} />
          ))}
          {env.segments.map((s) => (
            <Line key={s.index} data={s.points} dataKey="rate" type="linear" stroke={DATA} strokeWidth={1.4} dot={false}
              isAnimationActive={false} connectNulls={false} name={`Segment ${s.index + 1}`} activeDot={{ r: 4 }} />
          ))}
          <Tooltip content={<Tip kind="rate" />} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Chart 3 — estimated accumulated sensor dose over accepted intervals; flat and visibly broken across exclusions. */
export function SensorDoseChart({ env }: { env: EnvironmentView }) {
  return (
    <div className="chart-box" role="img"
      aria-label={`Estimated accumulated sensor dose in µGy over covered intervals, reaching ${fmt(env.integration.estimated_sensor_dose_uGy, 2)} µGy. The line is interrupted wherever intervals were excluded.`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart margin={{ top: 12, right: 16, bottom: 28, left: 8 }} accessibilityLayer={false}>
          <CartesianGrid stroke="#E6ECF1" vertical={false} />
          <XAxis {...axisProps()} label={{ value: "Source timestamp, 1 March 2022", position: "insideBottom", offset: -18, fill: "#53697D", fontSize: 12 }} />
          <YAxis domain={[0, "auto"]} tick={{ fill: "#53697D", fontSize: 12 }} tickLine={false} axisLine={false} width={64}
            tickFormatter={(v: number) => fmt(v, 0)}
            label={{ value: "Estimated sensor dose (µGy)", angle: -90, position: "insideLeft", offset: 4, fill: "#53697D", fontSize: 12, style: { textAnchor: "middle" } }} />
          {env.quality.conflict_groups.map((g) => (
            <ReferenceLine key={g.timestamp} x={g.t} stroke={ERROR} strokeDasharray="3 3" strokeWidth={1.4} />
          ))}
          {env.segments.map((s) => (
            <Line key={s.index} data={s.points} dataKey="cumulative" type="linear" stroke={DATA} strokeWidth={2} dot={false}
              isAnimationActive={false} name={`Segment ${s.index + 1}`} activeDot={{ r: 4 }} />
          ))}
          <Tooltip content={<Tip kind="dose" />} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RadiationLegend() {
  return (
    <div className="chart-legend" aria-hidden="true">
      <span className="legend-item"><span className="legend-swatch" />Accepted readings (segments are never joined)</span>
      <span className="legend-item"><span className="legend-swatch gap" />Excluded conflict timestamp</span>
    </div>
  );
}
