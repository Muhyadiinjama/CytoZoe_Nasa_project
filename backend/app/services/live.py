"""Real-time server-sent events: a broker for review/data changes and paced replays of real source data.

Replays stream the actual imported readings in their original order, faster than real time, and are always
labelled REPLAY. Nothing is generated: every streamed value is a stored source value or an E2/E3 result.
"""
from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, AsyncIterator, Awaitable, Callable


class Broker:
    """Fan-out of small change notifications to every connected browser tab."""

    def __init__(self) -> None:
        self._subs: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        with self._lock:
            self._loop = asyncio.get_running_loop()
            self._subs.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._subs.discard(queue)

    @property
    def subscribers(self) -> int:
        return len(self._subs)

    def publish(self, event: dict[str, Any]) -> None:
        """Thread-safe: called from sync route handlers running in the threadpool."""
        with self._lock:
            loop, subs = self._loop, list(self._subs)
        if loop is None or loop.is_closed():
            return
        for queue in subs:
            loop.call_soon_threadsafe(_offer, queue, event)


def _offer(queue: asyncio.Queue, event: dict[str, Any]) -> None:
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        pass  # a stalled tab misses a notification; it re-fetches on reconnect


broker = Broker()


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, allow_nan=False)}\n\n"


def review_event(kind: str, review: dict[str, Any]) -> dict[str, Any]:
    # Note text is deliberately not broadcast; tabs re-fetch what they need.
    return {"type": kind, "review": {k: review[k] for k in
            ("id", "finding_id", "case", "participant_id", "title", "status", "version", "updated_at")}}


async def environment_replay(view: dict[str, Any], speed: float, start: float, tick: float = 0.1,
                             is_disconnected: Callable[[], Awaitable[bool]] | None = None) -> AsyncIterator[str]:
    """Stream the day's accepted readings plus quality events in source-time order.

    `speed` = source seconds per real second. Events are flushed in small batches every `tick` seconds.
    Read-only: replays stored values; never writes. Stops promptly when the client disconnects.
    """
    integ = view["integration"]
    items: list[tuple[float, int, dict[str, Any]]] = []
    for seg in view["segments"]:
        for i, p in enumerate(seg["points"]):
            items.append((p["t"], 1, {"kind": "reading", "segment": seg["index"], "segment_start": i == 0, **p}))
    for g in view["quality"]["conflict_groups"]:
        items.append((g["t"], 0, {"kind": "excluded", "t": g["t"], "ts": g["timestamp"], "evidence_id": g["evidence_id"],
                                  "rows": g["rows"], "reason": "Conflicting duplicate timestamp — all rows quarantined"}))
    items.sort(key=lambda x: (x[0], x[1]))
    # Covered time is computed over the whole day first, so a resumed stream reports the same values.
    covered = 0.0
    prev: dict[str, Any] | None = None
    for _, _, item in items:
        if item["kind"] == "reading":
            if prev is not None and prev["segment"] == item["segment"]:
                covered += item["t"] - prev["t"]
            item["covered_seconds"] = covered
            prev = item
    items = [x for x in items if x[0] >= start]
    yield sse("meta", {"mode": "HISTORICAL_REPLAY", "label": "Replay of recorded data · 1 March 2022 · not live",
                       "timestamp_semantics": "Source clock as exported; no timezone suffix.",
                       "speed": speed, "start": start, "total_points": sum(len(s["points"]) for s in view["segments"]),
                       "final_estimated_sensor_dose_uGy": integ["estimated_sensor_dose_uGy"],
                       "span_seconds": integ["span_seconds"], "day_start": view["segments"][0]["points"][0]["t"] if view["segments"] else 0})
    if not items:
        yield sse("end", {"covered_seconds": 0})
        return
    loop = asyncio.get_running_loop()
    t_origin = items[0][0]
    wall_origin = loop.time()
    batch: list[dict[str, Any]] = []
    last_flush = wall_origin
    for t, _, item in items:
        due = wall_origin + (t - t_origin) / speed
        now = loop.time()
        if due > now:
            if batch:
                yield sse("frame", {"events": batch})
                batch = []
                last_flush = loop.time()
                if is_disconnected is not None and await is_disconnected():
                    return  # client went away: stop work, emit nothing further
            await asyncio.sleep(due - loop.time() if due > loop.time() else 0)
        batch.append(item)
        if loop.time() - last_flush >= tick and batch:
            yield sse("frame", {"events": batch})
            batch = []
            last_flush = loop.time()
    if batch:
        yield sse("frame", {"events": batch})
    yield sse("end", {"covered_seconds": covered, "estimated_sensor_dose_uGy": integ["estimated_sensor_dose_uGy"]})
