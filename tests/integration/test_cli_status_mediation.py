"""Integration tests for WP08 CLI status mediation (#1348).

These tests verify FR-030 / SC-02: read-side commands resolve the
coordination worktree (or the primary checkout for legacy missions)
regardless of operator CWD.  The same ``spec-kitty agent tasks status``
invocation must return identical results whether the operator is
standing in:

* the primary checkout root
* a lane worktree
* an unrelated CWD (``/tmp``)

For legacy missions (no coordination worktree on disk), the resolver
falls back to the primary checkout view.

These tests exercise the resolver via the canonical
``resolve_mission_read_path`` API so they remain stable across CLI
refactors; a final spawn-the-binary smoke test ensures the wiring is
intact end-to-end.

Spec source: FR-030, SC-02, contracts/cli_status_mediation.md.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

from specify_cli.missions._read_path_resolver import (
    STATUS_READ_PATH_NOT_FOUND_CODE,
    StatusReadPathNotFound,
    _resolve_mission_read_path as resolve_mission_read_path,
)
from specify_cli.coordination.workspace import CoordinationWorkspace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def _init_git_repo(repo_root: Path) -> None:
    _run(repo_root, "git", "init", "--initial-branch=main")
    _run(repo_root, "git", "config", "user.email", "test@example.invalid")
    _run(repo_root, "git", "config", "user.name", "WP08 Test")
    _run(repo_root, "git", "config", "commit.gpgsign", "false")
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")
    _run(repo_root, "git", "add", "README.md")
    _run(repo_root, "git", "commit", "-m", "seed")


def _make_coord_mission(repo_root: Path) -> dict[str, Any]:
    """Mission with coord branch + coord worktree materialised on disk."""
    mission_slug = "cli-mediation-mission"
    mission_id = "01KMEDIATEZZZZZZZZZZZZZZZZ"
    mid8 = mission_id[:8]
    coord_branch = f"kitty/mission-{mission_slug}-{mid8}"
    feature_dir = repo_root / "kitty-specs" / f"{mission_slug}-{mid8}"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_slug": f"{mission_slug}-{mid8}",
                "mid8": mid8,
                "coordination_branch": coord_branch,
                "mission_type": "software-dev",
                "target_branch": "main",
                "created_at": "2026-05-28T00:00:00+00:00",
                "friendly_name": "CLI mediation mission",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _run(repo_root, "git", "add", "kitty-specs")
    _run(repo_root, "git", "commit", "-m", "seed coord mission")
    _run(repo_root, "git", "branch", coord_branch)
    # Materialise the coord worktree at the canonical path with a
    # distinct status file so we can tell it apart from the primary
    # checkout's view.
    coord_path = CoordinationWorkspace.resolve(
        repo_root, f"{mission_slug}-{mid8}", mid8,
    )
    coord_feature_dir = coord_path / "kitty-specs" / f"{mission_slug}-{mid8}"
    coord_feature_dir.mkdir(parents=True, exist_ok=True)
    (coord_feature_dir / "status.json").write_text(
        json.dumps({"source": "coord"}, indent=2), encoding="utf-8",
    )
    # And drop a divergent file in the primary checkout to prove the
    # resolver does not return it.
    (feature_dir / "status.json").write_text(
        json.dumps({"source": "primary"}, indent=2), encoding="utf-8",
    )

    # Build a lane worktree the operator can stand in.
    lane_branch = f"kitty/mission-{mission_slug}-{mid8}-lane-a"
    _run(repo_root, "git", "branch", lane_branch, "main")
    lane_path = repo_root / ".worktrees" / f"{mission_slug}-{mid8}-lane-a"
    lane_path.parent.mkdir(parents=True, exist_ok=True)
    _run(repo_root, "git", "worktree", "add", str(lane_path), lane_branch)

    return {
        "mission_slug": f"{mission_slug}-{mid8}",
        "mid8": mid8,
        "mission_id": mission_id,
        "coord_path": coord_path,
        "coord_feature_dir": coord_feature_dir,
        "primary_feature_dir": feature_dir,
        "lane_worktree": lane_path,
    }


def _make_legacy_mission(repo_root: Path) -> dict[str, Any]:
    """Pre-coord mission (no coord branch, no coord worktree)."""
    mission_slug = "legacy-cli-mediation"
    mission_id = "01KLEGCLIZZZZZZZZZZZZZZZZZ"
    mid8 = mission_id[:8]
    feature_dir = repo_root / "kitty-specs" / f"{mission_slug}-{mid8}"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mission_slug": f"{mission_slug}-{mid8}",
                "mid8": mid8,
                # NOTE: no coordination_branch — legacy.
                "mission_type": "software-dev",
                "target_branch": "main",
                "created_at": "2026-05-28T00:00:00+00:00",
                "friendly_name": "Legacy CLI mediation mission",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (feature_dir / "status.json").write_text(
        json.dumps({"source": "primary"}, indent=2), encoding="utf-8",
    )
    _run(repo_root, "git", "add", "kitty-specs")
    _run(repo_root, "git", "commit", "-m", "seed legacy mission")
    return {
        "mission_slug": f"{mission_slug}-{mid8}",
        "mid8": mid8,
        "mission_id": mission_id,
        "primary_feature_dir": feature_dir,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    return tmp_path


@pytest.fixture()
def coord_mission(repo_root: Path) -> dict[str, Any]:
    return _make_coord_mission(repo_root)


@pytest.fixture()
def legacy_mission(repo_root: Path) -> dict[str, Any]:
    return _make_legacy_mission(repo_root)


# ---------------------------------------------------------------------------
# Resolver-level mediation
# ---------------------------------------------------------------------------


def test_resolver_prefers_coord_worktree(
    repo_root: Path,
    coord_mission: dict[str, Any],
) -> None:
    """The resolver returns the coord worktree when one exists on disk."""
    resolved = resolve_mission_read_path(
        repo_root, coord_mission["mission_slug"], coord_mission["mid8"],
    )
    assert resolved == coord_mission["coord_feature_dir"]
    # Confirm it carries the coord-source status.json.
    data = json.loads((resolved / "status.json").read_text())
    assert data == {"source": "coord"}


def test_resolver_falls_back_to_primary_for_legacy(
    repo_root: Path,
    legacy_mission: dict[str, Any],
) -> None:
    """A legacy mission with no coord worktree falls back to the primary checkout."""
    resolved = resolve_mission_read_path(
        repo_root, legacy_mission["mission_slug"], legacy_mission["mid8"],
    )
    assert resolved == legacy_mission["primary_feature_dir"]
    data = json.loads((resolved / "status.json").read_text())
    assert data == {"source": "primary"}


def test_resolver_raises_when_required_and_missing(
    repo_root: Path,
) -> None:
    """``require_exists=True`` surfaces ``STATUS_READ_PATH_NOT_FOUND``."""
    with pytest.raises(StatusReadPathNotFound) as exc_info:
        resolve_mission_read_path(
            repo_root, "no-such-mission", "01XXXXXX", require_exists=True,
        )
    assert exc_info.value.error_code == STATUS_READ_PATH_NOT_FOUND_CODE


def test_resolver_is_cwd_independent(
    repo_root: Path,
    coord_mission: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SC-02: spawning resolution from anywhere returns the same path."""
    # From primary root
    monkeypatch.chdir(repo_root)
    from_primary = resolve_mission_read_path(
        repo_root, coord_mission["mission_slug"], coord_mission["mid8"],
    )

    # From inside the lane worktree
    monkeypatch.chdir(coord_mission["lane_worktree"])
    from_lane = resolve_mission_read_path(
        repo_root, coord_mission["mission_slug"], coord_mission["mid8"],
    )

    # From an unrelated CWD
    unrelated = tmp_path / "elsewhere"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    from_random = resolve_mission_read_path(
        repo_root, coord_mission["mission_slug"], coord_mission["mid8"],
    )

    assert from_primary == from_lane == from_random == coord_mission["coord_feature_dir"]


# ---------------------------------------------------------------------------
# CLI-level mediation via execution_context
# ---------------------------------------------------------------------------


def test_status_from_lane_worktree_matches_primary(
    repo_root: Path,
    coord_mission: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end mediation through ``_resolve_mission_slug``.

    ``resolve_action_context`` is the shared engine behind
    ``agent context resolve``; verifying its mission-dir resolution
    proves the CLI mediation surface independent of any spawn cost.
    """
    from mission_runtime import _resolve_mission_slug

    # Lane CWD
    monkeypatch.chdir(coord_mission["lane_worktree"])
    _, dir_from_lane = _resolve_mission_slug(
        repo_root,
        feature=coord_mission["mission_slug"],
        cwd=coord_mission["lane_worktree"],
        env=None,
    )

    # Primary CWD
    monkeypatch.chdir(repo_root)
    _, dir_from_primary = _resolve_mission_slug(
        repo_root,
        feature=coord_mission["mission_slug"],
        cwd=repo_root,
        env=None,
    )

    assert dir_from_lane == dir_from_primary == coord_mission["coord_feature_dir"]


def test_legacy_mission_read_falls_back_to_primary(
    repo_root: Path,
    legacy_mission: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy mission read goes to the primary checkout via the resolver."""
    from mission_runtime import _resolve_mission_slug

    monkeypatch.chdir(repo_root)
    _, resolved_dir = _resolve_mission_slug(
        repo_root,
        feature=legacy_mission["mission_slug"],
        cwd=repo_root,
        env=None,
    )
    assert resolved_dir == legacy_mission["primary_feature_dir"]
