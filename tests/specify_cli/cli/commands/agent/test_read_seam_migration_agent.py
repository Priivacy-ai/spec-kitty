"""Acceptance pins for the agent-command read-side placement migration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent import status, workflow
from specify_cli.coordination.surface_resolver import CoordinationBranchDeleted

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

MISSION_ID = "01KWZ46VTY9CVJ8G10ERTMPVRH"
MID8 = MISSION_ID[:8]
MISSION_SLUG = "read-seam-agent"
MISSION_DIR_NAME = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{MISSION_DIR_NAME}"


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _seed_repo(tmp_path: Path, *, deleted_coord: bool) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "read-seam@example.test")
    _git(tmp_path, "config", "user.name", "Read Seam Test")
    _git(tmp_path, "commit", "--allow-empty", "-qm", "init")

    mission_dir = tmp_path / "kitty-specs" / MISSION_DIR_NAME
    (mission_dir / "tasks").mkdir(parents=True)
    metadata: dict[str, str] = {
        "mission_id": MISSION_ID,
        "mission_slug": MISSION_DIR_NAME,
    }
    if deleted_coord:
        metadata["coordination_branch"] = COORD_BRANCH
    (mission_dir / "meta.json").write_text(json.dumps(metadata), encoding="utf-8")
    return mission_dir


# NOTE: the former ``test_agent_command_cluster_retains_only_ledger_approved_lenient_sites``
# and its private AST visitor lived here. Both are gone: the whole-tree
# structural gate ``tests/architectural/test_no_read_side_bypass.py`` already
# scans every module under ``src/`` (this directory included) with the SAME
# grammar, reconciles the residuals against the WP02 ledger, and REDS on any
# un-allow-listed bypass. This file keeps only behavioural pins.


def test_primary_metadata_handle_resolution_preserves_the_canonical_slug(tmp_path: Path) -> None:
    """The migrated PRIMARY_METADATA read returns the same canonical directory name."""
    mission_dir = _seed_repo(tmp_path, deleted_coord=False)

    assert status._find_mission_slug(MID8, repo_root=tmp_path) == mission_dir.name


def test_preview_claimable_wp_fails_loudly_when_coord_branch_was_deleted(tmp_path: Path) -> None:
    """The stable workflow preview entry point exposes deleted COORD authority."""
    _seed_repo(tmp_path, deleted_coord=True)

    with pytest.raises(CoordinationBranchDeleted) as exc_info:
        workflow._preview_claimable_wp_for_mission(tmp_path, MISSION_DIR_NAME)

    assert exc_info.value.error_code == "COORDINATION_BRANCH_DELETED"
