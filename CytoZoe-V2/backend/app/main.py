"""CytoZoe local service. Run: uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

Starlette + Pydantic (FastAPI's own foundations; FastAPI itself was not installable on the build machine).
Serves the compiled React app and the /api routes from one loopback origin. No outbound requests except the
optional Ollama call to a loopback address.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ValidationError
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .config import APP_VERSION, MAX_IMPORT_BYTES, SCHEMA_VERSION, Settings, load_settings
from .db import Database, dumps
from .engines.ingest import MARKERS, DataError
from .services import assistant, explain as explain_svc, export as export_svc
from .services.evidence import EvidenceNotFound, environment, find_evidence, health_cards, health_trend
from .services.reviews import ReviewError, Reviews, STATUSES
from .services.store import Store

log = logging.getLogger("cytozoe")
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]", "::1"]


# ---------- request schemas ----------
class ReviewCreate(BaseModel):
    evidence_id: str = Field(min_length=3, max_length=300)


class ReviewPatch(BaseModel):
    version: int = Field(ge=1)
    status: Optional[Literal["OPEN", "FOLLOW_UP_REQUESTED", "REVIEWED"]] = None
    note: Optional[str] = Field(default=None, max_length=4000)
    follow_up_date: Optional[date] = None
    clear_follow_up_date: bool = False


class ExplainRequest(BaseModel):
    evidence_id: str = Field(min_length=3, max_length=300)
    question_id: Literal["EXPLAIN", "HOW_CALCULATED", "LIMITS", "FREE_TEXT"]
    free_text: Optional[str] = Field(default=None, max_length=300)
    want_ai_draft: bool = True


# ---------- helpers ----------
class JSONR(JSONResponse):
    def render(self, content: Any) -> bytes:
        return dumps(content).encode("utf-8")  # never NaN/Infinity


def err(status: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONR:
    return JSONR({"code": code, "message": message, "details": details or {}}, status_code=status)


EVIDENCE_ERRORS = {
    "NO_HEALTH_DATA": (404, "No blood dataset is imported yet."),
    "NO_RADIATION_DATA": (404, "No radiation dataset is imported yet."),
    "UNKNOWN_PARTICIPANT": (404, "That participant is not in the imported data."),
    "UNKNOWN_SAMPLE": (404, "That sample is not in the imported data for this participant."),
    "UNKNOWN_MARKER": (404, "Unknown marker."),
    "UNKNOWN_INSTRUMENT": (404, "That instrument is not in the imported file."),
    "UNKNOWN_EVIDENCE": (404, "Unknown evidence id."),
    "EVIDENCE_NOT_IN_ACTIVE_DATA": (409, "That evidence belongs to a dataset that is no longer active."),
}


def ev_err(e: EvidenceNotFound) -> JSONR:
    code = str(e)
    st, msg = EVIDENCE_ERRORS.get(code, (404, "Not found."))
    return err(st, code, msg)


async def body_model(request: Request, model: type[BaseModel]) -> BaseModel:
    raw = await request.body()
    if len(raw) > 64_000:
        raise HTTPException(413, "Request too large.")
    return model.model_validate_json(raw or b"{}")


# ---------- app factory ----------
def create_app(settings: Settings | None = None) -> Starlette:
    s = settings or load_settings()
    db = Database(s.db_path)
    store = Store(db)
    reviews = Reviews(db, store)

    async def status(request: Request) -> Response:
        dbs = db.status()
        ds = [{"id": d["id"], "kind": d["kind"], "file_name": d["file_name"], "sha256": d["sha256"], "imported_at": d["imported_at"]}
              for d in store.datasets() if d["is_active"]]
        return JSONR({"app_version": APP_VERSION, "schema_version": SCHEMA_VERSION, "db": dbs, "datasets": ds,
                      "assistant_mode": s.assistant_mode, "assistant_model": s.ollama_model or None, "local_only": True,
                      "server_time": time.strftime("%Y-%m-%dT%H:%M:%S")})

    async def datasets(request: Request) -> Response:
        return JSONR({"datasets": store.datasets()})

    async def do_import(request: Request) -> Response:
        kind = request.query_params.get("kind", "")
        name = request.query_params.get("file_name", "upload.csv")
        cl = request.headers.get("content-length")
        data = bytearray()
        too_big = bool(cl and cl.isdigit() and int(cl) > MAX_IMPORT_BYTES)
        seen = 0
        async for chunk in request.stream():  # drain so the client gets a clean 413 instead of a reset
            seen += len(chunk)
            if seen > MAX_IMPORT_BYTES:
                too_big = True
            if not too_big:
                data.extend(chunk)
            if seen > 8 * MAX_IMPORT_BYTES:
                break
        if too_big:
            return err(413, "FILE_TOO_LARGE", "The file is over 10 MB. Nothing was replaced.")
        try:
            rep = store.import_file(kind, bytes(data), name)
        except DataError as e:
            return err(422 if e.code not in ("UNKNOWN_KIND",) else 400, e.code, e.message + " Nothing was replaced.", e.details)
        return JSONR(rep, status_code=201 if rep["status"] == "IMPORTED" else 200)

    async def participants(request: Request) -> Response:
        ds = store.active("HEALTH_CMP")
        if not ds:
            return err(404, "NO_HEALTH_DATA", "No blood dataset is imported yet.")
        obs = store.health_obs(ds["id"])
        out: dict[str, dict[str, Any]] = {}
        for o in obs:
            p = out.setdefault(o["participant_id"], {})
            p.setdefault(o["visit"], {"sample_id": o["sample_id"], "visit": o["visit"], "phase": o["phase"],
                                      "relative_day": o["relative_day"], "visit_order": o["visit_order"]})
        return JSONR({"dataset_id": ds["id"], "markers": [{k: m[k] for k in ("id", "label", "unit", "dp")} for m in MARKERS],
                      "participants": [{"id": pid, "samples": sorted(v.values(), key=lambda x: x["visit_order"])} for pid, v in sorted(out.items())]})

    def with_reviews(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rv = reviews.by_finding()
        return [{**it, "review_state": rv.get(it["evidence_id"])} for it in items]

    async def get_health(request: Request) -> Response:
        p, sample = request.query_params.get("participant", ""), request.query_params.get("sample", "")
        try:
            res = health_cards(store, p, sample)
        except EvidenceNotFound as e:
            return ev_err(e)
        cards = with_reviews(res["cards"])
        outside = [c["evidence_id"] for c in cards if c["measurement"]["range_status"] in ("ABOVE_SUPPLIED_UPPER_BOUND", "BELOW_SUPPLIED_LOWER_BOUND")]
        awaiting = sum(1 for r in reviews.list(case="health", participant=p)["items"] if r["status"] != "REVIEWED")
        return JSONR({"dataset": _ds_public(res["dataset"]), "sample": res["sample"], "cards": cards, "to_review": outside,
                      "summary": {"outside": len(outside), "available": sum(1 for c in cards if c["measurement"]["value"] is not None),
                                  "total": len(cards), "awaiting_follow_up": awaiting}})

    async def get_trend(request: Request) -> Response:
        try:
            res = health_trend(store, request.query_params.get("participant", ""), request.query_params.get("marker", ""))
        except EvidenceNotFound as e:
            return ev_err(e)
        res["dataset"] = _ds_public(res["dataset"])
        return JSONR(res)

    async def get_env(request: Request) -> Response:
        try:
            res = environment(store, request.query_params.get("dataset_id") or None, request.query_params.get("instrument") or None)
        except EvidenceNotFound as e:
            return ev_err(e)
        res["dataset"] = _ds_public(res["dataset"])
        res["findings"] = with_reviews(res["findings"])
        return JSONR(res)

    async def do_explain(request: Request) -> Response:
        try:
            req = await body_model(request, ExplainRequest)
        except ValidationError as e:
            return err(422, "VALIDATION_ERROR", "Invalid explain request.", {"errors": e.errors(include_url=False, include_input=False)})
        try:
            ev = find_evidence(store, req.evidence_id)
        except EvidenceNotFound as e:
            return ev_err(e)
        qid = req.question_id if req.question_id != "FREE_TEXT" else explain_svc.classify_free_text(req.free_text or "")
        verified = explain_svc.explain(ev, qid) if qid != "INSUFFICIENT_EVIDENCE" else explain_svc.insufficient()
        ai = assistant.draft(s, verified) if req.want_ai_draft and qid != "INSUFFICIENT_EVIDENCE" else (
            {"status": "OFF"} if not s.ollama_model else {"status": "FALLBACK", "reason": "Unsupported questions are answered by the verified template only."})
        return JSONR({"verified": verified, "ai": ai, "assistant_mode": s.assistant_mode})

    async def list_reviews(request: Request) -> Response:
        q = request.query_params
        case = q.get("case") or None
        st = q.get("status") or None
        if case not in (None, "health", "environment") or st not in (None, *STATUSES):
            return err(422, "VALIDATION_ERROR", "Unknown filter value.")
        try:
            limit, offset = min(max(int(q.get("limit", 200)), 1), 500), max(int(q.get("offset", 0)), 0)
        except ValueError:
            return err(422, "VALIDATION_ERROR", "limit and offset must be integers.")
        res = reviews.list(case, st, q.get("participant") or None, limit, offset)
        return JSONR(res)

    async def create_review(request: Request) -> Response:
        try:
            req = await body_model(request, ReviewCreate)
        except ValidationError as e:
            return err(422, "VALIDATION_ERROR", "Invalid review request.", {"errors": e.errors(include_url=False, include_input=False)})
        try:
            r, created = reviews.create(req.evidence_id)
        except EvidenceNotFound as e:
            return ev_err(e)
        return JSONR(reviews.get(r["id"]), status_code=201 if created else 200)

    async def review_detail(request: Request) -> Response:
        try:
            rid = int(request.path_params["rid"])
        except ValueError:
            return err(404, "NOT_FOUND", "Review not found.")
        if request.method == "GET":
            try:
                return JSONR(reviews.get(rid))
            except ReviewError as e:
                return err(e.status, e.code, e.message, e.details)
        try:
            req = await body_model(request, ReviewPatch)
        except ValidationError as e:
            return err(422, "VALIDATION_ERROR", "Invalid review update.", {"errors": e.errors(include_url=False, include_input=False)})
        set_date = req.clear_follow_up_date or req.follow_up_date is not None
        try:
            r = reviews.update(rid, req.version, req.status, req.note, req.follow_up_date.isoformat() if req.follow_up_date else None, set_date)
        except ReviewError as e:
            return err(e.status, e.code, e.message, e.details)
        return JSONR(r)

    async def do_export(request: Request) -> Response:
        fmt = request.query_params.get("format", "json")
        if fmt not in ("json", "html", "csv"):
            return err(422, "VALIDATION_ERROR", "format must be json, html or csv.")
        p = export_svc.build_packet(store, reviews)
        body, mime = {"json": (export_svc.to_json, "application/json"), "html": (export_svc.to_html, "text/html; charset=utf-8"),
                      "csv": (export_svc.to_csv, "text/csv; charset=utf-8")}[fmt]
        disp = "inline" if request.query_params.get("inline") == "1" else "attachment"
        return Response(body(p), media_type=mime, headers={"Content-Disposition": f'{disp}; filename="{export_svc.safe_filename(fmt)}"',
                                                           "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    async def api_404(request: Request) -> Response:
        return err(404, "NOT_FOUND", "Unknown API route.")

    dist = s.frontend_dist

    async def spa(request: Request) -> Response:
        index = dist / "index.html"
        if not index.exists():
            return HTMLResponse("<h1>CytoZoe</h1><p>The frontend is not built. Run <code>scripts/build_local.sh</code>.</p>", status_code=503)
        return FileResponse(index, headers={"Cache-Control": "no-store"})

    routes = [
        Route("/api/status", status), Route("/api/datasets", datasets), Route("/api/import", do_import, methods=["POST"]),
        Route("/api/participants", participants), Route("/api/health", get_health), Route("/api/health/trend", get_trend),
        Route("/api/environment", get_env), Route("/api/explain", do_explain, methods=["POST"]),
        Route("/api/reviews", list_reviews, methods=["GET"]), Route("/api/reviews", create_review, methods=["POST"]),
        Route("/api/reviews/{rid}", review_detail, methods=["GET", "PATCH"]), Route("/api/export", do_export),
        Route("/api/{rest:path}", api_404, methods=["GET", "POST", "PATCH", "PUT", "DELETE"]),
    ]
    if (dist / "assets").exists():
        routes.append(Mount("/assets", StaticFiles(directory=dist / "assets"), name="assets"))
    if (dist / "fonts").exists():
        routes.append(Mount("/fonts", StaticFiles(directory=dist / "fonts"), name="fonts"))
    routes += [Route("/", spa), Route("/{page:path}", spa)]

    app = Starlette(routes=routes, middleware=[
        Middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS + ["testserver"]),
        Middleware(LocalGuard),
    ], exception_handlers={HTTPException: _http_exc, Exception: _unexpected})
    app.state.settings, app.state.store, app.state.reviews, app.state.db = s, store, reviews, db
    return app


def _ds_public(d: dict[str, Any]) -> dict[str, Any]:
    return {k: d[k] for k in ("id", "kind", "title", "file_name", "sha256", "source_url", "license_note", "imported_at", "quality")}


class LocalGuard(BaseHTTPMiddleware):
    """Same-origin writes only, request ids, safe headers, no note contents in logs."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        rid = uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        if request.method in ("POST", "PATCH", "PUT", "DELETE"):
            origin = request.headers.get("origin")
            if origin and origin not in (f"http://{request.headers.get('host', '')}",):
                return err(403, "CROSS_ORIGIN_BLOCKED", "Requests from other sites are not accepted.")
        resp = await call_next(request)
        resp.headers["X-Request-ID"] = rid
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Content-Security-Policy",
                                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self'; "
                                "connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'")
        log.info("rid=%s %s %s -> %s %.1fms", rid, request.method, request.url.path, resp.status_code, (time.perf_counter() - t0) * 1000)
        return resp


async def _http_exc(request: Request, exc: HTTPException) -> Response:
    if request.url.path.startswith("/api/"):
        return err(exc.status_code, "HTTP_ERROR", str(exc.detail))
    return HTMLResponse(f"<h1>{exc.status_code}</h1>", status_code=exc.status_code)


async def _unexpected(request: Request, exc: Exception) -> Response:
    log.exception("unexpected error on %s", request.url.path)
    return err(500, "INTERNAL_ERROR", "Something went wrong in the local service. Your saved reviews are unchanged.")


_app: Starlette | None = None


def __getattr__(name: str) -> Any:
    """Lazy `app` for `uvicorn app.main:app`, so importing this module in tests creates nothing."""
    global _app
    if name == "app":
        if _app is None:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
            _app = create_app()
        return _app
    raise AttributeError(name)
