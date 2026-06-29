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
        patch("specify_cli.status.fire_dossier_sync"),
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
    """An explicit ``single_branch`` create skips the mint and stores
    topology == 'single_branch' with NO coordination_branch key.

    Re-pinned to the #2218 contract (WP03): topology is now the operator's
    EXPLICIT ``MissionTopology`` choice, not a value re-derived by
    ``classify_topology`` from a (possibly stubbed) mint outcome. A
    ``single_branch`` choice is coordination-flat, so ``ensure_coordination_branch``
    is never called and ``meta.json`` carries no ``coordination_branch`` key.
    The old form stubbed ``ensure_coordination_branch`` to return ``branch_name=None``
    (a non-production value) to coax classify into ``single_branch``; that path is
    retired."""
    from mission_runtime import MissionTopology

    _init_git_repo(tmp_path)
    with (
        _patched_context(tmp_path),
        patch(
            "specify_cli.missions._create.ensure_coordination_branch",
        ) as mint,
    ):
        create_mission_core(
            tmp_path,
            "topology-single",
            topology=MissionTopology.SINGLE_BRANCH,
            **_mission_summary("topology-single"),
        )

    meta = _read_meta(tmp_path)
    assert "coordination_branch" not in meta
    assert meta["topology"] == "single_branch"
    mint.assert_not_called()  # branch-flat shape: the mint is skipped entirely
    assert meta["flattened"] is False
