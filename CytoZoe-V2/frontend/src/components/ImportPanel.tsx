import { useState } from 'react';
import { api, ApiError, qs } from '../api/client';
import type { ImportReport } from '../api/contracts';

const MAX = 10 * 1024 * 1024;
/** Local CSV import: checked in the browser, validated again by the service; a failed import never replaces good data. */
export function ImportPanel({ kind, onImported }: { kind: 'HEALTH_CMP' | 'ENV_RADIATION'; onImported: () => void }) {
  const [msg, setMsg] = useState<{ kind: 'info' | 'success' | 'error'; text: string; details?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const label = kind === 'HEALTH_CMP' ? 'OSD-575 blood panel CSV' : 'RadLab radiation CSV';
  async function onFile(f: File | undefined) {
    if (!f) return;
    if (!/\.csv$/i.test(f.name)) { setMsg({ kind: 'error', text: 'Only .csv files are accepted. Nothing was replaced.' }); return; }
    if (f.size > MAX) { setMsg({ kind: 'error', text: 'That file is over 10 MB. Nothing was replaced.' }); return; }
    setBusy(true); setMsg({ kind: 'info', text: `Importing ${f.name}…` });
    try {
      const r = await api<ImportReport>('POST', `/api/import?${qs({ kind, file_name: f.name })}`, undefined, { raw: f, timeoutMs: 60000 });
      setMsg({ kind: 'success', text: r.status === 'ALREADY_IMPORTED' ? `${f.name} was already imported (same SHA-256); it is now the active file.` : `Imported ${f.name}. SHA-256 ${r.sha256.slice(0, 12)}…` });
      onImported();
    } catch (e) {
      const err = e as ApiError;
      setMsg({ kind: 'error', text: `${err.code}: ${err.message}`, details: Object.keys(err.details ?? {}).length ? JSON.stringify(err.details) : undefined });
    } finally { setBusy(false); }
  }
  const id = 'imp-' + kind;
  return (
    <div className="stack">
      <label className="lbl" htmlFor={id}>{`Choose ${label}`}
        <input id={id} className="field" type="file" accept=".csv,text/csv" disabled={busy}
          onChange={(e: { target: HTMLInputElement }) => { void onFile(e.target.files?.[0]); e.target.value = ''; }} />
      </label>
      <p className="meta">Read on this computer by the local service; nothing is uploaded to the internet. Max 10 MB, documented columns only.</p>
      {msg ? <div className={`notice ${msg.kind}`} role={msg.kind === 'error' ? 'alert' : 'status'} data-testid={'import-msg-' + kind}>{msg.text}{msg.details ? <div className="mono" style={{ marginTop: 6 }}>{msg.details}</div> : null}</div> : null}
    </div>
  );
}
