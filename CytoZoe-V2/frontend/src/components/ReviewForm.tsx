import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api/client';
import { REVIEW_STATUSES } from '../api/contracts';
import type { Review, ReviewStatus } from '../api/contracts';
import { statusLabel, when } from '../lib/format';
import { reviewsChanged } from '../lib/hooks';

interface Props { evidenceId: string; reviewId?: number | null; note: string; setNote: (v: string) => void; idPrefix?: string }

/** Save a follow-up: idempotent create, then a versioned update. A 409 keeps the draft and shows the newer version. */
export function ReviewForm({ evidenceId, reviewId, note, setNote, idPrefix = 'rv' }: Props) {
  const [review, setReview] = useState<Review | null>(null);
  const [status, setStatus] = useState<ReviewStatus>('FOLLOW_UP_REQUESTED');
  const [date, setDate] = useState('');
  const [state, setState] = useState<{ kind: 'idle' | 'saving' | 'saved' | 'error' | 'conflict'; msg?: string; latest?: Record<string, unknown> }>({ kind: 'idle' });

  useEffect(() => {
    let live = true;
    setReview(null); setState({ kind: 'idle' });
    if (reviewId) {
      api<Review>('GET', `/api/reviews/${reviewId}`).then((r) => {
        if (!live) return;
        setReview(r); setStatus(r.status); setDate(r.follow_up_date ?? ''); setNote(r.note);
      }).catch(() => { /* the form still works; save will create or report */ });
    } else { setStatus('FOLLOW_UP_REQUESTED'); setDate(''); }
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [evidenceId, reviewId]);

  const inflight = useRef(false);
  async function save() {
    if (inflight.current) return;
    if (!note.trim()) { setState({ kind: 'error', msg: 'Write a short note before saving (for example what to check next).' }); return; }
    setState({ kind: 'saving' });
    inflight.current = true;
    try {
      const base = review ?? await api<Review>('POST', '/api/reviews', { evidence_id: evidenceId });
      const body: Record<string, unknown> = { version: base.version, status, note };
      if (date) body.follow_up_date = date; else if (base.follow_up_date) body.clear_follow_up_date = true;
      const r = await api<Review>('PATCH', `/api/reviews/${base.id}`, body);
      setReview(r); setState({ kind: 'saved' }); reviewsChanged();
    } catch (e) {
      if (e instanceof ApiError && e.code === 'VERSION_CONFLICT') {
        setState({ kind: 'conflict', msg: e.message, latest: e.details.current as Record<string, unknown> });
      } else {
        setState({ kind: 'error', msg: (e as Error).message + ' Your note is still here. Try again.' });
      }
    } finally { inflight.current = false; }
  }
  async function loadLatest() {
    if (!review) return;
    const r = await api<Review>('GET', `/api/reviews/${review.id}`);
    setReview(r); setStatus(r.status); setDate(r.follow_up_date ?? ''); setState({ kind: 'idle' });
  }
  const p = idPrefix;
  return (
    <div className="stack">
      <label className="lbl" htmlFor={`${p}-note`}>Follow-up note
        <textarea className="field" id={`${p}-note`} rows={4} maxLength={4000} value={note} aria-describedby={`${p}-help`}
          onChange={(e: { target: HTMLTextAreaElement }) => setNote(e.target.value)} />
      </label>
      <p id={`${p}-help`} className="meta">Saved locally on this computer and included in the review packet. It is your note, not medical advice. {note.length}/4000</p>
      <div className="row">
        <label className="lbl" htmlFor={`${p}-status`}>Status
          <select className="field" id={`${p}-status`} value={status} onChange={(e: { target: HTMLSelectElement }) => setStatus(e.target.value as ReviewStatus)}>
            {REVIEW_STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
          </select>
        </label>
        <label className="lbl" htmlFor={`${p}-date`}>Follow-up date (optional)
          <input className="field" type="date" id={`${p}-date`} value={date} onChange={(e: { target: HTMLInputElement }) => setDate(e.target.value)} />
        </label>
      </div>
      <div className="row">
        <button className="btn primary" type="button" id={`${p}-save`} aria-disabled={state.kind === 'saving'} onClick={() => { if (state.kind !== 'saving') void save(); }}>
          {state.kind === 'saving' ? 'Saving…' : review ? 'Update follow-up' : 'Record follow-up'}
        </button>
      </div>
      <div role="status" aria-live="polite" id={`${p}-msg`}>
        {state.kind === 'saved' && review ? <span className="badge success">✓ Saved locally · {statusLabel(review.status)} · v{review.version} · {when(review.updated_at)}</span> : null}
        {state.kind === 'idle' && review ? <span className="meta">Last saved {when(review.updated_at)} · {statusLabel(review.status)} · v{review.version}</span> : null}
        {state.kind === 'error' ? <span className="badge error" role="alert">! {state.msg}</span> : null}
        {state.kind === 'conflict' ? (
          <div className="notice error" role="alert">
            <p><strong>Not saved: this review changed in another tab.</strong> {state.msg}</p>
            <p className="small">Newer saved note: “{String(state.latest?.note ?? '')}” · status {String(state.latest?.status ?? '')}</p>
            <button className="btn small" type="button" onClick={loadLatest}>Use the newer version (my draft stays in the box)</button>
          </div>) : null}
      </div>
    </div>
  );
}
