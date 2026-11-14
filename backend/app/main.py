"""CytoZoe FastAPI application: loopback API + compiled SPA from one origin."""
from __future__ import annotations

import logging
import mimetypes
import sqlite3
import time
import uuid
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import config, db
from .api.routes import router
from .errors import AppError
from .services import importer, runtime

log = logging.getLogger("cytozoe")
# Bundled media must be served with an image type: the Windows registry often lacks .webp/.avif, and with
# "X-Content-Type-Options: nosniff" a text/plain image would be refused by the browser.
for _ext, _type in ((".webp", "image/webp"), (".avif", "image/avif"), (".woff2", "font/woff2"), (".svg", "image/svg+xml")):
    mimetypes.add_type(_type, _ext)
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")


def _error(status: int, code: str, message: str, details: dict | None = None, request: Request | None = None) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) if request is not None else None
    return JSONResponse(status_code=status, content={"code": code, "message": message, "details": details or {},
                                                     "request_id": request_id})


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    runtime.STARTUP.update(error_code=None, error_message=None)
    try:
        db.migrate()
        importer.reconcile_provenance()
    except sqlite3.Error as exc:
        # Keep the process alive so /api/healthz answers and /api/readyz explains the failure.
        log.error("database unavailable at startup: %s", type(exc).__name__)
        runtime.STARTUP.update(error_code="DATABASE_UNAVAILABLE",
                               error_message="The local SQLite database could not be opened or migrated. "
                                             "Restore a backup (scripts/backup_db.py --restore) or move the file aside.")
    app = FastAPI(title="CytoZoe local API", version=config.APP_VERSION, docs_url="/api/docs",
                  openapi_url="/api/openapi.json", redoc_url=None)
    hosts = config.allowed_hosts()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts + ["testserver"])

    @app.middleware("http")
    async def guard_and_log(request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        # CSRF/origin protection for a single-origin loopback service: reject cross-site writes.
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).hostname not in hosts + ["testserver"]:
                return _error(403, "ORIGIN_REJECTED", "Cross-origin write requests are not accepted.", request=request)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = CSP
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        # Never log note contents or file bytes.
        log.info("req=%s %s %s status=%s ms=%.1f", request_id, request.method, request.url.path,
                 response.status_code, (time.perf_counter() - start) * 1000)
        return response

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return _error(exc.status, exc.code, exc.message, exc.details, request)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = [{"loc": [str(x) for x in e.get("loc", [])], "msg": e.get("msg")} for e in exc.errors()]
        return _error(422, "VALIDATION_ERROR", "The request did not pass validation.", {"fields": fields}, request)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return _error(exc.status_code, code, str(exc.detail) if exc.status_code != 404 else "Not found.", request=request)

    @app.exception_handler(sqlite3.Error)
    async def database_error(request: Request, exc: sqlite3.Error):
        log.error("database error: %s", type(exc).__name__)
        return _error(503, "DATABASE_UNAVAILABLE", "The local database is unavailable. Saved data was not changed; "
                      "check /api/readyz for the cause.", request=request)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.exception("unexpected error: %s", type(exc).__name__)
        return _error(500, "INTERNAL_ERROR", "An unexpected local error occurred. Your saved data was not changed.",
                      request=request)

    app.include_router(router)

    dist = config.FRONTEND_DIST.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/") or path == "api":
            return _error(404, "NOT_FOUND", "Not found.")
        index = dist / "index.html"
        if not index.exists():
            return _error(503, "FRONTEND_NOT_BUILT",
                          "The interface has not been built. Run 'npm run build' in frontend/.")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist in candidate.parents:
            headers = {"Cache-Control": "public, max-age=31536000, immutable"} if "/assets/" in candidate.as_posix() else {}
            return FileResponse(candidate, headers=headers)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
