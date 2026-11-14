import { useId, useRef, type KeyboardEvent } from "react";
import type { Participant, Sample } from "../api/contracts";

export function ParticipantSelect({ participants, value, onChange }: { participants: Participant[]; value: string; onChange: (v: string) => void }) {
  const id = useId();
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>Participant (anonymised)</label>
      <select id={id} className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        {participants.map((p) => <option key={p.participant_id} value={p.participant_id}>{p.participant_id}</option>)}
      </select>
    </div>
  );
}

export function SampleSelect({ samples, value, onChange }: { samples: Sample[]; value: string; onChange: (v: string) => void }) {
  const id = useId();
  return (
    <div className="field" style={{ minWidth: 200 }}>
      <label className="field-label" htmlFor={id}>Visit (historical sample)</label>
      <select id={id} className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        {samples.map((s) => <option key={s.visit} value={s.visit}>{s.label}</option>)}
      </select>
    </div>
  );
}

/** WAI-ARIA tabs with roving focus (Left/Right/Home/End). */
export function MarkerTabs({ markers, value, onChange, flagged, panelId }: {
  markers: { id: string; label: string }[]; value: string; onChange: (v: string) => void; flagged: Set<string>; panelId: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent, i: number) => {
    let next = -1;
    if (e.key === "ArrowRight") next = (i + 1) % markers.length;
    else if (e.key === "ArrowLeft") next = (i - 1 + markers.length) % markers.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = markers.length - 1;
    if (next >= 0) {
      e.preventDefault();
      refs.current[next]?.focus();
      onChange(markers[next].id);
    }
  };
  return (
    <div className="tabs" role="tablist" aria-label="Blood marker">
      {markers.map((m, i) => (
        <button key={m.id} ref={(el) => { refs.current[i] = el; }} type="button" role="tab" className="tab"
          id={`tab-${m.id}`} aria-selected={value === m.id} aria-controls={panelId} tabIndex={value === m.id ? 0 : -1}
          onClick={() => onChange(m.id)} onKeyDown={(e) => onKey(e, i)}>
          {m.label}
          {flagged.has(m.id) ? <><span className="tab-flag" aria-hidden="true" /><span className="sr-only"> (outside supplied range at this visit)</span></> : null}
        </button>
      ))}
    </div>
  );
}
