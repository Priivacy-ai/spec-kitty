"""FastAPI app factory for the dashboard transport.

The factory is the canonical entry point. It accepts the same parameters the
legacy ``DashboardRouter`` was wired with (project_dir + project_token) and
returns a FastAPI app with every router mounted. The strangler boundary in
``src/specify_cli/dashboard/server.py`` calls this factory when
``dashboard.transport == "fastapi"``.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from .errors import register_exception_handlers

__all__ = ["create_app"]


def create_app(project_dir: Path, project_token: str | None) -> FastAPI:
    """Build the dashboard FastAPI app.

    Args:
        project_dir: Absolute path to the Spec Kitty project root.
        project_token: Optional project token used to authorise mutating
            endpoints (`POST /api/sync/trigger`, `POST /api/shutdown`).
            When ``None``, those endpoints accept any caller.

    Returns:
        A FastAPI application ready to be served by Uvicorn (or any
        ASGI server). Routers for individual route families are added by
        the helper below; the import is local to avoid a circular import
        when routers import service objects.
    """
    app = FastAPI(
        title="Spec Kitty Dashboard API",
        description=(
            "HTTP surface for the local Spec Kitty dashboard. "
            "All routes are localhost-only. "
            "See `kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/` "
            "for the contract authoring rules."
        ),
        version="1.0.0",
        # Match the legacy stack: trailing-slash mismatches return 404,
        # never a 308 redirect. The contract-parity test enforces this.
        redirect_slashes=False,
    )
    app.state.project_dir = Path(project_dir).resolve()
    app.state.project_token = project_token

    register_exception_handlers(app)
    _register_api_docs_alias(app)
    _wire_routers(app)
    return app


def _register_api_docs_alias(app: FastAPI) -> None:
    """Mount ``/api-docs`` as a project-canonical alias for Swagger UI.

    FastAPI's defaults expose Swagger at ``/docs``; the operator-facing
    convention this project follows is ``/api-docs`` (named in the
    migration runbook and the post-merge GitHub comment thread). We add
    the alias as a non-redirecting route so consumers that hard-code
    ``/api-docs`` get the expected UI without a 308 hop.
    """
    from fastapi.openapi.docs import get_swagger_ui_html

    @app.get("/api-docs", include_in_schema=False)
    def api_docs():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " — Swagger UI",
        )


def _wire_routers(app: FastAPI) -> None:
    """Mount every dashboard router on the app.

    Routers are imported lazily so the dashboard can be partially mounted
    during the WP04 migration: missing routers fail open (no route is
    registered for the missing family) rather than breaking app
    construction. Each router module exposes ``register(app)`` which calls
    ``app.include_router(...)``.

    Alphabetical order is intentional: it keeps the OpenAPI snapshot
    deterministic across runs.
    """
    import importlib

    router_modules = (
        "artifacts",
        "charter",
        "diagnostics",
        "dossier",
        "features",
        "glossary",
        "health",
        "kanban",
        "lint",
        "shutdown",
        "static_mount",
        "sync",
    )
    for name in router_modules:
        try:
            module = importlib.import_module(f"dashboard.api.routers.{name}")
        except ModuleNotFoundError:
            # WP02 ships the scaffold; WP04 adds the router modules.
            # Skipping a missing router lets the scaffold pass smoke tests
            # before WP04 lands.
            continue
        register = getattr(module, "register", None)
        if register is not None:
            register(app)
