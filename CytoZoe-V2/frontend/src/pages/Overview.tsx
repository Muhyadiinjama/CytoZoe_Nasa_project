import { useCallback, useState } from 'react';
import { get, qs } from '../api/client';
import type { HealthEvidence, HealthResponse } from '../api/contracts';
import { navigate } from '../app/router';
import { ContextBar, useSelection } from '../components/Context';
import { Drawer } from '../components/Drawer';
import { EvidencePanel } from '../components/EvidencePanel';
import { ImportPanel } from '../components/ImportPanel';
import { PageHead } from '../components/PageHead';
import { EmptyState, ErrorNotice, Notice, Skeleton } from '../components/States';
import { isOutside, num, rangeText, signed, statusLabel, visitLabel } from '../lib/format';
import { useAsync, useReviewsChanged } from '../lib/hooks';

export function Overview({ params }: { params: URLSearchParams }) {
  const { ps, sel } = useSelection(params);
  const health = useAsync(() => (sel ? get<HealthResponse>(`/api/health?${qs({ participant: sel.participant, sample: sel.visit })}`) : Promise.resolve(null)), [sel?.participant, sel?.visit]);
  const [open, setOpen] = useState<HealthEvidence | null>(null);
  useReviewsChanged(useCallback(() => health.reload(), [health.reload]));
  const head = <PageHead title="Health overview" purpose="What should I review? A numerical comparison for one actual historical blood sample." chips={<span className="badge outline">NASA OSD-575 · Inspiration4</span>} />;
  if (ps.error?.code === 'NO_HEALTH_DATA') return <>{head}<EmptyState title="No blood data imported yet"><p>Nothing is shown until the real OSD-575 file is imported; no data is invented. Run the setup import, or choose the file here.</p><ImportPanel kind="HEALTH_CMP" onImported={ps.reload} /></EmptyState></>;
  if (ps.error) return <>{head}<ErrorNotice error={ps.error} onRetry={ps.reload} /></>;
  if (!sel) return <>{head}<Skeleton label="Loading participants" /></>;
  const d = health.data;
  const cards = d?.cards ?? [];
  const outside = cards.filter((c) => isOutside(c.measurement.range_status));
  const rest = cards.filter((c) => !isOutside(c.measurement.range_status) && c.measurement.value !== null);
  const openTrend = (c: HealthEvidence) => navigate('/health', { participant: sel.participant, sample: sel.visit, marker: c.measurement.marker });
  return (
    <>
      {head}
      {sel.fallbackNote ? <Notice kind="info">{sel.fallbackNote}</Notice> : null}
      <ContextBar sel={sel} />
      {health.error ? <ErrorNotice error={health.error} onRetry={health.reload} /> : null}
      {!d ? <Skeleton label="Loading the selected sample" /> : (
        <>
          <div className="markers">
            {cards.map((c) => {
              const m = c.measurement, cmp = c.comparison, out = isOutside(m.range_status);
              return (
                <article key={c.evidence_id} className="card marker" aria-label={`${m.label} card`}>
                  <div className="name">{m.label}</div>
                  <div className="val metric-value">{num(m.value, m.display_decimals)}<small>{m.unit}</small></div>
                  {out ? <span className="badge review">▲ {rangeText(m.range_status)}</span> : <span className="status-neutral">{rangeText(m.range_status)}</span>}
                  <p className="meta">{cmp.baseline === null ? `No baseline (n=${cmp.n})` : `vs retrospective preflight mean ${num(cmp.baseline, m.display_decimals)} (n=${cmp.n}): ${signed(cmp.delta, m.display_decimals)}${cmp.percent_delta === null ? '' : ` (${signed(cmp.percent_delta, 1)}%)`}`}</p>
                  {c.review_state ? <span className="badge success">✓ {statusLabel(c.review_state.status)}</span> : null}
                  <div className="actions">
                    <button className="btn small" type="button" aria-label={`Open ${m.label} trend`} onClick={() => openTrend(c)}>Trend</button>
                    <button className="btn small" type="button" aria-label={`Inspect ${m.label} result`} onClick={() => setOpen(c)}>Inspect</button>
                  </div>
                </article>);
            })}
          </div>
          <div className="grid-2-1">
            <section className="card" aria-labelledby="rtr">
              <div className="card-head"><h2 id="rtr">Results to review</h2><span className="meta">{sel.participant} · {visitLabel(sel.visit)}</span></div>
              {outside.length === 0 ? <p className="notice info">No selected measurements are outside the supplied ranges. This does not assess overall health.</p> : null}
              <ul className="list">
                {[...outside, ...rest].map((c) => {
                  const m = c.measurement, out = isOutside(m.range_status);
                  return (
                    <li key={c.evidence_id}>
                      <div>
                        <strong>{m.label}</strong> {out ? <span className="badge review">▲ {rangeText(m.range_status)}</span> : <span className="status-neutral">{rangeText(m.range_status)}</span>}
                        <p className="small muted">{out
                          ? `${num(m.value, m.display_decimals)} ${m.unit} compared with the supplied ${m.range_status === 'ABOVE_SUPPLIED_UPPER_BOUND' ? `upper bound ${m.range_high}` : `lower bound ${m.range_low}`} ${m.unit}.${c.context.phase === 'PREFLIGHT' ? ' Preflight sample.' : ''}`
                          : `${num(m.value, m.display_decimals)} ${m.unit}`}</p>
                        {c.review_state ? <span className="badge success">✓ Review saved · {statusLabel(c.review_state.status)}</span> : null}
                      </div>
                      <button className={out ? 'btn primary' : 'btn'} type="button" aria-label={`Inspect ${m.label} result`} onClick={() => setOpen(c)}>Inspect result</button>
                    </li>);
                })}
              </ul>
            </section>
            <aside className="card" aria-labelledby="avd">
              <h2 id="avd">Available data</h2>
              <div className="summary" style={{ marginTop: 12 }}>
                <div><b className="metric-value">{d.summary.outside}</b><span className="small muted">outside supplied range</span></div>
                <div><b className="metric-value">{d.summary.available} of {d.summary.total}</b><span className="small muted">measurements available</span></div>
                <div><b className="metric-value">{d.summary.awaiting_follow_up}</b><span className="small muted">{sel.participant} reviews not yet marked reviewed</span></div>
              </div>
              <p className="meta" style={{ marginTop: 16 }}>Source: {d.dataset.file_name} (line {d.cards[0]?.source.source_row}, sample {d.sample.sample_id}). Four anonymised participants, seven visits. Historical research data, not live monitoring.</p>
            </aside>
          </div>
        </>)}
      {open ? <Drawer title={`Evidence: ${open.measurement.label}, ${open.context.participant_id} ${open.context.visit}`} onClose={() => setOpen(null)}>
        <EvidencePanel ev={cards.find((c) => c.evidence_id === open.evidence_id) ?? open} />
      </Drawer> : null}
    </>
  );
}
