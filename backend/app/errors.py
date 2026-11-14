"""Structured application errors: {code, message, details}. Never carries paths or tracebacks."""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


class SchemaMismatch(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(422, code, message, details)


def not_found(what: str, **details: Any) -> AppError:
    return AppError(404, "NOT_FOUND", f"{what} was not found.", details)


def bad_request(code: str, message: str, **details: Any) -> AppError:
    return AppError(400, code, message, details)
