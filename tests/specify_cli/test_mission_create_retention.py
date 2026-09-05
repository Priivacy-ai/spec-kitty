"""Create-time retention opt-in (#3131 FR-009 / User Story 3, T016).

``create_mission_core()`` accepts keyword-only ``retain_branches`` /
``retain_worktrees`` flags (WP04 T014) so a mission can DECLARE its retention
policy at creation, making it machine-readable from the start. The
byte-identical guarantee (FR-010, SC-004) is the load-bearing assertion here:
a non-retaining create must leave BOTH fields field-ABSENT from ``meta.json``
-- never a written ``false`` -- so missions that never opt in are
indistinguishable from pre-#3131 output.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from specify_cli.core.paths import load_meta_fail_closed

from tests._factories import make_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


_PLANNING_BRANCH = "feature/retention-mission"


def _init_git_repo(repo: Path) -> None:
    # Non-protected planning branch: create_mission_core's safe_commit refuses
    # a commit to a protected branch (e.g. "main"); mint on a feature branch
    # so the mission's meta.json commit succeeds (mirrors the pattern in
    # tests/_factories/test_make_mission_parity.py).
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", _PLANNING_BRANCH], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)


def _mission_dir(repo_root: Path, mission_slug_prefix: str) -> Path:
    matches = [p for p in (repo_root / "kitty-specs").iterdir() if p.name.startswith(f"{mission_slug_prefix}-")]
    assert len(matches) == 1, f"expected exactly one mission dir, found {matches}"
    return matches[0]


def _read_meta(repo_root: Path, mission_slug_prefix: str) -> dict[str, object]:
    meta_file = _mission_dir(repo_root, mission_slug_prefix) / "meta.json"
    return json.loads(meta_file.read_text(encoding="utf-8"))


def test_both_retention_flags_mint_true_into_meta(tmp_path: Path) -> None:
    """Both flags supplied at create time -> both fields land as JSON ``true``."""
    _init_git_repo(tmp_path)

    make_mission(
        tmp_path,
        "retain-both",
        retain_branches=True,
        retain_worktrees=True,
    )

    meta = _read_meta(tmp_path, "retain-both")
    assert meta["retain_branches"] is True
    assert meta["retain_worktrees"] is True


def test_neither_flag_leaves_both_fields_absent(tmp_path: Path) -> None:
    """FR-010 / SC-004: default (no flags) create leaves BOTH fields ABSENT.

    The byte-identical guarantee: a non-retaining mission's meta.json must
    never carry a written ``"retain_branches": false`` / ``"retain_worktrees":
    false`` -- the keys themselves must not exist.
    """
    _init_git_repo(tmp_path)

    make_mission(tmp_path, "retain-neither")

    meta = _read_meta(tmp_path, "retain-neither")
    assert "retain_branches" not in meta
    assert "retain_worktrees" not in meta


def test_only_retain_branches_flag_present_leaves_worktrees_absent(tmp_path: Path) -> None:
    """One flag supplied -> only that field is minted; the other stays absent."""
    _init_git_repo(tmp_path)

    make_mission(tmp_path, "retain-branches-only", retain_branches=True)

    meta = _read_meta(tmp_path, "retain-branches-only")
    assert meta["retain_branches"] is True
    assert "retain_worktrees" not in meta


def test_only_retain_worktrees_flag_present_leaves_branches_absent(tmp_path: Path) -> None:
    """The mirror case: only ``retain_worktrees`` supplied."""
    _init_git_repo(tmp_path)

    make_mission(tmp_path, "retain-worktrees-only", retain_worktrees=True)

    meta = _read_meta(tmp_path, "retain-worktrees-only")
    assert "retain_branches" not in meta
    assert meta["retain_worktrees"] is True


def test_load_meta_fail_closed_round_trips_minted_true_values(tmp_path: Path) -> None:
    """The production reader (`load_meta_fail_closed`) reads the minted values
    back as real Python ``True`` -- not a string/truthy stand-in -- confirming
    the mint site writes genuine JSON booleans on the canonical read path."""
    _init_git_repo(tmp_path)

    make_mission(
        tmp_path,
        "retain-round-trip",
        retain_branches=True,
        retain_worktrees=True,
    )

    mission_dir = _mission_dir(tmp_path, "retain-round-trip")
    loaded = load_meta_fail_closed(mission_dir)

    assert loaded is not None
    assert loaded["retain_branches"] is True
    assert loaded["retain_worktrees"] is True
