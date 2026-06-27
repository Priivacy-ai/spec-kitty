"""WP03 no-selector regression tests: exit code 2 on missing --mission.

For each of the three commands cleaned up in WP03 (lifecycle plan,
lifecycle tasks, mission_type current), verifies that:
1. ``--feature`` is rejected outright by the parser (unknown option, exit 2).
2. Omitting ``--mission`` (or passing an empty string) exits with code 2 and
   a readable BadParameter message.
3. No uncaught TypeError escapes.

T017 verification: ``_legacy_aliases.py`` is confirmed absent — both
``find src/ -name '_legacy_aliases.py'`` and ``grep -rn '_legacy_aliases' src/``
return zero results (verified during WP03 implementation).
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from specify_cli import app as main_app
from specify_cli.cli.commands.lifecycle import _require_mission_or_exit, plan, tasks
from specify_cli.cli.commands.mission_type import app as mission_type_app

pytestmark = [pytest.mark.unit, pytest.mark.fast]
runner = CliRunner()


class TestRequireMissionOrExit:
    """Direct coverage for the version-robust no-selector helper plan/tasks share.

    Replaces the prior ``typer.BadParameter`` path, whose Rich error-panel
    rendering is dropped by some Typer versions (the ``--mission`` hint then
    never reaches captured output). The helper prints the message itself, so the
    contract is asserted independently of CLI rendering.
    """

    def test_valid_slug_passes_through(self) -> None:
        assert _require_mission_or_exit("  001-demo  ", json_output=False) == "001-demo"

    def test_human_no_selector_exits_2_with_mission_hint(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            _require_mission_or_exit(None, json_output=False)
        assert exc_info.value.exit_code == 2
        assert "--mission" in capsys.readouterr().out

    def test_json_no_selector_exits_2_with_mission_hint(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            _require_mission_or_exit("   ", json_output=True)
        assert exc_info.value.exit_code == 2
        out = capsys.readouterr().out
        assert '"error"' in out and "--mission" in out

_plan_app = typer.Typer()
_plan_app.command()(plan)

_tasks_app = typer.Typer()
_tasks_app.command()(tasks)


class TestPlanNoSelector:
    """lifecycle.plan: ``--feature`` removed; no ``--mission`` exits 2."""

    def test_feature_flag_rejected_exit2(self) -> None:
        with patch("specify_cli.cli.commands.lifecycle._enforce_initialized"):
            result = runner.invoke(_plan_app, ["--feature", "some-slug"])
        assert result.exit_code == 2, result.output
        assert "no such option" in result.output.lower()

    def test_no_mission_exits_2(self) -> None:
        with patch("specify_cli.cli.commands.lifecycle._enforce_initialized"):
            result = runner.invoke(_plan_app, [])
        assert result.exit_code == 2, result.output
        assert not isinstance(result.exception, TypeError)

    def test_empty_mission_exits_2(self) -> None:
        with patch("specify_cli.cli.commands.lifecycle._enforce_initialized"):
            result = runner.invoke(_plan_app, ["--mission", "  "])
        assert result.exit_code == 2, result.output
        assert not isinstance(result.exception, TypeError)

    def test_no_mission_message_mentions_mission(self) -> None:
        with patch("specify_cli.cli.commands.lifecycle._enforce_initialized"):
            result = runner.invoke(_plan_app, [])
        assert result.exit_code == 2, result.output
        assert "--mission" in result.output


class TestTasksNoSelector:
    """lifecycle.tasks: ``--feature`` removed; no ``--mission`` exits 2."""

    def test_feature_flag_rejected_exit2(self) -> None:
        with patch("specify_cli.cli.commands.lifecycle._enforce_initialized"):
            result = runner.invoke(_tasks_app, ["--feature", "some-slug"])
        assert result.exit_code == 2, result.output
        assert "no such option" in result.output.lower()

    def test_no_mission_exits_2(self) -> None:
        with patch("specify_cli.cli.commands.lifecycle._enforce_initialized"):
            result = runner.invoke(_tasks_app, [])
        assert result.exit_code == 2, result.output
        assert not isinstance(result.exception, TypeError)

    def test_empty_mission_exits_2(self) -> None:
        with patch("specify_cli.cli.commands.lifecycle._enforce_initialized"):
            result = runner.invoke(_tasks_app, ["--mission", ""])
        assert result.exit_code == 2, result.output
        assert not isinstance(result.exception, TypeError)

    def test_no_mission_message_mentions_mission(self) -> None:
        with patch("specify_cli.cli.commands.lifecycle._enforce_initialized"):
            result = runner.invoke(_tasks_app, [])
        assert result.exit_code == 2, result.output
        assert "--mission" in result.output


class TestMissionCurrentNoSelector:
    """mission_type.current: ``--feature`` removed; no ``--mission`` exits 2 (no auto-detect)."""

    def test_feature_flag_rejected_exit2(self) -> None:
        result = runner.invoke(main_app, ["mission", "current", "--feature", "some-slug"])
        assert result.exit_code == 2, result.output
        assert "no such option" in result.output.lower()

    def test_no_mission_no_type_error(self, tmp_path: Path) -> None:
        """No ``--mission`` and no auto-detected mission exits 2 (SC-003, not TypeError).

        Patches ``get_project_root_or_exit`` so the function body is reached
        and the no-selector guard (``raise typer.Exit(2)``) fires instead of
        the project-root guard (``raise typer.Exit(1)``).
        """
        with patch("specify_cli.cli.commands.mission_type.get_project_root_or_exit") as mock_root:
            mock_root.return_value = tmp_path / "nonexistent-test-path"
            result = runner.invoke(main_app, ["mission", "current"])
        assert result.exit_code == 2, (
            f"Expected exit code 2 (SC-003 no-selector guard), got {result.exit_code}"
        )
        assert not isinstance(result.exception, TypeError)

    def test_mission_current_canonical_still_works(self, tmp_path: Path) -> None:
        """Canonical ``--mission`` path remains intact after WP03."""
        mission_slug = "077-demo-mission"
        (tmp_path / "kitty-specs" / mission_slug).mkdir(parents=True)

        with (
            patch("specify_cli.cli.commands.mission_type.get_project_root_or_exit", return_value=tmp_path),
            patch("specify_cli.cli.commands.mission_type.get_mission_for_feature", return_value=SimpleNamespace(name="software-dev")),
            patch("specify_cli.cli.commands.mission_type._mission_details_lines", return_value=["ok"]),
        ):
            result = runner.invoke(mission_type_app, ["current", "--mission", mission_slug])

        assert result.exit_code == 0, result.output
        assert mission_slug in result.output
