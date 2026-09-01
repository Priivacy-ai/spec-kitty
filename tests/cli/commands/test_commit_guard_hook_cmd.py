"""Unit coverage for the hidden ``spec-kitty commit-guard-hook`` wrapper (#254).

The wrapper is a thin ``typer.Exit`` translation around
``commit_guard_hook.main()``'s int return code — the same shape as
``merge_driver_event_log`` in ``tests/merge/test_merge_driver_wrappers_2709.py``.
Covered directly (not via subprocess) since the pre-commit hook's fallback
branch execs ``spec-kitty commit-guard-hook`` as a SUBPROCESS, which the
coverage instrument cannot see.
"""

from __future__ import annotations

import pytest
import typer
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.cli.commands.commit_guard_hook_cmd import commit_guard_hook_cli

pytestmark = pytest.mark.fast

runner = CliRunner()


def test_commit_guard_hook_cli_exits_zero_on_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("specify_cli.policy.commit_guard_hook.main", lambda: 0)

    with pytest.raises(typer.Exit) as excinfo:
        commit_guard_hook_cli()

    assert excinfo.value.exit_code == 0


def test_commit_guard_hook_cli_accepts_argv_through_the_registered_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("specify_cli.policy.commit_guard_hook.main", lambda: 0)

    result = runner.invoke(app, ["commit-guard-hook", ".git/COMMIT_EDITMSG"])

    assert result.exit_code == 0, result.output


def test_commit_guard_hook_cli_exits_nonzero_on_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("specify_cli.policy.commit_guard_hook.main", lambda: 1)

    with pytest.raises(typer.Exit) as excinfo:
        commit_guard_hook_cli()

    assert excinfo.value.exit_code == 1
