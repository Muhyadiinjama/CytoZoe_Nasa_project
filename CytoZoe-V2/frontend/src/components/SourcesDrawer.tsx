import { get } from '../api/client';
import type { DatasetPublic, Status } from '../api/contracts';
import { when } from '../lib/format';
import { useAsync } from '../lib/hooks';
import { ImportPanel } from './ImportPanel';
import { ErrorNotice, Skeleton } from './States';

export function SourcesContent({ status, onImported }: { status: Status | null; onImported: () => void }) {
  const ds = useAsync(() => get<{ datasets: (DatasetPublic & { is_active: boolean })[] }>('/api/datasets'), []);
  const refresh = () => { ds.reload(); onImported(); };
  const block = (kind: 'HEALTH_CMP' | 'ENV_RADIATION', title: string) => {
    const d = ds.data?.datasets.find((x) => x.kind === kind && x.is_active);
    const q = (d?.quality ?? {}) as Record<string, unknown>;
    const pi = kind === 'ENV_RADIATION' ? (q.per_instrument as Record<string, Record<string, number>> | undefined) : undefined;
    return (
      <section className="ev" style={{ gap: 8 }}>
        <h3>{title}</h3>
        {d ? <dl className="kv">
          <dt>File</dt><dd>{d.file_name}</dd><dt>SHA-256</dt><dd className="mono">{d.sha256}</dd>
          <dt>Imported</dt><dd>{when(d.imported_at)}</dd><dt>Source</dt><dd>{d.source_url}</dd><dt>Terms</dt><dd>{d.license_note}</dd>
          <dt>Quality</dt><dd>{kind === 'HEALTH_CMP'
            ? `${q.rows} samples · ${q.participant_count} participants · ${q.visit_count} visits · ${q.nonmissing_total} marker values · ${q.invalid_values_treated_as_missing} invalid values`
            : Object.entries(pi ?? {}).map(([k, v]) => `${k}: ${v.raw_rows} rows · ${v.conflict_groups} conflicting timestamps · ${v.quarantined_rows} rows excluded · ${v.accepted_rows} unambiguous`).join('; ')}</dd>
        </dl> : <p>Not imported.</p>}
        <ImportPanel kind={kind} onImported={refresh} />
      </section>);
  };
  return (
    <div className="ev">
      {ds.error ? <ErrorNotice error={ds.error} onRetry={ds.reload} /> : !ds.data ? <Skeleton label="Loading sources" /> : <>
        {block('HEALTH_CMP', 'Blood panel · NASA OSD-575 (Inspiration4)')}
        {block('ENV_RADIATION', 'Radiation · NASA RadLab (ISS)')}
      </>}
      <p className="meta">The two records are separate historical cases with different people, missions and dates. They are never paired.</p>
      {status ? <section className="ev" style={{ gap: 6 }}><h3>Local service</h3>
        <dl className="kv"><dt>App</dt><dd>v{status.app_version} · schema {status.schema_version}</dd><dt>Database</dt><dd>{status.db.ok ? 'OK (SQLite, this computer)' : 'Problem'}</dd>
          <dt>Assistant</dt><dd>{status.assistant_mode === 'VERIFIED_ONLY' ? 'Verified explanations only (no local model configured)' : `Verified explanations + AI draft wording from local model ${status.assistant_model}`}</dd></dl></section> : null}
    </div>);
}
