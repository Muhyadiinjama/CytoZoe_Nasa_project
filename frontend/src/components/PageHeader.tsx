import { useEffect, type ReactNode } from "react";
import { useDrawer, useServiceStatus } from "../app/providers";

export function ServiceStatus() {
  const { state } = useServiceStatus();
  const ok = state === "READY" || state === "NO_DATA";
  return (
    <span className={`service-status ${ok ? "ok" : "bad"}`} role="status">
      <span className="dot" aria-hidden="true" />
      {state === "BOOTING" ? "Checking local data…" : state === "READY" ? "Local data loaded" : state === "NO_DATA" ? "No data imported" : "Local service unavailable"}
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
        {study ? (
          <>
            <span>{study === "health" ? "Historical data, not live · OSD-575" : "Separate case study · ISS DosTel1"}</span>
            <span className="meta-sep" aria-hidden="true">·</span>
          </>
        ) : null}
        <ServiceStatus />
        <span className="meta-sep" aria-hidden="true">·</span>
        <button type="button" className="link-button" onClick={() => open({ kind: "sources" })}>
          Sources &amp; quality
        </button>
        {children}
      </div>
    </header>
  );
}
