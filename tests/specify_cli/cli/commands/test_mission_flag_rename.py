"""ATDD acceptance tests for FR-017, FR-018: --feature → --mission CLI flag rename.

These tests cover US-7 acceptance scenarios. All 4 tests must FAIL on the
baseline (before T003/T004 apply the rename) and PASS after.
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

import pytest

# Ensure the worktree's own src/ is first on PYTHONPATH so subprocess calls
# pick up this worktree's modified files rather than the editable-install in
# the main repo's venv.
_WORKTREE_SRC = str(Path(__file__).parents[4] / "src")


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run spec-kitty CLI via its installed entry-point."""
    env = os.environ.copy()
    env["PYTHONPATH"] = _WORKTREE_SRC + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "specify_cli.__main__", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        env=env,
    )


def _help(*subcommand: str) -> subprocess.CompletedProcess[str]:
    """Fetch --help output for a subcommand."""
    return _run_cli(*subcommand, "--help")


# ---------------------------------------------------------------------------
# Unit-level tests for resolve_mission_or_feature (T001 utility)
# ---------------------------------------------------------------------------


def test_resolve_utility_mission_only() -> None:
    """resolve_mission_or_feature returns mission when only --mission given."""
    from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature

    result = resolve_mission_or_feature("056-my-feature", None)
    assert result == "056-my-feature"


def test_resolve_utility_feature_only() -> None:
    """resolve_mission_or_feature returns feature value and emits DeprecationWarning."""
    import warnings
    from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = resolve_mission_or_feature(None, "056-my-feature")

    assert result == "056-my-feature"
    assert any(issubclass(w.category, DeprecationWarning) for w in caught), (
        f"Expected DeprecationWarning but got: {[w.category for w in caught]}"
    )


def test_resolve_utility_conflicting_raises() -> None:
    """resolve_mission_or_feature raises BadParameter on conflicting values."""
    import typer
    from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature

    with pytest.raises(typer.BadParameter):
        resolve_mission_or_feature("056-a", "056-b")


def test_resolve_utility_same_value_silent() -> None:
    """resolve_mission_or_feature returns the value when both flags have the same value."""
    from specify_cli.cli.commands._flag_utils import resolve_mission_or_feature

    result = resolve_mission_or_feature("056-x", "056-x")
    assert result == "056-x"


# ---------------------------------------------------------------------------
# CLI-level integration tests: --mission must appear as a recognised option
# (These fail until T003/T004 add --mission to each command)
# ---------------------------------------------------------------------------


def test_mission_flag_present_in_next_help() -> None:
    """spec-kitty next --help must expose --mission as a documented option."""
    result = _help("next")
    assert "--mission" in result.stdout, (
        f"--mission not found in `spec-kitty next --help`.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_feature_flag_deprecated_label_in_next_help() -> None:
    """--feature should be absent (hidden) or labelled deprecated in next --help."""
    result = _help("next")
    # After the rename --feature is hidden=True, so it should NOT appear in help.
    # Before the rename it IS visible.  The test asserts it is gone from visible help.
    assert "--feature" not in result.stdout, (
        "--feature should be hidden after rename but is still visible in help.\n"
        f"stdout: {result.stdout}"
    )


def test_mission_flag_present_in_verify_help() -> None:
    """spec-kitty verify-setup --help must expose --mission as a documented option."""
    result = _help("verify-setup")
    assert "--mission" in result.stdout, (
        f"--mission not found in `spec-kitty verify-setup --help`.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_mission_flag_present_in_agent_workflow_implement_help() -> None:
    """spec-kitty agent workflow implement --help must expose --mission."""
    result = _help("agent", "workflow", "implement")
    assert "--mission" in result.stdout, (
        f"--mission not found in `spec-kitty agent workflow implement --help`.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
