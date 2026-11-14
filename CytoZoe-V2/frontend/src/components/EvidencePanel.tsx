import { useEffect, useState } from 'react';
import type { EnvEvidence, Evidence, HealthEvidence } from '../api/contracts';
import { bound, isOutside, num, rangeText, signed, visitLabel } from '../lib/format';
import { Assistant } from './Assistant';
import { ReviewForm } from './ReviewForm';

/** Observed → Compared with → Source → Limits → Follow-up, then the assistant. Shared by drawer and Health Trends. */
export function EvidencePanel({ ev, idPrefix = 'rv' }: { ev: Evidence; idPrefix?: string }) {
  const [note, setNote] = useState('');
  useEffect(() => { setNote(''); }, [ev.evidence_id]);
  return (
    <div className="ev" data-evidence-id={ev.evidence_id}>
      {ev.kind === 'HEALTH_OBSERVATION' ? <HealthFacts ev={ev} /> : <EnvFacts ev={ev} />}
      <section>
        <h3>Source</h3>
        <dl className="kv">
          <dt>File</dt><dd>{ev.source.file_name}</dd>
          {ev.source.source_row !== null ? <><dt>Line</dt><dd>{ev.source.source_row} (header is line 1)</dd></> : null}
          <dt>SHA-256</dt><dd className="mono">{ev.source.sha256}</dd>
          <dt>Source</dt><dd>{ev.source.source_url}</dd>
          <dt>Terms</dt><dd>{ev.source.license_note}</dd>
        </dl>
      </section>
      <section>
        <h3>Limits</h3>
        <ul>{ev.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
      </section>
      <section>
        <h3>Follow-up</h3>
        <ReviewForm evidenceId={ev.evidence_id} reviewId={ev.review_state?.id ?? null} note={note} setNote={setNote} idPrefix={idPrefix} />
      </section>
      <Assistant evidenceId={ev.evidence_id} onUseDraft={(t) => setNote((n) => (n.trim() ? n.trim() + '\n\n' : '') + t)} />
    </div>
  );
}

function HealthFacts({ ev }: { ev: HealthEvidence }) {
  const m = ev.measurement, c = ev.comparison, x = ev.context;
  return (
    <>
      <section>
        <h3>Observed</h3>
        <div className="big metric-value">{num(m.value, m.display_decimals)} <span className="small muted">{m.unit}</span></div>
        <p>{m.label} · {x.participant_id} · {visitLabel(x.visit)} · historical research sample</p>
        {isOutside(m.range_status) ? <span className="badge review">▲ {rangeText(m.range_status)}</span> : <span className="status-neutral">{rangeText(m.range_status)}</span>}
      </section>
      <section>
        <h3>Compared with</h3>
        <p>Supplied range (same source row): {bound(m.range_low, 'no lower bound')} to {bound(m.range_high, 'no upper bound')} {m.unit}.</p>
        {c.baseline === null
          ? <p>Personal baseline not available: needs at least 2 preflight values; found {c.n}.</p>
          : <p>Compared with retrospective preflight mean: {num(c.baseline, 4)} {m.unit} (n={c.n}: {c.baseline_values.join(', ')}). Difference {signed(c.delta, 4)} {m.unit}{c.percent_delta === null ? '' : ` (${signed(c.percent_delta, 2)}%)`}.</p>}
        <p className="meta">Retrospective: the mean uses all preflight visits, including ones after an earlier sample. Rule {c.rule_version}.</p>
      </section>
    </>
  );
}

function EnvFacts({ ev }: { ev: EnvEvidence }) {
  const o = ev.observation as Record<string, unknown>;
  const conflicts = (o.conflicts as { source_timestamp: string; rows: { source_row: number; rate: number | null }[] }[] | undefined) ?? [];
  return (
    <>
      <section>
        <h3>Observed</h3>
        <p className="big" style={{ fontSize: 20, lineHeight: '28px' }}>{ev.title}</p>
        {ev.kind === 'DATA_QUALITY' ? (
          <div className="conflict"><table><thead><tr><th scope="col">Source timestamp</th><th scope="col">Source lines and rates (µGy/h)</th></tr></thead>
            <tbody>{conflicts.map((g) => <tr key={g.source_timestamp}><td>{g.source_timestamp}</td><td>{g.rows.map((r) => `line ${r.source_row}: ${r.rate}`).join(' · ')}</td></tr>)}</tbody></table></div>
        ) : <p>At source time {String(o.source_timestamp)} (line {String(o.source_row)}).</p>}
      </section>
      <section>
        <h3>Compared with</h3>
        <p>Nothing. This is a separate ISS sensor record ({ev.context.instrument_id}, {ev.context.date_text}); it is not paired with any person.</p>
      </section>
    </>
  );
}
