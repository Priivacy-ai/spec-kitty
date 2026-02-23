"""Tests for branch-specific contract gating helpers."""

from __future__ import annotations

from tests.branch_contract import _is_2x_context


def test_is_2x_context_matches_literal_2x_branch() -> None:
    assert _is_2x_context("2.x")


def test_is_2x_context_matches_codex_prefixed_2x_branch() -> None:
    assert _is_2x_context("codex/2x-adr-docs-versioning")


def test_is_2x_context_matches_pr_base_ref() -> None:
    assert _is_2x_context(
        "feature/some-work",
        github_base_ref="2.x",
    )


def test_is_2x_context_false_for_non_2x_branch() -> None:
    assert not _is_2x_context("main")
