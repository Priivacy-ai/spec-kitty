"""Unit tests for the FastAPI app factory and shared dependencies.

Tests the WP02 transport scaffold in isolation. Routers are mounted lazily
by `_wire_routers`; missing router modules fail open (no route registered).
This test exercises the scaffold itself — app construction, deps, error
handlers, and the strangler boundary's transport resolution.

Per FR-009 / NFR-007 the route handler bodies must stay thin; that
invariant is enforced by `tests/architectural/test_fastapi_handler_purity.py`
in WP05, not here.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.fast


def test_create_app_returns_fastapi_instance(tmp_path: Path) -> None:
    """`create_app` returns a FastAPI app with redirect_slashes off."""
    from dashboard.api import create_app

    app = create_app(project_dir=tmp_path, project_token=None)

    # Lazy import to avoid eager FastAPI import during test collection.
    from fastapi import FastAPI  # noqa: F401 — type assertion only

    assert isinstance(app, FastAPI)
    # FR-011 / NFR research §R-5: trailing-slash redirects are off so the
    # FastAPI surface matches the legacy stack's behavior.
    assert app.router.redirect_slashes is False


def test_create_app_stores_project_dir_and_token_on_state(tmp_path: Path) -> None:
    """The factory persists the constructor arguments on `app.state`."""
    from dashboard.api import create_app

    app = create_app(project_dir=tmp_path, project_token="secret-token")

    assert app.state.project_dir == tmp_path.resolve()
    assert app.state.project_token == "secret-token"


def test_create_app_resolves_relative_project_dir(tmp_path: Path, monkeypatch) -> None:
    """Relative project directories are resolved to absolute paths on app.state."""
    monkeypatch.chdir(tmp_path)
    sub = tmp_path / "subproj"
    sub.mkdir()

    from dashboard.api import create_app

    app = create_app(project_dir=Path("subproj"), project_token=None)

    assert app.state.project_dir == sub.resolve()
    assert app.state.project_dir.is_absolute()


def test_openapi_doc_is_well_formed(tmp_path: Path) -> None:
    """The auto-generated OpenAPI document has the expected top-level shape."""
    from dashboard.api import create_app

    app = create_app(project_dir=tmp_path, project_token=None)
    spec = app.openapi()

    assert spec["openapi"].startswith("3.")  # FastAPI emits OpenAPI 3.x
    assert spec["info"]["title"] == "Spec Kitty Dashboard API"
    assert spec["info"]["version"] == "1.0.0"
    # paths may be empty before WP04 mounts routers; that is acceptable here.
    assert "paths" in spec


def test_resolve_transport_default_when_no_config_no_override(tmp_path: Path) -> None:
    """Without a CLI override and without config, the default is 'fastapi'."""
    from specify_cli.dashboard.server import resolve_transport

    assert resolve_transport(tmp_path, cli_override=None) == "fastapi"


def test_resolve_transport_cli_override_wins(tmp_path: Path) -> None:
    """Explicit CLI override takes precedence over config."""
    from specify_cli.dashboard.server import resolve_transport

    config_dir = tmp_path / ".kittify"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "dashboard:\n  transport: fastapi\n", encoding="utf-8"
    )

    assert resolve_transport(tmp_path, cli_override="legacy") == "legacy"


def test_resolve_transport_reads_from_config(tmp_path: Path) -> None:
    """When the CLI override is absent, the config value is used."""
    from specify_cli.dashboard.server import resolve_transport

    config_dir = tmp_path / ".kittify"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "dashboard:\n  transport: legacy\n", encoding="utf-8"
    )

    assert resolve_transport(tmp_path, cli_override=None) == "legacy"


def test_resolve_transport_rejects_unknown_value(tmp_path: Path) -> None:
    """Unknown transport values raise ValueError so the strangler fails closed."""
    from specify_cli.dashboard.server import resolve_transport

    with pytest.raises(ValueError, match="Unknown dashboard transport"):
        resolve_transport(tmp_path, cli_override="rocketship")


def test_resolve_transport_rejects_unknown_config_value(tmp_path: Path) -> None:
    """Unknown values in config also fail closed."""
    from specify_cli.dashboard.server import resolve_transport

    config_dir = tmp_path / ".kittify"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "dashboard:\n  transport: galactic\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Unknown dashboard.transport"):
        resolve_transport(tmp_path, cli_override=None)


def test_verify_project_token_passes_when_no_token_configured(tmp_path: Path) -> None:
    """When app.state.project_token is None, verify_project_token returns the input."""
    from dashboard.api import create_app
    from dashboard.api.deps import verify_project_token
    from fastapi import Request

    app = create_app(project_dir=tmp_path, project_token=None)

    class _StubRequest:
        def __init__(self, app):
            self.app = app

    # No token configured → no validation, returns whatever was passed.
    result = verify_project_token(_StubRequest(app), token="anything")  # type: ignore[arg-type]
    assert result == "anything"


def test_verify_project_token_rejects_mismatch(tmp_path: Path) -> None:
    """A mismatching token raises HTTPException(403)."""
    from dashboard.api import create_app
    from dashboard.api.deps import verify_project_token
    from fastapi import HTTPException

    app = create_app(project_dir=tmp_path, project_token="expected")

    class _StubRequest:
        def __init__(self, app):
            self.app = app

    with pytest.raises(HTTPException) as excinfo:
        verify_project_token(_StubRequest(app), token="wrong")  # type: ignore[arg-type]

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == {"error": "invalid_token"}


def test_verify_project_token_accepts_matching_token(tmp_path: Path) -> None:
    """Matching token returns the token unchanged."""
    from dashboard.api import create_app
    from dashboard.api.deps import verify_project_token

    app = create_app(project_dir=tmp_path, project_token="match-me")

    class _StubRequest:
        def __init__(self, app):
            self.app = app

    assert verify_project_token(_StubRequest(app), token="match-me") == "match-me"  # type: ignore[arg-type]


def test_get_project_dir_returns_path(tmp_path: Path) -> None:
    """`get_project_dir` reads from app.state."""
    from dashboard.api import create_app
    from dashboard.api.deps import get_project_dir

    app = create_app(project_dir=tmp_path, project_token=None)

    class _StubRequest:
        def __init__(self, app):
            self.app = app

    assert get_project_dir(_StubRequest(app)) == tmp_path.resolve()  # type: ignore[arg-type]


def test_runtime_error_handler_returns_500_json(tmp_path: Path) -> None:
    """Service-layer RuntimeError surfaces as 500 JSON."""
    from dashboard.api import create_app
    from fastapi.testclient import TestClient

    app = create_app(project_dir=tmp_path, project_token=None)

    @app.get("/_test/runtime-error")
    def _trigger() -> None:  # pragma: no cover - exercised via TestClient
        raise RuntimeError("dashboard project_dir is not configured")

    client = TestClient(app)
    response = client.get("/_test/runtime-error")
    assert response.status_code == 500
    assert response.json() == {
        "error": "service_error",
        "detail": "dashboard project_dir is not configured",
    }


def test_value_error_handler_returns_400_json(tmp_path: Path) -> None:
    """Service-layer ValueError surfaces as 400 JSON."""
    from dashboard.api import create_app
    from fastapi.testclient import TestClient

    app = create_app(project_dir=tmp_path, project_token=None)

    @app.get("/_test/value-error")
    def _trigger() -> None:  # pragma: no cover - exercised via TestClient
        raise ValueError("nope")

    client = TestClient(app)
    response = client.get("/_test/value-error")
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_request", "detail": "nope"}
