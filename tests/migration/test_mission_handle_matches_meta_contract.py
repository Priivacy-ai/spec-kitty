"""Contract tests for _mission_handle_matches meta-load path (FR-006b, WP09).

``_mission_handle_matches`` now delegates meta reads to the canonical
``load_meta_or_empty`` adapter (silent contract — returns ``{}`` on both
missing and malformed meta.json).  These tests assert the OBSERVABLE
RETURN VALUE (CT4 — not call-graph) for both error arms.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.migration.mission_state import _mission_handle_matches

pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]


class TestMissionHandleMatchesMetaLoadContract:
    """load_meta_or_empty contract tests for _mission_handle_matches (FR-006b).

    The observable invariant: missing/malformed meta.json never raises — the
    function degrades silently to a name-only match (returns False when no
    name match exists).
    """

    def test_missing_meta_returns_false_on_no_name_match(
        self, tmp_path: Path
    ) -> None:
        """Missing meta.json: _mission_handle_matches returns False (no raises)."""
        mission_dir = tmp_path / "kitty-specs" / "01KVRJ6P-cleanup"
        mission_dir.mkdir(parents=True)
        assert not (mission_dir / "meta.json").exists()

        # Handle that won't match directory name — only meta.mission_id would match.
        result = _mission_handle_matches(mission_dir, "01KVRJ6P0000000000000000AB")
        assert result is False

    def test_malformed_meta_returns_false_on_no_name_match(
        self, tmp_path: Path
    ) -> None:
        """Malformed meta.json: _mission_handle_matches returns False (no raises).

        load_meta_or_empty absorbs malformed JSON to {} — the function continues
        name-only matching and returns False when no match exists.
        """
        mission_dir = tmp_path / "kitty-specs" / "01KVRJ6P-cleanup"
        mission_dir.mkdir(parents=True)
        (mission_dir / "meta.json").write_text("{bad json", encoding="utf-8")

        result = _mission_handle_matches(mission_dir, "01KVRJ6P0000000000000000AB")
        assert result is False

    def test_valid_meta_mission_id_matches(self, tmp_path: Path) -> None:
        """Valid meta.json with matching mission_id returns True."""
        mission_id = "01KVRJ6P0000000000000000AB"
        mission_dir = tmp_path / "kitty-specs" / "01KVRJ6P-cleanup"
        mission_dir.mkdir(parents=True)
        meta = {"mission_id": mission_id, "mission_slug": "01KVRJ6P-cleanup"}
        (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        result = _mission_handle_matches(mission_dir, mission_id)
        assert result is True
