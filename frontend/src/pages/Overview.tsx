import { useCallback } from "react";
import { Link } from "react-router-dom";
import { HealthReplayPanel } from "../components/HealthReplayPanel";
import { api } from "../api/client";
import type { HealthEvidence, ReviewStatus } from "../api/contracts";
import { useDrawer } from "../app/providers";
import { IconFlag } from "../components/icons";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { ParticipantSelect, SampleSelect } from "../components/Selectors";
import { Alert, Empty, ErrorState, Skeleton } from "../components/StatusViews";
import { fmt, REVIEW_LABEL } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useHealthSelection } from "../lib/useHealthSelection";

function findingSentence(ev: HealthEvidence): string {
  const m = ev.measurement;
  const above = m.range_status === "ABOVE_SUPPLIED_UPPER_BOUND";
  const bound = above ? m.range_high! : m.range_low!;
  const gap = Math.abs((m.value ?? 0) - bound);
  return `${fmt(m.value)} ${m.unit} is ${above ? "above the supplied upper" : "below the supplied lower"} bound of ${fmt(bound)} ${m.unit} by ${fmt(gap)} ${m.unit}.`;
}

export default function Overview() {
  const { participants, resolved, notice, update } = useHealthSelection(false);
  const { open, dataVersion } = useDrawer();
  const pid = resolved?.participant.participant_id;
  const visit = resolved?.sample.visit;
  const overview = useAsync(() => api.health(pid!, visit!), [pid, visit, dataVersion], Boolean(pid && visit));
  const crew = useAsync(() => api.crew(visit!), [visit, dataVersion], Boolean(visit));
  const data = overview.data;
  const onVisit = useCallback((v: string) => update({ sample: v }, { replace: true }), [update]);
  const flagged = data ? data.cards.filter((c) => c.measurement.needs_review) : [];
  const totalFlagged = crew.data?.participants.reduce((n, p) => n + p.needs_review_count, 0) ?? 0;
  const totalMeasurements = crew.data?.participants.reduce((n, p) => n + p.measurement_count, 0) ?? 0;
  const crewVisit = crew.data?.visit_timeline.find((t) => t.visit === crew.data?.visit);

  return (
    <>
      <PageHeader eyebrow="01 · Health Overview" title="Health Overview" study="health"
        purpose="Five blood markers from one historical sample, compared with supplied ranges." />

      {participants.error ? <ErrorState error={participants.error} onRetry={participants.reload} /> : null}
      {resolved && participants.data ? (
        <div className="toolbar toolbar-compact" role="group" aria-label="Sample selection">
          <ParticipantSelect participants={participants.data} value={resolved.participant.participant_id} onChange={(v) => update({ participant: v })} compact />
          <SampleSelect samples={resolved.participant.samples} value={resolved.sample.visit} onChange={(v) => update({ sample: v })} compact />
          <p className="toolbar-note">L = days before launch · R = days after return.</p>
        </div>
      ) : participants.loading ? <Skeleton height={70} label="Loading participants…" /> : null}
      {notice ? <Alert tone="info">{notice}</Alert> : null}

      {pid && visit ? <HealthReplayPanel participant={pid} visit={visit} onVisit={onVisit} /> : null}

      {crew.error ? <ErrorState error={crew.error} onRetry={crew.reload} /> : null}
      {!crew.data && crew.loading ? <Skeleton height={240} label="Loading crew visit summary…" /> : null}
      {crew.data ? (
        <section className="crew-card" aria-labelledby="crew-title" aria-busy={crew.loading}>
          <div className="card-head">
            <div>
              <h2 id="crew-title">Crew snapshot · {crew.data.visit_label}</h2>
              <p>{crewVisit ? `${Math.abs(crewVisit.relative_day)} ${crewVisit.phase === "PREFLIGHT" ? "days before launch" : "days after return"} · ` : ""}
                {crew.data.participant_count} participants</p>
            </div>
            <span className={`crew-summary${totalFlagged ? " is-flagged" : ""}`}>{totalFlagged} of {totalMeasurements} outside supplied range</span>
          </div>
          <div className="crew-grid">
            {crew.data.participants.map((p) => (
              <article key={p.participant_id} className={`crew-member${p.participant_id === pid ? " is-current" : ""}`} aria-labelledby={`crew-${p.participant_id}`}>
                <div className="crew-head">
                  <h3 id={`crew-${p.participant_id}`}>{p.participant_id}</h3>
                  <span className={`crew-count${p.needs_review_count ? " is-flagged" : ""}`}>{p.needs_review_count} of {p.measurement_count}</span>
                </div>
                <div className="crew-flags">
                  {p.markers.filter((m) => m.needs_review).map((m) => (
                    <button key={m.marker} type="button" className="crew-marker"
                      onClick={() => open({ kind: "evidence", id: m.evidence_id })}
                      aria-label={`Inspect ${m.marker_name} for ${p.participant_id} at ${p.visit_label}: ${fmt(m.value)} ${m.unit}`}>
                      <IconFlag width={16} height={16} aria-hidden="true" />
                      <span>{m.marker_name}</span>{" "}
                      <strong>{fmt(m.value)} <span className="crew-marker-unit">{m.unit}</span></strong>
                    </button>
                  ))}
                  {p.needs_review_count === 0 ? <span className="crew-ok">All within range</span> : null}
                </div>
                <div className="crew-foot">
                  {p.participant_review_counts.OPEN ? (
                    <span className="meta">{p.participant_review_counts.OPEN} open review{p.participant_review_counts.OPEN === 1 ? "" : "s"}</span>
                  ) : <span />}
                  <Link className="btn btn-ghost btn-sm"
                    to={`/health?participant=${p.participant_id}&sample=${encodeURIComponent(p.visit)}&marker=${p.needs_review_markers[0] ?? "creatinine"}`}>
                    Open trends
                  </Link>
                </div>
              </article>
            ))}
          </div>
          <p className="visit-track-meta">{crew.data.participant_count} participants · values outside the supplied range</p>
          <div className="visit-track" role="group" aria-label="Seven-visit timeline">
            {crew.data.visit_timeline.map((t) => (
              <button key={t.visit} type="button" className={`visit-step${t.visit === visit ? " is-current" : ""}`}
                aria-pressed={t.visit === visit} aria-label={`Show ${t.label}: ${t.needs_review_count} of ${t.measurement_count} values outside the supplied range`}
                onClick={() => update({ sample: t.visit })}>
                <span className="visit-step-code">{t.visit}</span>
                <span className="visit-step-phase">{t.phase === "PREFLIGHT" ? "Preflight" : "Postflight"}</span>
                <span className={`visit-step-value${t.needs_review_count ? " is-flagged" : ""}`}>{t.needs_review_count}/{t.measurement_count}</span>
              </button>
            ))}
          </div>
          <p className="chart-note" title={`Counts are recorded values outside the source file's laboratory range. Rule ${crew.data.rule_version}; no participant is compared with another.`}>
            Counts = values outside the supplied range · rule {crew.data.rule_version}.
          </p>
        </section>
      ) : null}

      {overview.error ? <ErrorState error={overview.error} onRetry={overview.reload} /> : null}
      {!data && overview.loading ? <Skeleton height={190} label="Loading marker cards…" /> : null}

      {data ? (
        <>
          <section aria-labelledby="markers-title" aria-busy={overview.loading}>
            <h2 id="markers-title" className="sr-only">Marker values for {data.participant_id} at {data.visit_label}</h2>
            <div className="metric-grid">
              {data.cards.map((c) => <MetricCard key={c.evidence_id} ev={c} />)}
            </div>
          </section>

          <div className="split">
            <section className="card" aria-labelledby="review-title">
              <div className="card-head">
                <div>
                  <h2 id="review-title">Results to review</h2>
                  <p>{data.participant_id} · {data.visit_label} · values outside the range supplied in the source file</p>
                </div>
                <span className={`badge ${flagged.length ? "badge-review" : "badge-history"}`}>
                  {flagged.length ? <IconFlag /> : null}{flagged.length} of {data.cards.length} outside supplied range
                </span>
              </div>
              {flagged.length === 0 ? (
                <Empty>No selected measurements are outside the supplied ranges. This does not assess overall health.</Empty>
              ) : flagged.map((ev) => (
                <div className="finding" key={ev.evidence_id}>
                  <div style={{ minWidth: 0 }}>
                    <div className="finding-title">{ev.measurement.marker_name} · <span className="status-review">Needs review</span></div>
                    <p className="finding-body">{findingSentence(ev)}</p>
                    <p className="small muted" style={{ marginTop: 4 }}>
                      {ev.comparison.baseline_available
                        ? `Compared with ${ev.context.participant_id}'s retrospective preflight mean of ${fmt(ev.comparison.baseline)} ${ev.measurement.unit} (n = ${ev.comparison.n}).`
                        : "No personal baseline (fewer than two preflight values)."}
                      {ev.context.phase === "PREFLIGHT" ? " Collected before launch — not a spaceflight effect." : " Descriptive only; no cause is inferred."}
                      {" "}Not a diagnosis.
                    </p>
                    {ev.review ? <p style={{ marginTop: 6 }}><span className="badge badge-teal">{REVIEW_LABEL[ev.review.status]}</span></p> : null}
                  </div>
                  <div className="btn-row">
                    <button type="button" className="btn btn-primary" onClick={() => open({ kind: "evidence", id: ev.evidence_id })}
                      aria-label={`Inspect result: ${ev.measurement.marker_name}`}>Inspect result</button>
                    <button type="button" className="btn btn-secondary" onClick={() => open({ kind: "evidence", id: ev.evidence_id, section: "review" })}
                      aria-label={`${ev.review ? "Update follow-up" : "Record follow-up"} for ${ev.measurement.marker_name}`}>{ev.review ? "Update follow-up" : "Record follow-up"}</button>
                  </div>
                </div>
              ))}
            </section>

            <aside className="stack">
              <section className="card" aria-labelledby="data-title">
                <h2 id="data-title" style={{ marginBottom: 12 }}>Available data</h2>
                <dl className="kv small">
                  <dt>Dataset</dt><dd>NASA OSD-575 · Comprehensive Metabolic Panel</dd>
                  <dt>Samples</dt><dd>{data.dataset.samples} ({data.dataset.participants} participants × {data.dataset.visits.length} visits)</dd>
                  <dt>Selected values</dt><dd>{data.dataset.nonmissing_values} across 5 markers</dd>
                  <dt>SHA-256</dt><dd><code title={data.dataset.sha256}>{data.dataset.sha256.slice(0, 16)}…</code></dd>
                </dl>
                <p className="small muted" style={{ marginTop: 12 }}>Sparse blood draws, not continuous monitoring. The ISS radiation record is a separate case and is not linked to any participant.</p>
              </section>
              <section className="card" aria-labelledby="saved-title">
                <h2 id="saved-title" style={{ marginBottom: 12 }}>Saved reviews · {data.participant_id}</h2>
                <dl className="kv small">
                  {(Object.keys(REVIEW_LABEL) as ReviewStatus[]).map((s) => (
                    <FactPair key={s} k={REVIEW_LABEL[s]} v={String(data.participant_review_counts[s] ?? 0)} />
                  ))}
                </dl>
                <p style={{ marginTop: 12 }}><Link to={`/reviews?case=health&participant=${data.participant_id}`}>Open in Review Log</Link></p>
              </section>
            </aside>
          </div>
        </>
      ) : null}
    </>
  );
}

function FactPair({ k, v }: { k: string; v: string }) {
  return (<><dt>{k}</dt><dd>{v}</dd></>);
}
