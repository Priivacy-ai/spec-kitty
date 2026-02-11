"""Integration tests for the change command surface (WP01).

Tests that the change command is registered at both top-level and agent level,
that agent subcommands (preview, apply, next, reconcile) exist and return
structured JSON, and that command templates render correctly.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.agent.change import app as agent_change_app
from specify_cli.cli.commands.change import change

runner = CliRunner()


class TestChangeCommandRegistration:
    """Verify the change command is registered in both command trees."""

    def test_top_level_change_command_exists(self):
        """The top-level change command function should be importable."""
        assert callable(change)
        assert change.__name__ == "change"

    def test_agent_change_app_exists(self):
        """The agent change typer app should be importable."""
        assert agent_change_app is not None
        assert agent_change_app.info.name == "change"

    def test_agent_change_subcommands_registered(self):
        """All four agent change subcommands should be registered."""
        command_names = [c.name for c in agent_change_app.registered_commands]
        assert "preview" in command_names
        assert "apply" in command_names
        assert "next" in command_names
        assert "reconcile" in command_names

    def test_no_alias_commands(self):
        """No legacy aliases (changeset, changset) should be registered."""
        command_names = [c.name for c in agent_change_app.registered_commands]
        assert "changeset" not in command_names
        assert "changset" not in command_names

    def test_change_in_top_level_registration(self):
        """The change command should be in the top-level command registry."""
        import typer

        from specify_cli.cli.commands import register_commands

        app = typer.Typer()
        register_commands(app)

        command_names = []
        for c in app.registered_commands:
            command_names.append(
                c.name or (c.callback.__name__ if c.callback else None)
            )
        for g in app.registered_groups:
            command_names.append(g.name)

        assert "change" in command_names

    def test_change_in_agent_registration(self):
        """The change subcommand should be in the agent command tree."""
        from specify_cli.cli.commands.agent import app as agent_app

        group_names = [g.name for g in agent_app.registered_groups]
        assert "change" in group_names


class TestAgentChangePreview:
    """Test the agent change preview subcommand."""

    def test_preview_returns_json(self):
        """Preview should return structured JSON with required fields."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test-feature",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "use SQLAlchemy instead", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "requestId" in data
            assert "stashKey" in data
            assert "validationState" in data
            assert "complexity" in data
            assert "proposedMode" in data

    def test_preview_complexity_fields(self):
        """Preview complexity assessment should have all scoring fields."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test-feature",
            ),
            patch("specify_cli.core.change_stack._get_main_repo_root") as mock_main,
        ):
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_main.return_value = Path("/tmp/fake-repo")

            result = runner.invoke(
                agent_change_app,
                ["preview", "add caching layer", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            complexity = data["complexity"]
            assert "scopeBreadthScore" in complexity
            assert "couplingScore" in complexity
            assert "dependencyChurnScore" in complexity
            assert "ambiguityScore" in complexity
            assert "integrationRiskScore" in complexity
            assert "totalScore" in complexity
            assert "classification" in complexity
            assert "recommendSpecify" in complexity


class TestAgentChangeApply:
    """Test the agent change apply subcommand."""

    def test_apply_returns_json(self, tmp_path):
        """Apply should return structured JSON with required fields."""
        tasks_dir = tmp_path / "kitty-specs" / "029-test-feature" / "tasks"
        tasks_dir.mkdir(parents=True)

        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
            patch(
                "specify_cli.core.change_stack.get_current_branch",
                return_value="029-test-feature",
            ),
            patch(
                "specify_cli.core.change_stack._get_main_repo_root",
                return_value=tmp_path,
            ),
        ):
            mock_root.return_value = tmp_path
            mock_slug.return_value = "029-test-feature"

            result = runner.invoke(
                agent_change_app,
                [
                    "apply",
                    "test-request-id",
                    "--request-text",
                    "fix typo in README",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["requestId"] == "test-request-id"
            assert "createdWorkPackages" in data
            assert "closedReferenceLinks" in data
            assert "mergeCoordinationJobs" in data
            assert "consistency" in data


class TestAgentChangeNext:
    """Test the agent change next subcommand."""

    def test_next_returns_json(self):
        """Next should return structured JSON with required fields."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
        ):
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_slug.return_value = "029-test-feature"

            result = runner.invoke(
                agent_change_app,
                ["next", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "stashKey" in data
            assert "selectedSource" in data
            assert "normalProgressionBlocked" in data
            assert "blockers" in data


class TestAgentChangeReconcile:
    """Test the agent change reconcile subcommand."""

    def test_reconcile_returns_json(self):
        """Reconcile should return structured JSON with required fields."""
        with (
            patch(
                "specify_cli.cli.commands.agent.change.locate_project_root"
            ) as mock_root,
            patch(
                "specify_cli.cli.commands.agent.change.detect_feature_slug"
            ) as mock_slug,
        ):
            mock_root.return_value = Path("/tmp/fake-repo")
            mock_slug.return_value = "029-test-feature"

            result = runner.invoke(
                agent_change_app,
                ["reconcile", "--json"],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "stashKey" in data
            assert "consistency" in data
            assert "mergeCoordinationJobs" in data


class TestChangeCommandTemplates:
    """Verify change command templates exist and have correct format."""

    def test_base_template_exists(self):
        """Base change command template should exist."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "specify_cli"
            / "templates"
            / "command-templates"
            / "change.md"
        )
        assert template_path.exists(), f"Base template not found at {template_path}"

    def test_mission_template_exists(self):
        """Mission-specific change command template should exist."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "specify_cli"
            / "missions"
            / "software-dev"
            / "command-templates"
            / "change.md"
        )
        assert template_path.exists(), f"Mission template not found at {template_path}"

    def test_base_template_has_frontmatter(self):
        """Base template should have YAML frontmatter with description."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "specify_cli"
            / "templates"
            / "command-templates"
            / "change.md"
        )
        content = template_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "description:" in content
        # Frontmatter must be closed
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Frontmatter not properly closed with ---"

    def test_mission_template_has_frontmatter(self):
        """Mission template should have YAML frontmatter with description."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "specify_cli"
            / "missions"
            / "software-dev"
            / "command-templates"
            / "change.md"
        )
        content = template_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "description:" in content

    def test_base_template_has_arguments_placeholder(self):
        """Base template should include $ARGUMENTS placeholder."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "specify_cli"
            / "templates"
            / "command-templates"
            / "change.md"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "$ARGUMENTS" in content

    def test_mission_template_has_arguments_placeholder(self):
        """Mission template should include $ARGUMENTS placeholder."""
        template_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "specify_cli"
            / "missions"
            / "software-dev"
            / "command-templates"
            / "change.md"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "$ARGUMENTS" in content

    def test_no_legacy_alias_in_templates(self):
        """Templates should not reference legacy aliases."""
        for subdir in [
            "templates/command-templates",
            "missions/software-dev/command-templates",
        ]:
            template_path = (
                Path(__file__).parent.parent.parent
                / "src"
                / "specify_cli"
                / subdir
                / "change.md"
            )
            content = template_path.read_text(encoding="utf-8")
            assert "changeset" not in content.lower()
            assert "changset" not in content.lower()


class TestTopLevelChangeCommand:
    """Test the top-level spec-kitty change command end-to-end."""

    @staticmethod
    def _make_app():
        """Create a Typer app with the change command registered."""
        import typer as _typer

        _app = _typer.Typer()
        _app.command()(change)
        return _app

    @staticmethod
    def _mock_change_req(tmp_path):
        """Build a mock ChangeRequest for testing."""
        from specify_cli.core.change_classifier import classify_change_request
        from specify_cli.core.change_stack import (
            AmbiguityResult,
            BranchStash,
            ChangeRequest,
            ClosedReferenceCheck,
            StashScope,
            ValidationState,
        )

        stash_path = tmp_path / "kitty-specs" / "029-test" / "tasks"
        stash_path.mkdir(parents=True, exist_ok=True)
        return ChangeRequest(
            request_id="test-id",
            raw_text="use SQLAlchemy instead",
            submitted_branch="029-test",
            stash=BranchStash(
                scope=StashScope.FEATURE,
                stash_key="029-test",
                stash_path=stash_path,
            ),
            validation_state=ValidationState.VALID,
            ambiguity=AmbiguityResult(is_ambiguous=False),
            closed_references=ClosedReferenceCheck(
                has_closed_references=False,
            ),
            complexity_score=classify_change_request(""),
        )

    def test_change_command_completes_without_markup_error(self, tmp_path):
        """Top-level change command should not crash with Rich MarkupError."""
        app = self._make_app()
        mock_req = self._mock_change_req(tmp_path)
        with (
            patch("specify_cli.cli.commands.change.find_repo_root") as mock_root,
            patch(
                "specify_cli.cli.commands.change.get_project_root_or_exit"
            ) as mock_proj,
            patch("specify_cli.cli.commands.change.check_version_compatibility"),
            patch(
                "specify_cli.cli.commands.change.validate_change_request",
                return_value=mock_req,
            ),
            patch(
                "specify_cli.cli.commands.change.synthesize_change_plan"
            ) as mock_plan,
            patch(
                "specify_cli.cli.commands.change.generate_change_work_packages",
                return_value=[],
            ),
            patch(
                "specify_cli.cli.commands.change.write_change_work_packages",
                return_value=[],
            ),
            patch(
                "specify_cli.cli.commands.change.reconcile_change_stack"
            ) as mock_recon,
        ):
            from specify_cli.core.change_stack import ConsistencyReport

            mock_root.return_value = tmp_path
            mock_proj.return_value = tmp_path
            mock_recon.return_value = ConsistencyReport(
                updated_tasks_doc=False,
                dependency_validation_passed=True,
                broken_links_fixed=0,
                issues=[],
            )

            result = runner.invoke(app, ["use SQLAlchemy instead"])
            # Should complete without MarkupError crash
            assert result.exit_code == 0

    def test_change_preview_flag_alters_behavior(self, tmp_path):
        """--preview flag should show preview output instead of apply output."""
        app = self._make_app()
        mock_req = self._mock_change_req(tmp_path)
        with (
            patch("specify_cli.cli.commands.change.find_repo_root") as mock_root,
            patch(
                "specify_cli.cli.commands.change.get_project_root_or_exit"
            ) as mock_proj,
            patch("specify_cli.cli.commands.change.check_version_compatibility"),
            patch(
                "specify_cli.cli.commands.change.validate_change_request",
                return_value=mock_req,
            ),
        ):
            mock_root.return_value = tmp_path
            mock_proj.return_value = tmp_path

            result = runner.invoke(app, ["refactor auth", "--preview"])
            assert result.exit_code == 0
            # Preview output includes request ID and stash info
            assert "Preview" in result.output or "preview" in result.output.lower()

    def test_change_json_output_writes_file(self, tmp_path):
        """--json flag should write structured JSON to the provided path."""
        app = self._make_app()
        mock_req = self._mock_change_req(tmp_path)
        json_path = tmp_path / "output.json"
        with (
            patch("specify_cli.cli.commands.change.find_repo_root") as mock_root,
            patch(
                "specify_cli.cli.commands.change.get_project_root_or_exit"
            ) as mock_proj,
            patch("specify_cli.cli.commands.change.check_version_compatibility"),
            patch(
                "specify_cli.cli.commands.change.validate_change_request",
                return_value=mock_req,
            ),
            patch(
                "specify_cli.cli.commands.change.synthesize_change_plan"
            ) as mock_plan,
            patch(
                "specify_cli.cli.commands.change.generate_change_work_packages",
                return_value=[],
            ),
            patch(
                "specify_cli.cli.commands.change.write_change_work_packages",
                return_value=[],
            ),
            patch(
                "specify_cli.cli.commands.change.reconcile_change_stack"
            ) as mock_recon,
        ):
            from specify_cli.core.change_stack import ConsistencyReport

            mock_root.return_value = tmp_path
            mock_proj.return_value = tmp_path
            mock_recon.return_value = ConsistencyReport(
                updated_tasks_doc=False,
                dependency_validation_passed=True,
                broken_links_fixed=0,
                issues=[],
            )

            result = runner.invoke(app, ["add caching", "--json", str(json_path)])
            assert result.exit_code == 0
            assert json_path.exists()
            data = json.loads(json_path.read_text())
            assert data["mode"] == "apply"
            assert data["status"] == "applied"
            assert "createdWorkPackages" in data

    def test_change_preview_json_output(self, tmp_path):
        """--preview --json should write preview JSON."""
        app = self._make_app()
        mock_req = self._mock_change_req(tmp_path)
        json_path = tmp_path / "preview.json"
        with (
            patch("specify_cli.cli.commands.change.find_repo_root") as mock_root,
            patch(
                "specify_cli.cli.commands.change.get_project_root_or_exit"
            ) as mock_proj,
            patch("specify_cli.cli.commands.change.check_version_compatibility"),
            patch(
                "specify_cli.cli.commands.change.validate_change_request",
                return_value=mock_req,
            ),
        ):
            mock_root.return_value = tmp_path
            mock_proj.return_value = tmp_path

            result = runner.invoke(
                app, ["refactor auth", "--preview", "--json", str(json_path)]
            )
            assert result.exit_code == 0
            assert json_path.exists()
            data = json.loads(json_path.read_text())
            assert data["mode"] == "preview"


class TestInitFlowIncludesChange:
    """Verify that init flow references include /spec-kitty.change."""

    def test_enhancement_commands_include_change(self):
        """The init.py enhancement commands should reference /spec-kitty.change."""
        init_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "specify_cli"
            / "cli"
            / "commands"
            / "init.py"
        )
        content = init_path.read_text(encoding="utf-8")
        assert "/spec-kitty.change" in content
