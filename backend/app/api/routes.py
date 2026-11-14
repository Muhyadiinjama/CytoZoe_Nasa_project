"""HTTP API. All numeric facts are computed here, never in the frontend."""
from __future__ import annotations

import asyncio
import json
import re
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from .. import config, db
from ..errors import AppError, bad_request
from ..schemas import MissionBriefV1
from ..services import environment_service, evidence, explain, export, health_service, importer, live, reviews, runtime
from ..services import mission_brief as mission_brief_service

router = APIRouter(prefix="/api")

Status = Literal["OPEN", "FOLLOW_UP_REQUESTED", "REVIEWED"]
QuestionId = Literal["EXPLAIN_RESULT", "HOW_CALCULATED", "LIMITATIONS", "DIAGNOSIS_REQUEST", "CAUSATION_REQUEST",
                     "SOURCE_LOCATION", "FOLLOW_UP_OPTIONS"]
ID_RE = re.compile(r"^[A-Za-z0-9_\-:+.T]{1,200}$")


def _check_note(value: str) -> str:
    if not value.strip():
        raise ValueError("A review note is required and cannot be only whitespace.")
    return value


class ReviewCreate(BaseModel):
    finding_id: str = Field(min_length=1, max_length=200)
    status: Status = "OPEN"
    note: str = Field(min_length=1, max_length=config.NOTE_MAX_CHARS)
    follow_up_date: date | None = None

    _note = field_validator("note")(_check_note)


class ReviewPatch(BaseModel):
    version: int = Field(ge=1)
    status: Status | None = None
    note: str | None = Field(default=None, min_length=1, max_length=config.NOTE_MAX_CHARS)
    follow_up_date: date | None = None
    clear_follow_up_date: bool = False

    @field_validator("note")
    @classmethod
    def _note(cls, v: str | None) -> str | None:
        return _check_note(v) if v is not None else v


class ExplainRequest(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    question_id: QuestionId | None = None
    # Typed question. Routed to a fixed template by keyword rules; never echoed or executed.
    message: str | None = Field(default=None, min_length=1, max_length=500)


@router.get("/healthz")
def healthz() -> dict[str, Any]:
    """Liveness: answers while the process is up, without touching the database."""
    return {"status": "alive", "app": "CytoZoe", "app_version": config.APP_VERSION}


@router.get("/readyz")
def readyz(response: Response) -> dict[str, Any]:
    """Readiness: 200 only when the DB, migrations and verified NASA datasets are all usable; 503 + code otherwise."""
    result = runtime.readiness()
    if not result["ready"]:
        response.status_code = 503
    return result


@router.get("/status")
def status() -> dict[str, Any]:
    readiness = runtime.readiness()
    out: dict[str, Any] = {
        "state": readiness["state"],
        "checks": readiness["checks"],
        "app": "CytoZoe", "app_version": config.APP_VERSION, "git_version": config.git_version(),
        "schema_version": db.schema_version(), "assistant_mode": "VERIFIED_TEMPLATES",
        "assistant_note": "Deterministic verified explanations. No language model is configured.",
        "network": "Loopback-only local service. The app makes no external requests at runtime.",
    }
    try:
        with db.session() as conn:
            rows = conn.execute("SELECT id, kind, sha256, imported_at FROM datasets ORDER BY id").fetchall()
            out["db_status"] = "OK"
            out["datasets"] = [dict(r) for r in rows]
            out["ready"] = {"health": any(r["kind"] == "HEALTH_CMP" for r in rows),
                            "environment": any(r["kind"] == "ENV_RADIATION" for r in rows)}
    except Exception:  # noqa: BLE001 — report state, never a traceback
        out["db_status"] = "UNAVAILABLE"
        out["datasets"] = []
        out["ready"] = {"health": False, "environment": False}
    return out


@router.get("/datasets")
def datasets() -> list[dict[str, Any]]:
    with db.session() as conn:
        out = []
        for r in conn.execute("SELECT * FROM datasets ORDER BY id"):
            d = dict(r)
            d["quality"] = json.loads(d.pop("quality_json"))
            if d["kind"] == "ENV_RADIATION":
                d["quality"].pop("conflict_groups_rows", None)
            out.append(d)
        return out


@router.post("/import")
async def import_csv(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise bad_request("UNSUPPORTED_FILE", "Only .csv files with a documented schema can be imported.")
    raw = await file.read(config.MAX_IMPORT_BYTES + 1)
    if len(raw) > config.MAX_IMPORT_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", "The file exceeds the 10 MB import limit.")
    result = importer.import_bytes(raw)
    environment_service._cache.clear()
    if result["status"] != "ALREADY_IMPORTED":
        live.broker.publish({"type": "dataset.imported", "dataset_id": result["dataset_id"], "sha256": result["sha256"]})
    return result


@router.get("/participants")
def participants() -> list[dict[str, Any]]:
    with db.session() as conn:
        return health_service.participants(conn)


@router.get("/health")
def health_overview(participant: str = Query(max_length=20), sample: str = Query(max_length=20)) -> dict[str, Any]:
    with db.session() as conn:
        return health_service.overview(conn, participant, sample)


@router.get("/mission/brief", response_model=MissionBriefV1)
def mission_brief(participant: str = Query(min_length=1, max_length=20),
                  sample: str = Query(min_length=1, max_length=20),
                  mode: str = Query(default="historical", max_length=20)) -> dict[str, Any]:
    """Mission Health Intelligence Brief for one historical sample, built only from canonical evidence."""
    with db.session() as conn:
        return mission_brief_service.build(conn, participant, sample, mode)


@router.get("/health/trend")
def health_trend(participant: str = Query(max_length=20), marker: str = Query(max_length=20)) -> dict[str, Any]:
    with db.session() as conn:
        return health_service.trend(conn, participant, marker)


@router.get("/environment")
def environment_view(request: Request, dataset_id: str | None = Query(default=None, max_length=60)) -> dict[str, Any]:
    if "participant" in request.query_params or "sample" in request.query_params:
        raise bad_request("CROSS_CASE_LINK_REJECTED",
                          "The environment case study is not linked to any health participant and cannot be paired.")
    with db.session() as conn:
        view = environment_service.environment_view(conn)
        if dataset_id and dataset_id != view["dataset"]["dataset_id"]:
            raise AppError(404, "NOT_FOUND", "Environment dataset was not found.", {"dataset_id": dataset_id})
        return view


@router.get("/evidence/{evidence_id:path}")
def get_evidence(evidence_id: str) -> dict[str, Any]:
    with db.session() as conn:
        return evidence.resolve(conn, evidence_id)


@router.post("/explain")
def post_explain(body: ExplainRequest) -> dict[str, Any]:
    if body.question_id is None and body.message is None:
        raise bad_request("QUESTION_REQUIRED", "Send a supported question_id or a message.")
    with db.session() as conn:
        ev = evidence.resolve(conn, body.evidence_id, include_review=False)
    qid = body.question_id or explain.classify(body.message or "")
    if qid is None:
        return explain.unsupported(ev["evidence_id"])
    return explain.explain(ev, qid)


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    """Live change feed (server-sent events) for reviews and imports across all open tabs."""
    queue = await live.broker.subscribe()

    async def gen():
        try:
            yield "retry: 3000\n\n"
            yield live.sse("hello", {"subscribers": live.broker.subscribers})
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                    yield live.sse(event["type"], event)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            live.broker.unsubscribe(queue)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.get("/replay/environment")
async def replay_environment(request: Request, speed: float = Query(default=1200, ge=1, le=200_000),
                             start: float = Query(default=0, ge=0, le=86_400)) -> StreamingResponse:
    """Stream the recorded DosTel1 day in source order at `speed`× real time. Always labelled HISTORICAL_REPLAY."""
    with db.session() as conn:
        view = environment_service.environment_view(conn)
    return StreamingResponse(live.environment_replay(view, speed, start, is_disconnected=request.is_disconnected),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.get("/replay/health")
def replay_health(participant: str = Query(max_length=20)) -> dict[str, Any]:
    with db.session() as conn:
        return health_service.replay(conn, participant)


@router.get("/reviews")
def list_reviews(
    case: Literal["health", "environment"] | None = None,
    status: Status | None = None,
    participant: str | None = Query(default=None, max_length=20),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    if participant and case == "environment":
        raise bad_request("CROSS_CASE_LINK_REJECTED", "Environment reviews have no participant.")
    with db.session() as conn:
        return reviews.list_reviews(conn, case, status, participant, page, page_size)


@router.get("/reviews/{review_id}")
def get_review(review_id: str) -> dict[str, Any]:
    with db.session() as conn:
        return reviews.get(conn, review_id)


def _origin(request: Request) -> str:
    value = request.headers.get("x-cytozoe-client", "")
    return value if re.fullmatch(r"[A-Za-z0-9-]{1,64}", value) else ""


@router.post("/reviews")
def create_review(body: ReviewCreate, response: Response, request: Request) -> dict[str, Any]:
    if not ID_RE.match(body.finding_id):
        raise bad_request("INVALID_FINDING_ID", "Finding ID has an unsupported format.")
    with db.session() as conn:
        review, created = reviews.create(
            conn, body.finding_id, body.status, body.note,
            body.follow_up_date.isoformat() if body.follow_up_date else None,
        )
    response.status_code = 201 if created else 200
    if created:
        live.broker.publish({**live.review_event("review.created", review), "origin": _origin(request)})
    return {"review": review, "created": created}


@router.patch("/reviews/{review_id}")
def patch_review(review_id: str, body: ReviewPatch, request: Request) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if body.status is not None:
        changes["status"] = body.status
    if body.note is not None:
        changes["note"] = body.note
    if body.follow_up_date is not None:
        changes["follow_up_date"] = body.follow_up_date.isoformat()
    elif body.clear_follow_up_date:
        changes["follow_up_date"] = None
    with db.session() as conn:
        review = reviews.patch(conn, review_id, body.version, changes)
    live.broker.publish({**live.review_event("review.updated", review), "origin": _origin(request)})
    return {"review": review}


@router.get("/export")
def export_packet(format: Literal["json", "html"] = "json", download: bool = True) -> Response:
    with db.session() as conn:
        packet = export.build_packet(conn)
    stamp = packet["generated_at"].replace(":", "").replace("-", "")
    disposition = f'attachment; filename="cytozoe-review-packet-{stamp}.{format}"' if download else "inline"
    if format == "html":
        return Response(export.render_html(packet), media_type="text/html; charset=utf-8",
                        headers={"Content-Disposition": disposition})
    return Response(export.to_json(packet), media_type="application/json; charset=utf-8",
                    headers={"Content-Disposition": disposition})
