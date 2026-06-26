"""Tests for the pre-3.0 layout boundary guard (NFR-004)."""
from pathlib import Path

import pytest

from specify_cli.upgrade.pre30_guard import Pre30LayoutError, check_pre30_layout

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _make_feature_dir(tmp_path: Path) -> Path:
    feature = tmp_path / "kitty-specs" / "001-test"
    feature.mkdir(parents=True)
    return feature


def test_guard_rejects_pre30_project(tmp_path: Path) -> None:
    """T-GUARD-01: pre-3.0 lane directory with .md files raises Pre30LayoutError."""
    feature = _make_feature_dir(tmp_path)
    planned = feature / "tasks" / "planned"
    planned.mkdir(parents=True)
    (planned / "WP01.md").write_text("---\nwork_package_id: WP01\n---\n")

    with pytest.raises(Pre30LayoutError) as exc_info:
        check_pre30_layout(feature)

    message = str(exc_info.value)
    assert "Pre-3.0 layout detected" in message
    assert "spec-kitty upgrade" in message


def test_guard_passes_post30_project(tmp_path: Path) -> None:
    """T-GUARD-02: flat tasks/WP01.md (post-3.0) passes without exception."""
    feature = _make_feature_dir(tmp_path)
    tasks = feature / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "WP01.md").write_text("---\nwork_package_id: WP01\n---\n")

    check_pre30_layout(feature)  # Must not raise


def test_guard_passes_empty_lane_directory(tmp_path: Path) -> None:
    """T-GUARD-03: empty lane directory (no .md files) passes without exception."""
    feature = _make_feature_dir(tmp_path)
    planned = feature / "tasks" / "planned"
    planned.mkdir(parents=True)
    (planned / ".gitkeep").write_text("")

    check_pre30_layout(feature)  # Must not raise


def test_guard_passes_no_tasks_directory(tmp_path: Path) -> None:
    """T-GUARD-04: no tasks/ directory at all passes without exception."""
    feature = _make_feature_dir(tmp_path)
    check_pre30_layout(feature)  # Must not raise
