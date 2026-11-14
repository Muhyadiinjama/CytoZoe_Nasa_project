import { useCallback } from 'react';
import { get, qs } from '../api/client';
import type { HealthResponse, Trend } from '../api/contracts';
import { setParams } from '../app/router';
import { HealthVisitChart } from '../charts/HealthVisitChart';
import { ContextBar, useSelection } from '../components/Context';
import { EvidencePanel } from '../components/EvidencePanel';
import { ImportPanel } from '../components/ImportPanel';
import { PageHead } from '../components/PageHead';
import { EmptyState, ErrorNotice, Notice, Skeleton } from '../components/States';
import { bound, num, rangeText, signed, visitLabel } from '../lib/format';
import { useAsync, useReviewsChanged } from '../lib/hooks';

export function Health({ params }: { params: URLSearchParams }) {
  const { ps, sel } = useSelection(params);
  const markers = ps.data?.markers ?? [];
  const wanted = params.get('marker');
  const marker = markers.find((m) => m.id === wanted)?.id ?? 'creatinine';
  const trend = useAsync(() => (sel ? get<Trend>(`/api/health/trend?${qs({ participant: sel.participant, marker })}`) : Promise.resolve(null)), [sel?.participant, marker]);
  const health = useAsync(() => (sel ? get<HealthResponse>(`/api/health?${qs({ participant: sel.participant, sample: sel.visit })}`) : Promise.resolve(null)), [sel?.participant, sel?.visit]);
  useReviewsChanged(useCallback(() => health.reload(), [health.reload]));
  const head = <PageHead title="Health trends" purpose="What changed? One marker across the actual visits. Dots are real samples; nothing is interpolated." chips={<span className="badge outline">NASA OSD-575 · Inspiration4</span>} />;
  if (ps.error?.code === 'NO_HEALTH_DATA') return <>{head}<EmptyState title="No blood data imported yet"><ImportPanel kind="HEALTH_CMP" onImported={ps.reload} /></EmptyState></>;
  if (ps.error) return <>{head}<ErrorNotice error={ps.error} onRetry={ps.reload} /></>;
  if (!sel) return <>{head}<Skeleton label="Loading participants" /></>;
  const ev = health.data?.cards.find((c) => c.measurement.marker === marker) ?? null;
  const t = trend.data;
  const ids = markers.map((m) => m.id);
  const pick = (id: string) => { setParams({ marker: id }); window.setTimeout(() => document.getElementById('tab-' + id)?.focus(), 0); };
  return (
    <>
      {head}
      {sel.fallbackNote ? <Notice kind="info">{sel.fallbackNote}</Notice> : null}
      {wanted && wanted !== marker ? <Notice kind="info">Unknown marker “{wanted}” in the link; showing Creatinine.</Notice> : null}
      <ContextBar sel={sel} />
      <div className="tabs" role="tablist" aria-label="Blood marker">
        {markers.map((m) => (
          <button key={m.id} id={'tab-' + m.id} type="button" role="tab" aria-selected={m.id === marker} aria-controls="marker-panel" tabIndex={m.id === marker ? 0 : -1}
            onClick={() => pick(m.id)}
            onKeyDown={(e: { key: string; preventDefault(): void }) => {
              let i = ids.indexOf(marker);
              if (e.key === 'ArrowRight') i = (i + 1) % ids.length; else if (e.key === 'ArrowLeft') i = (i + ids.length - 1) % ids.length;
              else if (e.key === 'Home') i = 0; else if (e.key === 'End') i = ids.length - 1; else return;
              e.preventDefault(); pick(ids[i]);
            }}>{m.label}</button>))}
      </div>
      <div className="grid-2-1">
        <section className="card" id="marker-panel" role="tabpanel" aria-labelledby={'tab-' + marker}>
          {trend.error ? <ErrorNotice error={trend.error} onRetry={trend.reload} /> : !t ? <Skeleton label="Loading chart" height={320} /> : (
            <>
              <div className="card-head"><h2>{t.marker.label} ({t.marker.unit}) · {t.participant_id}</h2><span className="meta">Visits are in order, not to time scale</span></div>
              <HealthVisitChart trend={t} selected={sel.visit} onSelect={(v) => setParams({ sample: v })} />
              <details className="tbl">
                <summary>Show data table</summary>
                <div className="table-wrap"><table>
                  <caption className="sr-only">{t.marker.label} values for {t.participant_id} by visit</caption>
                  <thead><tr>{['Visit', 'Value', 'Supplied range', 'Retrospective preflight mean', 'Difference', '%', 'Status', 'Source line'].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
                  <tbody>{t.points.map((p) => (
                    <tr key={p.visit} data-selected={p.visit === sel.visit}>
                      <td>{visitLabel(p.visit)}</td><td>{p.value === null ? 'n/a' : `${num(p.value, t.marker.dp + 1)} ${t.marker.unit}`}</td>
                      <td>{bound(p.range_low, '—')} to {bound(p.range_high, '—')}</td><td>{num(t.baseline.mean, 4)} (n={t.baseline.n})</td>
                      <td>{signed(p.delta, 4)}</td><td>{p.percent_delta === null ? 'n/a' : signed(p.percent_delta, 2) + '%'}</td>
                      <td>{rangeText(p.range_status)}</td><td>{p.source_row}</td>
                    </tr>))}</tbody>
                </table></div>
              </details>
            </>)}
        </section>
        <aside className="card" aria-labelledby="evh">
          <h2 id="evh">Evidence for {sel.participant} {sel.visit}</h2>
          <div style={{ marginTop: 12 }}>
            {health.error ? <ErrorNotice error={health.error} onRetry={health.reload} /> : !ev ? <Skeleton label="Loading evidence" /> : <EvidencePanel ev={ev} idPrefix="hv" />}
          </div>
        </aside>
      </div>
    </>
  );
}
