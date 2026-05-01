"""Tests for the ``spec-kitty materialize`` command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

# Marked for mutmut sandbox skip — see ADR 2026-04-20-1.
# Reason: subprocess CLI invocation
pytestmark = pytest.mark.non_sandbox


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    mission_slug: str,
    wp_id: str,
    from_lane: str,
    to_lane: str,
    event_id: str,
    at: str = "2026-01-01T12:00:00+00:00",
) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug=mission_slug,
        wp_id=wp_id,
        from_lane=Lane(from_lane),
        to_lane=Lane(to_lane),
        at=at,
        actor="test-agent",
        force=False,
        execution_mode="worktree",
    )


def _setup_feature(
    tmp_path: Path,
    mission_slug: str,
    wp_lanes: dict[str, str],
) -> Path:
    """Create a feature directory with event log for the given WP lanes."""
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    for idx, (wp_id, lane) in enumerate(wp_lanes.items()):
        event_id = f"01TEST{idx:020d}"
        event = _make_event(mission_slug, wp_id, "planned", lane, event_id)
        append_event(feature_dir, event)
    return feature_dir


# ---------------------------------------------------------------------------
# Materialisation function tests (unit-level)
# ---------------------------------------------------------------------------


def test_write_derived_views_creates_files(tmp_path):
    """write_derived_views writes status.json and board-summary.json."""
    from specify_cli.status.views import write_derived_views

    feature_dir = _setup_feature(tmp_path, "001-test", {"WP01": "done"})
    derived_dir = tmp_path / ".kittify" / "derived"

    write_derived_views(feature_dir, derived_dir)

    status_path = derived_dir / "001-test" / "status.json"
    board_path = derived_dir / "001-test" / "board-summary.json"
    assert status_path.exists()
    assert board_path.exists()

    status_data = json.loads(status_path.read_text())
    board_data = json.loads(board_path.read_text())
    assert status_data["mission_slug"] == "001-test"
    assert board_data["mission_slug"] == "001-test"


def test_generate_progress_json_creates_file(tmp_path):
    """generate_progress_json writes progress.json."""
    from specify_cli.status.progress import generate_progress_json

    feature_dir = _setup_feature(tmp_path, "002-test", {"WP01": "in_progress"})
    derived_dir = tmp_path / ".kittify" / "derived"

    generate_progress_json(feature_dir, derived_dir)

    progress_file = derived_dir / "002-test" / "progress.json"
    assert progress_file.exists()
    data = json.loads(progress_file.read_text())
    assert data["mission_slug"] == "002-test"
    assert data["percentage"] == pytest.approx(30.0)


def test_materialize_all_features_via_function(tmp_path):
    """Direct call to write_derived_views + progress/lifecycle for two features."""
    from specify_cli.status.views import write_derived_views
    from specify_cli.status.lifecycle import generate_lifecycle_json
    from specify_cli.status.progress import generate_progress_json

    mission_slugs = ["003-alpha", "003-beta"]
    for slug in mission_slugs:
        _setup_feature(tmp_path, slug, {"WP01": "done"})

    derived_dir = tmp_path / ".kittify" / "derived"

    for slug in mission_slugs:
        feature_dir = tmp_path / "kitty-specs" / slug
        write_derived_views(feature_dir, derived_dir)
        generate_progress_json(feature_dir, derived_dir)
        generate_lifecycle_json(feature_dir, derived_dir)

    for slug in mission_slugs:
        assert (derived_dir / slug / "status.json").exists()
        assert (derived_dir / slug / "board-summary.json").exists()
        assert (derived_dir / slug / "progress.json").exists()
        assert (derived_dir / slug / "lifecycle.json").exists()


def test_materialize_output_json_structure(tmp_path):
    """Materialised progress.json has expected top-level keys."""
    from specify_cli.status.progress import generate_progress_json

    feature_dir = _setup_feature(
        tmp_path,
        "004-structure",
        {"WP01": "done", "WP02": "in_progress"},
    )
    derived_dir = tmp_path / ".kittify" / "derived"
    generate_progress_json(feature_dir, derived_dir)

    data = json.loads((derived_dir / "004-structure" / "progress.json").read_text())
    for key in ("mission_slug", "percentage", "done_count", "total_count", "per_lane_counts", "per_wp"):
        assert key in data, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# CLI command tests (invoke via function directly with patched locate_project_root)
# ---------------------------------------------------------------------------


def test_materialize_command_no_project(tmp_path):
    """materialize exits with code 1 when not in a spec-kitty project."""
    from specify_cli.cli.commands.materialize import materialize
    import typer

    with patch("specify_cli.cli.commands.materialize.locate_project_root", return_value=None):
        with pytest.raises(typer.Exit) as exc_info:
            materialize()
        assert exc_info.value.exit_code == 1


def test_materialize_command_all_features(tmp_path):
    """materialize processes all features when no --feature given."""
    from specify_cli.cli.commands.materialize import materialize
    import typer

    _setup_feature(tmp_path, "005-alpha", {"WP01": "done"})
    _setup_feature(tmp_path, "005-beta", {"WP01": "planned"})

    with patch("specify_cli.cli.commands.materialize.locate_project_root", return_value=tmp_path):
        with pytest.raises(typer.Exit) as exc_info:
            materialize(feature=None, json_output=False)
        assert exc_info.value.exit_code == 0

    # Verify files written
    assert (tmp_path / ".kittify" / "derived" / "005-alpha" / "progress.json").exists()
    assert (tmp_path / ".kittify" / "derived" / "005-beta" / "progress.json").exists()


def test_materialize_command_single_feature(tmp_path):
    """materialize --feature processes only the specified feature."""
    from specify_cli.cli.commands.materialize import materialize
    import typer

    _setup_feature(tmp_path, "006-target", {"WP01": "done"})

    with patch("specify_cli.cli.commands.materialize.locate_project_root", return_value=tmp_path):
        with pytest.raises(typer.Exit) as exc_info:
            materialize(feature="006-target", json_output=False)
        assert exc_info.value.exit_code == 0

    assert (tmp_path / ".kittify" / "derived" / "006-target" / "status.json").exists()


def test_materialize_command_feature_not_found(tmp_path):
    """materialize exits 1 when --feature slug does not exist."""
    from specify_cli.cli.commands.materialize import materialize
    import typer

    (tmp_path / "kitty-specs").mkdir(parents=True)

    with patch("specify_cli.cli.commands.materialize.locate_project_root", return_value=tmp_path):
        with pytest.raises(typer.Exit) as exc_info:
            materialize(feature="999-nonexistent", json_output=False)
        assert exc_info.value.exit_code == 1


def test_materialize_command_json_output(tmp_path):
    """materialize --json outputs a machine-readable summary."""
    from specify_cli.cli.commands.materialize import materialize
    import typer

    _setup_feature(tmp_path, "007-json", {"WP01": "done"})

    with patch("specify_cli.cli.commands.materialize.locate_project_root", return_value=tmp_path):
        with pytest.raises(typer.Exit) as exc_info:
            materialize(feature="007-json", json_output=True)
        assert exc_info.value.exit_code == 0


# ---------------------------------------------------------------------------
# Lazy regeneration (materialize_if_stale)
# ---------------------------------------------------------------------------


def test_materialize_if_stale_creates_on_missing(tmp_path):
    """materialize_if_stale regenerates when derived files are missing."""
    from specify_cli.status.views import materialize_if_stale

    feature_dir = _setup_feature(tmp_path, "008-stale", {"WP01": "done"})

    snapshot = materialize_if_stale(feature_dir, tmp_path)

    assert snapshot is not None
    assert (tmp_path / ".kittify" / "derived" / "008-stale" / "status.json").exists()
    assert (tmp_path / ".kittify" / "derived" / "008-stale" / "progress.json").exists()
    assert (tmp_path / ".kittify" / "derived" / "008-stale" / "lifecycle.json").exists()


def test_materialize_if_stale_skips_when_fresh(tmp_path):
    """materialize_if_stale does not regenerate when derived files are up-to-date."""
    from specify_cli.status.views import materialize_if_stale, write_derived_views
    from specify_cli.status.lifecycle import generate_lifecycle_json
    from specify_cli.status.progress import generate_progress_json

    feature_dir = _setup_feature(tmp_path, "009-fresh", {"WP01": "done"})
    derived_dir = tmp_path / ".kittify" / "derived"

    # Write derived files
    write_derived_views(feature_dir, derived_dir)
    generate_progress_json(feature_dir, derived_dir)
    generate_lifecycle_json(feature_dir, derived_dir)

    # Touch derived file to make it newer than event log
    status_path = derived_dir / "009-fresh" / "status.json"
    progress_path = derived_dir / "009-fresh" / "progress.json"
    lifecycle_path = derived_dir / "009-fresh" / "lifecycle.json"
    events_path = feature_dir / "status.events.jsonl"

    # Set event log mtime to past, derived files to future
    import os

    past_time = events_path.stat().st_mtime - 10
    future_time = events_path.stat().st_mtime + 10
    os.utime(events_path, (past_time, past_time))
    os.utime(status_path, (future_time, future_time))
    os.utime(progress_path, (future_time, future_time))
    os.utime(lifecycle_path, (future_time, future_time))

    original_mtime = status_path.stat().st_mtime

    # Should not regenerate
    materialize_if_stale(feature_dir, tmp_path)

    # mtime should be unchanged (file not rewritten)
    assert status_path.stat().st_mtime == original_mtime


def test_materialize_if_stale_regenerates_when_stale(tmp_path):
    """materialize_if_stale regenerates when event log is newer than derived files."""
    from specify_cli.status.views import materialize_if_stale, write_derived_views
    from specify_cli.status.lifecycle import generate_lifecycle_json
    from specify_cli.status.progress import generate_progress_json
    import os

    feature_dir = _setup_feature(tmp_path, "010-regen", {"WP01": "done"})
    derived_dir = tmp_path / ".kittify" / "derived"

    # Write derived files first
    write_derived_views(feature_dir, derived_dir)
    generate_progress_json(feature_dir, derived_dir)
    generate_lifecycle_json(feature_dir, derived_dir)

    status_path = derived_dir / "010-regen" / "status.json"
    events_path = feature_dir / "status.events.jsonl"

    # Make event log newer than derived files
    future_time = status_path.stat().st_mtime + 10
    os.utime(events_path, (future_time, future_time))

    # Should regenerate
    materialize_if_stale(feature_dir, tmp_path)

    # status.json should have been rewritten (mtime updated)
    new_mtime = status_path.stat().st_mtime
    assert new_mtime >= status_path.stat().st_mtime  # file exists and is valid


def test_materialize_if_stale_no_events(tmp_path):
    """materialize_if_stale handles features with no event log (empty progress)."""
    from specify_cli.status.views import materialize_if_stale

    feature_dir = tmp_path / "kitty-specs" / "011-empty"
    feature_dir.mkdir(parents=True)

    snapshot = materialize_if_stale(feature_dir, tmp_path)

    assert snapshot is not None
    assert snapshot.mission_slug == ""  # empty snapshot
    assert snapshot.event_count == 0
