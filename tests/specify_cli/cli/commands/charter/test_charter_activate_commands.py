"""Tests for WP06/T024+T025: spec-kitty charter activate refactored command.

Covers:
- T024: New activate API: <kind> <id> [--cascade], writes to config.yaml
- T025: charter_activate.activate_mission_type_override writes to config.yaml (FR-014)

The old API (--action-sequence, mission-type subcommand, override file) is removed.
All assertions for override-file behavior are also removed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli.charter_activate import activate_mission_type_override
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


def _invoke_activate(project_root: Path, *args: str) -> object:
    """Invoke charter activate with --repo-root placed before positional args."""
    return runner.invoke(
        charter_app,
        ["activate", "--repo-root", str(project_root), *args],
        catch_exceptions=False,
    )


# ---------------------------------------------------------------------------
# T024 — new activate API: <kind> <id> [--cascade]
# ---------------------------------------------------------------------------


class TestActivateCommand:
    def test_activate_directive_happy_path(self, project_root: Path) -> None:
        """Activating a directive kind writes to config.yaml."""
        result = _invoke_activate(project_root, "directive", "some-directive")
        assert result.exit_code == 0, result.output
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "some-directive" in data["activated_directives"]

    def test_activate_config_yaml_updated(self, project_root: Path) -> None:
        """config.yaml is updated, not an override file."""
        _invoke_activate(project_root, "directive", "new-directive")
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "activated_directives" in data
        assert "new-directive" in data["activated_directives"]

    def test_activate_unknown_kind_exits_1(self, project_root: Path) -> None:
        """Activating with an unknown kind exits with code 1."""
        result = runner.invoke(
            charter_app,
            ["activate", "--repo-root", str(project_root), "nonsense-kind", "some-id"],
        )
        assert result.exit_code == 1
        assert "Unknown kind" in result.output

    def test_activate_cascade_flag_accepted(self, project_root: Path) -> None:
        """--cascade flag is accepted and processed without error."""
        result = runner.invoke(
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
        assert result.exit_code == 0, result.output
        # CharterPackManager emits a cascade warning (deferred DRG traversal)
        assert "cascade" in result.output.lower() or "Warning" in result.output

    def test_activate_cascade_calls_with_true(self, project_root: Path) -> None:
        """--cascade flag passes cascade=True to CharterPackManager.activate."""
        from unittest.mock import MagicMock, patch
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

    def test_activate_mission_type_kind(self, project_root: Path) -> None:
        """Activating mission-type kind writes to mission_type_activations key."""
        result = _invoke_activate(project_root, "mission-type", "software-dev")
        assert result.exit_code == 0, result.output
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "software-dev" in data["mission_type_activations"]

    def test_activate_already_active_emits_warning(self, project_root: Path) -> None:
        """Activating an already-active artifact emits a warning."""
        # First activation
        _invoke_activate(project_root, "directive", "existing-directive")
        # Second activation of the same artifact
        result = _invoke_activate(project_root, "directive", "existing-directive")
        assert result.exit_code == 0, result.output
        assert "Warning" in result.output or "already activated" in result.output.lower()

    def test_activate_no_action_sequence_flag_exists(self) -> None:
        """The old --action-sequence flag is no longer present."""
        result = runner.invoke(charter_app, ["activate", "--help"])
        assert "action-sequence" not in result.output.lower()
        assert "action_sequence" not in result.output.lower()

    def test_activate_output_contains_activated(self, project_root: Path) -> None:
        """Successful activation prints 'Activated' in output."""
        result = _invoke_activate(project_root, "tactic", "my-tactic")
        assert result.exit_code == 0, result.output
        assert "Activated" in result.output


# ---------------------------------------------------------------------------
# T025 — FR-014: activate_mission_type_override writes to config.yaml
# ---------------------------------------------------------------------------


class TestActivateMissionTypeOverrideRefactored:
    """Tests that activate_mission_type_override now writes to config.yaml."""

    def _make_console(self):
        from io import StringIO
        from rich.console import Console

        buf = StringIO()
        return Console(file=buf, highlight=False, markup=True), buf

    def test_writes_to_config_yaml(self, project_root: Path) -> None:
        """activate_mission_type_override now writes to config.yaml (FR-014)."""
        console, buf = self._make_console()
        with patch(
            "charter.mission_type_profiles.resolve_action_sequence",
            return_value=["specify", "plan", "review"],
        ):
            activate_mission_type_override(
                mission_type_id="software-dev",
                incoming_sequence=["specify", "plan"],
                repo_root=project_root,
                console=console,
            )
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "software-dev" in data["mission_type_activations"]

    def test_activation_complete_message_present(self, project_root: Path) -> None:
        """activate_mission_type_override still emits 'Activation complete.'."""
        console, buf = self._make_console()
        with patch(
            "charter.mission_type_profiles.resolve_action_sequence",
            return_value=["specify", "plan"],
        ):
            activate_mission_type_override(
                mission_type_id="software-dev",
                incoming_sequence=["specify", "plan"],
                repo_root=project_root,
                console=console,
            )
        assert "Activation complete." in buf.getvalue()

    def test_no_override_file_written(self, project_root: Path) -> None:
        """activate_mission_type_override no longer writes to overrides/ directory."""
        console, _ = self._make_console()
        with patch(
            "charter.mission_type_profiles.resolve_action_sequence",
            return_value=["specify", "plan"],
        ):
            activate_mission_type_override(
                mission_type_id="software-dev",
                incoming_sequence=["specify", "plan"],
                repo_root=project_root,
                console=console,
            )
        override_path = (
            project_root / ".kittify" / "overrides" / "mission-types" / "software-dev.yaml"
        )
        assert not override_path.exists(), (
            "Override file should NOT be written (FR-014 reader gap fix)"
        )

    def test_empty_action_sequence_raises(self, project_root: Path) -> None:
        """Empty action_sequence raises ValueError (behavior unchanged)."""
        console, _ = self._make_console()
        with pytest.raises(ValueError, match="non-empty"):
            activate_mission_type_override(
                mission_type_id="software-dev",
                incoming_sequence=[],
                repo_root=project_root,
                console=console,
            )

    def test_duplicate_steps_raises(self, project_root: Path) -> None:
        """Duplicate steps raise ValueError (behavior unchanged)."""
        console, _ = self._make_console()
        with pytest.raises(ValueError, match="unique"):
            activate_mission_type_override(
                mission_type_id="software-dev",
                incoming_sequence=["specify", "specify"],
                repo_root=project_root,
                console=console,
            )
