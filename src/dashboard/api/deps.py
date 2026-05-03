"""FastAPI dependencies.

These dependency functions run before route handler bodies and produce
typed inputs the handlers can rely on. Token validation lives here (not in
the handler bodies) so the MCP-friendly invariant from FR-009 holds — a
future MCP adapter can re-use a route handler as a plain Python callable
because the handler does not perform HTTP-layer side effects.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException, Query, Request

if TYPE_CHECKING:  # pragma: no cover - type-only import
    from dashboard.services.registry import MissionRegistry

__all__ = ["verify_project_token", "get_project_dir", "get_mission_registry"]


def verify_project_token(
    request: Request,
    token: str | None = Query(default=None),
) -> str | None:
    """Validate the ``?token=`` query parameter against ``app.state.project_token``.

    When ``app.state.project_token`` is falsy (no token configured), no
    validation runs and the dependency simply returns the (possibly None)
    token from the query string. When a token is configured and the query
    param does not match, we raise ``HTTPException(403)`` with the same
    JSON shape the legacy stack returns: ``{"error": "invalid_token"}``.

    Returns the validated token string (or None when no validation runs).
    """
    expected = getattr(request.app.state, "project_token", None)
    if expected and token != expected:
        raise HTTPException(status_code=403, detail={"error": "invalid_token"})
    return token


def get_project_dir(request: Request) -> Path:
    """Pull the configured project directory from app state.

    Raises ``RuntimeError`` (mapped to 500 by the exception handler) when the
    app was constructed without a ``project_dir`` — this matches the legacy
    handler's ``RuntimeError("dashboard project_dir is not configured")``.
    """
    project_dir = getattr(request.app.state, "project_dir", None)
    if project_dir is None:
        raise RuntimeError("dashboard project_dir is not configured")
    return Path(project_dir)


def get_mission_registry(request: Request) -> "MissionRegistry":
    """Pull the ``MissionRegistry`` from ``app.state``.

    Per ``DIRECTIVE_API_DEPENDENCY_DIRECTION`` (mission
    ``mission-registry-and-api-boundary-doctrine-01KQPDBB``), routers consume
    mission/WP data exclusively through this registry rather than importing
    ``specify_cli.scanner`` directly. The architectural test in
    ``tests/architectural/test_transport_does_not_import_scanner.py`` (WP05)
    enforces this at import time.

    Raises ``RuntimeError`` (mapped to 500 by the exception handler) when
    ``app.state.mission_registry`` is absent — matches the existing
    ``get_project_dir`` dependency's pattern.
    """
    registry = getattr(request.app.state, "mission_registry", None)
    if registry is None:
        raise RuntimeError("dashboard mission_registry is not configured")
    return registry
