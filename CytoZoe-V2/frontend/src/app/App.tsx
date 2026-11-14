import { useCallback, useEffect, useState } from 'react';
import { ApiError, get } from '../api/client';
import type { Status } from '../api/contracts';
import { Drawer } from '../components/Drawer';
import { SourcesContent } from '../components/SourcesDrawer';
import { Environment } from '../pages/Environment';
import { Health } from '../pages/Health';
import { Overview } from '../pages/Overview';
import { Reviews } from '../pages/Reviews';
import { navigate, ROUTES, useLocation } from './router';

type Boot = { kind: 'BOOTING' } | { kind: 'READY'; status: Status } | { kind: 'SERVICE_UNAVAILABLE'; message: string };

export function App() {
  const loc = useLocation();
  const [boot, setBoot] = useState<Boot>({ kind: 'BOOTING' });
  const [up, setUp] = useState(true);
  const [sources, setSources] = useState(false);
  const [menu, setMenu] = useState(false);
  const [gen, setGen] = useState(0);
  const check = useCallback(async () => {
    try { const s = await get<Status>('/api/status'); setBoot({ kind: 'READY', status: s }); setUp(true); }
    catch (e) { setUp(false); setBoot((b) => (b.kind === 'READY' ? b : { kind: 'SERVICE_UNAVAILABLE', message: (e as ApiError).message })); }
  }, []);
  useEffect(() => { void check(); const t = window.setInterval(check, 20000); return () => window.clearInterval(t); }, [check]);
  useEffect(() => {
    const cur = ROUTES.find((r) => r.path === loc.path)!;
    document.title = `${cur.label} · CytoZoe`;
    if (window.location.pathname === '/' ) navigate('/overview', undefined, { replace: true });
  }, [loc.path]);
  useEffect(() => { document.getElementById('page-title')?.focus(); window.scrollTo(0, 0); setMenu(false); }, [loc.path]);

  if (boot.kind === 'BOOTING') return <div className="center-screen"><div className="card" role="status"><h1>CytoZoe</h1><p>Connecting to the local service…</p></div></div>;
  if (boot.kind === 'SERVICE_UNAVAILABLE') return (
    <div className="center-screen"><div className="card" role="alert">
      <h1>Local service unavailable</h1>
      <p>CytoZoe's pages need the local service on this computer. {boot.message}</p>
      <p className="small">Start it with <code>scripts/start.sh</code> (macOS/Linux) or <code>scripts\start.ps1</code> (Windows), then try again. Nothing is saved in the browser while it is stopped.</p>
      <div><button className="btn primary" type="button" onClick={() => void check()}>Try again</button></div>
    </div></div>);

  const Page = { '/overview': Overview, '/health': Health, '/environment': Environment, '/reviews': Reviews }[loc.path];
  return (
    <div className="app">
      <a className="skip" href="#page-title" onClick={(e: { preventDefault(): void }) => { e.preventDefault(); document.getElementById('page-title')?.focus(); }}>Skip to main content</a>
      <aside className={menu ? 'rail open' : 'rail'} id="rail">
        <div className="wordmark">CytoZoe<small>Understand the change. Keep the evidence.</small></div>
        <nav className="nav" aria-label="Main">
          {ROUTES.map((r, i) => (
            <a key={r.path} href={r.path} aria-current={loc.path === r.path ? 'page' : undefined} title={r.label}
              onClick={(e: { preventDefault(): void; ctrlKey: boolean; metaKey: boolean }) => { if (e.ctrlKey || e.metaKey) return; e.preventDefault(); navigate(r.path, keepContext(r.path, loc.params)); }}>
              <span className="num" aria-hidden="true">{i + 1}</span><span className="label">{r.label}</span>
            </a>))}
        </nav>
        <div className="rail-foot">
          <p>Public research demo. Not clinical software.</p>
          <p className={up ? 'service' : 'service down'} role="status" title={up ? 'Local service running' : 'Local service not responding'}><span className="dot" aria-hidden="true" />{up ? 'Local workspace · service running' : 'Local service not responding'}</p>
          <button className="btn" type="button" aria-label="Sources and data quality" onClick={() => setSources(true)}><span className="label">Sources &amp; quality</span><span className="compact-only" aria-hidden="true">i</span></button>
        </div>
      </aside>
      <main className="main" id="main">
        <div style={{ marginBottom: 12 }}><button className="btn menu-btn" type="button" aria-expanded={menu} aria-controls="rail" onClick={() => setMenu((m) => !m)}>Menu</button></div>
        <div className="main-inner" key={gen}>
          {!up ? <div className="notice error" role="alert">The local service stopped responding. Saved reviews are safe in the local database; reconnect to continue. <button className="btn small" type="button" onClick={() => void check()}>Retry</button></div> : null}
          <Page params={loc.params} />
        </div>
      </main>
      {sources ? <Drawer title="Sources and data quality" onClose={() => setSources(false)}><SourcesContent status={boot.status} onImported={() => { void check(); setGen((g) => g + 1); }} /></Drawer> : null}
    </div>
  );
}

function keepContext(path: string, params: URLSearchParams): Record<string, string | null> {
  if (path === '/overview' || path === '/health') return { participant: params.get('participant'), sample: params.get('sample') };
  return {};
}
