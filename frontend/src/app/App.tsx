import { Component, type ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { DrawerHost } from "../components/DrawerHost";
import { SetupScreen, Skeleton } from "../components/StatusViews";
import Environment from "../pages/Environment";
import Health from "../pages/Health";
import Overview from "../pages/Overview";
import Reviews from "../pages/Reviews";
import { DrawerProvider, LiveProvider, StatusProvider, useServiceStatus } from "./providers";

class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="alert alert-error" role="alert">
        <div className="stack" style={{ gap: 8 }}>
          <strong>This view hit an unexpected interface error.</strong>
          <span>Saved reviews are stored by the local service and are not affected.</span>
          <div><button type="button" className="btn btn-secondary btn-sm" onClick={() => window.location.reload()}>Reload the page</button></div>
        </div>
      </div>
    );
  }
}

function Gate({ children }: { children: ReactNode }) {
  const { state } = useServiceStatus();
  if (state === "BOOTING") return <div style={{ paddingTop: 24 }}><Skeleton height={320} label="Connecting to the local CytoZoe service…" /></div>;
  if (state === "NO_DATA" || state === "SERVICE_UNAVAILABLE") return <SetupScreen kind={state} />;
  return <>{children}</>;
}

export function App() {
  return (
    <BrowserRouter>
      <StatusProvider>
        <DrawerProvider>
          <LiveProvider>
            <AppShell>
              <ErrorBoundary>
                <Gate>
                  <Routes>
                    <Route path="/" element={<Navigate to="/overview?participant=C001&sample=L-3" replace />} />
                    <Route path="/overview" element={<Overview />} />
                    <Route path="/health" element={<Health />} />
                    <Route path="/environment" element={<Environment />} />
                    <Route path="/reviews" element={<Reviews />} />
                    <Route path="*" element={<Navigate to="/overview" replace />} />
                  </Routes>
                  <DrawerHost />
                </Gate>
              </ErrorBoundary>
            </AppShell>
          </LiveProvider>
        </DrawerProvider>
      </StatusProvider>
    </BrowserRouter>
  );
}
