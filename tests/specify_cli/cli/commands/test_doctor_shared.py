"""Focused tests for the ``_doctor_shared`` infrastructure module (WP02, #2059).

Covers the single-Console invariant (H1, I-3), the ``--json`` output guard,
the ``_json_error`` envelope shape, and the env-gated branches of
``_is_interactive_environment``.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from specify_cli.cli.commands import _doctor_shared

pytestmark = [pytest.mark.fast]


def test_console_is_single_shared_instance_across_import_sites() -> None:
    # H1/I-3: exactly one Console() backs the whole doctor surface. The shim,
    # the render module, and _doctor_shared must all resolve to the SAME object.
    from specify_cli.cli.commands._profile_health_render import (
        console as render_console,
    )
    from specify_cli.cli.commands.doctor import console as doctor_console

    assert _doctor_shared.console is render_console
    assert _doctor_shared.console is doctor_console


def test_json_error_envelope_shape() -> None:
    envelope = _doctor_shared._json_error("NOT_IN_PROJECT", "Not here")
    assert envelope == {
        "ok": False,
        "error": {"code": "NOT_IN_PROJECT", "message": "Not here"},
    }


def test_json_output_guard_disabled_is_passthrough() -> None:
    previous = logging.root.manager.disable
    with _doctor_shared._json_output_guard(False):
        # When disabled, logging is untouched.
        assert logging.root.manager.disable == previous
    assert logging.root.manager.disable == previous


def test_json_output_guard_enabled_suppresses_logging_then_restores() -> None:
    previous = logging.root.manager.disable
    with _doctor_shared._json_output_guard(True):
        # While active, logging is disabled up to CRITICAL.
        assert logging.root.manager.disable == logging.CRITICAL
    # Restored to the prior level on exit.
    assert logging.root.manager.disable == previous


def test_json_output_guard_restores_on_exception() -> None:
    previous = logging.root.manager.disable
    with pytest.raises(RuntimeError), _doctor_shared._json_output_guard(True):
        raise RuntimeError("boom")
    assert logging.root.manager.disable == previous


def test_is_interactive_environment_false_when_not_a_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_doctor_shared.sys.stdin, "isatty", lambda: False)
    for var in _doctor_shared._CI_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    assert _doctor_shared._is_interactive_environment() is False


def test_is_interactive_environment_true_when_tty_and_no_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_doctor_shared.sys.stdin, "isatty", lambda: True)
    for var in _doctor_shared._CI_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    assert _doctor_shared._is_interactive_environment() is True


@pytest.mark.parametrize("ci_value", ["true", "1", "yes", "TRUE", "Yes"])
def test_is_interactive_environment_false_under_ci(
    monkeypatch: pytest.MonkeyPatch, ci_value: str
) -> None:
    monkeypatch.setattr(_doctor_shared.sys.stdin, "isatty", lambda: True)
    for var in _doctor_shared._CI_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CI", ci_value)
    assert _doctor_shared._is_interactive_environment() is False


def test_constants_are_stable() -> None:
    assert _doctor_shared._STARTED_AT_COLUMN == "Started At"
    assert _doctor_shared._NOT_IN_PROJECT_MESSAGE == "Not in a spec-kitty project"
    assert "CI" in _doctor_shared._CI_ENV_VARS
    assert "GITHUB_ACTIONS" in _doctor_shared._CI_ENV_VARS


def test_doctor_shared_does_not_import_orchestrator_or_siblings() -> None:
    # One-way import graph (I-2): _doctor_shared must not pull in doctor.py or
    # any cluster sibling. Its module dependencies are stdlib + rich +
    # _profile_health_render only.
    import ast
    from pathlib import Path

    source = Path(_doctor_shared.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    absolute_imports: list[str] = []
    relative_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                relative_modules.append(node.module or "")
            elif node.module:
                absolute_imports.append(node.module)
        elif isinstance(node, ast.Import):
            absolute_imports.extend(alias.name for alias in node.names)
    forbidden = [
        m for m in absolute_imports if m.endswith("doctor") or m == "doctor"
    ]
    assert forbidden == []
    # The only relative import allowed is the console singleton home.
    assert relative_modules == ["_profile_health_render"]


def test_no_unexpected_public_symbols() -> None:
    expected: set[str] = {
        "console",
        "_CI_ENV_VARS",
        "_STARTED_AT_COLUMN",
        "_NOT_IN_PROJECT_MESSAGE",
        "_is_interactive_environment",
        "_json_output_guard",
        "_json_error",
    }
    declared: Any = set(_doctor_shared.__all__)
    assert declared == expected
