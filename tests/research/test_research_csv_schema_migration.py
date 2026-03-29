"""Integration tests for research CSV schema detection migration (0.13.0).

Tests validate that the migration correctly detects schema mismatches in
research mission CSVs and provides informational messages without auto-fixing.
"""

from __future__ import annotations

import json

import pytest

from specify_cli.upgrade.migrations.m_0_13_0_research_csv_schema_check import (
    ResearchCSVSchemaCheckMigration,
)

pytestmark = pytest.mark.fast

@pytest.fixture
def mock_research_project(tmp_path):
    """Create a mock spec-kitty project with research missions."""
    # Create kitty-specs structure
    kitty_specs = tmp_path / "kitty-specs"
    kitty_specs.mkdir()

    return tmp_path


@pytest.fixture
def research_mission_with_correct_schema(mock_research_project):
    """Create a research mission with correct CSV schemas."""
    mission_dir = mock_research_project / "kitty-specs" / "001-test-mission"
    mission_dir.mkdir()

    # Create meta.json
    meta = {"mission": "research"}
    (mission_dir / "meta.json").write_text(json.dumps(meta))

    # Create research directory with correct schemas
    research_dir = mission_dir / "research"
    research_dir.mkdir()

    # Correct evidence-log.csv schema
    (research_dir / "evidence-log.csv").write_text(
        "timestamp,source_type,citation,key_finding,confidence,notes\n"
        "2025-01-25T10:00:00,journal,Citation,Finding,high,Notes\n",
        encoding="utf-8",
    )

    # Correct source-register.csv schema
    (research_dir / "source-register.csv").write_text(
        "source_id,citation,url,accessed_date,relevance,status\n"
        "S001,Citation,https://example.com,2025-01-25,high,reviewed\n",
        encoding="utf-8",
    )

    return mock_research_project


@pytest.fixture
def research_mission_with_wrong_evidence_schema(mock_research_project):
    """Create a research mission with wrong evidence-log.csv schema."""
    mission_dir = mock_research_project / "kitty-specs" / "002-wrong-evidence"
    mission_dir.mkdir()

    # Create meta.json
    meta = {"mission": "research"}
    (mission_dir / "meta.json").write_text(json.dumps(meta))

    # Create research directory with WRONG schema
    research_dir = mission_dir / "research"
    research_dir.mkdir()

    # WRONG evidence-log.csv schema (wrong column names and order)
    (research_dir / "evidence-log.csv").write_text(
        "evidence_id,component,finding,citation,confidence,timestamp,notes\n"
        "E001,Component,Finding,Citation,high,2025-01-25T10:00:00,Notes\n",
        encoding="utf-8",
    )

    return mock_research_project


@pytest.fixture
def research_mission_with_wrong_source_schema(mock_research_project):
    """Create a research mission with wrong source-register.csv schema."""
    mission_dir = mock_research_project / "kitty-specs" / "003-wrong-source"
    mission_dir.mkdir()

    # Create meta.json
    meta = {"mission": "research"}
    (mission_dir / "meta.json").write_text(json.dumps(meta))

    # Create research directory with WRONG schema
    research_dir = mission_dir / "research"
    research_dir.mkdir()

    # WRONG source-register.csv schema
    (research_dir / "source-register.csv").write_text(
        "id,reference,link,date,priority\n1,Reference,http://example.com,2025-01-25,high\n",
        encoding="utf-8",
    )

    return mock_research_project


@pytest.fixture
def software_dev_mission(mock_research_project):
    """Create a software-dev mission (should be skipped by migration)."""
    mission_dir = mock_research_project / "kitty-specs" / "004-software-dev"
    mission_dir.mkdir()

    # Create meta.json with software-dev mission
    meta = {"mission": "software-dev"}
    (mission_dir / "meta.json").write_text(json.dumps(meta))

    return mock_research_project


class TestDetection:
    """Tests for migration detection logic."""

    def test_detect_no_missions(self, mock_research_project):
        """Test detection returns False when no missions exist."""
        migration = ResearchCSVSchemaCheckMigration()
        assert migration.detect(mock_research_project) is False

    def test_detect_correct_schema(self, research_mission_with_correct_schema):
        """Test detection returns False when schemas are correct."""
        migration = ResearchCSVSchemaCheckMigration()
        assert migration.detect(research_mission_with_correct_schema) is False

    def test_detect_wrong_evidence_schema(self, research_mission_with_wrong_evidence_schema):
        """Test detection returns True when evidence-log.csv schema is wrong."""
        migration = ResearchCSVSchemaCheckMigration()
        assert migration.detect(research_mission_with_wrong_evidence_schema) is True

    def test_detect_wrong_source_schema(self, research_mission_with_wrong_source_schema):
        """Test detection returns True when source-register.csv schema is wrong."""
        migration = ResearchCSVSchemaCheckMigration()
        assert migration.detect(research_mission_with_wrong_source_schema) is True

    def test_detect_skips_software_dev(self, software_dev_mission):
        """Test detection skips software-dev missions."""
        migration = ResearchCSVSchemaCheckMigration()
        assert migration.detect(software_dev_mission) is False


class TestMigrationApply:
    """Tests for migration application."""

    def test_apply_no_missions(self, mock_research_project):
        """Test migration handles project with no missions."""
        migration = ResearchCSVSchemaCheckMigration()
        result = migration.apply(mock_research_project, dry_run=False)

        assert result.success is True
        assert len(result.errors) == 0
        # Empty kitty-specs directory means all schemas are correct (no mismatches found)
        assert any("correct" in change.lower() for change in result.changes_made)

    def test_apply_correct_schemas(self, research_mission_with_correct_schema, capsys):
        """Test migration reports success when schemas are correct."""
        migration = ResearchCSVSchemaCheckMigration()
        result = migration.apply(research_mission_with_correct_schema, dry_run=False)

        assert result.success is True
        assert len(result.errors) == 0
        assert any("correct" in change.lower() for change in result.changes_made)

        # Should not print informational report
        captured = capsys.readouterr()
        assert "Schema mismatch" not in captured.out

    def test_apply_wrong_evidence_schema(self, research_mission_with_wrong_evidence_schema, capsys):
        """Test migration reports mismatch for wrong evidence-log.csv schema."""
        migration = ResearchCSVSchemaCheckMigration()
        result = migration.apply(research_mission_with_wrong_evidence_schema, dry_run=False)

        assert result.success is True  # Informational only
        assert len(result.errors) == 0
        assert any("mismatch" in change.lower() for change in result.changes_made)

        # Should print informational report
        captured = capsys.readouterr()
        assert "Research CSV Schema Check" in captured.out
        assert "evidence-log.csv" in captured.out
        assert "Expected:" in captured.out
        assert "Actual:" in captured.out
        assert "timestamp,source_type,citation,key_finding,confidence,notes" in captured.out

    def test_apply_wrong_source_schema(self, research_mission_with_wrong_source_schema, capsys):
        """Test migration reports mismatch for wrong source-register.csv schema."""
        migration = ResearchCSVSchemaCheckMigration()
        result = migration.apply(research_mission_with_wrong_source_schema, dry_run=False)

        assert result.success is True  # Informational only
        assert len(result.errors) == 0
        assert any("mismatch" in change.lower() for change in result.changes_made)

        # Should print informational report
        captured = capsys.readouterr()
        assert "source-register.csv" in captured.out
        assert "source_id,citation,url,accessed_date,relevance,status" in captured.out

    def test_apply_skips_software_dev(self, software_dev_mission):
        """Test migration skips software-dev missions."""
        migration = ResearchCSVSchemaCheckMigration()
        result = migration.apply(software_dev_mission, dry_run=False)

        assert result.success is True
        # Should report no mismatches (skipped non-research mission)
        assert any("correct" in change.lower() for change in result.changes_made)

    def test_apply_dry_run(self, research_mission_with_wrong_evidence_schema, capsys):
        """Test dry run mode produces same output."""
        migration = ResearchCSVSchemaCheckMigration()
        result = migration.apply(research_mission_with_wrong_evidence_schema, dry_run=True)

        assert result.success is True
        assert len(result.errors) == 0

        # Dry run should still report (informational only, no changes made)
        captured = capsys.readouterr()
        assert "schema mismatch" in captured.out.lower()

    def test_apply_provides_migration_tips(self, research_mission_with_wrong_evidence_schema, capsys):
        """Test migration provides actionable migration tips."""
        migration = ResearchCSVSchemaCheckMigration()
        migration.apply(research_mission_with_wrong_evidence_schema, dry_run=False)

        captured = capsys.readouterr()
        # Check for migration tips
        assert "To fix this schema mismatch" in captured.out
        assert "implement.md" in captured.out
        assert "LLM agents can help" in captured.out

    def test_apply_does_not_modify_files(self, research_mission_with_wrong_evidence_schema):
        """Test migration does NOT modify CSV files (informational only)."""
        csv_path = (
            research_mission_with_wrong_evidence_schema
            / "kitty-specs"
            / "002-wrong-evidence"
            / "research"
            / "evidence-log.csv"
        )
        original_content = csv_path.read_text()

        migration = ResearchCSVSchemaCheckMigration()
        migration.apply(research_mission_with_wrong_evidence_schema, dry_run=False)

        # File should be unchanged
        assert csv_path.read_text() == original_content

    def test_can_apply_always_returns_true(self, mock_research_project):
        """Test can_apply always returns True (informational migration)."""
        migration = ResearchCSVSchemaCheckMigration()
        can_apply, reason = migration.can_apply(mock_research_project)

        assert can_apply is True
        assert reason == ""


class TestMultipleMissions:
    """Tests with multiple research missions."""

    def test_mixed_correct_and_wrong_schemas(self, mock_research_project, capsys):
        """Test migration reports only wrong schemas when mix exists."""
        # Create one correct mission
        correct_mission = mock_research_project / "kitty-specs" / "001-correct"
        correct_mission.mkdir()
        (correct_mission / "meta.json").write_text(json.dumps({"mission": "research"}))
        research_dir = correct_mission / "research"
        research_dir.mkdir()
        (research_dir / "evidence-log.csv").write_text("timestamp,source_type,citation,key_finding,confidence,notes\n")

        # Create one wrong mission
        wrong_mission = mock_research_project / "kitty-specs" / "002-wrong"
        wrong_mission.mkdir()
        (wrong_mission / "meta.json").write_text(json.dumps({"mission": "research"}))
        research_dir = wrong_mission / "research"
        research_dir.mkdir()
        (research_dir / "evidence-log.csv").write_text("id,component,finding\n")

        migration = ResearchCSVSchemaCheckMigration()
        result = migration.apply(mock_research_project, dry_run=False)

        assert result.success is True
        captured = capsys.readouterr()

        # Should report only the wrong mission
        assert "002-wrong" in captured.out
        assert "001-correct" not in captured.out
