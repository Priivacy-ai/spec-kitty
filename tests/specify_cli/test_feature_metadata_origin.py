"""Tests for set_origin_ticket() in specify_cli.mission_metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.mission_metadata import load_meta, set_origin_ticket


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _minimal_meta() -> dict[str, Any]:
    """Return a minimal valid meta dict with all required fields."""
    return {
        "mission_number": "061",
        "slug": "061-ticket-first",
        "mission_slug": "061-ticket-first",
        "friendly_name": "Ticket First Mission",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-04-01T00:00:00+00:00",
    }


def _valid_origin_ticket() -> dict[str, Any]:
    """Return a valid origin_ticket dict with all 7 required keys."""
    return {
        "provider": "linear",
        "resource_type": "linear_team",
        "resource_id": "TEAM-A",
        "external_issue_id": "issue-abc-123",
        "external_issue_key": "ENG-42",
        "external_issue_url": "https://linear.app/team/ENG-42",
        "title": "Implement dark mode",
    }


def _write_meta_file(feature_dir: Path, meta: dict[str, Any]) -> Path:
    """Write a meta.json file to *feature_dir* and return the path."""
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return meta_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSetOriginTicketHappyPath:
    """Happy-path tests for set_origin_ticket()."""

    def test_writes_origin_ticket_and_returns_meta(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())
        origin = _valid_origin_ticket()

        result = set_origin_ticket(tmp_path, origin)

        assert "origin_ticket" in result
        assert result["origin_ticket"] == origin
        # All original fields still present
        assert result["mission_number"] == "061"

    def test_preserves_existing_fields(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["documentation_state"] = {"iteration_mode": "initial"}
        meta["vcs"] = "git"
        _write_meta_file(tmp_path, meta)

        origin = _valid_origin_ticket()
        result = set_origin_ticket(tmp_path, origin)

        assert result["documentation_state"] == {"iteration_mode": "initial"}
        assert result["vcs"] == "git"
        assert result["origin_ticket"] == origin

    def test_persisted_as_valid_json_with_sorted_keys(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())
        origin = _valid_origin_ticket()

        set_origin_ticket(tmp_path, origin)

        raw = (tmp_path / "meta.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)
        # Verify sort_keys was used -- keys should be in alphabetical order
        keys = list(parsed.keys())
        assert keys == sorted(keys)
        # Verify trailing newline
        assert raw.endswith("\n")


class TestSetOriginTicketOverwrite:
    """Idempotent overwrite behaviour."""

    def test_overwrites_existing_origin_ticket(self, tmp_path: Path) -> None:
        meta = _minimal_meta()
        meta["origin_ticket"] = {
            "provider": "jira",
            "resource_type": "jira_project",
            "resource_id": "OLD",
            "external_issue_id": "old-id",
            "external_issue_key": "OLD-1",
            "external_issue_url": "https://jira.example.com/OLD-1",
            "title": "Old ticket",
        }
        _write_meta_file(tmp_path, meta)

        new_origin = _valid_origin_ticket()
        result = set_origin_ticket(tmp_path, new_origin)

        assert result["origin_ticket"]["provider"] == "linear"
        assert result["origin_ticket"]["title"] == "Implement dark mode"

        # Verify on disk too
        on_disk = load_meta(tmp_path)
        assert on_disk is not None
        assert on_disk["origin_ticket"] == new_origin


class TestSetOriginTicketErrors:
    """Error handling tests."""

    def test_missing_meta_json_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No meta.json"):
            set_origin_ticket(tmp_path, _valid_origin_ticket())

    def test_missing_required_keys_raises_value_error(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        incomplete = {"provider": "linear", "title": "Partial"}
        with pytest.raises(ValueError, match="origin_ticket missing required keys"):
            set_origin_ticket(tmp_path, incomplete)

    def test_error_message_lists_missing_keys(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        incomplete = {"provider": "linear", "title": "Partial"}
        with pytest.raises(ValueError) as exc_info:
            set_origin_ticket(tmp_path, incomplete)

        msg = str(exc_info.value)
        # Should list the 5 missing keys (sorted)
        assert "external_issue_id" in msg
        assert "external_issue_key" in msg
        assert "external_issue_url" in msg
        assert "resource_id" in msg
        assert "resource_type" in msg

    def test_extra_keys_are_allowed(self, tmp_path: Path) -> None:
        _write_meta_file(tmp_path, _minimal_meta())

        origin = _valid_origin_ticket()
        origin["extra_field"] = "bonus"

        result = set_origin_ticket(tmp_path, origin)
        assert result["origin_ticket"]["extra_field"] == "bonus"
