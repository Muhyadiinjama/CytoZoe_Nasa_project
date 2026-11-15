import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { HealthEvidence } from "../api/contracts";
import { useDrawer } from "../app/providers";
import { HealthChartLegend, HealthVisitChart, type ChartMode } from "../charts/HealthVisitChart";
import { HealthEvidencePanel } from "../components/EvidencePanel";
import { PageHeader } from "../components/PageHeader";
import { ReviewForm } from "../components/ReviewForm";
import { MarkerTabs, ParticipantSelect, SampleSelect } from "../components/Selectors";
import { Alert, ErrorState, Skeleton } from "../components/StatusViews";
import { fmt, RANGE_TEXT, signed } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { MARKER_NAME, MARKERS, useHealthSelection } from "../lib/useHealthSelection";

export default function Health() {
  const { participants, resolved, notice, update } = useHealthSelection(true);
  const { open, dataVersion } = useDrawer();
  const pid = resolved?.participant.participant_id;
  const visit = resolved?.sample.visit;
  const marker = resolved?.marker ?? undefined;
  const enabled = Boolean(pid && visit && marker);
  const trend = useAsync(() => api.trend(pid!, marker!), [pid, marker, dataVersion], enabled);
  const overview = useAsync(() => api.health(pid!, visit!), [pid, visit, dataVersion], enabled);
  const ev: HealthEvidence | undefined = overview.data?.cards.find((c) => c.measurement.marker === marker);
  const flagged = new Set(overview.data?.cards.filter((c) => c.measurement.needs_review).map((c) => c.measurement.marker) ?? []);
  const [writing, setWriting] = useState(false);
  const [mode, setMode] = useState<ChartMode>("absolute");
  const deltaAvailable = Boolean(trend.data?.baseline.available && trend.data.baseline.value !== null);
  useEffect(() => setWriting(false), [pid, visit, marker]);

  return (
    <>
      <PageHeader eyebrow="02 · Health Trends" title="Health Trends" study="health"
        purpose="Every sample visit for one marker, against the supplied range and preflight mean." />

      {participants.error ? <ErrorState error={participants.error} onRetry={participants.reload} /> : null}
      {resolved && participants.data ? (
        <div className="toolbar toolbar-compact" role="group" aria-label="Sample selection">
          <ParticipantSelect participants={participants.data} value={resolved.participant.participant_id} onChange={(v) => update({ participant: v })} compact />
          <SampleSelect samples={resolved.participant.samples} value={resolved.sample.visit} onChange={(v) => update({ sample: v })} compact />
        </div>
      ) : participants.loading ? <Skeleton height={70} label="Loading participants…" /> : null}
      {notice ? <Alert tone="info">{notice}</Alert> : null}

      {marker ? (
        <MarkerTabs markers={MARKERS.map((m) => ({ id: m, label: MARKER_NAME[m] }))} value={marker} flagged={flagged}
          onChange={(m) => update({ marker: m })} panelId="marker-panel" />
      ) : null}

      <div id="marker-panel" role="tabpanel" aria-labelledby={marker ? `tab-${marker}` : undefined} className="split split-trends">
        <section className="card" aria-labelledby="chart-title" aria-busy={trend.loading}>
          <div className="card-head">
            <div>
              <h2 id="chart-title">{trend.data ? `${trend.data.marker_name} by visit · ${trend.data.participant_id}` : "Marker by visit"}</h2>
              <p>{trend.data ? `${trend.data.points.length} actual samples · L = before launch · R = after return` : "Actual sample visits"}</p>
            </div>
            <div className="seg-control" role="group" aria-label="Chart value mode">
              <button type="button" className="seg-btn" aria-pressed={mode === "absolute"} onClick={() => setMode("absolute")}>Actual values</button>
              <button type="button" className="seg-btn" aria-pressed={mode === "delta"} disabled={!deltaAvailable} onClick={() => setMode("delta")}>Change from baseline</button>
            </div>
          </div>
          {trend.error ? <ErrorState error={trend.error} onRetry={trend.reload} /> : null}
          {!trend.data && trend.loading ? <Skeleton height={360} label="Loading chart…" /> : null}
          {trend.data && visit ? (
            <>
              <HealthVisitChart trend={trend.data} selectedVisit={visit} onSelect={(v) => update({ sample: v })} mode={mode} />
              <HealthChartLegend trend={trend.data} mode={mode} />
              <p className="chart-note" title={mode === "delta" && deltaAvailable ? trend.data.delta_note : undefined}>
                Click a dot or table row to select a visit. Visits are categorical, not equally spaced; values are not interpolated.
              </p>
              <details className="disclosure">
                <summary>Data table · {trend.data.points.length} source values</summary>
                <div className="table-wrap">
                  <table className="data">
                    <caption>{trend.data.marker_name} ({trend.data.unit}) for {trend.data.participant_id}, from {trend.data.points.length} source rows</caption>
                    <thead><tr>
                      <th scope="col">Visit</th><th scope="col" className="num">Value</th>
                      <th scope="col" className="num">Δ vs mean</th><th scope="col" className="num">%Δ</th>
                      <th scope="col" className="num">Supplied min</th><th scope="col" className="num">Supplied max</th>
                      <th scope="col">Range status</th><th scope="col" className="num">Data row</th>
                    </tr></thead>
                    <tbody>
                      {trend.data.points.map((p) => (
                        <tr key={p.visit} className={p.visit === visit ? "row-selected" : undefined} aria-current={p.visit === visit ? "true" : undefined}>
                          <td><button type="button" className="btn btn-ghost btn-sm" onClick={() => update({ sample: p.visit })}
                            aria-label={`Select visit ${p.visit_label}`}>{p.visit_label}</button></td>
                          <td className="num">{p.value === null ? "missing" : fmt(p.value)}</td>
                          <td className="num">{p.delta === null ? "—" : `${signed(p.delta)} ${trend.data!.unit}`}</td>
                          <td className="num">{p.percent_delta === null ? "—" : `${signed(p.percent_delta, 1)}%`}</td>
                          <td className="num">{fmt(p.range_low)}</td>
                          <td className="num">{fmt(p.range_high)}</td>
                          <td className={p.needs_review ? "status-review" : undefined}>{RANGE_TEXT[p.range_status]}</td>
                          <td className="num">{p.source_row}</td>
                        </tr>
                      ))}
                      <tr>
                        <th scope="row">Preflight mean</th>
                        <td className="num">{trend.data.baseline.available ? fmt(trend.data.baseline.value) : "not computed"}</td>
                        <td colSpan={6} className="muted">n = {trend.data.baseline.n} · calculated, not a sample · Δ = x − B</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </details>
            </>
          ) : null}
        </section>

        <section className="card" aria-labelledby="evidence-title">
          <div className="card-head">
            <div>
              <h2 id="evidence-title">Evidence</h2>
              <p>{ev ? `${ev.measurement.marker_name} · ${ev.context.visit_label}` : "Selected sample"}</p>
            </div>
            {ev ? <button type="button" className="btn btn-ghost btn-sm" onClick={() => open({ kind: "evidence", id: ev.evidence_id, section: "explain" })}>Explain</button> : null}
          </div>
          {overview.error ? <ErrorState error={overview.error} onRetry={overview.reload} /> : null}
          {!ev && overview.loading ? <Skeleton height={420} label="Loading evidence…" /> : null}
          {ev ? (
            <HealthEvidencePanel ev={ev} variant="trend" followUp={writing
              ? <ReviewForm key={ev.evidence_id} findingId={ev.evidence_id} review={ev.review} autoFocus />
              : <button type="button" className="btn btn-primary" onClick={() => setWriting(true)}>{ev.review ? "Update follow-up" : "Record follow-up"}</button>} />
          ) : null}
        </section>
      </div>
    </>
  );
}
