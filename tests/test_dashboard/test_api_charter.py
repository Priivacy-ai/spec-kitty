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
    new_path = tmp_path / ".kittify" / "charter" / "charter.md"
    legacy_path = tmp_path / ".kittify" / "memory" / "charter.md"
    new_path.parent.mkdir(parents=True)
    legacy_path.parent.mkdir(parents=True)
    new_path.write_text("new-path-content", encoding="utf-8")
    legacy_path.write_text("legacy-content", encoding="utf-8")
    # charter-preflight-remediation (WP04 cycle 2): presence is gated on
    # charter.yaml (R-001) -- the companion file only ever lives at the
    # canonical (new) location, so adding it here is orthogonal to this
    # test's intent (new-path-vs-legacy-path preference) while making the
    # fixture agree with the corrected presence semantics.
    (new_path.parent / "charter.yaml").write_text("schema_version: '2.0.0'\n", encoding="utf-8")

    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_charter(handler)  # type: ignore[arg-type]

    assert handler.status_code == 200
    assert handler.wfile.getvalue().decode("utf-8") == "new-path-content"


def test_handle_charter_returns_404_for_legacy_bundle_without_charter_yaml(tmp_path: Path) -> None:
    """charter-preflight-remediation (WP04 cycle 2): F2 regression.

    Before this fix, ``handle_charter`` served ``charter.md`` (200) for a
    legacy bundle even though the freshness gate reported "missing" for
    the same project -- the mission's User Story 2 symptom, reproduced
    live on this exact HTTP surface in WP04 cycle-1 review. Mirrors
    ``test_all_surfaces_agree_on_presence``'s F2 case
    (tests/charter/test_charter_presence_seam.py).
    """
    new_path = tmp_path / ".kittify" / "charter" / "charter.md"
    new_path.parent.mkdir(parents=True)
    new_path.write_text("legacy-bundle-content", encoding="utf-8")
    # Deliberately no charter.yaml -- the legacy-bundle (F2) shape.

    handler = _DummyAPIHandler(tmp_path)
    APIHandler.handle_charter(handler)  # type: ignore[arg-type]

    assert handler.status_code == 404
    assert handler.wfile.getvalue() == b"Charter not found"


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
