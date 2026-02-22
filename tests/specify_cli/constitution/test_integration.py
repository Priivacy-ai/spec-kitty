"""Integration tests for the constitution workflow."""

import logging
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.constitution import (
    DirectivesConfig,
    GovernanceConfig,
    load_directives_config,
    load_governance_config,
    post_save_hook,
    sync,
)


class TestEndToEndWorkflow:
    def test_write_sync_load_governance(self, tmp_path: Path) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"

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

        result = sync(constitution_path)
        assert result.synced
        assert "governance.yaml" in result.files_written

        config = load_governance_config(tmp_path)
        assert config.testing.min_coverage == 80
        assert config.testing.tdd_required is True
        assert config.testing.framework == "pytest"
        assert config.quality.linting == "ruff"
        assert config.quality.pr_approvals == 2

    def test_write_sync_load_directives(self, tmp_path: Path) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"

        constitution_path.write_text(
            """
## Project Directives

1. Keep tests strict
2. Keep docs in sync
"""
        )

        result = sync(constitution_path)
        assert result.synced
        assert "directives.yaml" in result.files_written

        config = load_directives_config(tmp_path)
        assert len(config.directives) == 2
        assert config.directives[0].id == "DIR-001"

    def test_modify_constitution_triggers_staleness_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"

        constitution_path.write_text("## Testing\n\nCoverage: 80%")
        sync(constitution_path)

        constitution_path.write_text("## Testing\n\nCoverage: 90%")

        caplog.clear()
        load_governance_config(tmp_path)
        assert any("Constitution changed since last sync" in record.message for record in caplog.records)


class TestPostSaveHook:
    def test_post_save_hook_success(self, tmp_path: Path) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"
        constitution_path.write_text("## Testing\n\nCoverage: 80%")

        post_save_hook(constitution_path)

        assert (constitution_dir / "governance.yaml").exists()
        assert (constitution_dir / "directives.yaml").exists()
        assert (constitution_dir / "metadata.yaml").exists()

    def test_post_save_hook_logs_success(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"
        constitution_path.write_text("## Testing\n\nWe require 80% coverage.")

        caplog.clear()
        with caplog.at_level(logging.INFO, logger="specify_cli.constitution.sync"):
            post_save_hook(constitution_path)

        assert any("Constitution synced: 3 YAML files updated" in record.message for record in caplog.records)

    def test_post_save_hook_extraction_failure_no_crash(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        constitution_path = constitution_dir / "constitution.md"
        constitution_path.write_text("## Testing\n\nCoverage: 80%")

        with patch("specify_cli.constitution.sync.sync") as mock_sync:
            mock_sync.side_effect = RuntimeError("Extraction failed")

            caplog.clear()
            post_save_hook(constitution_path)
            assert any("Constitution auto-sync failed" in record.message for record in caplog.records)


class TestLoaderFunctions:
    def test_load_governance_config_missing_yaml_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        config = load_governance_config(tmp_path)

        assert isinstance(config, GovernanceConfig)
        assert config.testing.min_coverage == 0
        assert config.testing.tdd_required is False
        assert any("governance.yaml not found" in record.message for record in caplog.records)

    def test_load_directives_config_missing_yaml_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        config = load_directives_config(tmp_path)

        assert isinstance(config, DirectivesConfig)
        assert len(config.directives) == 0
        assert any("directives.yaml not found" in record.message for record in caplog.records)

    def test_load_governance_config_with_values(self, tmp_path: Path) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        governance_path = constitution_dir / "governance.yaml"

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

        config = load_governance_config(tmp_path)
        assert config.testing.min_coverage == 85
        assert config.testing.tdd_required is True
        assert config.quality.pr_approvals == 2
        assert config.quality.pre_commit_hooks is True


class TestPerformance:
    def test_load_governance_config_performance(self, tmp_path: Path) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        governance_path = constitution_dir / "governance.yaml"

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

        start = time.monotonic()
        config = load_governance_config(tmp_path)
        elapsed = time.monotonic() - start

        assert isinstance(config, GovernanceConfig)
        assert elapsed < 0.1, f"Loading took {elapsed:.3f}s (>100ms)"

    def test_load_directives_config_performance(self, tmp_path: Path) -> None:
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        directives_path = constitution_dir / "directives.yaml"

        directives_path.write_text(
            """
directives:
  - id: D001
    title: Coverage
  - id: D002
    title: TDD
"""
        )

        start = time.monotonic()
        config = load_directives_config(tmp_path)
        elapsed = time.monotonic() - start

        assert isinstance(config, DirectivesConfig)
        assert len(config.directives) == 2
        assert elapsed < 0.1, f"Loading took {elapsed:.3f}s (>100ms)"
