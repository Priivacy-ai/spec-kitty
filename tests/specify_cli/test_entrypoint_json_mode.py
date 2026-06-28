"""Tests for entrypoint-level JSON-mode detection."""

from __future__ import annotations

import pytest

import specify_cli

pytestmark = [pytest.mark.fast]


def test_argv_requests_json_mode_detects_json_flag() -> None:
    argv = ["spec-kitty", "agent", "mission", "finalize-tasks", "--mission", "001-x", "--json"]

    assert specify_cli._argv_requests_json_mode(argv) is True


def test_argv_requests_json_mode_ignores_json_as_option_value() -> None:
    argv = ["spec-kitty", "tracker", "search", "--provider", "linear", "--query", "--json"]

    assert specify_cli._argv_requests_json_mode(argv) is False


def test_argv_requests_json_mode_detects_second_json_after_value() -> None:
    argv = [
        "spec-kitty",
        "tracker",
        "search",
        "--provider",
        "linear",
        "--query",
        "--json",
        "--json",
    ]

    assert specify_cli._argv_requests_json_mode(argv) is True
