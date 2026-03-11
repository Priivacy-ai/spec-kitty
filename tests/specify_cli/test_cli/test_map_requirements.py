"""Tests for the map-requirements command and finalize-tasks integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.cli.commands.agent.feature import app as feature_app

runner = CliRunner()

# --- Helpers ---

SPEC_CONTENT = """\
# Spec
## Functional Requirements
| ID | Requirement | Acceptance Criteria | Status |
| --- | --- | --- | --- |
| FR-001 | First requirement | Done | proposed |
| FR-002 | Second requirement | Done | proposed |
| FR-003 | Third requirement | Done | proposed |

## Non-Functional Requirements
| ID | Requirement |
| --- | --- |
| NFR-001 | Performance |
"""


def _setup_feature(tmp_path: Path, *, wp_ids: list[str] | None = None) -> Path:
    """Create a minimal feature directory with spec.md and WP files."""
    feature_dir = tmp_path / "kitty-specs" / "001-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    (feature_dir / "spec.md").write_text(SPEC_CONTENT, encoding="utf-8")

    for wp_id in (wp_ids or ["WP01", "WP02"]):
        (tasks_dir / f"{wp_id}-test.md").write_text(
            f"---\nwork_package_id: \"{wp_id}\"\ntitle: \"{wp_id}\"\n---\n\n# {wp_id}\n",
            encoding="utf-8",
        )

    return feature_dir


# --- map-requirements command tests ---

class TestMapRequirementsIndividual:
    """Tests for individual mode (--wp + --refs)."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_stores_correctly(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        _setup_feature(tmp_path)

        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001,FR-002", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout.strip())
        assert payload["result"] == "success"
        assert payload["mapped"]["WP01"] == ["FR-001", "FR-002"]

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_merge_individual(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Second individual call merges, doesn't replace existing WPs."""
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        _setup_feature(tmp_path)

        # First call
        runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--json"],
        )
        # Second call for different WP
        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP02", "--refs", "FR-002", "--json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout.strip())
        # Both WPs should be in total_mappings
        assert "WP01" in payload["total_mappings"]
        assert "WP02" in payload["total_mappings"]


class TestMapRequirementsBatch:
    """Tests for batch mode (--batch)."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_stores_all_mappings(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        _setup_feature(tmp_path)

        batch = json.dumps({"WP01": ["FR-001", "FR-002"], "WP02": ["FR-003"]})
        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--batch", batch, "--json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout.strip())
        assert payload["result"] == "success"
        assert payload["mapped"]["WP01"] == ["FR-001", "FR-002"]
        assert payload["mapped"]["WP02"] == ["FR-003"]


class TestMapRequirementsValidation:
    """Tests for validation errors."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_validates_unknown_refs(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        _setup_feature(tmp_path)

        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-999", "--json"],
        )

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip())
        assert payload["error"] == "Invalid requirement refs"
        assert "FR-999" in payload["unknown_refs"]

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_validates_wp_exists(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        _setup_feature(tmp_path, wp_ids=["WP01"])

        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP99", "--refs", "FR-001", "--json"],
        )

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip())
        assert payload["error"] == "Unknown WP IDs"
        assert "WP99" in payload["unknown_wps"]

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_validates_ref_format(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        _setup_feature(tmp_path)

        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "INVALID-REF", "--json"],
        )

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip())
        assert payload["error"] == "Invalid requirement ref format"

    def test_rejects_mixed_modes(self):
        """Cannot combine --batch with --wp/--refs."""
        result = runner.invoke(
            tasks_app,
            [
                "map-requirements",
                "--wp", "WP01",
                "--refs", "FR-001",
                "--batch", '{"WP01":["FR-001"]}',
                "--json",
            ],
        )
        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip())
        assert "Cannot combine" in payload["error"]

    def test_rejects_no_args(self):
        """Must provide either --wp + --refs or --batch."""
        result = runner.invoke(tasks_app, ["map-requirements", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip())
        assert "Provide either" in payload["error"]


class TestMapRequirementsCoverage:
    """Tests for coverage summary."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_coverage_summary(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        _setup_feature(tmp_path)

        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout.strip())
        coverage = payload["coverage"]
        assert coverage["total_functional"] == 3
        assert coverage["mapped_functional"] == 1
        assert "FR-002" in coverage["unmapped_functional"]
        assert "FR-003" in coverage["unmapped_functional"]


# --- finalize-tasks integration with requirement-mapping.json ---

class TestFinalizeTasksWithMappingJson:
    """Tests for finalize-tasks reading from requirement-mapping.json."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    @patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True)
    @patch("specify_cli.cli.commands.agent.feature.run_command", return_value=(0, "a" * 40, ""))
    def test_reads_from_mapping_json(
        self,
        mock_run: Mock,
        mock_commit: Mock,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """finalize-tasks should use requirement-mapping.json as primary source."""
        mock_locate.return_value = tmp_path
        feature_dir = _setup_feature(tmp_path)
        mock_find.return_value = feature_dir

        # Write tasks.md (no requirement refs in it)
        (feature_dir / "tasks.md").write_text(
            "## Work Package WP01\n**Dependencies**: None\n"
            "## Work Package WP02\n**Dependencies**: WP01\n",
            encoding="utf-8",
        )

        # Write requirement-mapping.json via the module
        from specify_cli.requirement_mapping import save_requirement_mapping
        save_requirement_mapping(feature_dir, {
            "WP01": ["FR-001", "NFR-001"],
            "WP02": ["FR-002", "FR-003"],
        })

        result = runner.invoke(feature_app, ["finalize-tasks", "--json"])

        assert result.exit_code == 0, result.stdout
        json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
        payload = json.loads(json_lines[-1])
        assert payload["result"] == "success"
        assert payload["mapping_source"] == "api"
        assert payload["requirement_refs_parsed"]["WP01"] == ["FR-001", "NFR-001"]
        assert payload["requirement_refs_parsed"]["WP02"] == ["FR-002", "FR-003"]

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    @patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True)
    @patch("specify_cli.cli.commands.agent.feature.run_command", return_value=(0, "a" * 40, ""))
    def test_falls_back_to_tasks_md(
        self,
        mock_run: Mock,
        mock_commit: Mock,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """No mapping JSON → parses tasks.md (backward compat)."""
        mock_locate.return_value = tmp_path
        feature_dir = _setup_feature(tmp_path, wp_ids=["WP01"])
        mock_find.return_value = feature_dir

        # Write tasks.md WITH requirement refs (old-style)
        (feature_dir / "tasks.md").write_text(
            "## Work Package WP01\n**Dependencies**: None\n**Requirement Refs**: FR-001, FR-002, FR-003\n",
            encoding="utf-8",
        )

        result = runner.invoke(feature_app, ["finalize-tasks", "--json"])

        assert result.exit_code == 0, result.stdout
        json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
        payload = json.loads(json_lines[-1])
        assert payload["result"] == "success"
        assert payload["mapping_source"] == "tasks_md"
        assert "FR-001" in payload["requirement_refs_parsed"]["WP01"]

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    @patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True)
    @patch("specify_cli.cli.commands.agent.feature.run_command", return_value=(0, "a" * 40, ""))
    def test_reports_mapping_source(
        self,
        mock_run: Mock,
        mock_commit: Mock,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """JSON output includes mapping_source field."""
        mock_locate.return_value = tmp_path
        feature_dir = _setup_feature(tmp_path, wp_ids=["WP01"])
        mock_find.return_value = feature_dir

        (feature_dir / "tasks.md").write_text(
            "## Work Package WP01\n**Dependencies**: None\n",
            encoding="utf-8",
        )
        # WP frontmatter has refs
        (feature_dir / "tasks" / "WP01-test.md").write_text(
            "---\nwork_package_id: \"WP01\"\ntitle: \"WP01\"\nrequirement_refs:\n  - FR-001\n  - FR-002\n  - FR-003\n---\n\n# WP01\n",
            encoding="utf-8",
        )

        result = runner.invoke(feature_app, ["finalize-tasks", "--json"])

        assert result.exit_code == 0, result.stdout
        json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
        payload = json.loads(json_lines[-1])
        assert payload["result"] == "success"
        assert payload["mapping_source"] == "frontmatter"
