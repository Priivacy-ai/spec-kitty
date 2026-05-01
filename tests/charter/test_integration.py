"""Integration tests for the charter workflow."""

import logging
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from charter import (
    DirectivesConfig,
    GovernanceConfig,
    load_directives_config,
    load_governance_config,
    post_save_hook,
    sync,
)
from charter.sync import SyncResult, ensure_charter_bundle_fresh

pytestmark = pytest.mark.fast


class TestEndToEndWorkflow:
    def test_write_sync_load_governance(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"

        charter_path.write_text(
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

        result = sync(charter_path)
        assert result.synced
        assert "governance.yaml" in result.files_written

        config = load_governance_config(tmp_path)
        assert config.testing.min_coverage == 80
        assert config.testing.tdd_required is True
        assert config.testing.framework == "pytest"
        assert config.quality.linting == "ruff"
        assert config.quality.pr_approvals == 2

    def test_write_sync_load_directives(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"

        charter_path.write_text(
            """
## Project Directives

1. Keep tests strict
2. Keep docs in sync
"""
        )

        result = sync(charter_path)
        assert result.synced
        assert "directives.yaml" in result.files_written

        config = load_directives_config(tmp_path)
        assert len(config.directives) == 2
        assert config.directives[0].id == "DIR-001"

    def test_modify_charter_auto_syncs_stale_bundle(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"

        charter_path.write_text(
            """
## Testing Standards

We require 80% test coverage. TDD required.
We use pytest as our framework and mypy --strict for type checking.
""",
            encoding="utf-8",
        )
        sync(charter_path)

        charter_path.write_text(
            """
## Testing Standards

We require 90% test coverage. TDD required.
We use pytest as our framework and mypy --strict for type checking.
""",
            encoding="utf-8",
        )

        caplog.clear()
        config = load_governance_config(tmp_path)
        assert config.testing.min_coverage == 90
        assert not any("Run 'spec-kitty charter sync'" in record.message for record in caplog.records)


class TestPostSaveHook:
    def test_post_save_hook_success(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"
        charter_path.write_text("## Testing\n\nCoverage: 80%")

        post_save_hook(charter_path)

        assert (charter_dir / "governance.yaml").exists()
        assert (charter_dir / "directives.yaml").exists()
        assert (charter_dir / "metadata.yaml").exists()

    def test_post_save_hook_logs_success(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"
        charter_path.write_text("## Testing\n\nWe require 80% coverage.")

        caplog.clear()
        with caplog.at_level(logging.INFO, logger="charter.sync"):
            post_save_hook(charter_path)

        assert any("Charter synced: 3 YAML files updated" in record.message for record in caplog.records)

    def test_post_save_hook_extraction_failure_no_crash(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"
        charter_path.write_text("## Testing\n\nCoverage: 80%")

        with patch("charter.sync.sync") as mock_sync:
            mock_sync.side_effect = RuntimeError("Extraction failed")

            caplog.clear()
            post_save_hook(charter_path)
            assert any("Charter auto-sync failed" in record.message for record in caplog.records)


class TestLoaderFunctions:
    def test_load_governance_config_missing_yaml_returns_empty(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        caplog.clear()
        config = load_governance_config(tmp_path)

        assert isinstance(config, GovernanceConfig)
        assert config.testing.min_coverage == 0
        assert config.testing.tdd_required is False
        assert any("governance.yaml not found and charter.md is absent" in record.message for record in caplog.records)

    def test_load_directives_config_missing_yaml_returns_empty(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        caplog.clear()
        config = load_directives_config(tmp_path)

        assert isinstance(config, DirectivesConfig)
        assert len(config.directives) == 0
        assert any("directives.yaml not found and charter.md is absent" in record.message for record in caplog.records)

    def test_load_governance_config_missing_yaml_auto_syncs_when_charter_present(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text(
            """
## Testing Standards

We require 85% test coverage. TDD required.
We use pytest as our framework and mypy --strict for type checking.
""",
            encoding="utf-8",
        )

        config = load_governance_config(tmp_path)

        assert config.testing.min_coverage == 85
        assert (charter_dir / "governance.yaml").exists()
        assert (charter_dir / "directives.yaml").exists()
        assert (charter_dir / "metadata.yaml").exists()

    def test_load_directives_config_missing_yaml_auto_syncs_when_charter_present(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text(
            "## Project Directives\n\n1. Keep tests strict\n2. Keep docs in sync\n",
            encoding="utf-8",
        )

        config = load_directives_config(tmp_path)

        assert len(config.directives) == 2
        assert (charter_dir / "governance.yaml").exists()
        assert (charter_dir / "directives.yaml").exists()
        assert (charter_dir / "metadata.yaml").exists()

    def test_load_governance_config_with_values(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        governance_path = charter_dir / "governance.yaml"

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


class TestEnsureCharterBundleFresh:
    def test_recovers_from_stale_check_exception(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"
        charter_path.write_text("## Testing\n\nCoverage: 80%", encoding="utf-8")
        sync(charter_path)

        call_count = 0

        def raise_then_pass(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("corrupt metadata")
            return (True, "old", "new")

        with patch("charter.sync.is_stale", side_effect=raise_then_pass):
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="charter.sync"):
                result = ensure_charter_bundle_fresh(tmp_path)

        assert result is not None
        assert result.synced
        assert any("Failed to evaluate charter bundle freshness" in r.message for r in caplog.records)

    def test_logs_sync_failure(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text("## Testing\n\nCoverage: 80%", encoding="utf-8")

        with patch("charter.sync.sync") as mock_sync:
            mock_sync.return_value = SyncResult(
                synced=False,
                stale_before=False,
                files_written=[],
                extraction_mode="",
                error="Engine unavailable",
                canonical_root=tmp_path,
            )
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="charter.sync"):
                result = ensure_charter_bundle_fresh(tmp_path)

        assert result is not None
        assert result.error == "Engine unavailable"
        assert any("Charter auto-sync failed" in r.message for r in caplog.records)


class TestLoaderAutoSyncEdgeCases:
    def test_governance_unavailable_after_failed_auto_sync(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text("## Testing\n\nCoverage: 80%", encoding="utf-8")

        with patch("charter.sync.ensure_charter_bundle_fresh") as mock_ensure:
            mock_ensure.return_value = SyncResult(
                synced=False,
                stale_before=False,
                files_written=[],
                extraction_mode="",
                error="Engine unavailable",
                canonical_root=tmp_path,
            )
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="charter.sync"):
                config = load_governance_config(tmp_path)

        assert isinstance(config, GovernanceConfig)
        assert any("governance.yaml unavailable after charter auto-sync" in r.message for r in caplog.records)

    def test_governance_stale_after_sync_failure(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"
        charter_path.write_text("## Testing\n\nCoverage: 80%", encoding="utf-8")
        sync(charter_path)
        charter_path.write_text("## Testing\n\nCoverage: 95%", encoding="utf-8")

        with patch("charter.sync.ensure_charter_bundle_fresh") as mock_ensure:
            mock_ensure.return_value = SyncResult(
                synced=False,
                stale_before=True,
                files_written=[],
                extraction_mode="",
                error="Sync failed",
                canonical_root=tmp_path,
            )
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="charter.sync"):
                config = load_governance_config(tmp_path)

        assert isinstance(config, GovernanceConfig)
        assert any("stale after auto-sync failure" in r.message for r in caplog.records)

    def test_directives_unavailable_after_failed_auto_sync(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text("## Testing\n\nCoverage: 80%", encoding="utf-8")

        with patch("charter.sync.ensure_charter_bundle_fresh") as mock_ensure:
            mock_ensure.return_value = SyncResult(
                synced=False,
                stale_before=False,
                files_written=[],
                extraction_mode="",
                error="Engine unavailable",
                canonical_root=tmp_path,
            )
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="charter.sync"):
                config = load_directives_config(tmp_path)

        assert isinstance(config, DirectivesConfig)
        assert any("directives.yaml unavailable after charter auto-sync" in r.message for r in caplog.records)

    def test_directives_stale_after_sync_failure(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"
        charter_path.write_text("## Directives\n\n1. Keep tests strict", encoding="utf-8")
        sync(charter_path)
        charter_path.write_text("## Directives\n\n1. Updated directive", encoding="utf-8")

        with patch("charter.sync.ensure_charter_bundle_fresh") as mock_ensure:
            mock_ensure.return_value = SyncResult(
                synced=False,
                stale_before=True,
                files_written=[],
                extraction_mode="",
                error="Sync failed",
                canonical_root=tmp_path,
            )
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="charter.sync"):
                config = load_directives_config(tmp_path)

        assert isinstance(config, DirectivesConfig)
        assert any("stale after auto-sync failure" in r.message for r in caplog.records)


class TestPerformance:
    def test_load_governance_config_performance(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        governance_path = charter_dir / "governance.yaml"

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
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        directives_path = charter_dir / "directives.yaml"

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
