"""Acceptance parity tests for WP03: Unify Acceptance Logic.

These tests verify that acceptance behaviour is identical across:
- ``specify_cli.acceptance`` (installed-package CLI entrypoint)
- ``specify_cli.scripts.tasks.acceptance_support`` (standalone script entrypoint)
- ``specify_cli.core.acceptance_core`` (shared core)

They also confirm correct worktree/repo-root detection and output contract
stability.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

import pytest

# Script-path imports (tests/conftest.py adds scripts/tasks to sys.path)
import acceptance_support as script_acc
import task_helpers as th

# Installed-package imports
from specify_cli.acceptance import (
    AcceptanceError as PkgAcceptanceError,
    AcceptanceSummary as PkgAcceptanceSummary,
    collect_feature_summary as pkg_collect_feature_summary,
    choose_mode as pkg_choose_mode,
    detect_feature_slug as pkg_detect_feature_slug,
    perform_acceptance as pkg_perform_acceptance,
)
from specify_cli.core.acceptance_core import (
    AcceptanceError as CoreAcceptanceError,
    AcceptanceSummary as CoreAcceptanceSummary,
    collect_feature_summary as core_collect_feature_summary,
    choose_mode as core_choose_mode,
    perform_acceptance as core_perform_acceptance,
)
from tests.utils import run, run_tasks_cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summary_dict_without_volatile(summary_dict: Dict) -> Dict:
    """Strip fields that may differ due to environment (e.g. repo paths).

    We keep structural/semantic fields and normalise path fields to basename.
    """
    d = dict(summary_dict)
    for key in (
        "repo_root",
        "feature_dir",
        "tasks_dir",
        "worktree_root",
        "primary_repo_root",
    ):
        if key in d:
            d[key] = Path(d[key]).name
    return d


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def acceptance_repo(feature_repo: Path, feature_slug: str) -> tuple[Path, str]:
    """A repo with a single WP moved through to 'done'."""
    run_tasks_cli(
        ["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo
    )
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)
    run_tasks_cli(
        ["update", feature_slug, "WP01", "done", "--force"], cwd=feature_repo
    )
    run(["git", "commit", "-am", "Update to done"], cwd=feature_repo)
    return feature_repo, feature_slug


@pytest.fixture()
def acceptance_repo_not_done(
    feature_repo: Path, feature_slug: str
) -> tuple[Path, str]:
    """A repo with a WP still in 'doing' (acceptance checks should flag it)."""
    run_tasks_cli(
        ["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo
    )
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)
    return feature_repo, feature_slug


# ---------------------------------------------------------------------------
# Parity: collect_feature_summary
# ---------------------------------------------------------------------------


class TestCollectFeatureSummaryParity:
    """Verify that all three entrypoints produce structurally identical summaries."""

    def test_summary_fields_match_when_done(
        self, acceptance_repo: tuple[Path, str]
    ) -> None:
        repo_root, feature = acceptance_repo

        core_summary = core_collect_feature_summary(repo_root, feature)
        pkg_summary = pkg_collect_feature_summary(repo_root, feature)
        script_summary = script_acc.collect_feature_summary(repo_root, feature)

        core_dict = _summary_dict_without_volatile(core_summary.to_dict())
        pkg_dict = _summary_dict_without_volatile(pkg_summary.to_dict())
        script_dict = _summary_dict_without_volatile(script_summary.to_dict())

        # Core and script should be identical (both use acceptance_core)
        assert core_dict == script_dict, "Core and script summaries diverge"

        # Package may add path_violations; but by default they should be empty
        assert core_dict == pkg_dict, "Core and package summaries diverge"

    def test_summary_fields_match_when_not_done(
        self, acceptance_repo_not_done: tuple[Path, str]
    ) -> None:
        repo_root, feature = acceptance_repo_not_done

        core_summary = core_collect_feature_summary(repo_root, feature)
        script_summary = script_acc.collect_feature_summary(repo_root, feature)

        core_dict = _summary_dict_without_volatile(core_summary.to_dict())
        script_dict = _summary_dict_without_volatile(script_summary.to_dict())

        assert core_dict == script_dict

    def test_ok_and_all_done_consistent(
        self, acceptance_repo: tuple[Path, str]
    ) -> None:
        repo_root, feature = acceptance_repo

        core_summary = core_collect_feature_summary(
            repo_root, feature, strict_metadata=True
        )
        script_summary = script_acc.collect_feature_summary(
            repo_root, feature, strict_metadata=True
        )

        assert core_summary.ok == script_summary.ok
        assert core_summary.all_done == script_summary.all_done

    def test_outstanding_consistent(
        self, acceptance_repo_not_done: tuple[Path, str]
    ) -> None:
        repo_root, feature = acceptance_repo_not_done

        core_summary = core_collect_feature_summary(repo_root, feature)
        script_summary = script_acc.collect_feature_summary(repo_root, feature)

        assert core_summary.outstanding() == script_summary.outstanding()

    def test_lenient_metadata_parity(
        self, acceptance_repo: tuple[Path, str]
    ) -> None:
        """strict_metadata=False should produce identical results across entrypoints."""
        repo_root, feature = acceptance_repo

        core_summary = core_collect_feature_summary(
            repo_root, feature, strict_metadata=False
        )
        script_summary = script_acc.collect_feature_summary(
            repo_root, feature, strict_metadata=False
        )

        assert core_summary.metadata_issues == script_summary.metadata_issues == []


# ---------------------------------------------------------------------------
# Parity: choose_mode
# ---------------------------------------------------------------------------


class TestChooseModeParity:

    def test_explicit_modes(self, feature_repo: Path) -> None:
        for mode in ("pr", "local", "checklist"):
            assert (
                core_choose_mode(mode, feature_repo)
                == script_acc.choose_mode(mode, feature_repo)
            )
            assert (
                core_choose_mode(mode, feature_repo)
                == pkg_choose_mode(mode, feature_repo)
            )

    def test_auto_mode(self, feature_repo: Path) -> None:
        core_result = core_choose_mode(None, feature_repo)
        script_result = script_acc.choose_mode(None, feature_repo)
        pkg_result = pkg_choose_mode(None, feature_repo)
        assert core_result == script_result == pkg_result


# ---------------------------------------------------------------------------
# Parity: perform_acceptance
# ---------------------------------------------------------------------------


class TestPerformAcceptanceParity:

    def test_checklist_mode_result_matches(
        self, acceptance_repo: tuple[Path, str]
    ) -> None:
        repo_root, feature = acceptance_repo

        core_summary = core_collect_feature_summary(repo_root, feature)
        script_summary = script_acc.collect_feature_summary(repo_root, feature)

        core_result = core_perform_acceptance(
            core_summary, mode="checklist", actor="Tester", auto_commit=False
        )
        script_result = script_acc.perform_acceptance(
            script_summary, mode="checklist", actor="Tester", auto_commit=False
        )

        core_dict = core_result.to_dict()
        script_dict = script_result.to_dict()

        assert core_dict["accepted_by"] == script_dict["accepted_by"]
        assert core_dict["mode"] == script_dict["mode"]
        assert core_dict["commit_created"] == script_dict["commit_created"]
        assert core_dict["instructions"] == script_dict["instructions"]
        assert core_dict["cleanup_instructions"] == script_dict["cleanup_instructions"]

    def test_acceptance_json_contract_fields(
        self, acceptance_repo: tuple[Path, str]
    ) -> None:
        """Verify the output contract defined in the WP03 spec."""
        repo_root, feature = acceptance_repo

        summary = core_collect_feature_summary(repo_root, feature)
        result = core_perform_acceptance(
            summary, mode="checklist", actor="Tester", auto_commit=False
        )
        payload = result.to_dict()

        # Top-level result fields
        expected_top_keys = {
            "accepted_at",
            "accepted_by",
            "mode",
            "parent_commit",
            "accept_commit",
            "commit_created",
            "instructions",
            "cleanup_instructions",
            "notes",
            "summary",
        }
        assert set(payload.keys()) == expected_top_keys

        # Summary fields
        summary_dict = payload["summary"]
        expected_summary_keys = {
            "feature",
            "branch",
            "repo_root",
            "feature_dir",
            "tasks_dir",
            "worktree_root",
            "primary_repo_root",
            "lanes",
            "work_packages",
            "metadata_issues",
            "activity_issues",
            "unchecked_tasks",
            "needs_clarification",
            "missing_artifacts",
            "optional_missing",
            "git_dirty",
            "path_violations",
            "warnings",
            "all_done",
            "ok",
        }
        assert set(summary_dict.keys()) == expected_summary_keys

    def test_not_ok_raises_acceptance_error(
        self, acceptance_repo_not_done: tuple[Path, str]
    ) -> None:
        """Both entrypoints should raise AcceptanceError when not ok."""
        repo_root, feature = acceptance_repo_not_done

        core_summary = core_collect_feature_summary(repo_root, feature)
        script_summary = script_acc.collect_feature_summary(repo_root, feature)

        with pytest.raises(CoreAcceptanceError):
            core_perform_acceptance(
                core_summary, mode="pr", actor="Tester", auto_commit=False
            )

        with pytest.raises(script_acc.AcceptanceError):
            script_acc.perform_acceptance(
                script_summary, mode="pr", actor="Tester", auto_commit=False
            )


# ---------------------------------------------------------------------------
# Parity: detect_feature_slug
# ---------------------------------------------------------------------------


class TestDetectFeatureSlugParity:

    def test_env_detection_with_existing_feature(
        self, feature_repo: Path, feature_slug: str
    ) -> None:
        """Both entrypoints should honour SPECIFY_FEATURE with a valid feature."""
        env = {"SPECIFY_FEATURE": feature_slug}
        script_result = script_acc.detect_feature_slug(feature_repo, env=env)
        pkg_result = pkg_detect_feature_slug(feature_repo, env=env)
        assert script_result == pkg_result == feature_slug

    def test_script_detect_accepts_nonexistent_feature_slug(
        self, feature_repo: Path
    ) -> None:
        """Script entrypoint trusts env var without validating existence."""
        env = {"SPECIFY_FEATURE": "999-nonexistent"}
        result = script_acc.detect_feature_slug(feature_repo, env=env)
        assert result == "999-nonexistent"

    def test_pkg_detect_validates_feature_existence(
        self, feature_repo: Path
    ) -> None:
        """Package entrypoint (centralized) validates the feature directory exists."""
        env = {"SPECIFY_FEATURE": "999-nonexistent"}
        with pytest.raises(PkgAcceptanceError):
            pkg_detect_feature_slug(feature_repo, env=env)

    def test_branch_detection_parity(
        self, feature_repo: Path, feature_slug: str
    ) -> None:
        """Both entrypoints should detect from git branch."""
        cwd_before = Path.cwd()
        os.chdir(feature_repo)
        try:
            th.run_git(
                ["checkout", "-b", feature_slug], cwd=feature_repo
            )
            env_no_feature: dict[str, str] = {
                k: v for k, v in os.environ.items() if k != "SPECIFY_FEATURE"
            }
            script_result = script_acc.detect_feature_slug(
                feature_repo, env=env_no_feature
            )
            assert script_result == feature_slug
        finally:
            os.chdir(cwd_before)


# ---------------------------------------------------------------------------
# Parity: find_repo_root across helpers
# ---------------------------------------------------------------------------


class TestFindRepoRootParity:

    def test_same_root_from_task_helpers_and_core(
        self, feature_repo: Path
    ) -> None:
        """task_helpers_shared.find_repo_root is the single implementation for all."""
        from specify_cli.task_helpers_shared import find_repo_root as shared_find
        from specify_cli.tasks_support import find_repo_root as support_find

        # Both tasks_support and task_helpers_shared expose the same function.
        assert support_find is shared_find

    def test_find_repo_root_from_worktree(
        self, feature_repo: Path, feature_slug: str
    ) -> None:
        """find_repo_root returns the main repo root even from a worktree."""
        branch_name = f"{feature_slug}-WP01"
        worktree_dir = feature_repo / ".worktrees" / branch_name
        worktree_dir.parent.mkdir(parents=True, exist_ok=True)
        run(
            ["git", "worktree", "add", str(worktree_dir), "-b", branch_name],
            cwd=feature_repo,
        )

        from specify_cli.task_helpers_shared import find_repo_root as shared_find

        main_root = shared_find(worktree_dir)
        assert main_root == feature_repo

    def test_find_repo_root_integration_both_paths(
        self, feature_repo: Path, feature_slug: str
    ) -> None:
        """Calling find_repo_root via task_helpers and acceptance helpers
        from a worktree returns the same primary repo root."""
        branch_name = f"{feature_slug}-WP01"
        worktree_dir = feature_repo / ".worktrees" / branch_name
        worktree_dir.parent.mkdir(parents=True, exist_ok=True)
        run(
            ["git", "worktree", "add", str(worktree_dir), "-b", branch_name],
            cwd=feature_repo,
        )

        # Via task_helpers (script path)
        task_root = th.find_repo_root(worktree_dir)

        # Via tasks_support (package path, re-exports from task_helpers_shared)
        from specify_cli.tasks_support import find_repo_root as support_find
        support_root = support_find(worktree_dir)

        assert task_root == support_root == feature_repo


# ---------------------------------------------------------------------------
# Documentation vs non-documentation mission parity
# ---------------------------------------------------------------------------


class TestMissionAwareParity:

    def test_non_doc_mission_skips_path_violations(
        self, acceptance_repo: tuple[Path, str]
    ) -> None:
        """For a non-documentation mission, path_violations should be empty."""
        repo_root, feature = acceptance_repo

        core_summary = core_collect_feature_summary(repo_root, feature)
        assert core_summary.path_violations == []

        # Package version should also have empty path_violations for non-doc
        pkg_summary = pkg_collect_feature_summary(repo_root, feature)
        assert pkg_summary.path_violations == []

    def test_path_violations_in_to_dict(
        self, acceptance_repo: tuple[Path, str]
    ) -> None:
        """Verify path_violations appears in to_dict output even when empty."""
        repo_root, feature = acceptance_repo

        core_summary = core_collect_feature_summary(repo_root, feature)
        d = core_summary.to_dict()
        assert "path_violations" in d
        assert d["path_violations"] == []

    def test_doc_mission_skipped_for_non_doc(
        self, acceptance_repo: tuple[Path, str]
    ) -> None:
        """Core module never adds path_violations; only pkg does (and only
        when a mission has path constraints)."""
        repo_root, feature = acceptance_repo

        core_summary = core_collect_feature_summary(repo_root, feature)
        pkg_summary = pkg_collect_feature_summary(repo_root, feature)

        # Both should have empty path_violations for a feature without
        # mission-specific path constraints
        assert core_summary.path_violations == pkg_summary.path_violations == []


# ---------------------------------------------------------------------------
# Encoding error parity
# ---------------------------------------------------------------------------


class TestEncodingErrorParity:

    def test_artifact_encoding_error_type_shared(self) -> None:
        """ArtifactEncodingError should be the same class from core."""
        from specify_cli.core.acceptance_core import (
            ArtifactEncodingError as CoreAEE,
        )

        assert script_acc.ArtifactEncodingError is CoreAEE
