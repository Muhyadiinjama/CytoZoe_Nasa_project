import { useEffect } from 'react';
import { get } from '../api/client';
import type { Participants } from '../api/contracts';
import { setParams } from '../app/router';
import { visitLabel } from '../lib/format';
import { useAsync } from '../lib/hooks';

export interface Selection { participant: string; visit: string; fallbackNote: string | null; data: Participants }

/** Validates ?participant=&sample= against the imported data; bad values fall back to a visible, real selection. */
export function useSelection(params: URLSearchParams) {
  const ps = useAsync(() => get<Participants>('/api/participants'), []);
  const wantP = params.get('participant'), wantS = params.get('sample');
  let sel: Selection | null = null;
  if (ps.data) {
    const list = ps.data.participants;
    const p = list.find((x) => x.id === wantP) ?? list.find((x) => x.id === 'C001') ?? list[0];
    const s = p.samples.find((x) => x.visit === wantS) ?? p.samples.find((x) => x.visit === 'L-3') ?? p.samples[0];
    const bad = (wantP && wantP !== p.id) || (wantS && wantS !== s.visit);
    sel = { participant: p.id, visit: s.visit, data: ps.data,
      fallbackNote: bad ? `The link asked for ${wantP ?? p.id} ${wantS ?? ''}, which is not in the imported data. Showing ${p.id} ${s.visit} instead.` : null };
  }
  const p = sel?.participant, v = sel?.visit;
  useEffect(() => { if (p && v && (params.get('participant') !== p || params.get('sample') !== v) && !sel?.fallbackNote) setParams({ participant: p, sample: v }, { replace: true }); });
  return { ps, sel };
}

export function ContextBar({ sel }: { sel: Selection }) {
  const part = sel.data.participants.find((x) => x.id === sel.participant)!;
  const i = part.samples.findIndex((x) => x.visit === sel.visit);
  const go = (d: number) => setParams({ participant: sel.participant, sample: part.samples[i + d].visit });
  return (
    <div className="card">
      <div className="row">
        <label className="lbl" htmlFor="sel-p">Participant (anonymised code)
          <select className="field" id="sel-p" value={sel.participant} onChange={(e: { target: HTMLSelectElement }) => {
            const np = sel.data.participants.find((x) => x.id === e.target.value)!;
            setParams({ participant: np.id, sample: np.samples.some((s) => s.visit === sel.visit) ? sel.visit : np.samples[0].visit });
          }}>
            {sel.data.participants.map((x) => <option key={x.id} value={x.id}>{x.id}</option>)}
          </select>
        </label>
        <label className="lbl" htmlFor="sel-v">Visit (actual sample)
          <select className="field" id="sel-v" value={sel.visit} onChange={(e: { target: HTMLSelectElement }) => setParams({ participant: sel.participant, sample: e.target.value })}>
            {part.samples.map((s) => <option key={s.visit} value={s.visit}>{visitLabel(s.visit)}</option>)}
          </select>
        </label>
        <button className="btn" type="button" disabled={i <= 0} aria-label="Previous actual sample" onClick={() => go(-1)}>← Previous</button>
        <button className="btn" type="button" disabled={i >= part.samples.length - 1} aria-label="Next actual sample" onClick={() => go(1)}>Next →</button>
        <span className="badge outline">Historical research sample</span>
      </div>
    </div>
  );
}
