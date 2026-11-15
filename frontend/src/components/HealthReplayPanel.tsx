import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useDrawer } from "../app/providers";
import { useAsync } from "../lib/useAsync";
import { IconPause, IconPlay, IconRestart, IconStep } from "./icons";

const PACES = [
  { ms: 3200, label: "Slow" },
  { ms: 1800, label: "Normal" },
  { ms: 900, label: "Fast" },
];

/**
 * Steps through a participant's real historical visits in order and drives the page's visit selection, so
 * every card and finding updates as each sample "arrives". Events come from the server's replay endpoint.
 */
export function HealthReplayPanel({ participant, visit, onVisit }: { participant: string; visit: string; onVisit: (v: string) => void }) {
  const { open } = useDrawer();
  const replay = useAsync(() => api.healthReplay(participant), [participant]);
  const [playing, setPlaying] = useState(false);
  const [pace, setPace] = useState(1800);
  const [shown, setShown] = useState<number>(-1); // index of the last frame revealed in this replay session
  const frames = replay.data?.frames ?? [];
  const idx = frames.findIndex((f) => f.visit === visit);
  const timer = useRef<number | null>(null);

  useEffect(() => { setPlaying(false); setShown(-1); }, [participant]);

  useEffect(() => {
    if (!playing || !frames.length) return;
    timer.current = window.setTimeout(() => {
      const next = shown + 1;
      if (next >= frames.length) { setPlaying(false); return; }
      setShown(next);
      onVisit(frames[next].visit);
    }, shown < 0 ? 150 : pace);
    return () => { if (timer.current) window.clearTimeout(timer.current); };
  }, [playing, shown, pace, frames, onVisit]);

  function toggle() {
    if (playing) { setPlaying(false); return; }
    if (shown >= frames.length - 1) setShown(-1);
    setPlaying(true);
  }
  function step() {
    setPlaying(false);
    const next = Math.min(frames.length - 1, Math.max(shown, idx) + 1);
    setShown(next);
    onVisit(frames[next].visit);
  }
  function restart() {
    setPlaying(false);
    setShown(-1);
  }

  const events = shown >= 0 ? frames.slice(0, shown + 1).flatMap((f) => f.events.filter((e) => e.kind !== "baseline").map((e) => ({ ...e, visit: f.visit }))).reverse() : [];
  const latest = events[0];
  const progress = shown >= 0 ? (shown + 1) / Math.max(frames.length, 1) : 0;

  return (
    <section className="replay-bar" aria-labelledby="replay-title">
      <h2 id="replay-title" className="sr-only">Replay {participant}'s mission timeline</h2>
      <div className="player">
        <button type="button" className="play" onClick={toggle} disabled={!frames.length}
          aria-label={playing ? "Pause timeline replay" : shown >= 0 && shown < frames.length - 1 ? "Resume timeline replay" : "Play timeline replay"}>
          {playing ? <IconPause /> : <IconPlay />}
        </button>
        <div className="progress" aria-hidden="true">
          <div className="progress-track"><div className="progress-fill" style={{ width: `${progress * 100}%` }} /></div>
          <div className="progress-meta">
            <span>{shown >= 0 ? `${frames[shown]?.visit_label} · replay` : "Visit set by selector"}</span>
            <span>{Math.max(shown + 1, 0)} / {frames.length} visits</span>
          </div>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={step} disabled={!frames.length || shown >= frames.length - 1}><IconStep />Next visit</button>
        <label className="sr-only" htmlFor="replay-pace">Replay pace</label>
        <select id="replay-pace" className="select" value={pace} onChange={(e) => setPace(Number(e.target.value))}>
          {PACES.map((p) => <option key={p.ms} value={p.ms}>{p.label}</option>)}
        </select>
        <button type="button" className="btn btn-secondary btn-sm" onClick={restart} disabled={shown < 0}><IconRestart />Reset</button>
      </div>
      <div className="replay-status">
        <p className={`replay-latest${latest?.kind === "flag" ? " is-flagged" : ""}`} role="status">
          {latest ? <><span className="replay-visit">{latest.visit}</span><span>{latest.text}</span></> : "Play steps the visit in order, or use the Visit selector above."}
        </p>
        {latest?.evidence_id ? (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => open({ kind: "evidence", id: latest.evidence_id! })}>Inspect</button>
        ) : null}
      </div>
    </section>
  );
}
