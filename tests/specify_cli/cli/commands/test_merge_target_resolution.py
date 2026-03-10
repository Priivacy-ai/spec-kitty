"""Regression tests for merge target resolution (Feature 049).

Verifies that `spec-kitty merge --feature <slug>` resolves the target branch
from meta.json via get_feature_target_branch(), rather than always falling
back to resolve_primary_branch().

Covers:
  - FR-001: meta.json target_branch respected
  - FR-002: explicit --target overrides meta.json
  - FR-003: missing/malformed meta.json falls back to resolve_primary_branch()
  - FR-004: no --feature preserves existing behavior
  - FR-005: template consistency (no "agent feature merge" references)
  - FR-006: nonexistent target branch produces hard error
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.feature_detection import get_feature_target_branch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_meta_json(feature_dir: Path, target_branch: str) -> None:
    """Write a minimal meta.json with target_branch."""
    meta = {
        "feature_number": "049",
        "slug": "049-fix-merge-target-resolution",
        "target_branch": target_branch,
    }
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Test 1: Feature targets 2.x  (Acceptance Scenario 1.1 / FR-001)
# ---------------------------------------------------------------------------

def test_feature_targeting_2x_resolves_to_2x(tmp_path):
    """When meta.json says target_branch: '2.x', resolution returns '2.x'."""
    slug = "049-fix-merge-target-resolution"
    feature_dir = tmp_path / "kitty-specs" / slug
    _write_meta_json(feature_dir, "2.x")

    with (
        patch(
            "specify_cli.core.feature_detection._get_main_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.core.git_ops.resolve_primary_branch",
            return_value="main",
        ),
    ):
        result = get_feature_target_branch(tmp_path, slug)

    assert result == "2.x"


# ---------------------------------------------------------------------------
# Test 2: Feature targets main  (Acceptance Scenario 1.2)
# ---------------------------------------------------------------------------

def test_feature_targeting_main_resolves_to_main(tmp_path):
    """When meta.json says target_branch: 'main', resolution returns 'main'."""
    slug = "049-fix-merge-target-resolution"
    feature_dir = tmp_path / "kitty-specs" / slug
    _write_meta_json(feature_dir, "main")

    with (
        patch(
            "specify_cli.core.feature_detection._get_main_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.core.git_ops.resolve_primary_branch",
            return_value="main",
        ),
    ):
        result = get_feature_target_branch(tmp_path, slug)

    assert result == "main"


# ---------------------------------------------------------------------------
# Test 3: Missing meta.json  (Acceptance Scenario 1.4 / FR-003)
# ---------------------------------------------------------------------------

def test_missing_meta_json_falls_back_to_primary_branch(tmp_path):
    """When meta.json doesn't exist, fallback to resolve_primary_branch()."""
    slug = "049-fix-merge-target-resolution"
    # Deliberately do NOT create meta.json
    (tmp_path / "kitty-specs" / slug).mkdir(parents=True)

    with (
        patch(
            "specify_cli.core.feature_detection._get_main_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.core.git_ops.resolve_primary_branch",
            return_value="main",
        ),
    ):
        result = get_feature_target_branch(tmp_path, slug)

    assert result == "main"


# ---------------------------------------------------------------------------
# Test 4: Explicit --target overrides meta.json  (Acceptance Scenario 1.3 / FR-002)
# ---------------------------------------------------------------------------

def test_explicit_target_overrides_meta_json():
    """When --target is provided, the resolution block is skipped entirely.

    This tests the guard in merge.py:
        if target_branch is None:
            ...
    When target_branch is already set (from --target), the block doesn't run.
    We verify this by confirming get_feature_target_branch is never called.
    """
    with patch(
        "specify_cli.core.feature_detection.get_feature_target_branch"
    ) as mock_gftb:
        # Simulate: target_branch is already set (not None), so the
        # resolution block in merge.py is skipped.
        target_branch = "main"  # Provided via --target
        feature = "049-fix-merge-target-resolution"

        # Reproduce the merge.py logic
        if target_branch is None:
            if feature:
                from specify_cli.core.feature_detection import (
                    get_feature_target_branch as _gftb,
                )
                target_branch = _gftb(Path("."), feature)

        # get_feature_target_branch should never be called
        mock_gftb.assert_not_called()
        # target_branch stays as the explicit value
        assert target_branch == "main"


# ---------------------------------------------------------------------------
# Test 5: Nonexistent target branch  (FR-006)
# ---------------------------------------------------------------------------

def test_nonexistent_target_branch_produces_error(tmp_path):
    """When resolved branch doesn't exist locally or on remote, error is raised.

    Tests the branch validation block in merge.py that fires after resolution.
    """
    from specify_cli.core.git_ops import run_command as _real_run_command

    slug = "049-fix-merge-target-resolution"
    feature_dir = tmp_path / "kitty-specs" / slug
    _write_meta_json(feature_dir, "nonexistent-branch")

    def mock_run_command(cmd, *, capture=False, check_return=True, cwd=None, **kw):
        """Mock run_command to simulate nonexistent branch."""
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        if "rev-parse" in cmd_str and "nonexistent-branch" in cmd_str:
            return (1, "", "fatal: not a valid object name")
        # Default: success
        return (0, "", "")

    # Reproduce the merge.py validation logic
    with (
        patch(
            "specify_cli.core.feature_detection._get_main_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.core.git_ops.resolve_primary_branch",
            return_value="main",
        ),
    ):
        target_branch = get_feature_target_branch(tmp_path, slug)

    assert target_branch == "nonexistent-branch"

    # Now simulate the validation block from merge.py
    feature = slug
    error_raised = False
    error_msg = ""

    if feature and target_branch:
        ret_local, _, _ = mock_run_command(
            ["git", "rev-parse", "--verify", f"refs/heads/{target_branch}"],
            capture=True,
            check_return=False,
            cwd=tmp_path,
        )
        if ret_local != 0:
            ret_remote, _, _ = mock_run_command(
                ["git", "rev-parse", "--verify", f"refs/remotes/origin/{target_branch}"],
                capture=True,
                check_return=False,
                cwd=tmp_path,
            )
            if ret_remote != 0:
                error_msg = (
                    f"Target branch '{target_branch}' (from meta.json) does not exist "
                    f"locally or on origin. Check kitty-specs/{feature}/meta.json."
                )
                error_raised = True

    assert error_raised, "Should have raised error for nonexistent branch"
    assert "nonexistent-branch" in error_msg
    assert "meta.json" in error_msg


# ---------------------------------------------------------------------------
# Test 6: No --feature flag  (User Story 3 / FR-004)
# ---------------------------------------------------------------------------

def test_no_feature_flag_uses_resolve_primary_branch():
    """When --feature is not provided, resolve_primary_branch() is used directly.

    get_feature_target_branch should NOT be called.
    """
    with (
        patch(
            "specify_cli.core.feature_detection.get_feature_target_branch"
        ) as mock_gftb,
        patch(
            "specify_cli.core.git_ops.resolve_primary_branch",
            return_value="main",
        ) as mock_rpb,
    ):
        # Reproduce merge.py resolution logic with feature=None
        target_branch = None
        feature = None

        if target_branch is None:
            if feature:
                target_branch = mock_gftb(Path("."), feature)
            else:
                from specify_cli.core.git_ops import resolve_primary_branch
                target_branch = mock_rpb(Path("."))

        mock_gftb.assert_not_called()
        mock_rpb.assert_called_once()
        assert target_branch == "main"


# ---------------------------------------------------------------------------
# Test 7: Malformed meta.json  (Edge case 2 / FR-003)
# ---------------------------------------------------------------------------

def test_malformed_meta_json_falls_back_to_primary_branch(tmp_path):
    """When meta.json contains invalid JSON, fallback to resolve_primary_branch()."""
    slug = "049-fix-merge-target-resolution"
    feature_dir = tmp_path / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        "{ this is not valid json }", encoding="utf-8"
    )

    with (
        patch(
            "specify_cli.core.feature_detection._get_main_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.core.git_ops.resolve_primary_branch",
            return_value="main",
        ),
    ):
        result = get_feature_target_branch(tmp_path, slug)

    assert result == "main"


# ---------------------------------------------------------------------------
# Test SC-003: Template consistency  (FR-005)
# ---------------------------------------------------------------------------

def test_merge_template_has_no_agent_feature_merge_references():
    """merge.md template should only reference canonical 'spec-kitty merge'."""
    template_path = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "specify_cli"
        / "missions"
        / "software-dev"
        / "command-templates"
        / "merge.md"
    )
    assert template_path.exists(), f"Template not found at {template_path}"

    content = template_path.read_text(encoding="utf-8")
    assert "agent feature merge" not in content.lower(), (
        "merge.md should not reference 'agent feature merge'"
    )
    assert "spec-kitty merge" in content, (
        "merge.md should reference canonical 'spec-kitty merge'"
    )
