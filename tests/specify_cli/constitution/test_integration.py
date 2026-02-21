"""Integration tests for the full constitution workflow.

Tests cover:
- End-to-end workflow: write → sync → load
- Post-save hook success and failure scenarios
- Loader functions with missing files
- Staleness warnings
- Performance requirements
"""

import logging
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.constitution import (
    AgentsConfig,
    GovernanceConfig,
    load_agents_config,
    load_governance_config,
    post_save_hook,
    sync,
)


class TestEndToEndWorkflow:
    """Tests for the complete write → sync → load workflow."""

    def test_write_sync_load_governance(self, tmp_path: Path) -> None:
        """Write constitution → sync → load_governance_config returns values."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"

        # Write constitution with governance content
        constitution_path.write_text(
            """
## Testing Standards

We require 80% test coverage. TDD required.
We use pytest as our framework and mypy --strict for type checking.

## Quality Gates

Use ruff for linting.
PRs require 2 approvals.
Pre-commit hooks required.
"""
        )

        # Sync to extract YAML
        result = sync(constitution_path)
        assert result.synced
        assert "governance.yaml" in result.files_written

        # Load and verify
        config = load_governance_config(tmp_path)
        assert config.testing.min_coverage == 80
        assert config.testing.tdd_required is True
        assert config.testing.framework == "pytest"
        assert config.quality.linting == "ruff"
        assert config.quality.pr_approvals == 2

    def test_write_sync_load_agents(self, tmp_path: Path) -> None:
        """Write constitution → sync → load_agents_config returns profiles."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"

        # Write constitution with agent profiles table
        constitution_path.write_text(
            """
## Agent Configuration

| agent | role | model |
|-------|------|-------|
| claude | implementer | sonnet-4.5 |
| opus | reviewer | opus-4 |
"""
        )

        # Sync to extract YAML
        result = sync(constitution_path)
        assert result.synced
        assert "agents.yaml" in result.files_written

        # Load and verify
        config = load_agents_config(tmp_path)
        assert len(config.profiles) == 2
        assert config.profiles[0].agent_key == "claude"
        assert config.profiles[0].preferred_model == "sonnet-4.5"

    def test_modify_constitution_triggers_staleness_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Modify constitution.md → is_stale() → sync → load warns if stale."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"

        # Initial write and sync
        constitution_path.write_text("## Testing\n\nCoverage: 80%")
        sync(constitution_path)

        # Modify constitution (without syncing)
        constitution_path.write_text("## Testing\n\nCoverage: 90%")

        # Load should warn about staleness
        caplog.clear()
        load_governance_config(tmp_path)
        assert any("Constitution changed since last sync" in record.message for record in caplog.records)


class TestPostSaveHook:
    """Tests for post_save_hook() function."""

    def test_post_save_hook_success(self, tmp_path: Path) -> None:
        """post_save_hook() succeeds → YAML files created."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"
        constitution_path.write_text("## Testing\n\nCoverage: 80%")

        # Call hook
        post_save_hook(constitution_path)

        # Verify YAML files exist
        assert (constitution_dir / "governance.yaml").exists()
        assert (constitution_dir / "agents.yaml").exists()
        assert (constitution_dir / "directives.yaml").exists()
        assert (constitution_dir / "metadata.yaml").exists()

    def test_post_save_hook_logs_success(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """post_save_hook() logs success message."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"
        constitution_path.write_text("## Testing\n\nWe require 80% coverage.")

        caplog.clear()
        with caplog.at_level(logging.INFO, logger="specify_cli.constitution.sync"):
            post_save_hook(constitution_path)

        # Verify log message
        assert any("Constitution synced: 4 YAML files updated" in record.message for record in caplog.records)

    def test_post_save_hook_extraction_failure_no_crash(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """post_save_hook() with extraction error → no crash, warning logged."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"
        constitution_path.write_text("## Testing\n\nCoverage: 80%")

        # Mock sync to raise an exception
        with patch("specify_cli.constitution.sync.sync") as mock_sync:
            mock_sync.side_effect = RuntimeError("Extraction failed")

            # Should not raise
            caplog.clear()
            post_save_hook(constitution_path)

            # Verify warning logged
            assert any("Constitution auto-sync failed" in record.message for record in caplog.records)

    def test_post_save_hook_missing_constitution_graceful(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """post_save_hook() with missing constitution → graceful handling."""
        constitution_path = tmp_path / "nonexistent.md"

        # Should not raise
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="specify_cli.constitution.sync"):
            post_save_hook(constitution_path)

        # Verify warning logged (sync() catches error and returns it in result)
        assert any("Constitution sync warning" in record.message for record in caplog.records)


class TestLoaderFunctions:
    """Tests for load_governance_config() and load_agents_config()."""

    def test_load_governance_config_missing_yaml_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load_governance_config() with missing YAML → empty GovernanceConfig."""
        caplog.clear()
        config = load_governance_config(tmp_path)

        # Verify fallback to empty
        assert isinstance(config, GovernanceConfig)
        assert config.testing.min_coverage == 0
        assert config.testing.tdd_required is False

        # Verify warning logged
        assert any("governance.yaml not found" in record.message for record in caplog.records)

    def test_load_agents_config_missing_yaml_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """load_agents_config() with missing YAML → empty AgentsConfig."""
        caplog.clear()
        config = load_agents_config(tmp_path)

        # Verify fallback to empty
        assert isinstance(config, AgentsConfig)
        assert len(config.profiles) == 0

        # Verify warning logged
        assert any("agents.yaml not found" in record.message for record in caplog.records)

    def test_load_governance_config_with_values(self, tmp_path: Path) -> None:
        """load_governance_config() with valid YAML → returns values."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        governance_path = constitution_dir / "governance.yaml"

        # Write governance YAML
        governance_path.write_text(
            """
testing:
  min_coverage: 85
  tdd_required: true
  framework: pytest
  type_checking: mypy --strict

quality:
  linting: ruff
  pr_approvals: 2
  pre_commit_hooks: true
"""
        )

        # Load and verify
        config = load_governance_config(tmp_path)
        assert config.testing.min_coverage == 85
        assert config.testing.tdd_required is True
        assert config.quality.pr_approvals == 2
        assert config.quality.pre_commit_hooks is True

    def test_load_agents_config_with_profiles(self, tmp_path: Path) -> None:
        """load_agents_config() with valid YAML → returns profiles."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        agents_path = constitution_dir / "agents.yaml"

        # Write agents YAML
        agents_path.write_text(
            """
profiles:
  - agent_key: claude
    role: implementer
    preferred_model: sonnet-4.5
  - agent_key: opus
    role: reviewer
    preferred_model: opus-4
"""
        )

        # Load and verify
        config = load_agents_config(tmp_path)
        assert len(config.profiles) == 2
        assert config.profiles[0].agent_key == "claude"
        assert config.profiles[1].preferred_model == "opus-4"


class TestPerformance:
    """Performance tests for loader functions."""

    def test_load_governance_config_performance(self, tmp_path: Path) -> None:
        """load_governance_config() completes in <100ms (FR-4.5)."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        governance_path = constitution_dir / "governance.yaml"

        # Write governance YAML
        governance_path.write_text(
            """
testing:
  min_coverage: 80
  tdd_required: true
  framework: pytest
quality:
  linting: ruff
  pr_approvals: 2
"""
        )

        # Time the load
        start = time.monotonic()
        config = load_governance_config(tmp_path)
        elapsed = time.monotonic() - start

        assert isinstance(config, GovernanceConfig)
        assert elapsed < 0.1, f"Loading took {elapsed:.3f}s (>100ms)"

    def test_load_agents_config_performance(self, tmp_path: Path) -> None:
        """load_agents_config() completes in <100ms (FR-4.5)."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        agents_path = constitution_dir / "agents.yaml"

        # Write agents YAML with multiple profiles
        agents_path.write_text(
            """
profiles:
  - agent_key: claude
    role: implementer
    preferred_model: sonnet-4.5
  - agent_key: opus
    role: reviewer
    preferred_model: opus-4
  - agent_key: haiku
    role: implementer
    preferred_model: haiku-3.5
"""
        )

        # Time the load
        start = time.monotonic()
        config = load_agents_config(tmp_path)
        elapsed = time.monotonic() - start

        assert isinstance(config, AgentsConfig)
        assert len(config.profiles) == 3
        assert elapsed < 0.1, f"Loading took {elapsed:.3f}s (>100ms)"
