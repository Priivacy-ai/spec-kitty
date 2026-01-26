"""Integration tests for agent command wrappers.

Tests that agent commands correctly delegate to top-level commands
and validate dependencies before creating workspaces.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from specify_cli.cli.commands.agent.workflow import implement as agent_implement


class TestAgentWorkflowImplement:
    """Integration tests for spec-kitty agent workflow implement."""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository structure."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create kitty-specs structure
        feature_dir = repo_root / "kitty-specs" / "001-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create meta.json
        meta_file = feature_dir / "meta.json"
        meta_file.write_text('{"vcs": "git"}', encoding="utf-8")

        # Initialize as git repo
        subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo_root, check=True, capture_output=True)

        return repo_root

    def test_single_dependency_no_base_errors(self, mock_repo, capsys):
        """Agent implement should error when WP has dependency but no --base."""
        # Create WP02 with dependency on WP01
        wp_file = mock_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP02-build-api.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "title: Build API\n"
            "dependencies: [WP01]\n"
            "lane: planned\n"
            "---\n"
            "# Build API\n"
            "Task description\n",
            encoding="utf-8"
        )

        # Commit the WP file
        subprocess.run(["git", "add", "-f", str(wp_file)], cwd=mock_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP02"], cwd=mock_repo, check=True, capture_output=True)

        # Create feature branch
        subprocess.run(["git", "checkout", "-b", "001-test-feature"], cwd=mock_repo, check=True, capture_output=True)

        # Mock locate_project_root and locate_work_package
        with patch("specify_cli.cli.commands.agent.workflow.locate_project_root") as mock_locate_root, \
             patch("specify_cli.cli.commands.agent.workflow.locate_work_package") as mock_locate_wp, \
             patch("specify_cli.cli.commands.agent.workflow._find_feature_slug") as mock_find_slug:

            mock_locate_root.return_value = mock_repo
            mock_find_slug.return_value = "001-test-feature"

            # Mock WP object
            mock_wp = MagicMock()
            mock_wp.path = wp_file
            mock_wp.frontmatter = {
                "work_package_id": "WP02",
                "dependencies": ["WP01"],
                "lane": "planned"
            }
            mock_wp.body = "# Build API\nTask description\n"
            mock_locate_wp.return_value = mock_wp

            # Try to run agent implement without --base
            with pytest.raises(typer.Exit):
                agent_implement(
                    wp_id="WP02",
                    feature="001-test-feature",
                    agent="test-agent",
                    base=None  # Missing!
                )

            # Verify error message suggests --base WP01
            captured = capsys.readouterr()
            assert "WP02 depends on WP01" in captured.out
            assert "--base WP01" in captured.out

    def test_single_dependency_with_base_calls_toplevel(self, mock_repo):
        """Agent implement with valid --base should call top-level implement."""
        # Create WP01 and WP02
        wp01_file = mock_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-setup.md"
        wp01_file.write_text(
            "---\n"
            "work_package_id: WP01\n"
            "title: Setup\n"
            "dependencies: []\n"
            "lane: done\n"
            "---\n"
            "Setup task\n",
            encoding="utf-8"
        )

        wp02_file = mock_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP02-build-api.md"
        wp02_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "title: Build API\n"
            "dependencies: [WP01]\n"
            "lane: planned\n"
            "---\n"
            "Build API task\n",
            encoding="utf-8"
        )

        # Commit WP files
        subprocess.run(["git", "add", "-f", str(wp01_file), str(wp02_file)], cwd=mock_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WPs"], cwd=mock_repo, check=True, capture_output=True)

        # Create WP01 workspace (base workspace must exist)
        worktrees_dir = mock_repo / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)
        wp01_workspace = worktrees_dir / "001-test-feature-WP01"
        subprocess.run(
            ["git", "worktree", "add", str(wp01_workspace), "-b", "001-test-feature-WP01"],
            cwd=mock_repo,
            check=True,
            capture_output=True
        )

        # Mock dependencies
        with patch("specify_cli.cli.commands.agent.workflow.locate_project_root") as mock_locate_root, \
             patch("specify_cli.cli.commands.agent.workflow.locate_work_package") as mock_locate_wp, \
             patch("specify_cli.cli.commands.agent.workflow._find_feature_slug") as mock_find_slug, \
             patch("specify_cli.cli.commands.agent.workflow.top_level_implement") as mock_top_level:

            mock_locate_root.return_value = mock_repo
            mock_find_slug.return_value = "001-test-feature"

            # Mock WP02 object
            mock_wp = MagicMock()
            mock_wp.path = wp02_file
            mock_wp.frontmatter = {
                "work_package_id": "WP02",
                "dependencies": ["WP01"],
                "lane": "planned"
            }
            mock_wp.body = "Build API task\n"
            mock_locate_wp.return_value = mock_wp

            # Run agent implement with --base WP01
            # This should call top-level implement (mocked to avoid full execution)
            try:
                agent_implement(
                    wp_id="WP02",
                    feature="001-test-feature",
                    agent="test-agent",
                    base="WP01"
                )
            except Exception:
                # May fail during prompt display, but top-level should be called
                pass

            # Verify top-level implement was called with correct parameters
            mock_top_level.assert_called_once_with(
                wp_id="WP02",
                base="WP01",
                feature="001-test-feature",
                json_output=False
            )

    def test_multi_parent_auto_merge(self, mock_repo, capsys):
        """Agent implement should support auto-merge for multi-parent dependencies."""
        # Create WP04 with dependencies on WP02, WP03
        wp_file = mock_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP04-integration.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP04\n"
            "title: Integration\n"
            "dependencies: [WP02, WP03]\n"
            "lane: planned\n"
            "---\n"
            "Integration task\n",
            encoding="utf-8"
        )

        subprocess.run(["git", "add", "-f", str(wp_file)], cwd=mock_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP04"], cwd=mock_repo, check=True, capture_output=True)

        # Mock dependencies
        with patch("specify_cli.cli.commands.agent.workflow.locate_project_root") as mock_locate_root, \
             patch("specify_cli.cli.commands.agent.workflow.locate_work_package") as mock_locate_wp, \
             patch("specify_cli.cli.commands.agent.workflow._find_feature_slug") as mock_find_slug, \
             patch("specify_cli.cli.commands.agent.workflow.top_level_implement") as mock_top_level:

            mock_locate_root.return_value = mock_repo
            mock_find_slug.return_value = "001-test-feature"

            mock_wp = MagicMock()
            mock_wp.path = wp_file
            mock_wp.frontmatter = {
                "work_package_id": "WP04",
                "dependencies": ["WP02", "WP03"],
                "lane": "planned"
            }
            mock_wp.body = "Integration task\n"
            mock_locate_wp.return_value = mock_wp

            # Run agent implement without --base (should auto-merge)
            try:
                agent_implement(
                    wp_id="WP04",
                    feature="001-test-feature",
                    agent="test-agent",
                    base=None  # Auto-merge should trigger
                )
            except Exception:
                # May fail during workspace creation/prompt display
                pass

            # Verify top-level implement was called with base=None (auto-merge mode)
            mock_top_level.assert_called_once()
            call_args = mock_top_level.call_args
            assert call_args[1]["wp_id"] == "WP04"
            assert call_args[1]["base"] is None  # Auto-merge uses None
            assert call_args[1]["feature"] == "001-test-feature"

    def test_validation_error_prevents_workspace_creation(self, mock_repo):
        """Validation errors should prevent workspace creation."""
        # Create WP02 with dependency on WP01
        wp_file = mock_repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP02-build-api.md"
        wp_file.write_text(
            "---\n"
            "work_package_id: WP02\n"
            "dependencies: [WP01]\n"
            "lane: planned\n"
            "---\n"
            "Task\n",
            encoding="utf-8"
        )

        subprocess.run(["git", "add", "-f", str(wp_file)], cwd=mock_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add WP02"], cwd=mock_repo, check=True, capture_output=True)

        # Mock dependencies
        with patch("specify_cli.cli.commands.agent.workflow.locate_project_root") as mock_locate_root, \
             patch("specify_cli.cli.commands.agent.workflow.locate_work_package") as mock_locate_wp, \
             patch("specify_cli.cli.commands.agent.workflow._find_feature_slug") as mock_find_slug, \
             patch("specify_cli.cli.commands.agent.workflow.top_level_implement") as mock_top_level:

            mock_locate_root.return_value = mock_repo
            mock_find_slug.return_value = "001-test-feature"

            mock_wp = MagicMock()
            mock_wp.path = wp_file
            mock_wp.frontmatter = {"work_package_id": "WP02", "dependencies": ["WP01"], "lane": "planned"}
            mock_wp.body = "Task\n"
            mock_locate_wp.return_value = mock_wp

            # Should error during validation (before calling top-level)
            with pytest.raises(typer.Exit):
                agent_implement(
                    wp_id="WP02",
                    feature="001-test-feature",
                    agent="test-agent",
                    base=None
                )

            # Verify top-level implement was NOT called
            mock_top_level.assert_not_called()


class TestAgentFeatureAccept:
    """Integration tests for spec-kitty agent feature accept."""

    @patch("specify_cli.cli.commands.agent.feature.top_level_accept")
    def test_delegates_to_toplevel(self, mock_accept):
        """Agent accept should delegate to top-level accept command."""
        from specify_cli.cli.commands.agent.feature import accept_feature

        # Call agent accept
        accept_feature(
            feature="001-test",
            mode="auto",
            json_output=True,
            lenient=False,
            no_commit=False,
        )

        # Verify top-level accept was called with correct parameters
        mock_accept.assert_called_once_with(
            feature="001-test",
            mode="auto",
            actor=None,  # Agent doesn't use actor
            test=[],  # Agent doesn't use test
            json_output=True,
            lenient=False,
            no_commit=False,
            allow_fail=False,
        )

    @patch("specify_cli.cli.commands.agent.feature.top_level_accept")
    def test_propagates_typer_exit(self, mock_accept):
        """Agent accept should propagate typer.Exit from top-level."""
        from specify_cli.cli.commands.agent.feature import accept_feature

        # Make top-level raise typer.Exit
        mock_accept.side_effect = typer.Exit(1)

        # Should propagate exit
        with pytest.raises(typer.Exit):
            accept_feature(
                feature="001-test",
                mode="auto",
                json_output=False,
                lenient=False,
                no_commit=False,
            )


class TestAgentFeatureMerge:
    """Integration tests for spec-kitty agent feature merge."""

    @patch("specify_cli.cli.commands.agent.feature.top_level_merge")
    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_delegates_to_toplevel(self, mock_locate_root, mock_merge, tmp_path):
        """Agent merge should delegate to top-level merge command."""
        from specify_cli.cli.commands.agent.feature import merge_feature

        mock_locate_root.return_value = tmp_path

        # Mock auto-retry check (skip retry logic for this test)
        with patch("specify_cli.cli.commands.agent.feature._get_current_branch") as mock_branch:
            mock_branch.return_value = "001-test-feature-WP01"  # On feature branch

            # Call agent merge
            merge_feature(
                feature="001-test",
                target="main",
                strategy="merge",
                push=True,
                dry_run=False,
                keep_branch=False,
                keep_worktree=False,
                auto_retry=False,
            )

            # Verify top-level merge was called with parameter mapping
            mock_merge.assert_called_once_with(
                strategy="merge",
                delete_branch=True,  # Inverted from keep_branch=False
                remove_worktree=True,  # Inverted from keep_worktree=False
                push=True,
                target_branch="main",  # Parameter name differs
                dry_run=False,
                feature="001-test",
                resume=False,
                abort=False,
            )

    @patch("specify_cli.cli.commands.agent.feature.top_level_merge")
    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    def test_parameter_inversion(self, mock_locate_root, mock_merge, tmp_path):
        """Agent merge should correctly invert keep_* parameters."""
        from specify_cli.cli.commands.agent.feature import merge_feature

        mock_locate_root.return_value = tmp_path

        with patch("specify_cli.cli.commands.agent.feature._get_current_branch") as mock_branch:
            mock_branch.return_value = "001-test-feature-WP01"

            # Call with keep_branch=True, keep_worktree=True
            merge_feature(
                feature="001-test",
                target="develop",
                strategy="squash",
                push=False,
                dry_run=True,
                keep_branch=True,  # Should invert to delete_branch=False
                keep_worktree=True,  # Should invert to remove_worktree=False
                auto_retry=False,
            )

            # Verify inversions
            call_args = mock_merge.call_args
            assert call_args[1]["delete_branch"] is False  # Inverted from keep=True
            assert call_args[1]["remove_worktree"] is False  # Inverted from keep=True
            assert call_args[1]["strategy"] == "squash"
            assert call_args[1]["target_branch"] == "develop"

    @patch("specify_cli.cli.commands.agent.feature.top_level_merge")
    def test_propagates_typer_exit(self, mock_merge):
        """Agent merge should propagate typer.Exit from top-level."""
        from specify_cli.cli.commands.agent.feature import merge_feature

        # Make top-level raise typer.Exit
        mock_merge.side_effect = typer.Exit(1)

        with patch("specify_cli.cli.commands.agent.feature.locate_project_root") as mock_locate_root, \
             patch("specify_cli.cli.commands.agent.feature._get_current_branch") as mock_branch:
            mock_locate_root.return_value = Path("/tmp/test")
            mock_branch.return_value = "001-test-feature-WP01"

            # Should propagate exit
            with pytest.raises(typer.Exit):
                merge_feature(
                    feature="001-test",
                    target="main",
                    strategy="merge",
                    push=False,
                    dry_run=False,
                    keep_branch=False,
                    keep_worktree=False,
                    auto_retry=False,
                )


class TestAgentCommandConsistency:
    """Tests for consistent behavior across agent commands."""

    def test_all_agent_commands_use_direct_import(self):
        """Verify agent commands import top-level commands, not subprocess."""
        from specify_cli.cli.commands.agent import feature, workflow

        # Check workflow.py imports
        assert hasattr(workflow, "top_level_implement") or \
               "top_level_implement" in workflow.implement.__code__.co_names

        # Check feature.py imports (in function scope)
        feature_source = Path(feature.__file__).read_text()
        assert "from specify_cli.cli.commands.accept import accept" in feature_source
        assert "from specify_cli.cli.commands.merge import merge" in feature_source

        # Verify NO legacy script calls
        assert "scripts/tasks/tasks_cli.py" not in feature_source

    def test_no_legacy_script_references(self):
        """Verify no agent commands reference legacy scripts/tasks/tasks_cli.py."""
        agent_dir = Path(__file__).parent.parent.parent / "src" / "specify_cli" / "cli" / "commands" / "agent"

        for py_file in agent_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text()
            assert "scripts/tasks/tasks_cli.py" not in content, \
                f"{py_file.name} still references legacy tasks_cli.py"
