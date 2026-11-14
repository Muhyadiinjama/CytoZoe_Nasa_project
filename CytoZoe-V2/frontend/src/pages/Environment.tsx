import { useCallback, useState } from 'react';
import { get, qs } from '../api/client';
import type { EnvEvidence, EnvResponse } from '../api/contracts';
import { setParams } from '../app/router';
import { RadiationRateChart, SensorDoseChart } from '../charts/RadiationCharts';
import { Drawer } from '../components/Drawer';
import { EvidencePanel } from '../components/EvidencePanel';
import { ImportPanel } from '../components/ImportPanel';
import { PageHead } from '../components/PageHead';
import { EmptyState, ErrorNotice, Skeleton } from '../components/States';
import { num, reasonText, statusLabel } from '../lib/format';
import { useAsync, useReviewsChanged } from '../lib/hooks';

export function Environment({ params }: { params: URLSearchParams }) {
  const inst = params.get('instrument') ?? undefined;
  const env = useAsync(() => get<EnvResponse>(`/api/environment?${qs({ instrument: inst })}`), [inst]);
  const [open, setOpen] = useState<EnvEvidence | null>(null);
  const [why, setWhy] = useState(false);
  const [tableOpen, setTableOpen] = useState(false);
  useReviewsChanged(useCallback(() => env.reload(), [env.reload]));
  const head = <PageHead title="Radiation review" purpose="What does this separate environment record show? Data quality first, then the dose-rate history." chips={<span className="badge outline">Separate case study</span>} />;
  if (env.error?.code === 'NO_RADIATION_DATA') return <>{head}<EmptyState title="No radiation data imported yet"><p>Nothing is shown until a real RadLab file is imported.</p><ImportPanel kind="ENV_RADIATION" onImported={env.reload} /></EmptyState></>;
  if (env.error) return <>{head}<ErrorNotice error={env.error} onRetry={env.reload} /></>;
  const e = env.data;
  if (!e) return <>{head}<Skeleton label="Loading radiation record" height={300} /></>;
  const q = e.quality, I = e.integration;
  return (
    <>
      {head}
      <div className="banner" role="note">Separate case study · {e.banner.location} · {e.instrument} · {e.banner.date_text} · Not linked to any health participant.</div>
      {e.instruments.length > 1 ? (
        <label className="lbl" htmlFor="sel-i" style={{ maxWidth: 260 }}>Instrument in this file
          <select className="field" id="sel-i" value={e.instrument} onChange={(ev: { target: HTMLSelectElement }) => setParams({ instrument: ev.target.value })}>
            {e.instruments.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
        </label>) : null}
      <section className="card" aria-label="Data quality">
        <div className="quality">
          <div><b className="metric-value">{q.raw_rows}</b><span className="small muted">raw rows ({e.instrument})</span></div>
          <div><b className="metric-value">{q.quarantined_rows}</b><span className="small muted">rows excluded ({q.conflict_groups} conflicting timestamps)</span></div>
          <div><b className="metric-value">{q.accepted_rows}</b><span className="small muted">unambiguous rows</span></div>
          <div><b className="metric-value">{num(I.covered_seconds / 3600, 2)} h</b><span className="small muted">covered duration</span></div>
          <button className="btn" type="button" onClick={() => setWhy(true)}>Why excluded?</button>
        </div>
      </section>
      <section className="card">
        <div className="card-head"><h2>Absorbed dose rate (µGy/hour)</h2><span className="meta">Accepted readings · {q.first_timestamp} to {q.last_timestamp} (source clock)</span></div>
        <RadiationRateChart env={e} />
      </section>
      <section className="card">
        <div className="card-head"><h2>Estimated dose over covered intervals at sensor</h2></div>
        <p className="small" style={{ marginBottom: 12 }}><strong className="metric-value">{num(I.estimated_sensor_dose_uGy, 3)} µGy</strong> over <strong>{num(I.covered_seconds / 3600, 2)} h</strong> covered · {I.excluded_intervals.length} interval(s) excluded · method: {I.formula}, readings ≤ {I.max_gap_s} s apart (engineering coverage rule, not a NASA safety threshold). Not personal dose; no safe/unsafe judgement.</p>
        <SensorDoseChart env={e} />
        <details className="tbl" onToggle={(ev: { currentTarget: HTMLDetailsElement }) => setTableOpen(ev.currentTarget.open)}>
          <summary>Show data table ({e.table.length} source rows)</summary>
          {tableOpen ? <div className="table-wrap"><table>
            <caption className="sr-only">All {e.instrument} source rows with quality status and accepted intervals</caption>
            <thead><tr>{['Source line', 'Source timestamp', 'Rate (µGy/h)', 'Quality', 'Interval to next', 'Accumulated (µGy)'].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
            <tbody>{e.table.map((r) => (
              <tr key={r.source_row}><td>{r.source_row}</td><td>{r.source_timestamp}</td><td>{r.rate === null ? r.raw_rate || 'missing' : num(r.rate, 3)}</td>
                <td>{r.quality_status.toLowerCase().replaceAll('_', ' ')}</td>
                <td>{r.interval_s === null ? '' : r.interval_accepted ? `${r.interval_s} s accepted` : `excluded: ${reasonText(r.interval_reason)}`}</td>
                <td>{r.cumulative_uGy === null ? '' : num(r.cumulative_uGy, 4)}</td></tr>))}</tbody>
          </table></div> : null}
        </details>
      </section>
      <section className="card">
        <h2>Findings you can follow up</h2>
        <ul className="list">{e.findings.map((f) => (
          <li key={f.evidence_id}>
            <div><strong>{f.title}</strong>
              <p className="small muted">{f.kind === 'DATA_QUALITY' ? 'A data-quality decision about the record.' : 'An observation about the sensor record, not a health alarm.'}</p>
              {f.review_state ? <span className="badge success">✓ Review saved · {statusLabel(f.review_state.status)}</span> : null}</div>
            <button className="btn" type="button" aria-label={`Inspect result: ${f.title}`} onClick={() => setOpen(f)}>Inspect result</button>
          </li>))}</ul>
      </section>
      {why ? <Drawer title="Why readings were excluded" onClose={() => setWhy(false)}>
        <div className="ev">
          <p>{q.conflict_groups} timestamps each appear twice in the source file with different rates. All {q.quarantined_rows} of those rows are kept in the raw table but left out of the charts and the dose estimate. Nothing was averaged, summed or chosen.</p>
          <div className="conflict"><table><thead><tr><th scope="col">Source timestamp</th><th scope="col">Source line</th><th scope="col">Rate (µGy/h)</th></tr></thead>
            <tbody>{e.conflict_groups.flatMap((g) => g.rows.map((r, i) => <tr key={r.source_row}><td>{i === 0 ? g.source_timestamp : ''}</td><td>{r.source_row}</td><td>{r.rate}</td></tr>))}</tbody></table></div>
          <p>Excluded intervals: {Object.entries(I.excluded_by_reason).map(([k, v]) => `${v} × ${reasonText(k)}`).join(', ') || 'none'}. An interval is also excluded when readings are more than {I.max_gap_s} s apart (an engineering coverage rule, not a NASA safety threshold).</p>
        </div>
      </Drawer> : null}
      {open ? <Drawer title={`Evidence: ${open.title}`} onClose={() => setOpen(null)}>
        <EvidencePanel ev={e.findings.find((f) => f.evidence_id === open.evidence_id) ?? open} />
      </Drawer> : null}
    </>
  );
}
