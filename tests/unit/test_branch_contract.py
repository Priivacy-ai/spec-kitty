"""Tests for branch-specific contract gating helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.branch_contract import _check_2x_ancestry, _is_2x_context


# ---------------------------------------------------------------------------
# Existing name-based detection tests
# ---------------------------------------------------------------------------


def test_is_2x_context_matches_literal_2x_branch() -> None:
    assert _is_2x_context("2.x")


def test_is_2x_context_matches_develop_branch() -> None:
    assert _is_2x_context("develop")


def test_is_2x_context_matches_codex_prefixed_2x_branch() -> None:
    assert _is_2x_context("codex/2x-adr-docs-versioning")


def test_is_2x_context_matches_pr_base_ref() -> None:
    assert _is_2x_context(
        "feature/some-work",
        github_base_ref="2.x",
    )


def test_is_2x_context_matches_github_ref_name() -> None:
    assert _is_2x_context("main", github_ref_name="develop")


def test_is_2x_context_false_for_non_2x_branch() -> None:
    assert not _is_2x_context("main")


def test_is_2x_context_false_for_unrelated_feature_branch() -> None:
    assert not _is_2x_context("feature/add-logging")


# ---------------------------------------------------------------------------
# New ancestry-fallback tests
# ---------------------------------------------------------------------------


def test_is_2x_context_with_ancestor_flag_returns_true() -> None:
    """Any branch with branch_is_2x_ancestor=True should be treated as 2.x."""
    assert _is_2x_context("copilot/remediate-unit-cli-ruff-errors", branch_is_2x_ancestor=True)


def test_is_2x_context_ancestor_false_for_non_2x_branch() -> None:
    """Non-2.x branch without ancestry flag stays False."""
    assert not _is_2x_context("main", branch_is_2x_ancestor=False)


def test_is_2x_context_ancestor_overrides_unmatched_name() -> None:
    """Arbitrary branch name becomes 2.x when ancestry flag is set."""
    assert _is_2x_context("fix/unrelated-hotfix", branch_is_2x_ancestor=True)


# ---------------------------------------------------------------------------
# _check_2x_ancestry helper tests
# ---------------------------------------------------------------------------


def test_check_2x_ancestry_returns_true_when_local_2x_is_ancestor(tmp_path) -> None:
    """Returns True when 'git merge-base --is-ancestor 2.x HEAD' succeeds."""
    with patch("tests.branch_contract.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        assert _check_2x_ancestry(tmp_path) is True
        # Should have been called with the local 2.x ref first
        first_call_args = mock_run.call_args_list[0].args[0]
        assert "2.x" in first_call_args
        assert "merge-base" in first_call_args


def test_check_2x_ancestry_falls_back_to_origin_when_local_missing(tmp_path) -> None:
    """Falls back to origin/2.x when the local 2.x ref is absent."""
    results = [
        type("R", (), {"returncode": 128})(),  # local 2.x → not found
        type("R", (), {"returncode": 0})(),    # origin/2.x → ancestor
    ]
    with patch("tests.branch_contract.subprocess.run", side_effect=results):
        assert _check_2x_ancestry(tmp_path) is True


def test_check_2x_ancestry_returns_false_when_no_ref_available(tmp_path) -> None:
    """Returns False gracefully when neither 2.x nor origin/2.x exists."""
    with patch("tests.branch_contract.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 128  # all refs missing
        assert _check_2x_ancestry(tmp_path) is False


@pytest.mark.parametrize("branch,expected", [
    ("2.x", True),
    ("develop", True),
    ("codex/2x-some-feature", True),
    ("codex/2.x-some-feature", True),
    ("feature/2.x-my-work", True),
    ("fix/2.x/edge-case", True),
    ("main", False),
    ("feature/add-logging", False),
    ("copilot/remediate-unit-cli-ruff-errors", False),   # name alone → False
])
def test_is_2x_context_name_patterns(branch: str, expected: bool) -> None:
    """Parametrised name-only detection (no ancestry flag, no CI env vars)."""
    assert _is_2x_context(branch) == expected

