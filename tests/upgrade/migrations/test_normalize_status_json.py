"""Tests for migration m_3_1_1_normalize_status_json.

Covers:
- detect() returns False when no status.json files exist
- detect() returns False when status.json is already in deterministic format
- detect() returns True when status.json has a wall-clock materialized_at
- apply() rewrites stale files and skips already-normalised ones
- apply(dry_run=True) reports changes without writing
- Idempotency: second apply() is a no-op
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_1_1_normalize_status_json import (
    NormalizeStatusJsonMigration,
    _needs_normalisation,
)

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WALL_CLOCK_TS = "2026-04-07T09:56:25.543799+00:00"
# Canonical output of materialize_to_json(reduce([])) — must stay in sync with
# the reducer.  Contains mission_slug only (no legacy feature_slug) and all
# 9 canonical lanes.
_CANONICAL_EMPTY_STATUS = """\
{
  "event_count": 0,
  "last_event_id": null,
  "materialized_at": "",
  "mission_slug": "",
  "summary": {
    "approved": 0,
    "blocked": 0,
    "canceled": 0,
    "claimed": 0,
    "done": 0,
    "for_review": 0,
    "in_progress": 0,
    "in_review": 0,
    "planned": 0
  },
  "work_packages": {}
}
"""


def _make_status_json(feature_dir: Path, materialized_at: str) -> Path:
    """Write a status.json.

    If ``materialized_at`` is empty string the file is written in the
    canonical (already-normalised) form so that ``_needs_normalisation``
    returns False.  Any non-empty value replaces the field, producing a
    "stale" file that should trigger normalisation.
    """
    feature_dir.mkdir(parents=True, exist_ok=True)
    path = feature_dir / "status.json"
    if materialized_at == "":
        path.write_text(_CANONICAL_EMPTY_STATUS, encoding="utf-8")
    else:
        # Replace the materialized_at field to simulate a stale wall-clock timestamp.
        content = _CANONICAL_EMPTY_STATUS.replace(
            '"materialized_at": ""',
            f'"materialized_at": "{materialized_at}"',
        )
        path.write_text(content, encoding="utf-8")
    return path


def _make_kitty_specs(project_path: Path) -> Path:
    ks = project_path / "kitty-specs"
    ks.mkdir(parents=True, exist_ok=True)
    return ks


# ---------------------------------------------------------------------------
# detect()
# ---------------------------------------------------------------------------


class TestDetect:
    def test_no_kitty_specs(self, tmp_path: Path) -> None:
        migration = NormalizeStatusJsonMigration()
        assert migration.detect(tmp_path) is False

    def test_empty_kitty_specs(self, tmp_path: Path) -> None:
        _make_kitty_specs(tmp_path)
        migration = NormalizeStatusJsonMigration()
        assert migration.detect(tmp_path) is False

    def test_feature_without_status_json(self, tmp_path: Path) -> None:
        ks = _make_kitty_specs(tmp_path)
        (ks / "001-feature").mkdir()
        migration = NormalizeStatusJsonMigration()
        assert migration.detect(tmp_path) is False

    def test_already_normalised_no_events(self, tmp_path: Path) -> None:
        """status.json with materialized_at='' is already in the new format."""
        ks = _make_kitty_specs(tmp_path)
        _make_status_json(ks / "001-feature", materialized_at="")
        migration = NormalizeStatusJsonMigration()
        assert migration.detect(tmp_path) is False

    def test_wall_clock_timestamp_triggers_detect(self, tmp_path: Path) -> None:
        """status.json with a wall-clock timestamp needs normalisation."""
        ks = _make_kitty_specs(tmp_path)
        _make_status_json(ks / "001-feature", materialized_at=_WALL_CLOCK_TS)
        migration = NormalizeStatusJsonMigration()
        assert migration.detect(tmp_path) is True

    def test_one_stale_among_many_normalised(self, tmp_path: Path) -> None:
        ks = _make_kitty_specs(tmp_path)
        _make_status_json(ks / "001-feature", materialized_at="")
        _make_status_json(ks / "002-feature", materialized_at=_WALL_CLOCK_TS)
        _make_status_json(ks / "003-feature", materialized_at="")
        migration = NormalizeStatusJsonMigration()
        assert migration.detect(tmp_path) is True


# ---------------------------------------------------------------------------
# can_apply()
# ---------------------------------------------------------------------------


class TestCanApply:
    def test_with_kitty_specs(self, tmp_path: Path) -> None:
        _make_kitty_specs(tmp_path)
        m = NormalizeStatusJsonMigration()
        ok, reason = m.can_apply(tmp_path)
        assert ok is True

    def test_with_kittify(self, tmp_path: Path) -> None:
        (tmp_path / ".kittify").mkdir()
        m = NormalizeStatusJsonMigration()
        ok, _ = m.can_apply(tmp_path)
        assert ok is True

    def test_empty_dir_returns_false(self, tmp_path: Path) -> None:
        m = NormalizeStatusJsonMigration()
        ok, reason = m.can_apply(tmp_path)
        assert ok is False
        assert reason


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------


class TestApply:
    def test_normalises_stale_file(self, tmp_path: Path) -> None:
        ks = _make_kitty_specs(tmp_path)
        status_path = _make_status_json(ks / "001-feature", materialized_at=_WALL_CLOCK_TS)

        m = NormalizeStatusJsonMigration()
        result = m.apply(tmp_path, dry_run=False)

        assert result.success is True
        assert len(result.changes_made) == 1
        assert "001-feature" in result.changes_made[0]

        data = json.loads(status_path.read_text(encoding="utf-8"))
        assert data["materialized_at"] == ""  # no events → deterministic empty string

    def test_skips_already_normalised(self, tmp_path: Path) -> None:
        ks = _make_kitty_specs(tmp_path)
        _make_status_json(ks / "001-feature", materialized_at="")

        m = NormalizeStatusJsonMigration()
        result = m.apply(tmp_path, dry_run=False)

        assert result.success is True
        assert result.changes_made == []

    def test_dry_run_reports_but_does_not_write(self, tmp_path: Path) -> None:
        ks = _make_kitty_specs(tmp_path)
        status_path = _make_status_json(ks / "001-feature", materialized_at=_WALL_CLOCK_TS)
        before = status_path.read_text(encoding="utf-8")

        m = NormalizeStatusJsonMigration()
        result = m.apply(tmp_path, dry_run=True)

        assert result.success is True
        assert "001-feature" in result.changes_made[0]
        assert "would" in result.changes_made[0]
        assert status_path.read_text(encoding="utf-8") == before  # unchanged

    def test_idempotent(self, tmp_path: Path) -> None:
        ks = _make_kitty_specs(tmp_path)
        _make_status_json(ks / "001-feature", materialized_at=_WALL_CLOCK_TS)

        m = NormalizeStatusJsonMigration()
        m.apply(tmp_path, dry_run=False)  # first run normalises
        result2 = m.apply(tmp_path, dry_run=False)  # second run is no-op

        assert result2.success is True
        assert result2.changes_made == []

    def test_multiple_features_mixed(self, tmp_path: Path) -> None:
        ks = _make_kitty_specs(tmp_path)
        _make_status_json(ks / "001-stale", materialized_at=_WALL_CLOCK_TS)
        _make_status_json(ks / "002-clean", materialized_at="")
        _make_status_json(ks / "003-stale", materialized_at=_WALL_CLOCK_TS)

        m = NormalizeStatusJsonMigration()
        result = m.apply(tmp_path, dry_run=False)

        assert result.success is True
        assert len(result.changes_made) == 2
        names = " ".join(result.changes_made)
        assert "001-stale" in names
        assert "003-stale" in names
        assert "002-clean" not in names

    def test_no_status_json_skipped(self, tmp_path: Path) -> None:
        ks = _make_kitty_specs(tmp_path)
        (ks / "001-feature").mkdir()  # no status.json

        m = NormalizeStatusJsonMigration()
        result = m.apply(tmp_path, dry_run=False)

        assert result.success is True
        assert result.changes_made == []


# ---------------------------------------------------------------------------
# _needs_normalisation() helper
# ---------------------------------------------------------------------------


class TestNeedsNormalisation:
    def test_returns_false_when_no_status_json(self, tmp_path: Path) -> None:
        assert _needs_normalisation(tmp_path) is False

    def test_returns_false_for_empty_materialized_at(self, tmp_path: Path) -> None:
        _make_status_json(tmp_path, materialized_at="")
        assert _needs_normalisation(tmp_path) is False

    def test_returns_true_for_wall_clock_timestamp(self, tmp_path: Path) -> None:
        _make_status_json(tmp_path, materialized_at=_WALL_CLOCK_TS)
        assert _needs_normalisation(tmp_path) is True
