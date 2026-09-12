"""Tests for dashboard charter API path resolution behavior."""

from __future__ import annotations

import io
from pathlib import Path

from specify_cli.dashboard.handlers.api import APIHandler


import pytest

pytestmark = [pytest.mark.integration]

class _DummyAPIHandler:
    """Minimal handler shim to execute APIHandler methods in isolation."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.status_code = None
        self.headers: dict[str, str] = {}
        self.wfile = io.BytesIO()

    def send_response(self, code: int) -> None:
        self.status_code = code

    def send_header(self, key: str, value: str) -> None:
        self.headers[key] = value

    def end_headers(self) -> None:
        return None


def test_handle_charter_prefers_new_path(tmp_path: Path) -> None:
    """Both charter.yaml and charter.md present: presence gates on yaml (C-001),

    body still reads from charter.md (T003 both-files no-regression pin).
    """
    new_path = tmp_path / ".kittify" / "charter" / "charter.md"
    yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
    legacy_path = tmp_path / ".kittify" / "memory" / "charter.md"
    new_path.parent.mkdir(parents=True)
    legacy_path.parent.mkdir(parents=True)
    new_path.write_text("new-path-content", encoding="utf-8")
    yaml_path.write_text("schema_version: '2.0.0'\n", encoding="utf-8")
    legacy_path.write_text("legacy-content", encoding="utf-8")

    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_charter(handler)  # type: ignore[arg-type]

    assert handler.status_code == 200
    assert handler.wfile.getvalue().decode("utf-8") == "new-path-content"


def test_handle_charter_serves_empty_body_when_only_yaml_present(tmp_path: Path) -> None:
    """FR-003 (#3150): charter.yaml-only project reports present (no 404),

    but there is no charter.md prose companion to serve, so the body is empty.
    """
    yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
    yaml_path.parent.mkdir(parents=True)
    yaml_path.write_text("schema_version: '2.0.0'\n", encoding="utf-8")

    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_charter(handler)  # type: ignore[arg-type]

    assert handler.status_code == 200
    assert handler.wfile.getvalue() == b""


def test_handle_charter_returns_404_for_non_charter_state(tmp_path: Path) -> None:
    """Only .kittify/charter/charter.md is resolved — other paths return 404."""
    # Create a .kittify dir with files but NOT the canonical charter path
    other_dir = tmp_path / ".kittify" / "memory"
    other_dir.mkdir(parents=True)
    (other_dir / "notes.md").write_text("not a charter", encoding="utf-8")

    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_charter(handler)  # type: ignore[arg-type]

    assert handler.status_code == 404


def test_handle_charter_returns_404_when_missing(tmp_path: Path) -> None:
    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_charter(handler)  # type: ignore[arg-type]

    assert handler.status_code == 404
    assert handler.wfile.getvalue() == b"Charter not found"


def test_handle_charter_serves_content_when_only_md_present(tmp_path: Path) -> None:
    """Landing-fold regression: an authored charter.md with no compiled

    charter.yaml yet (project has not run ``charter sync``/compile) must
    still report present and serve its prose -- not 404. This is the
    regression #3150's yaml-only presence fix silently introduced: the
    presence probe keyed solely on charter.yaml, so a project with only
    charter.md authored (the far more common pre-compile shape) started
    404-ing on this endpoint.
    """
    md_path = tmp_path / ".kittify" / "charter" / "charter.md"
    md_path.parent.mkdir(parents=True)
    md_path.write_text("# Authored Charter\n\nNo yaml compiled yet.\n", encoding="utf-8")
    yaml_path = tmp_path / ".kittify" / "charter" / "charter.yaml"
    assert not yaml_path.exists(), "fixture must not seed charter.yaml"

    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_charter(handler)  # type: ignore[arg-type]

    assert handler.status_code == 200
    assert handler.wfile.getvalue().decode("utf-8") == "# Authored Charter\n\nNo yaml compiled yet.\n"
