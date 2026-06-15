"""Regression test for #1917: _validate_base_ref must pass base_ref after a '--' separator.

When `git rev-parse --verify` receives a value starting with '--' (like '--git-dir'),
it consumes the value as an option rather than as a ref name, potentially:
- Leaking git option side-effects (e.g., printing the git dir) as the returned "SHA"
- Silently succeeding for option-shaped values that are not valid refs

The fix inserts a '--' end-of-options separator so that leading-dash values
are always validated AS REF NAMES: git rev-parse --verify -- <base_ref>

Probe option: '--git-dir'
- WITHOUT '--': git consumes --git-dir as an option (emits git-dir path to stdout), rc=128
- WITH '--': git treats --git-dir as a ref name (unknown-revision error), rc=128
Both return rc!=0 for real git, but the argv shape is different — the test captures
the exact subprocess argv to prove the separator is present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import specify_cli.cli.commands.implement as impl_module
from specify_cli.cli.commands.implement import _validate_base_ref

pytestmark = [pytest.mark.unit]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LEADING_DASH_PROBE = "--git-dir"
"""A leading-dash value that maps to a real git rev-parse option.

Without '--', git consumes it as an option flag (option side-effect leaks);
with '--', git treats it as a ref name (unknown-revision, option not consumed).
The monkeypatched runner captures the exact argv, so we don't need real git
behavior — we assert the '--' separator is structurally present.
"""


def _make_mock_run(returncode: int = 0, stdout: str = "abc1234") -> MagicMock:
    """Return a subprocess.run mock that records calls and returns a controlled result."""
    mock_result = MagicMock()
    mock_result.returncode = returncode
    mock_result.stdout = stdout

    mock_fn = MagicMock(return_value=mock_result)
    return mock_fn


# ---------------------------------------------------------------------------
# T030 — Regression: '--' end-of-options separator MUST be present in argv
# ---------------------------------------------------------------------------


def test_validate_base_ref_separator_present_in_argv() -> None:
    """_validate_base_ref must pass base_ref after a '--' end-of-options separator.

    This test is the regression check for #1917. It monkeypatches subprocess.run
    to capture the exact argv forwarded to git and asserts that '--' appears
    between '--verify' and the base_ref value.

    Before the fix: argv = ["git", "rev-parse", "--verify", "--git-dir"]
        → '--' is ABSENT → assertion FAILS (test is RED)
    After the fix:  argv = ["git", "rev-parse", "--verify", "--", "--git-dir"]
        → '--' is PRESENT → assertion PASSES (test is GREEN)
    """
    repo_root = Path("/tmp/fake-repo")
    mock_run = _make_mock_run(returncode=0, stdout="deadbeef" * 5 + "12345678")

    with patch.object(impl_module.subprocess, "run", mock_run):
        _validate_base_ref(repo_root, _LEADING_DASH_PROBE)

    assert mock_run.call_count == 1, "subprocess.run should be called exactly once"
    call_args: list[Any] = mock_run.call_args[0][0]  # first positional arg = cmd list

    assert isinstance(call_args, list), f"Expected list argv, got {type(call_args)}"

    # The '--' separator MUST appear in the argv...
    assert "--" in call_args, (
        f"'--' end-of-options separator is ABSENT from git argv: {call_args}\n"
        f"Fix: change [\"git\", \"rev-parse\", \"--verify\", base_ref] to "
        f"[\"git\", \"rev-parse\", \"--verify\", \"--\", base_ref]"
    )

    # ...and MUST appear BEFORE the base_ref value
    separator_idx = call_args.index("--")
    base_ref_idx = call_args.index(_LEADING_DASH_PROBE)
    assert separator_idx < base_ref_idx, (
        f"'--' (at index {separator_idx}) must appear BEFORE base_ref "
        f"'{_LEADING_DASH_PROBE}' (at index {base_ref_idx}) in argv: {call_args}"
    )

    # '--verify' must still be present (no regression on the verification flag)
    assert "--verify" in call_args, (
        f"'--verify' must still be present in git argv: {call_args}"
    )


def test_validate_base_ref_normal_ref_passes() -> None:
    """Normal refs (branch names, SHAs) must still validate successfully.

    The '--' separator must not break normal usage — a branch name or SHA
    that returns rc=0 from git rev-parse --verify must still result in
    _validate_base_ref returning the resolved SHA string.
    """
    repo_root = Path("/tmp/fake-repo")
    expected_sha = "a" * 40
    mock_run = _make_mock_run(returncode=0, stdout=expected_sha + "\n")

    with patch.object(impl_module.subprocess, "run", mock_run):
        result = _validate_base_ref(repo_root, "main")

    assert result == expected_sha, (
        f"Expected SHA '{expected_sha}', got '{result}'"
    )

    call_args = mock_run.call_args[0][0]
    assert "main" in call_args, f"'main' must appear in git argv: {call_args}"
    # '--' must still be present for defense-in-depth even for normal refs
    assert "--" in call_args, (
        f"'--' end-of-options separator must be present even for normal refs: {call_args}"
    )


def test_validate_base_ref_exits_on_nonzero_returncode(tmp_path: Path) -> None:
    """_validate_base_ref must raise typer.Exit(1) when git returns non-zero.

    This exercises the error path: a ref that does not resolve locally.
    The '--' fix must not change the existing error semantics.
    """
    import typer

    mock_run = _make_mock_run(returncode=128, stdout="")

    with patch.object(impl_module.subprocess, "run", mock_run), pytest.raises(typer.Exit) as exc_info:
        _validate_base_ref(tmp_path, "no-such-ref")

    assert exc_info.value.exit_code == 1, (
        f"Expected exit code 1 for unknown ref, got {exc_info.value.exit_code}"
    )
