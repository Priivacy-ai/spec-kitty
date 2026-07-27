"""SC-002 end-to-end walkthrough (WP02 / T012).

Proves an operator on a legacy-bundle project (F2 — the mission's BC-2
trigger state) can reach an unblocked ``spec-kitty charter preflight`` using
**only** the commands the tool itself emits — no external knowledge, no
manual file edits — and records the step count, replacing the spec's
deliberately-unnumbered "bounded number of steps" (plan.md SC-002).

Kept in its own file (WP02's prompt explicitly sanctions "a new
fixture-driven test") rather than folded into ``test_computer.py``, which is
marked ``fast`` (pure-logic, no subprocess/git overhead per
``docs/context/testing-taxonomy.md`` and
``tests/architectural/test_pytest_marker_correctness.py`` Rule 2). This
walkthrough necessarily drives real git plumbing (via
``tests.specify_cli.charter_preflight._fixtures.init_git_repo``) and repeated
CLI invocations, so it carries ``integration`` + ``git_repo`` instead,
matching the sibling ``tests/specify_cli/charter_preflight/test_cli.py``
convention.

Uses Typer's in-process ``CliRunner`` (not a real ``spec-kitty`` subprocess)
for speed and to avoid PYTHONPATH/venv-resolution concerns — the commands
under test (``charter preflight`` / ``charter generate`` / ``charter
synthesize``) all live under the same ``charter_app``.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import cast

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app as charter_app

from tests.specify_cli.charter_preflight._fixtures import (
    build_f2_legacy_bundle_no_charter_yaml,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_runner = CliRunner()

# Matches ``runner.py:245``'s composed line exactly (same regex shape as
# ``tests/architectural/test_remediation_effectiveness.py``'s
# ``_BLOCKED_LINE_RE`` — duplicated rather than imported, since that module
# is WP01's and out of this WP's map).
_BLOCKED_LINE_RE = re.compile(r"^(?P<name>\S+) (?P<state>\S+); run `(?P<command>.+)`$")

# Generous ceiling so a genuine non-termination is a hard test failure
# (per the WP prompt: "If the loop does not terminate, that is a failure of
# this WP -- report it, do not adjust the fixture until it passes"), not an
# infinite loop hanging the suite.
_MAX_STEPS = 10


def _run_charter(*args: str) -> tuple[int, str]:
    """Invoke ``spec-kitty charter <args>`` in-process; return (exit_code, stdout)."""
    result = _runner.invoke(charter_app, list(args))
    return result.exit_code, result.stdout


def _preflight_payload() -> dict[str, object]:
    _exit_code, stdout = _run_charter("preflight", "--json")
    return json.loads(stdout.strip().splitlines()[-1])  # type: ignore[no-any-return]


def _commands_from_blocked_reason(blocked_reason: str) -> list[str]:
    """Extract the distinct ``spec-kitty ...`` commands named on each line.

    Order-preserving de-duplication: F2's first blocked state names the
    *same* command for both ``charter_source`` and ``synced_bundle`` (both
    read the same absent ``charter.yaml``) -- executing it once clears both,
    exactly like a real operator would not literally run an identical
    command twice back to back.
    """
    commands: list[str] = []
    for line in blocked_reason.splitlines():
        match = _BLOCKED_LINE_RE.match(line)
        assert match, f"blocked_reason line did not match the expected shape: {line!r}"
        command = match.group("command")
        if command not in commands:
            commands.append(command)
    return commands


def test_sc002_legacy_bundle_walkthrough_terminates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F2 (legacy bundle, no ``charter.yaml``) -> unblocked, following only
    the tool's own emitted commands. Records the SC-002 step count.
    """
    repo_root = tmp_path
    build_f2_legacy_bundle_no_charter_yaml(repo_root)
    monkeypatch.chdir(repo_root)

    step_count = 0
    executed_commands: list[str] = []
    payload = _preflight_payload()

    while not payload["passed"]:
        assert step_count < _MAX_STEPS, (
            f"SC-002 walkthrough did not terminate within {_MAX_STEPS} steps "
            f"(commands so far: {executed_commands}); this is a WP02 failure "
            "to report, not a fixture to adjust."
        )
        blocked_reason = payload["blocked_reason"]
        assert isinstance(blocked_reason, str)
        commands = _commands_from_blocked_reason(blocked_reason)

        for command in commands:
            args = shlex.split(command)
            assert args[:2] == ["spec-kitty", "charter"], (
                f"walkthrough only drives the charter_app in-process; "
                f"unexpected command shape: {command!r}"
            )
            exit_code, stdout = _run_charter(*args[2:])
            assert exit_code == 0, (
                f"remediation command `{command}` failed (exit={exit_code}): {stdout}"
            )
            executed_commands.append(command)
        step_count += 1

        before_checks = cast("list[dict[str, object]]", payload["checks"])
        before_states = {c["name"]: c["state"] for c in before_checks}
        payload = _preflight_payload()
        after_checks = cast("list[dict[str, object]]", payload["checks"])
        after_states = {c["name"]: c["state"] for c in after_checks}
        assert after_states != before_states, (
            "a full step (all commands from one blocked_reason) produced no "
            f"state change at all -- non-terminating loop. before={before_states} "
            f"after={after_states} commands={commands}"
        )

    assert payload["passed"] is True
    # SC-002: the plan's "bounded number of steps" -- this walkthrough's
    # observed count for the F2 (legacy-bundle, BC-2 trigger) fixture.
    print(f"\nSC-002 step count (F2 legacy-bundle walkthrough): {step_count}")
    print(f"SC-002 commands executed: {executed_commands}")
