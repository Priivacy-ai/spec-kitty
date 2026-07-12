"""Regression test for the ``git branch -D`` option-injection hardening.

Alert #49 (SonarCloud S6350): ``_force_delete_branch_if_exists`` passed an
internally-derived branch name straight to ``git branch -D`` unprefixed. A
value starting with ``-`` could be parsed as an option instead of the branch
positional. A ``--`` separator makes the value unambiguously positional data.
This test pins the argv shape via a monkeypatched ``subprocess.run`` seam so
a regression (separator removed) fails loudly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from specify_cli.cli.commands import mission_type

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_force_delete_branch_inserts_separator_before_branch_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``git branch -D`` gets a ``--`` immediately before the branch name."""
    calls: list[list[str]] = []

    class _FakeResult:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode
            self.stdout = ""
            self.stderr = ""

    def _fake_run(argv: list[str], **_kwargs: Any) -> _FakeResult:
        calls.append(argv)
        if argv[:2] == ["git", "rev-parse"]:
            return _FakeResult(returncode=0)  # branch "exists" -> proceed to delete
        return _FakeResult(returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    branch_name = "--upload-pack=touch /pwned-marker"
    mission_type._force_delete_branch_if_exists(Path("/fake/repo"), branch_name)

    delete_calls = [argv for argv in calls if argv[:2] == ["git", "branch"]]
    assert delete_calls, "expected a 'git branch -D ...' invocation"
    delete_argv = delete_calls[0]

    # The separator sits immediately before the (hostile) branch name.
    assert delete_argv == ["git", "branch", "-D", "--", branch_name]
    sep_index = delete_argv.index("--")
    assert delete_argv[sep_index + 1] == branch_name


def test_force_delete_branch_noop_when_branch_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No delete call is issued when the existence pre-check fails (unchanged behavior)."""
    calls: list[list[str]] = []

    class _FakeResult:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode
            self.stdout = ""
            self.stderr = ""

    def _fake_run(argv: list[str], **_kwargs: Any) -> _FakeResult:
        calls.append(argv)
        return _FakeResult(returncode=1)  # branch does not exist

    monkeypatch.setattr(subprocess, "run", _fake_run)

    mission_type._force_delete_branch_if_exists(Path("/fake/repo"), "some-branch")

    assert all(argv[:2] != ["git", "branch"] for argv in calls)
