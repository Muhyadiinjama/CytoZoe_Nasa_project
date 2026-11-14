import { useCallback, useEffect, useState } from 'react';
import { api, get, qs } from '../api/client';
import { REVIEW_STATUSES } from '../api/contracts';
import type { Review, ReviewList } from '../api/contracts';
import { setParams } from '../app/router';
import { PageHead } from '../components/PageHead';
import { ReviewForm } from '../components/ReviewForm';
import { EmptyState, ErrorNotice, Skeleton } from '../components/States';
import { statusLabel, when } from '../lib/format';
import { useAsync, useReviewsChanged } from '../lib/hooks';

export function Reviews({ params }: { params: URLSearchParams }) {
  const caseF = params.get('case') ?? '', statusF = params.get('status') ?? '', partF = params.get('participant') ?? '';
  const list = useAsync(() => get<ReviewList>(`/api/reviews?${qs({ case: caseF, status: statusF, participant: caseF === 'environment' ? '' : partF })}`), [caseF, statusF, partF]);
  const all = useAsync(() => get<ReviewList>('/api/reviews'), []);
  const [selId, setSelId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Review | null>(null);
  const [note, setNote] = useState('');
  const [preview, setPreview] = useState(false);
  const [exp, setExp] = useState<{ kind: 'idle' | 'busy' | 'done' | 'error'; text?: string }>({ kind: 'idle' });
  const refresh = useCallback(() => { list.reload(); all.reload(); if (selId) api<Review>('GET', `/api/reviews/${selId}`).then(setDetail).catch(() => setDetail(null)); }, [list.reload, all.reload, selId]);
  useReviewsChanged(refresh);
  useEffect(() => { if (selId) api<Review>('GET', `/api/reviews/${selId}`).then(setDetail).catch(() => setDetail(null)); else setDetail(null); }, [selId]);
  const parts = Array.from(new Set((all.data?.items ?? []).map((r) => r.participant_id).filter(Boolean) as string[])).sort();
  async function download(fmt: 'json' | 'html' | 'csv') {
    setExp({ kind: 'busy', text: `Preparing ${fmt.toUpperCase()}…` });
    try {
      const r = await fetch(`/api/export?format=${fmt}`);
      if (!r.ok) throw new Error(`The local service returned ${r.status}.`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `cytozoe-review-packet.${fmt}`; document.body.append(a); a.click(); a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 4000);
      setExp({ kind: 'done', text: `Saved cytozoe-review-packet.${fmt} to this computer's downloads. Nothing was sent anywhere.` });
    } catch (e) { setExp({ kind: 'error', text: `Export failed: ${(e as Error).message} Your reviews are unchanged.` }); }
  }
  const sel = (id: string, label: string, value: string, opts: [string, string][], key: string) => (
    <label className="lbl" htmlFor={id}>{label}
      <select className="field" id={id} value={value} onChange={(e: { target: HTMLSelectElement }) => setParams({ [key]: e.target.value || null, ...(key === 'case' && e.target.value === 'environment' ? { participant: null } : {}) })}>
        {opts.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
      </select>
    </label>);
  const items = list.data?.items ?? [];
  return (
    <>
      <PageHead title="Review log" purpose="What did we decide to follow up? Saved locally on this computer, with full history." chips={<span className="badge outline">Saved locally</span>} />
      <div className="card"><div className="row">
        {sel('f-case', 'Case', caseF, [['', 'All'], ['health', 'Health (OSD-575)'], ['environment', 'Environment (RadLab)']], 'case')}
        {sel('f-status', 'Status', statusF, [['', 'All'], ...REVIEW_STATUSES.map((s) => [s, statusLabel(s)] as [string, string])], 'status')}
        {caseF !== 'environment' ? sel('f-part', 'Participant (health only)', partF, [['', 'All'], ...parts.map((p) => [p, p] as [string, string])], 'participant') : null}
        <button className="btn primary" type="button" aria-expanded={preview} onClick={() => setPreview((v) => !v)}>{preview ? 'Hide export preview' : 'Export review packet'}</button>
      </div></div>
      {preview ? (
        <section className="card" aria-labelledby="exph">
          <h2 id="exph">Review packet preview</h2>
          <p className="small muted" style={{ margin: '8px 0 12px' }}>Includes every saved review in separate health and environment sections, source files with SHA-256, methods, notes, history and limitations. Downloading saves a local file; nothing is transmitted.</p>
          <div className="row" style={{ marginBottom: 12 }}>
            <button className="btn primary" type="button" onClick={() => download('html')} disabled={exp.kind === 'busy'}>Download HTML</button>
            <button className="btn" type="button" onClick={() => download('json')} disabled={exp.kind === 'busy'}>Download JSON</button>
            <button className="btn" type="button" onClick={() => download('csv')} disabled={exp.kind === 'busy'}>Download CSV (table only)</button>
          </div>
          <div role="status" aria-live="polite">{exp.text ? <p className={`notice ${exp.kind === 'error' ? 'error' : exp.kind === 'done' ? 'success' : 'info'}`}>{exp.text}</p> : null}</div>
          <iframe className="preview" title="Review packet preview" sandbox="" src={`/api/export?format=html&inline=1&t=${all.data?.items.map((r) => r.version).join('.') ?? ''}`} />
        </section>) : null}
      <div className={detail ? 'grid-2-1' : ''}>
        <section className="card" aria-labelledby="rvh">
          <h2 id="rvh">Reviews ({list.data?.total ?? '…'})</h2>
          <div style={{ marginTop: 12 }}>
            {list.error ? <ErrorNotice error={list.error} onRetry={list.reload} /> : list.loading && !list.data ? <Skeleton label="Loading reviews" /> : items.length === 0 ? (
              <EmptyState title={all.data?.total ? 'No reviews match these filters' : 'No follow-ups saved yet'}>
                <p>{all.data?.total ? 'Change the filters above.' : 'Open a result from Health overview, Health trends or Radiation review and choose Record follow-up.'}</p>
              </EmptyState>) : (
              <div className="table-wrap"><table>
                <caption className="sr-only">Saved reviews</caption>
                <thead><tr>{['Finding', 'Case', 'Participant / instrument', 'Status', 'Updated'].map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
                <tbody>{items.map((r) => (
                  <tr key={r.id} className="click" data-selected={r.id === selId} onClick={(e: { target: EventTarget }) => { if (!(e.target as HTMLElement).closest('button')) setSelId(r.id); }}>
                    <td><button className="linkbtn" type="button" aria-pressed={r.id === selId} onClick={() => { setSelId(r.id); window.setTimeout(() => document.getElementById('rl-note')?.focus(), 150); }}>{r.title}</button></td>
                    <td>{r.case}</td><td>{r.participant_id ?? r.instrument_id}</td><td>{statusLabel(r.status)}</td><td>{when(r.updated_at)}</td>
                  </tr>))}</tbody>
              </table></div>)}
          </div>
        </section>
        {detail ? (
          <aside className="card" aria-labelledby="rdh">
            <h2 id="rdh">{detail.title}</h2>
            <p className="small muted" style={{ margin: '6px 0 12px' }}>{detail.case === 'health' ? 'Health · NASA OSD-575' : 'Environment · NASA RadLab (separate case)'} · created {when(detail.created_at)} · evidence frozen at first save</p>
            <p className="meta">Source: {detail.evidence.source.file_name}{detail.evidence.source.source_row !== null ? ` line ${detail.evidence.source.source_row}` : ''} · SHA-256 {detail.evidence.source.sha256.slice(0, 16)}…</p>
            <div style={{ marginTop: 12 }}><ReviewForm evidenceId={detail.finding_id} reviewId={detail.id} note={note} setNote={setNote} idPrefix="rl" /></div>
            <h3 style={{ marginTop: 16 }}>History</h3>
            <ul className="list">{[...(detail.events ?? [])].reverse().map((e) => (
              <li key={e.id}><span className="small">{e.action === 'CREATED' ? 'Created' : 'Updated'}{e.after && 'status' in e.after ? ` · ${statusLabel(e.after.status as never)}` : ''}{e.before && e.after && e.before.note !== e.after.note ? ' · note changed' : ''}</span><span className="meta">{when(e.timestamp)}</span></li>))}</ul>
          </aside>) : null}
      </div>
    </>
  );
}
