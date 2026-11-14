import type { HealthEvidence } from "../api/contracts";
import { useDrawer } from "../app/providers";
import { fmt, REVIEW_LABEL, signed } from "../lib/format";
import { RangeStatusLine } from "./EvidencePanel";

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
