import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { ExplainResponse } from '../api/contracts';

/** Verified explanation first; optional local AI wording shown beside it, labelled, never saved unless the user copies it into a note. */
export function Assistant({ evidenceId, onUseDraft }: { evidenceId: string; onUseDraft: (text: string) => void }) {
  const [res, setRes] = useState<ExplainResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [free, setFree] = useState('');
  const [used, setUsed] = useState(false);
  const [discarded, setDiscarded] = useState(false);
  useEffect(() => { setRes(null); setErr(null); }, [evidenceId]);
  async function ask(question_id: string, free_text?: string) {
    setBusy(true); setErr(null); setUsed(false); setDiscarded(false);
    try { setRes(await api<ExplainResponse>('POST', '/api/explain', { evidence_id: evidenceId, question_id, free_text }, { timeoutMs: 25000 })); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  }
  const ai = res?.ai;
  return (
    <section className="assistant" aria-label="Evidence assistant">
      <h3>Evidence assistant</h3>
      <div className="asks">
        <button className="btn small" type="button" aria-disabled={busy} onClick={() => { if (!busy) void ask('EXPLAIN'); }}>Explain this result</button>
        <button className="btn small" type="button" aria-disabled={busy} onClick={() => { if (!busy) void ask('HOW_CALCULATED'); }}>How was this calculated?</button>
        <button className="btn small" type="button" aria-disabled={busy} onClick={() => { if (!busy) void ask('LIMITS'); }}>What can this dataset not tell us?</button>
      </div>
      <form className="row" onSubmit={(e: { preventDefault(): void }) => { e.preventDefault(); if (free.trim() && !busy) void ask('FREE_TEXT', free.trim()); }}>
        <div style={{ flex: '1 1 200px', minWidth: 0 }}>
          <input className="field" type="text" maxLength={300} value={free} aria-label="Ask about this result" placeholder="Ask about this result"
            onChange={(e: { target: HTMLInputElement }) => setFree(e.target.value)} />
        </div>
        <button className="btn" type="submit" aria-disabled={busy}>Ask</button>
      </form>
      <div aria-live="polite" data-testid="answer">
        {busy ? <p className="meta">Preparing the answer… (a local AI draft can take up to 15 s)</p> : null}
        {err ? <p className="notice error">{err}</p> : null}
        {res ? (
          <div className="answer">
            <span className="badge outline">Verified explanation</span>
            <h3>{res.verified.title}</h3>
            {res.verified.paragraphs.map((p, i) => <p key={i}>{p}</p>)}
            {res.verified.source_ids.length ? <p className="meta">Evidence id: {res.verified.source_ids.join(', ')}</p> : null}
          </div>) : null}
        {ai && ai.status === 'DRAFT' && ai.draft && !discarded ? (
          <div className="answer ai-draft" data-testid="ai-draft">
            <span className="badge review">{ai.label}</span>
            <p>{ai.draft.summary}</p>
            {ai.draft.limitations.length ? <ul>{ai.draft.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul> : null}
            <p className="meta">Worded by local model {ai.model} from the verified facts above; numbers were checked against them. Not saved unless you add it to your note and save.</p>
            <div className="row">
              <button className="btn small" type="button" onClick={() => { onUseDraft(ai.draft!.summary); setUsed(true); }}>Use as note draft</button>
              <button className="btn small" type="button" onClick={() => setDiscarded(true)}>Discard draft</button>
            </div>
            {used ? <p className="meta" role="status">Added to the note box. It is saved only when you choose Record / Update follow-up.</p> : null}
          </div>) : null}
        {ai && ai.status === 'FALLBACK' ? <p className="notice info small" data-testid="ai-fallback">{ai.reason} The verified explanation is unchanged.</p> : null}
      </div>
      <p className="meta">{res?.assistant_mode === 'VERIFIED_PLUS_LOCAL_AI_DRAFT'
        ? 'Answers come from fixed templates over the calculated evidence. Optional local AI wording is on; it only rewords them.'
        : 'Answers come from fixed templates over the calculated evidence ("Verified explanation"). Optional local AI wording is off on this computer.'}</p>
    </section>
  );
}
