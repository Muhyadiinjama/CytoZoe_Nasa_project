import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useDrawer, useLive, useServiceStatus } from "../app/providers";
import { REVIEW_LABEL } from "../lib/format";
import { BrandMark, IconCheck, IconClose, IconLog, IconMenu, IconOverview, IconRadiation, IconTrend } from "./icons";

const NAV = [
  { to: "/overview", label: "Health Overview", Icon: IconOverview },
  { to: "/health", label: "Health Trends", Icon: IconTrend },
  { to: "/environment", label: "Radiation Review", Icon: IconRadiation },
  { to: "/reviews", label: "Review Log & Export", Icon: IconLog },
];

function Brand() {
  return (
    <NavLink to="/overview" className="brand">
      <BrandMark className="brand-mark" />
      <span className="brand-text">
        <span className="brand-name">CytoZoe</span>
        <span className="brand-tag">Health evidence workspace</span>
      </span>
    </NavLink>
  );
}

function RecentReviews() {
  const { recent, flashId } = useLive();
  const { open } = useDrawer();
  return (
    <section aria-labelledby="recent-title">
      <h2 id="recent-title" className="side-label" >Recent reviews</h2>
      {recent.length === 0 ? <p className="side-empty">No reviews yet.</p> : (
        <ul className="recent-list">
          {recent.map((r) => (
            <li key={r.id}>
              <button type="button" className={`recent-item${flashId === r.id ? " flash" : ""}`} onClick={() => open({ kind: "review", id: r.id })}
                title={`${r.title} — ${REVIEW_LABEL[r.status]}`}>
                <span className={`status-dot ${r.status}`} aria-hidden="true" />
                <span className="t">{r.title}</span>
                <span className="sr-only">, {REVIEW_LABEL[r.status]}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Toasts() {
  const { toasts } = useLive();
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => <div className="toast" key={t.id}><IconCheck />{t.text}</div>)}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const { status, state } = useServiceStatus();
  const { connected } = useLive();
  // Close only on page change: query updates (URL normalisation, timeline replay) must not close the menu.
  useEffect(() => setMenuOpen(false), [location.pathname]);

  return (
    <div className="shell">
      <a className="skip-link" href="#main">Skip to main content</a>
      <div className="mobile-bar">
        <button type="button" className="menu-button" aria-expanded={menuOpen} aria-controls="primary-nav"
          aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"} onClick={() => setMenuOpen((o) => !o)}>
          {menuOpen ? <IconClose width={22} height={22} /> : <IconMenu width={22} height={22} />}
        </button>
        <Brand />
      </div>
      {menuOpen ? <div className="scrim" onClick={() => setMenuOpen(false)} aria-hidden="true" /> : null}
      <aside className={`sidebar${menuOpen ? " open" : ""}`} id="primary-nav">
        <Brand />
        <nav aria-label="Primary">
          <p className="side-label" aria-hidden="true">Workspace</p>
          <ul className="nav-list">
            {NAV.map(({ to, label, Icon }, i) => (
              <li key={to}>
                <NavLink to={to} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                  <Icon /><span className="nav-label">{label}</span><span className="nav-index" aria-hidden="true">0{i + 1}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        {state === "READY" ? <RecentReviews /> : null}
        <div className="side-foot">
          <span className={`live-pill${connected ? "" : " off"}`} role="status">
            <span className="pulse" aria-hidden="true" />{connected ? "Live sync on" : state === "SERVICE_UNAVAILABLE" ? "Local service offline" : "Connecting…"}
          </span>
          <span>Runs locally on this computer · historical NASA research data · not a clinical device</span>
          <Link to="/" className="side-about">About CytoZoe &amp; photo credits</Link>
          {status ? <span className="ver">v{status.app_version} · {status.git_version}</span> : null}
        </div>
      </aside>
      <main id="main" className="main" tabIndex={-1}>
        <div className="content">{children}</div>
      </main>
      <Toasts />
    </div>
  );
}
