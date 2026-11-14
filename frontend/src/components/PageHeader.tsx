import { useEffect, type ReactNode } from "react";
import { useDrawer, useServiceStatus } from "../app/providers";
import { IconHistory, IconSatellite, IconSource } from "./icons";

export function StudyBadge({ kind }: { kind: "health" | "environment" }) {
  return kind === "health" ? (
    <span className="badge badge-history"><IconHistory />Historical research data · OSD-575</span>
  ) : (
    <span className="badge badge-history"><IconSatellite />Separate case study · ISS DosTel1</span>
  );
}

export function ServiceStatus() {
  const { state } = useServiceStatus();
  const ok = state === "READY" || state === "NO_DATA";
  return (
    <span className={`service-status ${ok ? "ok" : "bad"}`} role="status">
      <span className="dot" aria-hidden="true" />
      {state === "BOOTING" ? "Checking local service…" : ok ? "Local service connected" : "Local service unavailable"}
    </span>
  );
}

export function PageHeader({ eyebrow, title, purpose, study, children }: {
  eyebrow: string; title: string; purpose: string; study?: "health" | "environment"; children?: ReactNode;
}) {
  const { open } = useDrawer();
  useEffect(() => {
    document.title = `${title} · CytoZoe`;
  }, [title]);
  return (
    <header className="page-head">
      <div className="page-head-text">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="purpose">{purpose}</p>
      </div>
      <div className="page-head-meta">
        {study ? <StudyBadge kind={study} /> : null}
        <ServiceStatus />
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => open({ kind: "sources" })}>
          <IconSource />Sources &amp; quality
        </button>
        {children}
      </div>
    </header>
  );
}
