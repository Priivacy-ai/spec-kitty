"""Tests for WP06/T024: spec-kitty charter activate refactored command.

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
import yaml
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
        result = _invoke_activate(
            project_root,
            "directive",
            "001-architectural-integrity-standard",
        )
        assert result.exit_code == 0, result.output
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "001-architectural-integrity-standard" in data["activated_directives"]

    def test_activate_config_yaml_updated(self, project_root: Path) -> None:
        """config.yaml is updated, not an override file."""
        _invoke_activate(
            project_root,
            "directive",
            "003-decision-documentation-requirement",
        )
        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text())
        assert "activated_directives" in data
        assert "003-decision-documentation-requirement" in data["activated_directives"]

    def test_activate_unknown_artifact_id_exits_1_without_mutating(self, project_root: Path) -> None:
        result = _invoke_activate(project_root, "directive", "not-a-real-directive")
        assert result.exit_code == 1
        # WP09: activation now delegates to the engine, which raises the typed
        # UnknownActivationIdError (a ValueError subclass) with an actionable
        # "Unknown <kind> ID ..." message. The CLI's existing `except ValueError`
        # still catches it and exits 1 without mutating config.yaml.
        assert "Unknown directive ID" in result.output

        config = project_root / ".kittify" / "config.yaml"
        data = yaml.safe_load(config.read_text()) or {}
        assert "activated_directives" not in data

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
                "001-architectural-integrity-standard",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        # CharterPackManager emits a cascade warning (deferred DRG traversal)
        assert "cascade" in result.output.lower() or "Warning" in result.output

    def test_activate_accepts_options_after_positional_args(self, project_root: Path) -> None:
        """Contract examples place --cascade after <kind> <id>."""
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
        assert "cascade" in result.output.lower() or "Warning" in result.output

    def test_activate_cascade_calls_with_true(self, project_root: Path) -> None:
        """--cascade flag passes cascade=True to CharterPackManager.activate."""
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
        _invoke_activate(project_root, "directive", "001-architectural-integrity-standard")
        # Second activation of the same artifact
        result = _invoke_activate(project_root, "directive", "001-architectural-integrity-standard")
        assert result.exit_code == 0, result.output
        assert "Warning" in result.output or "already activated" in result.output.lower()

    def test_activate_no_action_sequence_flag_exists(self) -> None:
        """The old --action-sequence flag is no longer present."""
        result = runner.invoke(charter_app, ["activate", "--help"])
        assert "action-sequence" not in result.output.lower()
        assert "action_sequence" not in result.output.lower()

    def test_activate_output_contains_activated(self, project_root: Path) -> None:
        """Successful activation prints 'Activated' in output."""
        (project_root / ".kittify" / "config.yaml").write_text(
            "activated_tactics: []\n",
            encoding="utf-8",
        )
        result = _invoke_activate(project_root, "tactic", "acceptance-test-first")
        assert result.exit_code == 0, result.output
        assert "Activated" in result.output
