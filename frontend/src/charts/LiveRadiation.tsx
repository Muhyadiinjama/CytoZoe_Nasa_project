import { useCallback, useEffect, useRef, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from "recharts";
import type { StreamEvent, StreamExcluded, StreamReading } from "../api/contracts";
import { useDrawer } from "../app/providers";
import { IconPause, IconPlay, IconRestart } from "../components/icons";
import { clock, duration, fmt, timeOnly } from "../lib/format";

const SPEEDS = [
  { v: 300, label: "300× (5 min / s)" },
  { v: 1200, label: "1200× (20 min / s)" },
  { v: 3600, label: "3600× (1 h / s)" },
];
type Status = "idle" | "playing" | "paused" | "ended" | "error";
interface FeedItem { id: number; time: string; text: string; kind: "excl" | "info"; evidenceId?: string }

/**
 * Real-time replay of the recorded DosTel1 day. The server streams the actual accepted readings and quality
 * events (SSE) in source-time order; this component only displays them. Always labelled as a replay.
 */
export function LiveRadiation({ spanSeconds, finalDose }: { spanSeconds: number; finalDose: number }) {
  const { open } = useDrawer();
  const [status, setStatus] = useState<Status>("idle");
  const [speed, setSpeed] = useState(1200);
  const [latest, setLatest] = useState<StreamReading | null>(null);
  const [peak, setPeak] = useState<StreamReading | null>(null);
  const [segments, setSegments] = useState<StreamReading[][]>([]);
  const [excluded, setExcluded] = useState<StreamExcluded[]>([]);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const es = useRef<EventSource | null>(null);
  const buffer = useRef<StreamEvent[]>([]);
  const lastT = useRef<number>(-1);
  const feedId = useRef(1);
  const segRef = useRef<StreamReading[][]>([]);
  const peakRef = useRef<StreamReading | null>(null);

  const stop = useCallback(() => {
    es.current?.close();
    es.current = null;
  }, []);
  useEffect(() => stop, [stop]);

  // Apply buffered stream events at most ~10 times per second.
  useEffect(() => {
    if (status !== "playing") return;
    const timer = window.setInterval(() => {
      const batch = buffer.current.splice(0);
      if (!batch.length) return;
      const newFeed: FeedItem[] = [];
      let last: StreamReading | null = null;
      for (const e of batch) {
        if (e.kind === "reading") {
          const segs = segRef.current;
          const tail = segs[segs.length - 1];
          if (!tail || tail[0].segment !== e.segment) {
            if (tail) newFeed.push({ id: feedId.current++, time: timeOnly(e.ts), text: "Line resumes after the excluded readings.", kind: "info" });
            segs.push([e]);
          } else tail.push(e);
          if (!peakRef.current || e.rate > peakRef.current.rate) peakRef.current = e;
          last = e;
          lastT.current = e.t;
        } else {
          setExcluded((x) => [...x, e]);
          newFeed.push({ id: feedId.current++, time: timeOnly(e.ts), kind: "excl", evidenceId: e.evidence_id,
            text: `Conflicting readings at ${timeOnly(e.ts)} (${e.rows.map((r) => fmt(r.rate, 3)).join(" vs ")} µGy/hour). Both quarantined; the line and dose estimate break here.` });
          lastT.current = e.t;
        }
      }
      setSegments(segRef.current.map((s) => s.slice()));
      if (last) setLatest(last);
      setPeak(peakRef.current);
      if (newFeed.length) setFeed((f) => [...newFeed.reverse(), ...f].slice(0, 30));
    }, 100);
    return () => window.clearInterval(timer);
  }, [status]);

  const start = useCallback((fromT: number, spd: number) => {
    stop();
    const source = new EventSource(`/api/replay/environment?speed=${spd}&start=${fromT > 0 ? (fromT + 0.001).toFixed(3) : 0}`);
    es.current = source;
    source.addEventListener("frame", (ev) => {
      buffer.current.push(...(JSON.parse((ev as MessageEvent).data).events as StreamEvent[]));
    });
    source.addEventListener("end", () => {
      source.close();
      window.setTimeout(() => {
        setStatus("ended");
        setFeed((f) => [{ id: feedId.current++, time: "end", kind: "info" as const, text: `Replay finished. Estimated sensor dose over covered intervals: ${fmt(finalDose, 2)} µGy.` }, ...f]);
      }, 250);
    });
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) return;
      source.close();
      setStatus("error");
    };
    setStatus("playing");
  }, [finalDose, stop]);

  function reset() {
    stop();
    buffer.current = [];
    segRef.current = [];
    peakRef.current = null;
    lastT.current = -1;
    setSegments([]); setExcluded([]); setLatest(null); setPeak(null); setFeed([]);
  }
  function onPlay() {
    if (status === "playing") { stop(); setStatus("paused"); return; }
    if (status === "ended" || status === "idle" || status === "error") { reset(); start(0, speed); return; }
    start(lastT.current, speed);
  }
  function onSpeed(v: number) {
    setSpeed(v);
    if (status === "playing") start(lastT.current, v);
  }

  const progress = latest ? Math.min(1, latest.t / 86400) : 0;
  const coverage = latest && spanSeconds ? latest.covered_seconds / spanSeconds : 0;

  return (
    <section className="card stack" aria-labelledby="live-title">
      <div className="card-head" style={{ marginBottom: 0 }}>
        <div>
          <h2 id="live-title">Replay the day in real time</h2>
          <p>The local service streams every recorded DosTel1 reading in its original order, sped up. Values are the real source values — this is a replay, not live telemetry.</p>
        </div>
        <span className="badge badge-replay">Replay · recorded 1 March 2022 · not live</span>
      </div>

      <div className="player">
        <button type="button" className="play" onClick={onPlay} aria-label={status === "playing" ? "Pause replay" : status === "paused" ? "Resume replay" : "Start replay"}>
          {status === "playing" ? <IconPause /> : <IconPlay />}
        </button>
        <div className="progress" aria-hidden="true">
          <div className="progress-track"><div className="progress-fill" style={{ width: `${progress * 100}%` }} /></div>
          <div className="progress-meta"><span>{latest ? clock(latest.t, true) : "00:00:00"} source clock</span><span>24:00</span></div>
        </div>
        <label className="sr-only" htmlFor="replay-speed">Replay speed</label>
        <select id="replay-speed" className="select" value={speed} onChange={(e) => onSpeed(Number(e.target.value))} style={{ minHeight: 40 }}>
          {SPEEDS.map((s) => <option key={s.v} value={s.v}>{s.label}</option>)}
        </select>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => { reset(); setStatus("idle"); }} disabled={status === "idle"}>
          <IconRestart />Reset
        </button>
      </div>
      <p className="sr-only" role="status">{status === "playing" ? "Replay playing" : status === "paused" ? "Replay paused" : status === "ended" ? "Replay finished" : ""}</p>
      {status === "error" ? <div className="alert alert-error" role="alert">The replay stream was interrupted. Check that the local service is running, then press play to resume.</div> : null}

      <div className="live-stats">
        <div className="stat"><div className="stat-label">Source clock</div><div className="stat-value">{latest ? clock(latest.t, true) : "—"}</div></div>
        <div className="stat"><div className="stat-label">Current rate</div><div className="stat-value">{latest ? fmt(latest.rate, 2) : "—"} <small>µGy/h</small></div></div>
        <div className="stat"><div className="stat-label">Peak so far</div><div className="stat-value">{peak ? fmt(peak.rate, 1) : "—"} <small>{peak ? `at ${clock(peak.t)}` : "µGy/h"}</small></div></div>
        <div className="stat"><div className="stat-label">Est. sensor dose so far</div><div className="stat-value">{latest ? fmt(latest.cumulative, 2) : "—"} <small>µGy</small></div></div>
      </div>

      <div className="split" style={{ gap: 16 }}>
        <div>
          <div className="chart-box live" role="img" aria-label="Absorbed dose rate as the replay progresses. Exact values are in the static charts and tables below.">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart margin={{ top: 8, right: 12, bottom: 4, left: 0 }} accessibilityLayer={false}>
                <CartesianGrid stroke="#E6ECF1" vertical={false} />
                <XAxis type="number" dataKey="t" domain={[0, 86400]} ticks={[0, 21600, 43200, 64800, 86400]} tickFormatter={(v: number) => clock(v)}
                  tick={{ fill: "#53697D", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "#DDE5EB" }} allowDuplicatedCategory={false} />
                <YAxis scale="log" domain={[1, 1000]} allowDataOverflow ticks={[1, 10, 100, 1000]} width={48}
                  tick={{ fill: "#53697D", fontSize: 12 }} tickLine={false} axisLine={false} />
                {excluded.map((e) => <ReferenceLine key={e.ts} x={e.t} stroke="#B42318" strokeDasharray="3 3" />)}
                {segments.map((s) => <Line key={s[0].segment} data={s} dataKey="rate" stroke="#1F4E79" strokeWidth={1.4} dot={false} isAnimationActive={false} />)}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-note">µGy/hour, log scale. Coverage so far: {latest ? `${duration(latest.covered_seconds)} (${fmt(coverage * 100, 1)}% of the recorded span)` : "—"}.</p>
        </div>
        <div>
          <h3 style={{ marginBottom: 8 }}>Stream events</h3>
          {feed.length === 0 ? <p className="small muted">Press play. Data-quality decisions appear here the moment the replay reaches them.</p> : (
            <ul className="feed">
              {feed.map((f) => (
                <li key={f.id} className={f.kind}>
                  <time>{f.time}</time>
                  <span>{f.text}{f.evidenceId ? <> <button type="button" className="btn btn-ghost btn-sm" style={{ minHeight: 28, padding: "0 6px" }} onClick={() => open({ kind: "evidence", id: f.evidenceId! })}>Inspect</button></> : null}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
