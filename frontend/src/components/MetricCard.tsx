import type { HealthEvidence } from "../api/contracts";
import { useDrawer } from "../app/providers";
import { fmt, rangeText, REVIEW_LABEL, signed } from "../lib/format";
import { RangeStatusLine } from "./EvidencePanel";

/**
 * Presentation-only position of the reported value against the two supplied bounds.
 * Nothing is classified here: the range status text above it comes from the backend.
 */
function RangeTrack({ value, low, high, flagged }: { value: number; low: number; high: number; flagged: boolean }) {
  const span = high - low || Math.abs(high) || 1;
  const d0 = Math.min(low, value) - span * 0.3;
  const d1 = Math.max(high, value) + span * 0.3;
  const pct = (x: number) => ((x - d0) / (d1 - d0)) * 100;
  return (
    <div className="range-track" aria-hidden="true">
      <span className="rail" />
      <span className="band" style={{ left: `${pct(low)}%`, width: `${pct(high) - pct(low)}%` }} />
      <span className={`pin${flagged ? " flag" : ""}`} style={{ left: `${pct(value)}%` }} />
    </div>
  );
}

export function MetricCard({ ev }: { ev: HealthEvidence }) {
  const { open } = useDrawer();
  const m = ev.measurement;
  const c = ev.comparison;
  return (
    <article className={`metric is-changed${m.needs_review ? " is-flagged" : ""}`} aria-labelledby={`mc-${m.marker}`}>
      <h3 className="metric-name" id={`mc-${m.marker}`}>{m.marker_name}</h3>
      <div className="metric-value-row">
        {m.value === null ? <span className="metric-value" style={{ fontSize: 20 }}>No value</span> : (
          <><span className="metric-value">{fmt(m.value)}</span><span className="metric-unit">{m.unit}</span></>
        )}
      </div>
      {m.value !== null && m.range_low !== null && m.range_high !== null
        ? <RangeTrack value={m.value} low={m.range_low} high={m.range_high} flagged={m.needs_review} /> : null}
      <span className="meta">Supplied range {rangeText(m.range_low, m.range_high, m.unit)}</span>
      <RangeStatusLine status={m.range_status} />
      <p className="metric-delta">
        {c.delta === null
          ? c.baseline_available ? "No comparison available" : "Personal mean not computed (n < 2)"
          : <>vs preflight mean {fmt(c.baseline, 2)}: <span className="tabular">{signed(c.delta, 2)} {m.unit}</span>{c.percent_delta !== null ? ` (${signed(c.percent_delta, 1)}%)` : ""}</>}
      </p>
      <div className="metric-foot">
        {ev.review ? <span className="badge badge-teal">{REVIEW_LABEL[ev.review.status]}</span> : <span className="meta">Not reviewed</span>}
        <button type="button" className="btn btn-ghost btn-sm" aria-label={`Inspect ${m.marker_name} evidence`}
          onClick={() => open({ kind: "evidence", id: ev.evidence_id })}>Inspect</button>
      </div>
    </article>
  );
}
