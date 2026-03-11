"""Tests for the map-requirements command and finalize-tasks integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.cli.commands.agent.feature import app as feature_app
from specify_cli.frontmatter import read_frontmatter

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
            f"---\nwork_package_id: \"{wp_id}\"\ntitle: \"{wp_id}\"\nlane: planned\n---\n\n# {wp_id}\n",
            encoding="utf-8",
        )

    return feature_dir


def _read_wp_refs(feature_dir: Path, wp_id: str) -> list[str]:
    """Read requirement_refs from a WP file's frontmatter."""
    tasks_dir = feature_dir / "tasks"
    wp_file = next(tasks_dir.glob(f"{wp_id}*.md"))
    fm, _ = read_frontmatter(wp_file)
    return fm.get("requirement_refs", [])


# --- map-requirements command tests ---

class TestMapRequirementsIndividual:
    """Tests for individual mode (--wp + --refs)."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_writes_to_frontmatter(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        feature_dir = _setup_feature(tmp_path)

        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001,FR-002", "--json"],
        )

        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout.strip())
        assert payload["result"] == "success"
        assert payload["mapped"]["WP01"] == ["FR-001", "FR-002"]

        # Verify frontmatter was written
        refs = _read_wp_refs(feature_dir, "WP01")
        assert refs == ["FR-001", "FR-002"]

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_individual_unions_refs(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Default individual call unions refs, not replaces them."""
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        feature_dir = _setup_feature(tmp_path)

        # First call: map FR-001
        runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--json"],
        )
        # Second call: map FR-002 to same WP
        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-002", "--json"],
        )

        assert result.exit_code == 0
        # Verify BOTH refs are present (union, not replace)
        refs = _read_wp_refs(feature_dir, "WP01")
        assert "FR-001" in refs
        assert "FR-002" in refs

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_replace_overwrites_refs(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """--replace overwrites existing refs instead of merging."""
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        feature_dir = _setup_feature(tmp_path)

        # First call: map FR-001
        runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--json"],
        )
        # Second call: replace with FR-002
        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-002", "--replace", "--json"],
        )

        assert result.exit_code == 0
        refs = _read_wp_refs(feature_dir, "WP01")
        assert refs == ["FR-002"]
        assert "FR-001" not in refs

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_merge_individual_different_wps(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Second individual call for different WP preserves first WP."""
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        feature_dir = _setup_feature(tmp_path)

        # First call for WP01
        runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--json"],
        )
        # Second call for WP02
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
    def test_writes_all_mappings_to_frontmatter(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        feature_dir = _setup_feature(tmp_path)

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

        # Verify frontmatter
        assert _read_wp_refs(feature_dir, "WP01") == ["FR-001", "FR-002"]
        assert _read_wp_refs(feature_dir, "WP02") == ["FR-003"]

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_batch_non_string_refs_p3_regression(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """P3 regression: batch with non-string refs returns error, not crash."""
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        _setup_feature(tmp_path)

        batch = json.dumps({"WP01": [1, 2]})
        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--batch", batch, "--json"],
        )

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip())
        assert "list of strings" in payload["error"]

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_batch_replace_overwrites(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Batch --replace overwrites all targeted WPs."""
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        feature_dir = _setup_feature(tmp_path)

        # First: map FR-001 to WP01
        runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--json"],
        )

        # Second: batch replace WP01 with FR-002
        batch = json.dumps({"WP01": ["FR-002"]})
        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--batch", batch, "--replace", "--json"],
        )

        assert result.exit_code == 0
        refs = _read_wp_refs(feature_dir, "WP01")
        assert refs == ["FR-002"]
        assert "FR-001" not in refs


class TestMapRequirementsStaleRefDetection:
    """Tests for post-merge stale ref validation."""

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_detects_stale_refs_in_other_wps(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """Adding valid FR-001 to WP01 fails if WP02 already has stale FR-999."""
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        feature_dir = _setup_feature(tmp_path)

        # Manually write a stale ref into WP02's frontmatter
        tasks_dir = feature_dir / "tasks"
        wp02_file = next(tasks_dir.glob("WP02*.md"))
        from specify_cli.frontmatter import write_frontmatter
        fm, body = read_frontmatter(wp02_file)
        fm["requirement_refs"] = ["FR-999"]
        write_frontmatter(wp02_file, fm, body)

        # Now try to add valid refs to WP01
        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--json"],
        )

        assert result.exit_code == 1
        payload = json.loads(result.stdout.strip())
        assert "Stale or invalid refs" in payload["error"]
        assert "WP02" in payload["stale_refs"]
        assert "FR-999" in payload["stale_refs"]["WP02"]

    @patch("specify_cli.cli.commands.agent.tasks.locate_project_root")
    @patch("specify_cli.cli.commands.agent.tasks._find_feature_slug")
    @patch("specify_cli.cli.commands.agent.tasks._ensure_target_branch_checked_out")
    def test_replace_fixes_stale_refs(
        self,
        mock_branch: Mock,
        mock_slug: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """--replace can fix a WP with stale refs by overwriting them."""
        mock_locate.return_value = tmp_path
        mock_slug.return_value = "001-test"
        mock_branch.return_value = (tmp_path, "main")
        feature_dir = _setup_feature(tmp_path, wp_ids=["WP01"])

        # Manually write a stale ref
        tasks_dir = feature_dir / "tasks"
        wp01_file = next(tasks_dir.glob("WP01*.md"))
        from specify_cli.frontmatter import write_frontmatter
        fm, body = read_frontmatter(wp01_file)
        fm["requirement_refs"] = ["FR-999"]
        write_frontmatter(wp01_file, fm, body)

        # Replace with valid ref
        result = runner.invoke(
            tasks_app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001,FR-002,FR-003", "--replace", "--json"],
        )

        assert result.exit_code == 0
        refs = _read_wp_refs(feature_dir, "WP01")
        assert "FR-999" not in refs
        assert "FR-001" in refs


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


# --- finalize-tasks integration ---

class TestFinalizeTasksWithFrontmatterRefs:
    """Tests for finalize-tasks reading from WP frontmatter."""

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    @patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True)
    @patch("specify_cli.cli.commands.agent.feature.run_command", return_value=(0, "a" * 40, ""))
    def test_reads_refs_from_frontmatter(
        self,
        mock_run: Mock,
        mock_commit: Mock,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """finalize-tasks reads requirement_refs from WP frontmatter."""
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (feature_dir / "spec.md").write_text(SPEC_CONTENT, encoding="utf-8")

        # WP files with requirement_refs in frontmatter
        (tasks_dir / "WP01-test.md").write_text(
            '---\nwork_package_id: "WP01"\ntitle: "WP01"\nlane: planned\n'
            "requirement_refs:\n  - FR-001\n  - NFR-001\n---\n\n# WP01\n",
            encoding="utf-8",
        )
        (tasks_dir / "WP02-test.md").write_text(
            '---\nwork_package_id: "WP02"\ntitle: "WP02"\nlane: planned\n'
            "requirement_refs:\n  - FR-002\n  - FR-003\n---\n\n# WP02\n",
            encoding="utf-8",
        )

        mock_find.return_value = feature_dir

        # Write tasks.md (no requirement refs in it)
        (feature_dir / "tasks.md").write_text(
            "## Work Package WP01\n**Dependencies**: None\n"
            "## Work Package WP02\n**Dependencies**: WP01\n",
            encoding="utf-8",
        )

        result = runner.invoke(feature_app, ["finalize-tasks", "--json"])

        assert result.exit_code == 0, result.stdout
        json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
        payload = json.loads(json_lines[-1])
        assert payload["result"] == "success"
        assert "FR-001" in payload["requirement_refs_parsed"]["WP01"]
        assert "NFR-001" in payload["requirement_refs_parsed"]["WP01"]
        assert "FR-002" in payload["requirement_refs_parsed"]["WP02"]

    @patch("specify_cli.cli.commands.agent.feature.locate_project_root")
    @patch("specify_cli.cli.commands.agent.feature._find_feature_directory")
    @patch("specify_cli.cli.commands.agent.feature._show_branch_context", return_value=(None, "main"))
    @patch("specify_cli.cli.commands.agent.feature.safe_commit", return_value=True)
    @patch("specify_cli.cli.commands.agent.feature.run_command", return_value=(0, "a" * 40, ""))
    def test_frontmatter_wins_over_tasks_md(
        self,
        mock_run: Mock,
        mock_commit: Mock,
        mock_show_branch: Mock,
        mock_find: Mock,
        mock_locate: Mock,
        tmp_path: Path,
    ):
        """P1 regression: frontmatter refs take priority over tasks.md refs."""
        mock_locate.return_value = tmp_path
        feature_dir = tmp_path / "kitty-specs" / "001-test"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (feature_dir / "spec.md").write_text(SPEC_CONTENT, encoding="utf-8")

        # WP01 frontmatter has all 3 FRs + NFR-001 (the correct, updated mapping)
        (tasks_dir / "WP01-test.md").write_text(
            '---\nwork_package_id: "WP01"\ntitle: "WP01"\nlane: planned\n'
            "requirement_refs:\n  - FR-001\n  - FR-002\n  - FR-003\n  - NFR-001\n---\n\n# WP01\n",
            encoding="utf-8",
        )

        mock_find.return_value = feature_dir

        # tasks.md has only FR-001 (stale subset — if this won, FR-002/FR-003 would be missing)
        (feature_dir / "tasks.md").write_text(
            "## Work Package WP01\n**Dependencies**: None\n"
            "**Requirement Refs**: FR-001\n",
            encoding="utf-8",
        )

        result = runner.invoke(feature_app, ["finalize-tasks", "--json"])

        assert result.exit_code == 0, result.stdout
        json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
        payload = json.loads(json_lines[-1])
        assert payload["result"] == "success"
        # Frontmatter should win: all 3 FRs + NFR-001 present
        wp01_refs = payload["requirement_refs_parsed"]["WP01"]
        assert "FR-001" in wp01_refs
        assert "FR-002" in wp01_refs
        assert "FR-003" in wp01_refs
        assert "NFR-001" in wp01_refs

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
        """No frontmatter refs → parses tasks.md (backward compat)."""
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
        assert "FR-001" in payload["requirement_refs_parsed"]["WP01"]
