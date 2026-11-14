import { useCallback } from "react";
import { Link } from "react-router-dom";
import { HealthReplayPanel } from "../components/HealthReplayPanel";
import { api } from "../api/client";
import type { HealthEvidence, ReviewStatus } from "../api/contracts";
import { useDrawer } from "../app/providers";
import { IconFlag } from "../components/icons";
import { MetricCard } from "../components/MetricCard";
import { MissionBriefPanel } from "../components/MissionBrief";
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
  const data = overview.data;
  const onVisit = useCallback((v: string) => update({ sample: v }, { replace: true }), [update]);
  const flagged = data ? data.cards.filter((c) => c.measurement.needs_review) : [];

  return (
    <>
      <PageHeader eyebrow="01 · Health Overview" title="Health Overview" study="health"
        purpose="What should I review? Five blood markers from one real historical Inspiration4 sample, compared with the laboratory range supplied in the source file and with the participant's own preflight samples." />

      {participants.error ? <ErrorState error={participants.error} onRetry={participants.reload} /> : null}
      {resolved && participants.data ? (
        <div className="toolbar" role="group" aria-label="Sample selection">
          <ParticipantSelect participants={participants.data} value={resolved.participant.participant_id} onChange={(v) => update({ participant: v })} />
          <SampleSelect samples={resolved.participant.samples} value={resolved.sample.visit} onChange={(v) => update({ sample: v })} />
          <p className="toolbar-note">Historical research sample · not a live reading. L = days before launch, R = days after return.</p>
          <div className="context-chips">
            <span className={`badge ${resolved.sample.phase === "PREFLIGHT" ? "badge-history" : "badge-replay"}`}>{resolved.sample.phase === "PREFLIGHT" ? "Preflight sample" : "Postflight sample"}</span>
          </div>
        </div>
      ) : participants.loading ? <Skeleton height={86} label="Loading participants…" /> : null}
      {notice ? <Alert tone="info">{notice}</Alert> : null}

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

          <div className="split-brief">
            <div className="stack" style={{ gap: 24, minWidth: 0 }}>
              <section className="card" aria-labelledby="review-title">
                <div className="card-head">
                  <div>
                    <p className="card-kicker">Action list</p>
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

              {pid && visit ? <HealthReplayPanel participant={pid} visit={visit} onVisit={onVisit} /> : null}

              <section className="card" aria-labelledby="data-title">
                <div className="card-head" style={{ marginBottom: 12 }}>
                  <div>
                    <p className="card-kicker">Dataset · OSD-575</p>
                    <h2 id="data-title">Available data &amp; saved reviews</h2>
                  </div>
                  <Link to={`/reviews?case=health&participant=${data.participant_id}`}>Open in Review Log</Link>
                </div>
                <div className="mini-stats" style={{ marginBottom: 14 }}>
                  {(Object.keys(REVIEW_LABEL) as ReviewStatus[]).map((s) => (
                    <div className="mini-stat" key={s}><b>{data.participant_review_counts[s] ?? 0}</b><span>{REVIEW_LABEL[s]} · {data.participant_id}</span></div>
                  ))}
                </div>
                <dl className="kv small">
                  <dt>Dataset</dt><dd>NASA OSD-575 · Comprehensive Metabolic Panel</dd>
                  <dt>Samples</dt><dd>{data.dataset.samples} ({data.dataset.participants} participants × {data.dataset.visits.length} visits)</dd>
                  <dt>Selected values</dt><dd>{data.dataset.nonmissing_values} across 5 markers</dd>
                  <dt>SHA-256</dt><dd><code title={data.dataset.sha256}>{data.dataset.sha256.slice(0, 16)}…</code></dd>
                </dl>
                <p className="small muted" style={{ marginTop: 12 }}>Sparse blood draws, not continuous monitoring. The ISS radiation record is a separate case and is not linked to any participant.</p>
              </section>
            </div>

            <MissionBriefPanel participant={data.participant_id} sample={data.visit} />
          </div>
        </>
      ) : null}
    </>
  );
}
