"""WP11: task_helpers thin re-export contract tests.

Asserts that every public name in task_helpers resolves to the canonical
specify_cli.task_utils.support implementation (behavioral result-equality
for hot helpers; set-equality for the public surface).

Test-DoD per WP11 spec:
- Behavioral result-equality for load_meta, run_git, split_frontmatter
  (not is-identity — identity passes even when a wrapper silently diverges)
- Public-surface set-equality guard asserting the re-exported name-set equals
  the required acceptance_support compat set (not len(__all__) == N)
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import specify_cli.task_utils.support as support
import specify_cli.scripts.tasks.task_helpers as task_helpers

# git_repo: run_git behavioral-equality tests drive a real ``git init`` repo via
# subprocess. NOT ``fast`` — subprocess git work would poison the inner -m fast loop.
pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------- Public-surface set-equality guard (CT5 / WP11 test-DoD) ----------


# The minimum compat set that importers depend on.
# This is a SET CONTRACT — not a count — so adding/removing a name fails the test.
_ACCEPTANCE_SUPPORT_COMPAT_SET: frozenset[str] = frozenset(
    {
        "LANES",
        "TIMESTAMP_FORMAT",
        "TaskCliError",
        "WorkPackage",
        "append_activity_log",
        "activity_entries",
        "build_document",
        "detect_conflicting_wp_status",
        "ensure_lane",
        "extract_scalar",
        "find_repo_root",
        "get_lane_from_frontmatter",
        "git_status_lines",
        "load_meta",
        "locate_work_package",
        "normalize_note",
        "now_utc",
        "path_has_changes",
        "run_git",
        "set_scalar",
        "split_frontmatter",
    }
)


def test_public_surface_set_equality() -> None:
    """task_helpers.__all__ must equal the acceptance_support compat set exactly."""
    exported = frozenset(task_helpers.__all__)
    missing = _ACCEPTANCE_SUPPORT_COMPAT_SET - exported
    extra = exported - _ACCEPTANCE_SUPPORT_COMPAT_SET
    assert not missing and not extra, (
        f"Public surface mismatch.\n"
        f"  Missing from task_helpers.__all__: {sorted(missing)}\n"
        f"  Unexpected in task_helpers.__all__: {sorted(extra)}"
    )


def test_all_public_names_importable() -> None:
    """Every name in __all__ must be importable (getattr must not raise)."""
    for name in task_helpers.__all__:
        obj = getattr(task_helpers, name, None)
        assert obj is not None, f"task_helpers.{name} is None or not importable"


def test_task_helpers_does_not_export_is_legacy_format() -> None:
    """is_legacy_format was de-exported from task_helpers in mission retire-pre30-readers."""
    assert "is_legacy_format" not in task_helpers.__all__


# ---------- Behavioral result-equality for hot helpers ----------


def test_split_frontmatter_behavioral_equality() -> None:
    """task_helpers.split_frontmatter and support.split_frontmatter return equal results."""
    text = "---\nwork_package_id: WP01\ntitle: Example\n---\n\nBody text here.\n"
    th_result = task_helpers.split_frontmatter(text)
    sup_result = support.split_frontmatter(text)
    assert th_result == sup_result, (
        f"split_frontmatter results diverged.\n  task_helpers: {th_result!r}\n  support: {sup_result!r}"
    )


def test_split_frontmatter_no_frontmatter() -> None:
    """split_frontmatter returns ('', text, '') when no frontmatter markers present."""
    text = "Just a body without frontmatter.\n"
    th_result = task_helpers.split_frontmatter(text)
    sup_result = support.split_frontmatter(text)
    assert th_result == sup_result


def test_load_meta_behavioral_equality(tmp_path: Path) -> None:
    """task_helpers.load_meta and support.load_meta return equal dicts from same file."""
    # Production-shaped meta.json with a real 26-char ULID mission_id
    meta_data = {
        "mission_id": "01KVRJ6P0000000000000000G0",
        "mission_slug": "single-authority-topology-cleanup-01KVRJ6P",
        "mission_number": None,
        "friendly_name": "Single Authority Topology Cleanup",
    }
    meta_path = tmp_path / "meta.json"
    meta_path.write_text(json.dumps(meta_data), encoding="utf-8")

    th_result = task_helpers.load_meta(meta_path)
    sup_result = support.load_meta(meta_path)
    assert th_result == sup_result


def test_load_meta_missing_file_raises(tmp_path: Path) -> None:
    """Both task_helpers.load_meta and support.load_meta raise TaskCliError on missing file."""
    missing = tmp_path / "nonexistent.json"
    with pytest.raises(task_helpers.TaskCliError):
        task_helpers.load_meta(missing)
    with pytest.raises(support.TaskCliError):
        support.load_meta(missing)


def test_run_git_behavioral_equality(tmp_path: Path) -> None:
    """task_helpers.run_git and support.run_git return equal CompletedProcess for 'git rev-parse --git-dir'."""
    # Initialize a real git repo so rev-parse succeeds
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        env={**__import__("os").environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t.com", "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t.com"},
    )
    th_result = task_helpers.run_git(["rev-parse", "--git-dir"], cwd=tmp_path)
    sup_result = support.run_git(["rev-parse", "--git-dir"], cwd=tmp_path)
    # Both should succeed and return the same stdout/returncode
    assert th_result.returncode == sup_result.returncode == 0
    assert th_result.stdout.strip() == sup_result.stdout.strip()


def test_run_git_error_raises_task_cli_error(tmp_path: Path) -> None:
    """task_helpers.run_git raises TaskCliError on git failure (check=True)."""
    # Non-git directory should fail rev-parse
    with pytest.raises(task_helpers.TaskCliError):
        task_helpers.run_git(["rev-parse", "--git-dir"], cwd=tmp_path, check=True)


# ---------- task_helpers-specific: path_has_changes has no support.py twin ----------


def test_path_has_changes_detects_modification() -> None:
    """path_has_changes returns True when the path appears in git status lines."""
    status_lines = [
        " M kitty-specs/001-demo/tasks/WP01.md",
        "?? untracked.txt",
    ]
    assert task_helpers.path_has_changes(
        status_lines, Path("kitty-specs/001-demo/tasks/WP01.md")
    )


def test_path_has_changes_unrelated_path() -> None:
    """path_has_changes returns False when path is not in git status lines."""
    status_lines = [
        " M kitty-specs/001-demo/tasks/WP02.md",
    ]
    assert not task_helpers.path_has_changes(
        status_lines, Path("kitty-specs/001-demo/tasks/WP01.md")
    )


def test_path_has_changes_empty_lines() -> None:
    """path_has_changes returns False on empty status."""
    assert not task_helpers.path_has_changes([], Path("kitty-specs/001-demo/tasks/WP01.md"))
