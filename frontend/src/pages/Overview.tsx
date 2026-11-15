import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { HealthEvidence, ReviewStatus } from "../api/contracts";
import { useDrawer } from "../app/providers";
import { IconFlag, IconShield } from "../components/icons";
import { MetricCard } from "../components/MetricCard";
import { PageHeader } from "../components/PageHeader";
import { useResultDetails } from "../components/ResultDetails";
import { ParticipantSelect, SampleSelect } from "../components/Selectors";
import { Alert, ErrorState, Skeleton } from "../components/StatusViews";
import { VisitStepper } from "../components/VisitStepper";
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
  const flagged = data ? data.cards.filter((c) => c.measurement.needs_review) : [];

  return (
    <>
      <PageHeader eyebrow="01 · Health Overview" title="Health Overview" study="health"
        purpose="Five blood markers from one historical sample, compared with the supplied laboratory range." />

      {participants.error ? <ErrorState error={participants.error} onRetry={participants.reload} /> : null}
      {resolved && participants.data ? (
        <div className="toolbar" role="group" aria-label="Sample selection">
          <ParticipantSelect participants={participants.data} value={resolved.participant.participant_id} onChange={(v) => update({ participant: v })} />
          <SampleSelect samples={resolved.participant.samples} value={resolved.sample.visit} onChange={(v) => update({ sample: v })} />
          <VisitStepper samples={resolved.participant.samples} value={resolved.sample.visit} onChange={(v) => update({ sample: v })} />
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

          <section className="card" aria-labelledby="review-title">
            <div className="card-head" style={{ marginBottom: flagged.length ? 12 : 8 }}>
              <div>
                <h2 id="review-title">Needs review</h2>
                <p>Values outside the range supplied in the source file. A flag is not a diagnosis.</p>
              </div>
              <span className={`badge ${flagged.length ? "badge-review" : "badge-history"}`}>
                {flagged.length ? <IconFlag /> : null}{flagged.length} of {data.cards.length} outside supplied range
              </span>
            </div>
            {flagged.length === 0 ? (
              <p className="small muted">Nothing to review at {data.visit_label}. This does not assess overall health.</p>
            ) : (
              <ul className="review-rows">
                {flagged.map((ev) => (
                  <li key={ev.evidence_id} className="review-row">
                    <span className="review-row-name">{ev.measurement.marker_name}</span>
                    <span className="review-row-text">{findingSentence(ev)}</span>
                    {ev.review ? <span className="badge badge-teal">{REVIEW_LABEL[ev.review.status]}</span> : <span className="meta">Not reviewed</span>}
                    <span className="btn-row">
                      <button type="button" className="btn btn-primary btn-sm" onClick={() => open({ kind: "evidence", id: ev.evidence_id })}
                        aria-label={`Inspect result: ${ev.measurement.marker_name}`}>Inspect result</button>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => open({ kind: "evidence", id: ev.evidence_id, section: "review" })}
                        aria-label={`${ev.review ? "Update follow-up" : "Record follow-up"} for ${ev.measurement.marker_name}`}>{ev.review ? "Update follow-up" : "Record follow-up"}</button>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <DataAndSources participant={data.participant_id} sample={data.visit} counts={data.participant_review_counts}
            dataset={data.dataset} />
        </>
      ) : null}
    </>
  );
}

/** Secondary information, collapsed by default: dataset identity, saved-review counts and dataset limitations. */
function DataAndSources({ participant, sample, counts, dataset }: {
  participant: string; sample: string; counts: Record<ReviewStatus, number>;
  dataset: { title: string; sha256: string; samples: number; participants: number; visits: string[]; nonmissing_values: number };
}) {
  const [opened, setOpened] = useState(false);
  const { open } = useDrawer();
  return (
    <details className="card data-sources" onToggle={(e) => setOpened((e.currentTarget as HTMLDetailsElement).open)}>
      <summary>
        <span className="ds-title">Data &amp; sources</span>
        <span className="ds-meta"><IconShield />NASA OSD-575 · SHA-256 {dataset.sha256.slice(0, 10)}…</span>
      </summary>
      <div className="ds-body">
        <dl className="kv small">
          <dt>Dataset</dt><dd>NASA OSD-575 · Inspiration4 Comprehensive Metabolic Panel</dd>
          <dt>Contents</dt><dd>{dataset.samples} samples ({dataset.participants} participants × {dataset.visits.length} visits) · {dataset.nonmissing_values} values across 5 markers</dd>
          <dt>SHA-256</dt><dd><code>{dataset.sha256}</code></dd>
          <dt>Saved reviews · {participant}</dt>
          <dd>{(Object.keys(REVIEW_LABEL) as ReviewStatus[]).map((s) => `${counts[s] ?? 0} ${REVIEW_LABEL[s].toLowerCase()}`).join(" · ")} · <Link to={`/reviews?case=health&participant=${participant}`}>Open in Review Log</Link></dd>
        </dl>
        {opened ? <Limitations participant={participant} sample={sample} /> : null}
        <div className="btn-row">
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => open({ kind: "sources" })}>Full source &amp; quality report</button>
        </div>
      </div>
    </details>
  );
}

function Limitations({ participant, sample }: { participant: string; sample: string }) {
  const details = useResultDetails(participant, sample);
  if (details.error) return <ErrorState error={details.error} onRetry={details.reload} />;
  if (!details.data) return <Skeleton height={80} label="Loading dataset limitations…" />;
  return (
    <div className="stack" style={{ gap: 6 }}>
      <h3>Dataset limitations</h3>
      <ul className="ev-list">{details.data.dataset_limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      <p className="small muted">{details.data.case_separation}</p>
    </div>
  );
}
