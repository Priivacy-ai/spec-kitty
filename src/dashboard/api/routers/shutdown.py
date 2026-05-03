"""Router: POST /api/shutdown.

Token-validated. Returns ``{"status": "stopping"}`` and flips
``app.state.uvicorn_server.should_exit = True`` so the ASGI loop
actually terminates after the response flushes (parity with the legacy
stack's ``server.shutdown()`` path). The server reference is stashed by
``specify_cli.dashboard.server._run_fastapi`` at boot.

When ``app.state.uvicorn_server`` is absent (e.g. test fixtures using
``TestClient`` directly), the route still returns the success shape but
logs a warning — exiting the test runner via ``should_exit`` would be
counter-productive there.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, FastAPI, Request

from dashboard.api.deps import verify_project_token
from dashboard.api.models import ShutdownResponse

__all__ = ["register"]

logger = logging.getLogger(__name__)


def register(app: FastAPI) -> None:
    """Mount the shutdown router on ``app``."""
    router = APIRouter()

    @router.post("/api/shutdown", response_model=ShutdownResponse)
    def shutdown(request: Request, _token: str | None = Depends(verify_project_token)):
        server = getattr(request.app.state, "uvicorn_server", None)
        if server is not None:
            server.should_exit = True
        else:
            logger.debug("/api/shutdown invoked without uvicorn_server on app.state; no-op")
        return {"status": "stopping"}

    app.include_router(router)
