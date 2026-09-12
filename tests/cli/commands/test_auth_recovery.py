"""Unit tests for ``specify_cli.cli.commands._auth_recovery`` (Mission 7, #829)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from specify_cli.cli.commands._auth_recovery import (
    detect_logged_out_with_connected_teamspace,
)


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# detect_logged_out_with_connected_teamspace
# ---------------------------------------------------------------------------


class TestDetector:
    """Read-only detector covering all five resolution branches."""

    def test_valid_session_returns_none(self, monkeypatch):
        tm = MagicMock()
        tm.is_authenticated = True
        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager",
            lambda: tm,
        )
        assert detect_logged_out_with_connected_teamspace() is None

    def test_falls_back_to_stored_private_team_name(self, monkeypatch):
        team = SimpleNamespace(name="Engineering", is_private_teamspace=True)
        session = SimpleNamespace(teams=[team])
        tm = MagicMock()
        tm.is_authenticated = False
        tm.get_current_session.return_value = session
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
        assert detect_logged_out_with_connected_teamspace() == "Engineering"

    def test_nothing_known_returns_none(self, monkeypatch):
        tm = MagicMock()
        tm.is_authenticated = False
        tm.get_current_session.return_value = None
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
        assert detect_logged_out_with_connected_teamspace() is None
