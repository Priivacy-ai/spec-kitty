"""FastAPI exception handlers.

Maps service-layer exceptions to JSON error payloads that match the legacy
dashboard's error shape (`{"error": "<code>", "detail": "<message>"}`),
preserving response parity for the contract-parity test suite.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the dashboard-canonical exception handlers to the FastAPI app.

    These handlers are the only place where ``JSONResponse(...)`` is allowed
    to be constructed manually inside the dashboard transport. Route handler
    bodies must not write to ``Response`` directly (FR-009 / NFR-007).
    """

    @app.exception_handler(RuntimeError)
    async def _handle_runtime_error(_request: Request, exc: RuntimeError) -> JSONResponse:
        """Map service-layer RuntimeErrors to a 500 JSON payload."""
        logger.exception("Dashboard service error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "service_error", "detail": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def _handle_value_error(_request: Request, exc: ValueError) -> JSONResponse:
        """Map service-layer ValueErrors (e.g. invalid path traversal) to 400."""
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_request", "detail": str(exc)},
        )
