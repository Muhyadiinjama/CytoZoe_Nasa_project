import { api } from "../api/client";
import type { BriefItem, MissionBrief } from "../api/contracts";
import { useDrawer } from "../app/providers";
import { fmt, RANGE_TEXT, rangeText } from "../lib/format";
import { useAsync, type AsyncState } from "../lib/useAsync";

/**
 * Pieces of "Evidence & Result Details" assembled from GET /api/mission/brief (MissionBriefV1).
 * Every sentence and number is the backend's; these components only lay them out.
 */
export function useResultDetails(participant: string, sample: string): AsyncState<MissionBrief> {
  const { dataVersion } = useDrawer();
  return useAsync(() => api.missionBrief(participant, sample), [participant, sample, dataVersion]);
}

const allItems = (b: MissionBrief) => [...b.findings, ...b.other_measurements, ...b.missing_measurements];

/** "Why flagged" and the recorded-follow-up guidance for one result. */
export function ResultGuidance({ brief, evidenceId }: { brief: MissionBrief | null; evidenceId: string }) {
  const item = brief ? allItems(brief).find((i) => i.evidence_id === evidenceId) : undefined;
  if (!item) return null;
  return (
    <div className="guidance">
      {item.explanation.why_flagged ? <p><strong>Why flagged.</strong> {item.explanation.why_flagged}</p> : null}
      <p><strong>Follow-up.</strong> {item.explanation.next_review_action}</p>
    </div>
  );
}

/** The other measured markers at the same visit (previously a table on the overview). */
export function OtherMarkers({ brief, evidenceId }: { brief: MissionBrief; evidenceId: string }) {
  const { open } = useDrawer();
  const rows: BriefItem[] = allItems(brief).filter((i) => i.evidence_id !== evidenceId);
  return (
    <section className="stack" style={{ gap: 8 }} aria-labelledby="other-markers-title">
      <h3 id="other-markers-title">Other markers at {brief.context.visit_label}</h3>
      <div className="table-wrap">
        <table className="data other-markers">
          <caption>Same sample, data row {brief.findings[0]?.source.source_row ?? brief.other_measurements[0]?.source.source_row}</caption>
          <thead><tr><th scope="col">Marker</th><th scope="col" className="num">Value</th><th scope="col">Supplied range</th><th scope="col">Status</th><th scope="col"><span className="sr-only">Action</span></th></tr></thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.evidence_id}>
                <th scope="row" style={{ fontWeight: 550 }}>{m.marker_name}</th>
                <td className="num">{m.value === null ? "—" : `${fmt(m.value)} ${m.unit}`}</td>
                <td>{rangeText(m.range_low, m.range_high, m.unit)}</td>
                <td className={m.needs_review ? "status-review" : undefined}>{RANGE_TEXT[m.status]}</td>
                <td style={{ textAlign: "right" }}>
                  <button type="button" className="btn btn-ghost btn-sm" style={{ minHeight: 32 }}
                    onClick={() => open({ kind: "evidence", id: m.evidence_id })} aria-label={`Show details: ${m.marker_name}`}>Show details</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
