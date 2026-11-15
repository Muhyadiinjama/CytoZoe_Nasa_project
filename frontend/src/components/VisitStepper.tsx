import type { Sample } from "../api/contracts";

/** Compact seven-visit indicator: shows where the selected historical sample sits and lets the reviewer jump. */
export function VisitStepper({ samples, value, onChange }: { samples: Sample[]; value: string; onChange: (v: string) => void }) {
  const firstPost = samples.findIndex((s) => s.phase !== "PREFLIGHT");
  return (
    <div className="stepper" role="group" aria-label="Visit timeline">
      {samples.map((s, i) => (
        <span key={s.visit} className="stepper-slot">
          {i === firstPost && i > 0 ? <span className="stepper-flight" aria-hidden="true">Flight</span> : null}
          <button type="button" className={`stepper-dot${s.phase === "PREFLIGHT" ? " pre" : " post"}`} aria-pressed={s.visit === value}
            title={s.label} onClick={() => onChange(s.visit)}>
            <span className="pip" aria-hidden="true" />{s.visit}
          </button>
        </span>
      ))}
    </div>
  );
}
