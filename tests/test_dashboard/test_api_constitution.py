"""Tests for dashboard constitution API path resolution behavior."""

from __future__ import annotations

import io
from pathlib import Path

from specify_cli.dashboard.handlers.api import APIHandler


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


def test_handle_constitution_prefers_new_path(tmp_path: Path) -> None:
    new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
    legacy_path = tmp_path / ".kittify" / "memory" / "constitution.md"
    new_path.parent.mkdir(parents=True)
    legacy_path.parent.mkdir(parents=True)
    new_path.write_text("new-path-content", encoding="utf-8")
    legacy_path.write_text("legacy-content", encoding="utf-8")

    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_constitution(handler)  # type: ignore[arg-type]

    assert handler.status_code == 200
    assert handler.wfile.getvalue().decode("utf-8") == "new-path-content"


def test_handle_constitution_uses_legacy_when_new_missing(tmp_path: Path) -> None:
    legacy_path = tmp_path / ".kittify" / "memory" / "constitution.md"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text("legacy-content", encoding="utf-8")

    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_constitution(handler)  # type: ignore[arg-type]

    assert handler.status_code == 200
    assert handler.wfile.getvalue().decode("utf-8") == "legacy-content"


def test_handle_constitution_returns_404_when_missing(tmp_path: Path) -> None:
    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_constitution(handler)  # type: ignore[arg-type]

    assert handler.status_code == 404
    assert handler.wfile.getvalue() == b"Constitution not found"
