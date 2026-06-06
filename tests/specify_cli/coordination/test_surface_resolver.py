"""Tests for specify_cli.coordination.surface_resolver."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.coordination.surface_resolver import resolve_status_surface


def _write_meta(feature_dir: Path, **fields: object) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(fields), encoding="utf-8")


def test_resolve_primary_checkout_when_no_coord_branch(tmp_path: Path) -> None:
    _write_meta(tmp_path / "kitty-specs" / "my-mission", mission_id="01KTDVHZKGCHCW6HQ4V577PNES")
    result = resolve_status_surface(tmp_path, "my-mission")
    assert result == tmp_path / "kitty-specs" / "my-mission" / "status.events.jsonl"


def test_resolve_coordination_worktree_when_coord_branch_set(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission",
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        coordination_branch="kitty/mission-my-mission-01KTDVHZ",
    )
    result = resolve_status_surface(tmp_path, "my-mission")
    expected = (
        tmp_path
        / ".worktrees"
        / "my-mission-01KTDVHZ-coord"
        / "kitty-specs"
        / "my-mission-01KTDVHZ"
        / "status.events.jsonl"
    )
    assert result == expected


def test_raises_when_meta_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_status_surface(tmp_path, "no-such-mission")


def test_mid8_is_first_8_chars_of_mission_id(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission",
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        coordination_branch="kitty/mission-my-mission-01KTDVHZ",
    )
    result = resolve_status_surface(tmp_path, "my-mission")
    assert "my-mission-01KTDVHZ-coord" in str(result)


def test_resolve_uses_explicit_mid8_field_when_present(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission",
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        mid8="ABCD1234",
        coordination_branch="kitty/mission-my-mission-ABCD1234",
    )
    result = resolve_status_surface(tmp_path, "my-mission")
    assert "my-mission-ABCD1234-coord" in str(result)


def test_slug_with_mid8_already_embedded_is_not_doubled(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission-01KTDVHZ",
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        coordination_branch="kitty/mission-my-mission-01KTDVHZ",
    )
    result = resolve_status_surface(tmp_path, "my-mission-01KTDVHZ")
    assert "my-mission-01KTDVHZ-coord" in str(result)
    assert "my-mission-01KTDVHZ-01KTDVHZ" not in str(result)
