"""Regression coverage for retired coordination-worktree husks.

A directory under ``.worktrees`` is not authoritative merely because it has the
right shape.  Without the canonical append-only event log, a post-teardown husk
must not shadow durable status projected to ``kitty-specs``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.surface_resolver import (
    WorktreeTopology,
    classify_worktree_topology,
    resolve_status_surface,
)
from specify_cli.missions._read_path_resolver import coord_feature_dir
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission,
    resolve_handle_to_read_path,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

MISSION_ID = "01KVYM1WQ4D5E6F7G8H9J0K1M2"
MID8 = MISSION_ID[:8]
SLUG = f"retired-coord-husk-{MID8}"
COORD_BRANCH = f"kitty/mission-{SLUG}"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _build_post_teardown_husk(repo_root: Path) -> tuple[Path, Path]:
    """Create durable primary status alongside an unregistered coord husk."""
    _git(repo_root, "init", "-q", "-b", "main")
    _git(repo_root, "config", "user.email", "husk@example.test")
    _git(repo_root, "config", "user.name", "Husk Regression")

    primary_dir = repo_root / "kitty-specs" / SLUG
    primary_dir.mkdir(parents=True)
    (primary_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": MISSION_ID,
                "mission_slug": SLUG,
                "topology": "coord",
                "coordination_branch": COORD_BRANCH,
            }
        ),
        encoding="utf-8",
    )
    (primary_dir / "status.events.jsonl").write_text("{}\n", encoding="utf-8")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-qm", "fixture: durable mission status")
    _git(repo_root, "branch", COORD_BRANCH)

    husk_dir = coord_feature_dir(repo_root, SLUG, MID8)
    husk_dir.mkdir(parents=True)
    (husk_dir / "status.json").write_text("{}\n", encoding="utf-8")
    return primary_dir, husk_dir


def test_unregistered_coord_husk_never_shadows_durable_primary_status(
    tmp_path: Path,
) -> None:
    """A post-teardown husk must resolve to the durable primary status surface."""
    primary_dir, husk_dir = _build_post_teardown_husk(tmp_path)

    assert (
        classify_worktree_topology(husk_dir, repo_root=tmp_path)
        is WorktreeTopology.UNREGISTERED
    )
    assert resolve_handle_to_read_path(tmp_path, SLUG) == primary_dir
    assert candidate_feature_dir_for_mission(tmp_path, SLUG) == primary_dir
    assert resolve_status_surface(tmp_path, SLUG) == primary_dir / "status.events.jsonl"
