"""Characterization tests for the #2139 target_branch reconcile (FR-008, WP05).

``read_target_branch_from_meta`` (``core/paths.py``) is the single authority
for the field-absent-vs-corrupt distinction on ``meta.json``'s
``target_branch`` key (see ``tests/specify_cli/core/test_target_branch_primitive.py``
for the primitive's own contract tests). This file characterizes the ROUTED
call sites this WP touches: for a ``meta.json`` missing ``target_branch``,
each site must now exhibit its own *documented* fallback (primary branch,
current branch, or ``None``) rather than the pre-fix hardcoded ``"main"`` /
``""`` silent default.

Repro discriminator: every fixture repo is checked out on a branch that is
deliberately NOT ``"main"`` (``trunk-integration``), so a stray hardcoded
``"main"`` literal is caught by assertion rather than passing by coincidence.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.acceptance import _target_branch_for_feature
from specify_cli.cli.commands.agent.mission_branch_context import (
    _resolve_feature_target_branch,
)
from specify_cli.context.resolver import _read_meta_json
from specify_cli.retrospective.generator import generate_retrospective
from specify_cli.retrospective.policy import default_policy

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

NON_MAIN_BRANCH = "trunk-integration"


def _init_repo_on_branch(repo_root: Path, branch: str) -> None:
    """Initialize a throwaway git repo checked out on a non-``main`` branch.

    No ``origin`` remote is configured, so ``resolve_primary_branch``'s
    method 1 (origin/HEAD) is unavailable and it falls through to method 2
    (current branch) -- exactly the discriminator this file needs.
    """
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo_root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True)
    (repo_root / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo_root, check=True)


def _write_meta_without_target_branch(feature_dir: Path, mission_slug: str) -> None:
    """Write a realistic meta.json with target_branch deliberately absent."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "mission_id": "01TESTRECONCILE00000000TB",
        "mission_slug": mission_slug,
        "friendly_name": "Reconcile Fixture Mission",
        "mission_type": "software-dev",
        "created_at": "2026-07-08T00:00:00+00:00",
        # target_branch deliberately absent -- this is the case the pre-fix
        # code paths handled with a divergent silent default at each site.
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


class TestContextResolverReadMetaJson:
    """``context/resolver.py::_read_meta_json`` -- routed at T021 (line 82)."""

    def test_absent_target_branch_resolves_primary_branch_not_hardcoded_main(
        self, tmp_path: Path
    ) -> None:
        _init_repo_on_branch(tmp_path, NON_MAIN_BRANCH)
        feature_dir = tmp_path / "kitty-specs" / "reconcile-resolver"
        _write_meta_without_target_branch(feature_dir, "reconcile-resolver")

        meta = _read_meta_json(feature_dir, tmp_path)

        assert meta["target_branch"] == NON_MAIN_BRANCH
        assert meta["target_branch"] != "main"


class TestMissionBranchContextResolver:
    """``mission_branch_context.py::_resolve_feature_target_branch`` -- T021 (line 63)."""

    def test_absent_target_branch_falls_back_to_current_branch_not_empty_string(
        self, tmp_path: Path
    ) -> None:
        _init_repo_on_branch(tmp_path, NON_MAIN_BRANCH)
        feature_dir = tmp_path / "kitty-specs" / "reconcile-branch-context"
        _write_meta_without_target_branch(feature_dir, "reconcile-branch-context")

        result = _resolve_feature_target_branch(feature_dir, tmp_path)

        assert result == NON_MAIN_BRANCH
        assert result != ""


class TestAcceptanceTargetBranchForFeature:
    """``acceptance/__init__.py::_target_branch_for_feature`` -- routes T021's
    two call sites (former lines 1075 and 1696).
    """

    def test_absent_target_branch_returns_none_not_empty_string(
        self, tmp_path: Path
    ) -> None:
        feature_dir = tmp_path / "kitty-specs" / "reconcile-acceptance"
        _write_meta_without_target_branch(feature_dir, "reconcile-acceptance")

        result = _target_branch_for_feature(feature_dir)

        assert result is None
        assert result != ""


class TestGeneratorTargetBranch:
    """``retrospective/generator.py::generate_retrospective`` -- T021 (line 1263)."""

    def test_absent_target_branch_resolves_primary_branch_not_hardcoded_main(
        self, tmp_path: Path
    ) -> None:
        _init_repo_on_branch(tmp_path, NON_MAIN_BRANCH)
        mission_slug = "reconcile-generator"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        _write_meta_without_target_branch(feature_dir, mission_slug)

        record = generate_retrospective(mission_slug, default_policy(), tmp_path)

        assert record.target_branch == NON_MAIN_BRANCH
        assert record.target_branch != "main"
