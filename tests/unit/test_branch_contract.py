"""Tests for branch-specific contract gating helpers."""

from __future__ import annotations

import pytest

from tests.branch_contract import _is_2x_context


# ---------------------------------------------------------------------------
# Existing name-based detection tests
# ---------------------------------------------------------------------------


def test_is_2x_context_matches_literal_2x_branch() -> None:
    assert _is_2x_context("2.x")


def test_is_2x_context_matches_codex_prefixed_2x_branch() -> None:
    assert _is_2x_context("codex/2x-adr-docs-versioning")


def test_is_2x_context_matches_pr_base_ref() -> None:
    assert _is_2x_context(
        "feature/some-work",
        github_base_ref="2.x",
    )


def test_is_2x_context_matches_github_ref_name() -> None:
    assert _is_2x_context("main", github_ref_name="2.x")


def test_is_2x_context_false_for_non_2x_branch() -> None:
    assert not _is_2x_context("main")


def test_is_2x_context_false_for_unrelated_feature_branch() -> None:
    assert not _is_2x_context("feature/add-logging")


@pytest.mark.parametrize("branch,expected", [
    ("2.x", True),
    ("2.x-some-suffix", True),
    ("2.x/sub-branch", True),
    ("codex/2x-some-feature", True),
    ("codex/2.x-some-feature", True),
    ("main", False),
    ("feature/add-logging", False),
    ("copilot/remediate-unit-cli-ruff-errors", False),
])
def test_is_2x_context_name_patterns(branch: str, expected: bool) -> None:
    """Parametrised name-only detection (no ancestry flag, no CI env vars)."""
    assert _is_2x_context(branch) == expected

