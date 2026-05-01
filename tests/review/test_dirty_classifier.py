"""Unit tests for dirty_classifier.py.

Covers the classify_dirty_paths() function which partitions git-status paths
into (blocking, benign) buckets for review handoff validation.
"""

from __future__ import annotations

import pytest

from specify_cli.review.dirty_classifier import classify_dirty_paths

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _classify(paths: list[str], wp_id: str = "WP01", mission_slug: str = "066-test") -> tuple[list[str], list[str]]:
    """Thin wrapper so tests stay concise."""
    return classify_dirty_paths(paths, wp_id=wp_id, mission_slug=mission_slug)


# ---------------------------------------------------------------------------
# 1. Empty input
# ---------------------------------------------------------------------------

def test_empty_dirty_list():
    blocking, benign = _classify([])
    assert blocking == []
    assert benign == []


# ---------------------------------------------------------------------------
# 2. Status artifacts are benign
# ---------------------------------------------------------------------------

def test_status_artifacts_are_benign():
    paths = [
        "kitty-specs/066-test/status.events.jsonl",
        "kitty-specs/066-test/status.json",
    ]
    blocking, benign = _classify(paths)
    assert blocking == []
    assert set(benign) == set(paths)


# ---------------------------------------------------------------------------
# 3. Other WP task files are benign (WP02 when checking WP01)
# ---------------------------------------------------------------------------

def test_other_wp_task_files_are_benign():
    paths = [
        "kitty-specs/066-test/tasks/WP02-some-feature.md",
        "kitty-specs/066-test/tasks/WP03-another-feature.md",
        "kitty-specs/066-test/tasks/WP10-double-digit.md",
    ]
    blocking, benign = _classify(paths, wp_id="WP01")
    assert blocking == []
    assert len(benign) == 3


# ---------------------------------------------------------------------------
# 4. Own task file is benign (planning artifact, auto-committed by move-task)
# ---------------------------------------------------------------------------

def test_own_task_file_is_benign():
    """WP task files are planning artifacts modified by move-task itself.
    They should not block review handoff even for the current WP."""
    paths = ["kitty-specs/066-test/tasks/WP01-my-feature.md"]
    blocking, benign = _classify(paths, wp_id="WP01")
    assert blocking == []
    assert benign == ["kitty-specs/066-test/tasks/WP01-my-feature.md"]


# ---------------------------------------------------------------------------
# 5. Source files are blocking
# ---------------------------------------------------------------------------

def test_source_files_are_blocking():
    paths = [
        "src/specify_cli/review/dirty_classifier.py",
        "tests/review/test_dirty_classifier.py",
        "pyproject.toml",
    ]
    blocking, benign = _classify(paths)
    assert set(blocking) == set(paths)
    assert benign == []


# ---------------------------------------------------------------------------
# 6. meta.json is benign
# ---------------------------------------------------------------------------

def test_meta_json_is_benign():
    paths = ["kitty-specs/066-test/meta.json"]
    blocking, benign = _classify(paths)
    assert blocking == []
    assert benign == ["kitty-specs/066-test/meta.json"]


# ---------------------------------------------------------------------------
# 7. .kittify/ paths are benign
# ---------------------------------------------------------------------------

def test_kittify_paths_are_benign():
    paths = [
        ".kittify/config.yaml",
        ".kittify/metadata.yaml",
        ".kittify/skills-manifest.json",
    ]
    blocking, benign = _classify(paths)
    assert blocking == []
    assert len(benign) == 3


# ---------------------------------------------------------------------------
# 8. Mixed dirty paths — correct partition
# ---------------------------------------------------------------------------

def test_mixed_dirty_paths():
    blocking_paths = [
        "src/specify_cli/tasks.py",
    ]
    benign_paths = [
        "kitty-specs/066-test/tasks/WP01-my-feature.md",
        "kitty-specs/066-test/status.events.jsonl",
        "kitty-specs/066-test/status.json",
        "kitty-specs/066-test/tasks/WP02-other.md",
        ".kittify/config.yaml",
        "kitty-specs/066-test/meta.json",
        "kitty-specs/066-test/lanes.json",
    ]
    all_paths = blocking_paths + benign_paths

    blocking, benign = _classify(all_paths, wp_id="WP01")

    assert set(blocking) == set(blocking_paths)
    assert set(benign) == set(benign_paths)


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

def test_lanes_json_is_benign():
    paths = ["kitty-specs/066-test/lanes.json"]
    blocking, benign = _classify(paths)
    assert blocking == []
    assert benign == ["kitty-specs/066-test/lanes.json"]


def test_root_tasks_md_is_benign():
    """The summary tasks.md at the mission root is auto-updated by mark-status."""
    paths = ["kitty-specs/066-test/tasks.md"]
    blocking, benign = _classify(paths)
    assert blocking == []
    assert benign == paths


def test_wp_task_file_with_double_digit_wp_id():
    """All WP task files are benign planning artifacts, even the current WP's."""
    paths = ["kitty-specs/066-test/tasks/WP10-big-feature.md"]
    blocking, benign = _classify(paths, wp_id="WP10")
    assert blocking == []
    assert benign == paths


def test_wp_task_file_other_double_digit_is_benign():
    """WP10 is benign when checking WP01."""
    paths = ["kitty-specs/066-test/tasks/WP10-big-feature.md"]
    blocking, benign = _classify(paths, wp_id="WP01")
    assert blocking == []
    assert benign == paths
