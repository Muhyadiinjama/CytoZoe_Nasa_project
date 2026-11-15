import type { ReactNode } from "react";
import type { CalculationStep, EnvConflictMeasurement, EnvEvidence, EnvSummaryMeasurement, Evidence, HealthEvidence, RangeStatus } from "../api/contracts";
import { duration, fmt, RANGE_TEXT, rangeText, REVIEW_LABEL, signed } from "../lib/format";
import { IconFlag, IconInfo } from "./icons";

function Step({ n, label, children }: { n: number; label: string; children: ReactNode }) {
  return (
    <section className="ev-step" aria-label={label}>
      <span className="ev-num" aria-hidden="true">{n}</span>
      <div style={{ minWidth: 0 }}>
        <h3 className="ev-label">{label}</h3>
        {children}
      </div>
    </section>
  );
}

export function RangeStatusLine({ status }: { status: HealthEvidence["measurement"]["range_status"] }) {
  const flagged = status === "ABOVE_SUPPLIED_UPPER_BOUND" || status === "BELOW_SUPPLIED_LOWER_BOUND";
  return (
    <span className={`metric-status ${flagged ? "status-review" : "status-neutral"}`}>
      {flagged ? <IconFlag /> : <IconInfo />}
      {RANGE_TEXT[status]}
    </span>
  );
}

function stepResult(s: CalculationStep): string {
  if (!s.available) return "Not computed";
  if (typeof s.result === "string") return RANGE_TEXT[s.result as RangeStatus] ?? s.result;
  if (s.result === null) return "—";
  return s.unit === "%" ? `${fmt(s.result, 2)} %` : `${fmt(s.result, 6)} ${s.unit}`;
}

function SourceStep({ ev, children }: { ev: Evidence; children?: ReactNode }) {
  const s = ev.source;
  return (
    <>
      <dl className="kv small">
        <dt>Dataset</dt><dd>{s.title}</dd>
        <dt>File</dt><dd><code>{s.file_name}</code></dd>
        {children}
      </dl>
      <details className="disclosure" style={{ marginTop: 8 }}>
        <summary>Full provenance</summary>
        <dl className="kv small">
          <dt>Provider</dt><dd>{s.provider}</dd>
          <dt>SHA-256</dt><dd><code title={s.sha256}>{s.sha256}</code></dd>
          <dt>Imported</dt><dd>{s.imported_at}</dd>
          <dt>Licence</dt><dd>{s.license_note}</dd>
        </dl>
        <p className="small" style={{ marginTop: 8 }}>
          Study page: <a href={s.source_url} target="_blank" rel="noreferrer noopener">{s.source_url}</a>
          <span className="meta"> (external link; needs internet)</span>
        </p>
      </details>
    </>
  );
}

export function HealthEvidencePanel({ ev, followUp, variant = "full" }: {
  ev: HealthEvidence; followUp?: ReactNode; variant?: "full" | "trend";
}) {
  if (variant === "trend") return <TrendHealthEvidencePanel ev={ev} followUp={followUp} />;
  const m = ev.measurement;
  const c = ev.comparison;
  const ctx = ev.context;
  return (
    <div className="evidence">
      <Step n={1} label="Observed">
        <div className="ev-big">{m.value === null ? "No value recorded" : <>{fmt(m.value)} <span className="metric-unit">{m.unit}</span></>}</div>
        <p className="small muted">{m.marker_name} · {ctx.participant_id} · {ctx.visit_label} ({Math.abs(ctx.relative_day)} {ctx.relative_day_reference}) · actual sample</p>
        <div style={{ marginTop: 6 }}><RangeStatusLine status={m.range_status} /></div>
      </Step>
      <Step n={2} label="Compared with">
        <dl className="kv small">
          <dt>Supplied laboratory range</dt><dd>{rangeText(m.range_low, m.range_high, m.unit)}</dd>
          <dt>Retrospective preflight mean</dt>
          <dd>{c.baseline_available ? `${fmt(c.baseline)} ${m.unit} (n = ${c.n})` : `Not computed — needs ≥ 2 preflight values (n = ${c.n})`}</dd>
          <dt>Preflight values used</dt>
          <dd>{c.baseline_values.map((b) => `${b.visit}: ${b.value === null ? "missing" : fmt(b.value)}`).join(" · ")}</dd>
          <dt>Difference from mean</dt>
          <dd>{c.delta === null ? "—" : `${signed(c.delta)} ${m.unit}${c.percent_delta === null ? "" : ` (${signed(c.percent_delta, 2)}%)`}`}</dd>
        </dl>
        {c.includes_selected_sample ? (
          <p className="small muted" style={{ marginTop: 6 }}>This preflight sample is one of the values in the mean, so the comparison is retrospective — not a real-time prediction.</p>
        ) : null}
        <p className="small muted" style={{ marginTop: 6 }}>A difference from the personal mean is descriptive; it is not an abnormality threshold.</p>
        {c.calculation_steps?.length ? (
          <details className="disclosure" style={{ marginTop: 8 }}>
            <summary>Worked calculation · {c.calculation_steps.length} steps</summary>
            <ol className="calc-steps">
              {c.calculation_steps.map((s) => (
                <li key={s.label}>
                  <strong>{s.label}</strong>
                  {s.n !== undefined ? <span className="meta"> · n = {s.n}</span> : null}
                  <div className="formula">{s.expression}</div>
                  <div className="small">{stepResult(s)}</div>
                  {s.note ? <p className="meta">{s.note}</p> : null}
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </Step>
      <Step n={3} label="Source">
        <SourceStep ev={ev}>
          <dt>Row</dt><dd>Data row {ev.source.source_row} (file line {ev.source.file_line}) · “{ev.source.sample_name}”</dd>
          <dt>Column</dt><dd><code>{ev.source.source_columns?.value}</code></dd>
          <dt>Raw value</dt><dd>{ev.source.raw_value} ({ev.source.source_unit})</dd>
          <dt>Rule</dt><dd>{c.rule_version}</dd>
        </SourceStep>
      </Step>
      <Step n={4} label="Limits">
        <ul className="ev-list">{ev.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </Step>
      <Step n={5} label="Follow-up">
        {ev.review ? (
          <p className="small" style={{ marginBottom: 8 }}>
            Current review: <span className="badge badge-teal">{REVIEW_LABEL[ev.review.status]}</span> · version {ev.review.version}
          </p>
        ) : <p className="small muted" style={{ marginBottom: 8 }}>No review saved for this result yet.</p>}
        {followUp}
      </Step>
    </div>
  );
}

function shortRangeStatus(status: RangeStatus): string {
  if (status === "ABOVE_SUPPLIED_UPPER_BOUND") return "Above supplied range";
  if (status === "BELOW_SUPPLIED_LOWER_BOUND") return "Below supplied range";
  if (status === "WITHIN_SUPPLIED_RANGE") return "Within supplied range";
  if (status === "ONE_SIDED_COMPARISON") return "One-sided comparison";
  return "Not assessable";
}

function TrendHealthEvidencePanel({ ev, followUp }: { ev: HealthEvidence; followUp?: ReactNode }) {
  const m = ev.measurement;
  const c = ev.comparison;
  const ctx = ev.context;
  const flagged = m.range_status === "ABOVE_SUPPLIED_UPPER_BOUND" || m.range_status === "BELOW_SUPPLIED_LOWER_BOUND";
  const baseline = c.baseline_available && c.baseline !== null ? `${c.baseline.toFixed(2)} ${m.unit} (n = ${c.n})` : `Not computed (n = ${c.n})`;
  const difference = c.delta === null
    ? "—"
    : `${signed(c.delta, 2)} ${m.unit}${c.percent_delta === null ? "" : ` (${signed(c.percent_delta, 1)}%)`}`;
  return (
    <div className="evidence evidence-trend">
      <section className="ev-section">
        <h3 className="ev-label">Observed</h3>
        <div className="ev-big">{m.value === null ? "No value recorded" : <>{fmt(m.value)} <span className="metric-unit">{m.unit}</span></>}</div>
        <p className="ev-meta">{Math.abs(ctx.relative_day)} {ctx.relative_day_reference}</p>
        <span className={`status-chip${flagged ? " is-flagged" : ""}`}>
          {flagged ? <IconFlag /> : <IconInfo />}
          {shortRangeStatus(m.range_status)}
        </span>
      </section>
      <section className="ev-section">
        <h3 className="ev-label">Compared with</h3>
        <dl className="compare-list">
          <dt>Supplied range</dt><dd>{rangeText(m.range_low, m.range_high, m.unit)}</dd>
          <dt>Preflight mean</dt><dd>{baseline}</dd>
          <dt>Difference</dt><dd>{difference}</dd>
        </dl>
        {c.baseline_values.length ? (
          <details className="disclosure disclosure-inline">
            <summary>Show values</summary>
            <table className="mini-table">
              <caption>Preflight values used ({m.unit})</caption>
              <thead><tr><th scope="col">Visit</th><th scope="col" className="num">Value</th></tr></thead>
              <tbody>
                {c.baseline_values.map((b) => (
                  <tr key={b.visit}>
                    <th scope="row">{b.visit}</th>
                    <td className="num">{b.value === null ? "missing" : b.value.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        ) : null}
        {c.includes_selected_sample ? (
          <p className="ev-note" title="This preflight sample is one of the values in the mean, so the comparison is retrospective — not a real-time prediction.">
            Retrospective: this sample is included in the preflight mean.
          </p>
        ) : (
          <p className="ev-note" title="A difference from the personal mean is descriptive; it is not an abnormality threshold.">
            A difference from the personal mean is descriptive, not a threshold.
          </p>
        )}
        {c.calculation_steps?.length ? (
          <details className="disclosure disclosure-inline">
            <summary>Worked calculation · {c.calculation_steps.length} steps</summary>
            <ol className="calc-steps">
              {c.calculation_steps.map((s) => (
                <li key={s.label}>
                  <strong>{s.label}</strong>
                  {s.n !== undefined ? <span className="meta"> · n = {s.n}</span> : null}
                  <div className="formula">{s.expression}</div>
                  <div className="small">{stepResult(s)}</div>
                  {s.note ? <p className="meta">{s.note}</p> : null}
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </section>
      <section className="ev-section">
        <h3 className="ev-label">Source</h3>
        <details className="disclosure disclosure-inline">
          <summary>Source and provenance</summary>
          <dl className="kv small">
            <dt>Dataset</dt><dd>{ev.source.title}</dd>
            <dt>File</dt><dd><code>{ev.source.file_name}</code></dd>
            <dt>Row</dt><dd>Data row {ev.source.source_row} (file line {ev.source.file_line})</dd>
            <dt>Rule</dt><dd>{c.rule_version}</dd>
          </dl>
        </details>
      </section>
      <section className="ev-section">
        <h3 className="ev-label">Limits</h3>
        <ul className="ev-list">{ev.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </section>
      <section className="ev-section">
        <h3 className="ev-label">Follow-up</h3>
        {ev.review ? (
          <p className="small" style={{ marginBottom: 8 }}>
            Current review: <span className="badge badge-teal">{REVIEW_LABEL[ev.review.status]}</span> · version {ev.review.version}
          </p>
        ) : <p className="small muted" style={{ marginBottom: 8 }}>No review saved for this result yet.</p>}
        {followUp}
      </section>
    </div>
  );
}

export function EnvEvidencePanel({ ev, followUp }: { ev: EnvEvidence; followUp?: ReactNode }) {
  const isConflict = ev.kind === "DATA_QUALITY";
  const sm = ev.measurement as EnvSummaryMeasurement;
  const cm = ev.measurement as EnvConflictMeasurement;
  return (
    <div className="evidence">
      <Step n={1} label="Observed">
        {isConflict ? (
          <>
            <p className="small muted">Source timestamp {cm.timestamp} (source clock, no timezone)</p>
            <div className="table-wrap" style={{ marginTop: 8 }}>
              <table className="data">
                <caption>Conflicting source rows (all retained, all quarantined)</caption>
                <thead><tr><th scope="col">Data row</th><th scope="col" className="num">Rate (µGy/hour)</th><th scope="col">Status</th></tr></thead>
                <tbody>{cm.rows.map((r) => (
                  <tr key={r.source_row} className="row-excluded"><td>{r.source_row}</td><td className="num">{r.rate_raw}</td><td>Quarantined</td></tr>
                ))}</tbody>
              </table>
            </div>
          </>
        ) : (
          <>
            <div className="ev-big">{fmt(sm.estimated_sensor_dose_uGy, 2)} <span className="metric-unit">µGy</span></div>
            <p className="small muted">{sm.label} · DosTel1 · ISS Columbus · 1 April 2022</p>
          </>
        )}
      </Step>
      <Step n={2} label={isConflict ? "Decision" : "Coverage and method"}>
        {isConflict ? (
          <ul className="ev-list">{Object.values(ev.comparison.formulas).map((f) => <li key={f}>{f}</li>)}</ul>
        ) : (
          <>
            <dl className="kv small">
              <dt>Covered duration</dt><dd>{duration(sm.covered_seconds)} of {duration(sm.span_seconds)} ({fmt((sm.coverage_ratio ?? 0) * 100, 2)}%)</dd>
              <dt>Rows</dt><dd>{sm.raw_rows} raw · {sm.accepted_rows} accepted · {sm.quarantined_conflict_rows} quarantined</dd>
              <dt>Intervals</dt><dd>{sm.included_intervals} included · {sm.excluded_intervals} excluded</dd>
            </dl>
            {Object.values(ev.comparison.formulas).map((f) => <div key={f} className="formula">{f}</div>)}
          </>
        )}
      </Step>
      <Step n={3} label="Source">
        <SourceStep ev={ev}>
          <dt>Instrument</dt><dd>DosTel1 · ISS Columbus module</dd>
          <dt>Rule</dt><dd>{ev.comparison.rule_version}</dd>
        </SourceStep>
      </Step>
      <Step n={4} label="Limits">
        <ul className="ev-list">{ev.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </Step>
      <Step n={5} label="Follow-up">
        {ev.review ? (
          <p className="small" style={{ marginBottom: 8 }}>Current review: <span className="badge badge-teal">{REVIEW_LABEL[ev.review.status]}</span> · version {ev.review.version}</p>
        ) : <p className="small muted" style={{ marginBottom: 8 }}>No review saved for this finding yet. Environment reviews never carry a participant.</p>}
        {followUp}
      </Step>
    </div>
  );
}
