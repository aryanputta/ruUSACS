"""
Centralised error-handling middleware for FastAPI.

Catches unhandled exceptions and ``HTTPException`` instances and turns
them into a consistent JSON envelope so the frontend never receives raw
stack traces in production.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("smart-commute")


def register_error_handlers(app: FastAPI) -> None:
    """Attach custom exception handlers to the FastAPI application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.error("[ERROR] %s - %s", exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {"message": str(exc.detail)},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            messages.append(f"{loc}: {err.get('msg', 'invalid')}")
        detail = "; ".join(messages)
        logger.error("[VALIDATION] %s", detail)
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {"message": detail},
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "[ERROR] 500 - %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {"message": "An unexpected error occurred."},
            },
        )
