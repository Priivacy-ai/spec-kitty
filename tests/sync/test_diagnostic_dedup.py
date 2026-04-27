"""Unit tests for the in-process diagnostic dedup + atexit success-flag.

Covers ``specify_cli.diagnostics.dedup`` (FR-008 / FR-009 / WP06).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from specify_cli.diagnostics import (
    invocation_succeeded,
    mark_invocation_succeeded,
    report_once,
    reset_for_invocation,
)


@pytest.fixture(autouse=True)
def _isolate_diagnostic_state() -> Iterator[None]:
    """Reset dedup + success-flag state before and after each test."""
    reset_for_invocation()
    yield
    reset_for_invocation()


def test_report_once_returns_true_first_time_then_false() -> None:
    """A given cause key fires exactly once per invocation."""
    assert report_once("test.cause") is True
    assert report_once("test.cause") is False
    assert report_once("test.cause") is False


def test_report_once_distinct_keys_independent() -> None:
    """Distinct cause keys do not share dedup state with each other."""
    assert report_once("test.cause.a") is True
    assert report_once("test.cause.b") is True
    assert report_once("test.cause.a") is False
    assert report_once("test.cause.b") is False


def test_reset_for_invocation_clears_dedup_state() -> None:
    """``reset_for_invocation`` clears the ContextVar so causes can fire again."""
    assert report_once("test.cause") is True
    reset_for_invocation()
    assert report_once("test.cause") is True


def test_invocation_success_flag_lifecycle() -> None:
    """The success flag starts False, flips on mark, and resets on reset."""
    assert invocation_succeeded() is False
    mark_invocation_succeeded()
    assert invocation_succeeded() is True
    reset_for_invocation()
    assert invocation_succeeded() is False
