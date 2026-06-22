"""Unit tests for backfill_topology: the ensure_topology shim + backfill helpers.

Covers:
- T010 compute-once-then-persist shim (present no-write / absent derive-persist /
  idempotent second read).
- T012 backfill: idempotence, dry-run, corrupt-meta error arm, per-mission scoping,
  and the full 4-cell coord × lanes classification.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mission_runtime import MissionTopology
from specify_cli.migration.backfill_topology import (
    backfill_mission_topology,
    backfill_topology_repo,
    ensure_topology,
)

pytestmark = pytest.mark.unit


def _write_meta(feature_dir: Path, meta: dict[str, object]) -> Path:
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta_path


def _write_lanes(feature_dir: Path) -> None:
    """Write a minimal, parseable lanes.json so read_lanes_json returns a manifest."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": 1,
        "mission_slug": feature_dir.name,
        "mission_branch": f"kitty/mission-{feature_dir.name}",
        "target_branch": "feat/x",
        "lanes": [{"lane_id": "lane-a", "wp_ids": ["WP00"]}],
        "computed_at": "2026-06-22T00:00:00+00:00",
        "computed_from": "tasks.md",
    }
    (feature_dir / "lanes.json").write_text(json.dumps(manifest), encoding="utf-8")


def _bytes(path: Path) -> bytes:
    """Return raw file bytes — used to prove a call wrote nothing (no-write law)."""
    return path.read_bytes()


# ---------------------------------------------------------------------------
# T010 — ensure_topology shim
# ---------------------------------------------------------------------------


def test_ensure_topology_present_field_no_write(tmp_path: Path) -> None:
    """A valid stored topology is returned with NO write (byte-identical file)."""
    feature_dir = tmp_path / "mission-present"
    meta_path = _write_meta(
        feature_dir, {"coordination_branch": "kitty/x", "topology": "single_branch"}
    )
    before = _bytes(meta_path)

    result = ensure_topology(feature_dir)

    assert result is MissionTopology.SINGLE_BRANCH
    assert _bytes(meta_path) == before, "present field must not trigger a write"


def test_ensure_topology_absent_derives_and_persists(tmp_path: Path) -> None:
    """An absent topology is derived once and persisted with flattened: false."""
    feature_dir = tmp_path / "mission-absent"
    meta_path = _write_meta(feature_dir, {"coordination_branch": "kitty/x"})

    result = ensure_topology(feature_dir)

    assert result is MissionTopology.COORD
    persisted = json.loads(meta_path.read_text(encoding="utf-8"))
    assert persisted["topology"] == "coord"
    assert persisted["flattened"] is False


def test_ensure_topology_second_read_idempotent(tmp_path: Path) -> None:
    """Compute-once law: the second read does not re-derive or re-write."""
    feature_dir = tmp_path / "mission-once"
    meta_path = _write_meta(feature_dir, {"coordination_branch": None})

    first = ensure_topology(feature_dir)
    after_first = _bytes(meta_path)
    second = ensure_topology(feature_dir)

    assert first is MissionTopology.SINGLE_BRANCH
    assert second is first
    assert _bytes(meta_path) == after_first, "second read must not re-write"


def test_ensure_topology_preserves_existing_flattened_flag(tmp_path: Path) -> None:
    """An existing flattened flag is preserved when deriving a missing topology."""
    feature_dir = tmp_path / "mission-flat"
    meta_path = _write_meta(feature_dir, {"coordination_branch": None, "flattened": True})

    result = ensure_topology(feature_dir)

    assert result is MissionTopology.SINGLE_BRANCH
    persisted = json.loads(meta_path.read_text(encoding="utf-8"))
    assert persisted["flattened"] is True


# ---------------------------------------------------------------------------
# T012 — backfill_mission_topology: 4-cell classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("coord", "lanes", "expected"),
    [
        (None, False, "single_branch"),
        (None, True, "lanes"),
        ("kitty/mission-x", False, "coord"),
        ("kitty/mission-x", True, "lanes_with_coord"),
    ],
)
def test_backfill_covers_four_cells(
    tmp_path: Path, coord: str | None, lanes: bool, expected: str
) -> None:
    """All four coord × lanes combinations backfill to the matching topology value."""
    feature_dir = tmp_path / "kitty-specs" / f"mission-{expected}"
    meta: dict[str, object] = {}
    if coord is not None:
        meta["coordination_branch"] = coord
    _write_meta(feature_dir, meta)
    if lanes:
        _write_lanes(feature_dir)

    result = backfill_mission_topology(feature_dir)

    assert result.action == "wrote"
    assert result.topology == expected
    persisted = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert persisted["topology"] == expected
    assert persisted["flattened"] is False


def test_backfill_idempotent_second_run_skips(tmp_path: Path) -> None:
    """Second backfill run is all-skip with a byte-identical meta.json."""
    feature_dir = tmp_path / "kitty-specs" / "mission-idem"
    meta_path = _write_meta(feature_dir, {"coordination_branch": "kitty/x"})

    first = backfill_mission_topology(feature_dir)
    assert first.action == "wrote"
    bytes_after_first = _bytes(meta_path)

    second = backfill_mission_topology(feature_dir)
    assert second.action == "skip"
    assert second.topology == "coord"
    assert _bytes(meta_path) == bytes_after_first, "second run must not modify the file"


def test_backfill_never_overwrites_existing_value(tmp_path: Path) -> None:
    """An existing topology is preserved even if it disagrees with current signals."""
    feature_dir = tmp_path / "kitty-specs" / "mission-keep"
    # coordination_branch present (would derive coord) but a value is already stored.
    meta_path = _write_meta(
        feature_dir, {"coordination_branch": "kitty/x", "topology": "single_branch"}
    )

    result = backfill_mission_topology(feature_dir)

    assert result.action == "skip"
    persisted = json.loads(meta_path.read_text(encoding="utf-8"))
    assert persisted["topology"] == "single_branch", "existing value must not be overwritten"


def test_backfill_dry_run_writes_nothing(tmp_path: Path) -> None:
    """--dry-run reports the would-write but does not touch the file."""
    feature_dir = tmp_path / "kitty-specs" / "mission-dry"
    meta_path = _write_meta(feature_dir, {"coordination_branch": "kitty/x"})
    before = _bytes(meta_path)

    result = backfill_mission_topology(feature_dir, dry_run=True)

    assert result.action == "wrote"
    assert result.topology == "coord"
    assert _bytes(meta_path) == before, "dry-run must not write"
    assert "topology" not in json.loads(meta_path.read_text(encoding="utf-8"))


def test_backfill_corrupt_meta_returns_error(tmp_path: Path) -> None:
    """Corrupt meta.json yields an error result, not an exception."""
    feature_dir = tmp_path / "kitty-specs" / "mission-corrupt"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text("{ not json", encoding="utf-8")

    result = backfill_mission_topology(feature_dir)

    assert result.action == "error"
    assert result.topology is None
    assert "corrupt json" in (result.reason or "")


def test_backfill_missing_meta_skips(tmp_path: Path) -> None:
    """A directory with no meta.json is skipped, not errored."""
    feature_dir = tmp_path / "kitty-specs" / "mission-nometa"
    feature_dir.mkdir(parents=True)

    result = backfill_mission_topology(feature_dir)

    assert result.action == "skip"
    assert result.reason == "meta.json not found"


# ---------------------------------------------------------------------------
# T012 — backfill_topology_repo: walk + scoping
# ---------------------------------------------------------------------------


def test_backfill_repo_walks_all_missions(tmp_path: Path) -> None:
    specs = tmp_path / "kitty-specs"
    _write_meta(specs / "mission-a", {"coordination_branch": "kitty/a"})
    _write_meta(specs / "mission-b", {"coordination_branch": None})

    results = backfill_topology_repo(tmp_path)

    by_slug = {r.slug: r for r in results}
    assert by_slug["mission-a"].topology == "coord"
    assert by_slug["mission-b"].topology == "single_branch"


def test_backfill_repo_scopes_to_single_mission(tmp_path: Path) -> None:
    specs = tmp_path / "kitty-specs"
    _write_meta(specs / "mission-a", {"coordination_branch": "kitty/a"})
    _write_meta(specs / "mission-b", {"coordination_branch": None})

    results = backfill_topology_repo(tmp_path, mission_slug="mission-b")

    assert len(results) == 1
    assert results[0].slug == "mission-b"
    assert "topology" not in json.loads((specs / "mission-a" / "meta.json").read_text())


def test_backfill_repo_no_kitty_specs_returns_empty(tmp_path: Path) -> None:
    assert backfill_topology_repo(tmp_path) == []
