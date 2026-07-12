"""Tests for WP06/T024: spec-kitty charter activate refactored command.

Split from the original `test_charter_activate_commands.py` (ci-test-topology-
performance-01KXBJRT WP05/T021, FR-005) to break the `fast-tests-cli` job's
single-worker tail: `--dist loadfile` pins every test in a file to one xdist
worker, so one heavy monolith caps the job regardless of idle workers.

This sibling covers the `--cascade` flag-handling tests of
`TestActivateCommand` (measured as the heaviest subset of that class,
~3.5-3.7s call time each) — the happy-path/error tests live in the `_core`
sibling and the cascade-output-absence tests live in the `_cascade_output`
sibling.

Covers:
- T024: New activate API: <kind> <id> [--cascade], writes to config.yaml

The old API (--action-sequence, mission-type subcommand, override file) is removed.
All assertions for override-file behavior are also removed.
The activate_mission_type_override function is removed (FR-014: activation now goes
through CharterPackManager.activate() which writes to config.yaml directly).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import charter_app

runner = CliRunner()

pytestmark = [pytest.mark.fast]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """A minimal project with .kittify/config.yaml."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("# empty config\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# T024 — new activate API: <kind> <id> [--cascade] (cascade flag handling)
# ---------------------------------------------------------------------------


class TestActivateCommand:
    def test_activate_cascade_flag_accepted(self, project_root: Path) -> None:
        """--cascade flag is accepted and processed without error; no deferral warning emitted."""
        result = runner.invoke(
            charter_app,
            [
                "activate",
                "--repo-root",
                str(project_root),
                "--cascade",
                "all",
                "directive",
                "001-architectural-integrity-standard",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        # SC-005: stale deferral strings must be absent from output
        assert "not yet implemented" not in result.output
        assert "deferred" not in result.output.lower()

    def test_activate_accepts_options_after_positional_args(self, project_root: Path) -> None:
        """Contract examples place --cascade after <kind> <id>; no deferral warning emitted."""
        result = runner.invoke(
            charter_app,
            [
                "activate",
                "directive",
                "001-architectural-integrity-standard",
                "--cascade",
                "all",
                "--repo-root",
                str(project_root),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0, result.output
        # SC-005: stale deferral strings must be absent from output
        assert "not yet implemented" not in result.output
        assert "deferred" not in result.output.lower()

    def test_activate_cascade_calls_with_true(self, project_root: Path) -> None:
        """--cascade flag passes cascade=True to CharterPackManager.activate (DD-4: parameter kept for stability)."""
        from unittest.mock import patch
        from charter.pack_manager import ActivationResult

        mock_result = ActivationResult(activated=["my-directive"], warnings=[])
        with patch("charter.pack_manager.CharterPackManager.activate", return_value=mock_result) as mock_activate:
            runner.invoke(
                charter_app,
                [
                    "activate",
                    "--repo-root",
                    str(project_root),
                    "--cascade",
                    "all",
                    "directive",
                    "my-directive",
                ],
                catch_exceptions=False,
            )
        mock_activate.assert_called_once()
        _, call_kwargs = mock_activate.call_args
        assert call_kwargs.get("cascade") is True
