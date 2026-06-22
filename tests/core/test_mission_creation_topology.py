"""Regression tests for MissionTopology minting at creation (T011 / FR-002).

A fresh ``mission create`` has no ``lanes.json`` yet, so create-time
classification only ever yields ``COORD`` (coordination branch present) or
``SINGLE_BRANCH`` (no coordination branch). The lanes-bearing cells arise only
after finalize and are covered in the classifier + backfill tests.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.mission_creation import create_mission_core

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_CORE_MODULE = "specify_cli.core.mission_creation"


def _init_git_repo(repo: Path) -> None:
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=repo, capture_output=True, check=True)


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").strip() or "test mission"
    return {
        "friendly_name": title.title(),
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (
            f"This mission delivers {title} so product and engineering can move "
            "forward with a clear outcome and shared understanding."
        ),
    }


@contextmanager
def _patched_context(tmp_path: Path):
    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch("specify_cli.sync.dossier_pipeline.trigger_feature_dossier_sync_if_enabled"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        yield


def _read_meta(tmp_path: Path) -> dict[str, object]:
    mission_dir = next((tmp_path / "kitty-specs").iterdir())
    return json.loads((mission_dir / "meta.json").read_text(encoding="utf-8"))


def test_coord_create_mints_coord_topology(tmp_path: Path) -> None:
    """A normal create (coordination branch minted) stores topology == 'coord'."""
    _init_git_repo(tmp_path)
    with _patched_context(tmp_path):
        create_mission_core(tmp_path, "topology-coord", **_mission_summary("topology-coord"))

    meta = _read_meta(tmp_path)
    assert meta["coordination_branch"]  # coordination branch present
    assert meta["topology"] == "coord"
    assert meta["flattened"] is False


def test_no_coord_create_mints_single_branch(tmp_path: Path) -> None:
    """When no coordination branch is minted, topology == 'single_branch'."""
    from specify_cli.missions._create import CoordinationBranchResult

    _init_git_repo(tmp_path)
    # Simulate a create that does not materialise a coordination branch: the
    # branch ref is absent, so classify_topology sees no coord and yields
    # SINGLE_BRANCH (the second create-reachable cell).
    no_coord = CoordinationBranchResult(
        branch_name=None,  # type: ignore[arg-type]  # exercises the no-coord create cell
        created=False,
        skipped_reason="target_branch missing",
    )

    with (
        _patched_context(tmp_path),
        patch(
            "specify_cli.missions._create.ensure_coordination_branch",
            return_value=no_coord,
        ),
    ):
        create_mission_core(tmp_path, "topology-single", **_mission_summary("topology-single"))

    meta = _read_meta(tmp_path)
    assert meta["coordination_branch"] is None
    assert meta["topology"] == "single_branch"
    assert meta["flattened"] is False
