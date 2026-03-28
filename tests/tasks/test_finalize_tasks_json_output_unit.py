"""Unit tests for finalize-tasks JSON output schema.

Extracted from tests/legacy/integration/test_finalize_tasks_json_output.py.
The legacy tests were integration-level (real git repos + subprocess); these
replicate the same behavioural contracts as fast unit tests using mock patches.

Covers:
- commit_hash is 40-char hex when a commit is created
- commit_created is True on first run, False on idempotent second run
- files_committed includes tasks.md and WP file paths
- all 6 required JSON fields are present and correctly typed
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.feature import app

pytestmark = pytest.mark.fast

runner = CliRunner()

_FAKE_SHA = "a" * 40


def _build_feature(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal feature + WP structure under tmp_path.

    Returns (feature_dir, tasks_dir).
    """
    feature_dir = tmp_path / "kitty-specs" / "001-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    (feature_dir / "spec.md").write_text(
        "# Spec\n"
        "## Functional Requirements\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| FR-001 | Test requirement | Covered by WP01. | proposed |\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "## Work Package WP01\n**Requirement Refs**: FR-001\n\n## Work Package WP02\n**Requirement Refs**: FR-001\n",
        encoding="utf-8",
    )
    # Give each WP distinct owned_files to avoid ownership overlap validation errors
    wp_data = {
        "WP01": ("src/module_a/**", "src/module_a/"),
        "WP02": ("src/module_b/**", "src/module_b/"),
    }
    for wp_id in ("WP01", "WP02"):
        owned_file, auth_surface = wp_data[wp_id]
        (tasks_dir / f"{wp_id}-test.md").write_text(
            f"---\n"
            f"work_package_id: {wp_id}\n"
            f"execution_mode: code_change\n"
            f"owned_files:\n  - {owned_file}\n"
            f"authoritative_surface: {auth_surface}\n"
            f"---\n\n# {wp_id}\n",
            encoding="utf-8",
        )
    return feature_dir, tasks_dir


def _patch_context(
    tmp_path: Path, feature_dir: Path, *, commit_success: bool = True, git_status_out: str = "M tasks.md"
):
    """Return a context-manager stack that patches the infrastructure helpers."""
    return (
        patch(
            "specify_cli.cli.commands.agent.feature.locate_project_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.cli.commands.agent.feature._find_feature_directory",
            return_value=feature_dir,
        ),
        patch(
            "specify_cli.cli.commands.agent.feature._show_branch_context",
            return_value=(None, "main"),
        ),
        patch(
            "specify_cli.cli.commands.agent.feature.safe_commit",
            return_value=commit_success,
        ),
        patch(
            "specify_cli.cli.commands.agent.feature.run_command",
            side_effect=_make_run_command(git_status_out),
        ),
        patch(
            "specify_cli.cli.commands.agent.feature.get_emitter",
        ),
    )


def _make_run_command(git_status_out: str):
    """Return a side-effect for run_command that:
    - Returns git_status_out for 'git status --porcelain' calls
    - Returns the fake SHA for 'git rev-parse HEAD' calls
    """

    def _side_effect(cmd, **kwargs):  # noqa: ANN001
        if "status" in cmd and "--porcelain" in cmd:
            return (0, git_status_out, "")
        if "rev-parse" in cmd and "HEAD" in cmd:
            return (0, _FAKE_SHA, "")
        return (0, "", "")

    return _side_effect


class TestFinalizeTasks:
    """Unit tests for finalize-tasks JSON output schema."""

    def test_json_output_commit_hash_is_40_char_hex(self, tmp_path: Path) -> None:
        """commit_hash in JSON output should be a 40-character hex SHA."""
        # Arrange
        feature_dir, _ = _build_feature(tmp_path)

        # Assumption check
        assert (feature_dir / "tasks.md").exists()

        # Act
        with (
            patch("specify_cli.cli.commands.agent.feature.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.agent.feature._find_feature_directory", return_value=feature_dir),
            patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main")),
            patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True),
            patch("specify_cli.cli.commands.agent.feature.run_command", side_effect=_make_run_command("M tasks.md")),
            patch("specify_cli.cli.commands.agent.feature.get_emitter"),
        ):
            result = runner.invoke(app, ["finalize-tasks", "--json"])

        # Assert
        assert result.exit_code == 0, result.stdout
        import json

        lines = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
        payload = json.loads(lines[-1])
        assert "commit_hash" in payload
        commit_hash = payload["commit_hash"]
        assert commit_hash is not None
        assert len(commit_hash) == 40, f"Expected 40-char SHA, got: {commit_hash!r}"
        assert all(c in "0123456789abcdef" for c in commit_hash), (
            f"commit_hash should be lowercase hex, got: {commit_hash!r}"
        )

    def test_json_output_commit_created_true_when_changes_exist(self, tmp_path: Path) -> None:
        """commit_created should be True when relevant files have changes to commit."""
        # Arrange
        feature_dir, _ = _build_feature(tmp_path)

        # Assumption check
        assert (feature_dir / "tasks.md").exists()

        # Act
        with (
            patch("specify_cli.cli.commands.agent.feature.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.agent.feature._find_feature_directory", return_value=feature_dir),
            patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main")),
            patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True),
            patch("specify_cli.cli.commands.agent.feature.run_command", side_effect=_make_run_command("M tasks.md")),
            patch("specify_cli.cli.commands.agent.feature.get_emitter"),
        ):
            result = runner.invoke(app, ["finalize-tasks", "--json"])

        # Assert
        assert result.exit_code == 0, result.stdout
        import json

        lines = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
        payload = json.loads(lines[-1])
        assert payload["commit_created"] is True
        assert isinstance(payload["commit_created"], bool)

    def test_json_output_commit_created_false_when_nothing_to_commit(self, tmp_path: Path) -> None:
        """commit_created should be False when git status reports no relevant changes."""
        # Arrange
        feature_dir, _ = _build_feature(tmp_path)

        # Assumption check
        assert (feature_dir / "tasks.md").exists()

        # Act — git status returns empty output (nothing to commit)
        with (
            patch("specify_cli.cli.commands.agent.feature.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.agent.feature._find_feature_directory", return_value=feature_dir),
            patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main")),
            patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True),
            patch("specify_cli.cli.commands.agent.feature.run_command", side_effect=_make_run_command("")),
            patch("specify_cli.cli.commands.agent.feature.get_emitter"),
        ):
            result = runner.invoke(app, ["finalize-tasks", "--json"])

        # Assert
        assert result.exit_code == 0, result.stdout
        import json

        lines = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
        payload = json.loads(lines[-1])
        assert payload["commit_created"] is False

    def test_json_output_files_committed_includes_tasks_and_wp_files(self, tmp_path: Path) -> None:
        """files_committed should list tasks.md and all WP file paths."""
        # Arrange
        feature_dir, _ = _build_feature(tmp_path)

        # Assumption check
        assert (feature_dir / "tasks" / "WP01-test.md").exists()
        assert (feature_dir / "tasks" / "WP02-test.md").exists()

        # Act
        with (
            patch("specify_cli.cli.commands.agent.feature.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.agent.feature._find_feature_directory", return_value=feature_dir),
            patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main")),
            patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True),
            patch("specify_cli.cli.commands.agent.feature.run_command", side_effect=_make_run_command("M tasks.md")),
            patch("specify_cli.cli.commands.agent.feature.get_emitter"),
        ):
            result = runner.invoke(app, ["finalize-tasks", "--json"])

        # Assert
        assert result.exit_code == 0, result.stdout
        import json

        lines = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
        payload = json.loads(lines[-1])
        assert isinstance(payload["files_committed"], list)
        files = payload["files_committed"]
        assert any("tasks.md" in f for f in files), f"tasks.md not found in {files}"
        assert any("WP01" in f for f in files), f"WP01 not found in {files}"
        assert any("WP02" in f for f in files), f"WP02 not found in {files}"

    def test_json_output_schema_has_all_required_fields(self, tmp_path: Path) -> None:
        """All 6 required JSON fields must be present with correct types."""
        # Arrange
        feature_dir, tasks_dir = _build_feature(tmp_path)
        required_fields = [
            "result",
            "commit_created",
            "commit_hash",
            "files_committed",
            "updated_wp_count",
            "tasks_dir",
        ]

        # Assumption check
        assert (feature_dir / "spec.md").exists()

        # Act
        with (
            patch("specify_cli.cli.commands.agent.feature.locate_project_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.agent.feature._find_feature_directory", return_value=feature_dir),
            patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main")),
            patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True),
            patch("specify_cli.cli.commands.agent.feature.run_command", side_effect=_make_run_command("M tasks.md")),
            patch("specify_cli.cli.commands.agent.feature.get_emitter"),
        ):
            result = runner.invoke(app, ["finalize-tasks", "--json"])

        # Assert
        assert result.exit_code == 0, result.stdout
        import json

        lines = [l for l in result.stdout.splitlines() if l.strip().startswith("{")]
        payload = json.loads(lines[-1])
        for field in required_fields:
            assert field in payload, f"Missing required field: {field!r}"
        assert isinstance(payload["result"], str)
        assert isinstance(payload["commit_created"], bool)
        assert isinstance(payload["commit_hash"], (str, type(None)))
        assert isinstance(payload["files_committed"], list)
        assert isinstance(payload["updated_wp_count"], int)
        assert isinstance(payload["tasks_dir"], str)
