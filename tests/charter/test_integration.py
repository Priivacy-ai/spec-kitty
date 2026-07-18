"""Integration tests for the charter governance/directives loaders (IC-04 / WP04).

The prose->triad scrape (``charter.md`` -> ``governance.yaml`` /
``directives.yaml`` / ``metadata.yaml``) is retired. ``load_governance_config``
/ ``load_directives_config`` now read the hand-authored ``governance:`` /
``directives:`` sections directly from the git-tracked ``charter.yaml``
(INV-3: no governance/directives DECISION reads charter.md prose or the
retired triad files). ``sync()`` / ``ensure_charter_bundle_fresh()`` are
retained for their ``charter.md`` staleness-check contract (other charter-layer
modules still call them for canonical-root resolution), but no longer extract
or write anything -- ``post_save_hook`` (whose only job was triggering that
extraction) is retired outright.
"""

import logging
from pathlib import Path

import pytest

from charter import (
    DirectivesConfig,
    GovernanceConfig,
    load_directives_config,
    load_governance_config,
    sync,
)
from charter.bundle import CHARTER_YAML
from charter.sync import SyncResult, ensure_charter_bundle_fresh

pytestmark = pytest.mark.fast


def _write_charter_yaml(repo_root: Path, document: str) -> Path:
    charter_yaml_path = repo_root / CHARTER_YAML
    charter_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    charter_yaml_path.write_text(document, encoding="utf-8")
    return charter_yaml_path


class TestLoadersReadCharterYaml:
    """T016 / ATDD (red-first until T016): the loaders read the authored
    ``governance:`` / ``directives:`` sections directly from charter.yaml."""

    def test_load_governance_config_reads_charter_yaml(self, tmp_path: Path) -> None:
        _write_charter_yaml(
            tmp_path,
            """
governance:
  testing:
    min_coverage: 85
    tdd_required: true
    framework: pytest
    type_checking: mypy --strict
  quality:
    linting: ruff
    pr_approvals: 2
    pre_commit_hooks: true
directives: {}
""",
        )

        config = load_governance_config(tmp_path)

        assert config.testing.min_coverage == 85
        assert config.testing.tdd_required is True
        assert config.testing.framework == "pytest"
        assert config.quality.linting == "ruff"
        assert config.quality.pr_approvals == 2
        assert config.quality.pre_commit_hooks is True

    def test_load_directives_config_reads_charter_yaml(self, tmp_path: Path) -> None:
        _write_charter_yaml(
            tmp_path,
            """
governance: {}
directives:
  directives:
    - id: DIR-001
      title: Keep tests strict
      description: Keep tests strict
      severity: warn
    - id: DIR-002
      title: Keep docs in sync
      description: Keep docs in sync
      severity: warn
""",
        )

        config = load_directives_config(tmp_path)

        assert {d.id for d in config.directives} == {"DIR-001", "DIR-002"}
        assert config.directives[0].id == "DIR-001"

    def test_load_governance_config_missing_charter_yaml_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="charter.sync"):
            config = load_governance_config(tmp_path)

        assert isinstance(config, GovernanceConfig)
        assert config.testing.min_coverage == 0
        assert config.testing.tdd_required is False
        assert any("charter.yaml governance section not found" in record.message for record in caplog.records)
        assert all(record.levelno < logging.WARNING for record in caplog.records)

    def test_load_directives_config_missing_charter_yaml_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="charter.sync"):
            config = load_directives_config(tmp_path)

        assert isinstance(config, DirectivesConfig)
        assert len(config.directives) == 0
        assert any("charter.yaml directives section not found" in record.message for record in caplog.records)
        assert all(record.levelno < logging.WARNING for record in caplog.records)

    def test_load_governance_config_charter_yaml_without_governance_section(self, tmp_path: Path) -> None:
        """A charter.yaml present but without a 'governance' key falls back
        to an empty GovernanceConfig, same as a missing charter.yaml."""
        _write_charter_yaml(tmp_path, "directives: {}\n")

        config = load_governance_config(tmp_path)

        assert isinstance(config, GovernanceConfig)
        assert config.testing.min_coverage == 0

    def test_governance_and_directives_are_independent_sections(self, tmp_path: Path) -> None:
        """Charter.md presence/absence is irrelevant now -- only charter.yaml
        matters; a charter.md-only tree (no charter.yaml at all) still
        yields empty configs, never an exception (INV-3: no prose fallback)."""
        (tmp_path / ".kittify" / "charter").mkdir(parents=True)
        (tmp_path / ".kittify" / "charter" / "charter.md").write_text(
            "## Testing\n\nWe require 80% coverage.\n", encoding="utf-8"
        )

        gov = load_governance_config(tmp_path)
        directives = load_directives_config(tmp_path)

        assert gov.testing.min_coverage == 0, "governance must never be scraped from charter.md prose"
        assert directives.directives == []


class TestSyncNoLongerExtracts:
    """T017: sync()'s prose->triad scrape is retired -- it now only reports
    ``charter.md`` staleness, never writes governance/directives/metadata."""

    def test_sync_never_writes_triad_files(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"
        charter_path.write_text("## Testing\n\nWe require 80% coverage.\n", encoding="utf-8")

        result = sync(charter_path)

        assert result.synced is False
        assert result.files_written == []
        assert result.error is None
        for name in ("governance.yaml", "directives.yaml", "metadata.yaml"):
            assert not (charter_dir / name).exists()

    def test_sync_reports_stale_before_accurately(self, tmp_path: Path) -> None:
        """The staleness check itself is retained -- other callers
        (``ensure_charter_bundle_fresh``, the ``charter sync`` CLI command)
        still rely on ``stale_before``."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        charter_path = charter_dir / "charter.md"
        charter_path.write_text("## Testing\n\nCoverage: 80%", encoding="utf-8")

        # No metadata.yaml exists at all (never will again) -- always "stale".
        first = sync(charter_path)
        assert first.stale_before is True

    def test_sync_error_path_still_reports_via_syncresult(self, tmp_path: Path) -> None:
        missing_charter = tmp_path / "does-not-exist.md"

        result = sync(missing_charter)

        assert result.synced is False
        assert result.error is not None


class TestEnsureCharterBundleFresh:
    """``ensure_charter_bundle_fresh`` retains its canonical-root resolution
    contract (FR-010) -- unaffected by the prose->triad scrape retirement,
    since ``CANONICAL_MANIFEST.derived_files`` is already empty (WP01)."""

    def test_returns_none_without_charter_md(self, tmp_path: Path) -> None:
        assert ensure_charter_bundle_fresh(tmp_path) is None

    def test_returns_syncresult_with_canonical_root_when_charter_md_present(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text("## Testing\n\nCoverage: 80%", encoding="utf-8")

        result = ensure_charter_bundle_fresh(tmp_path)

        assert result is not None
        assert result.canonical_root == tmp_path
        assert result.synced is False

    def test_logs_sync_failure(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from unittest.mock import patch

        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text("## Testing\n\nCoverage: 80%", encoding="utf-8")

        with patch("charter.sync.sync") as mock_sync:
            mock_sync.return_value = SyncResult(
                synced=False, stale_before=False, files_written=[],
                extraction_mode="", error="Engine unavailable",
                canonical_root=tmp_path,
            )
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="charter.sync"):
                result = ensure_charter_bundle_fresh(tmp_path)

        assert result is not None
        assert result.error == "Engine unavailable"
        assert any("Charter auto-sync failed" in r.message for r in caplog.records)


class TestPerformance:
    @pytest.mark.timeout(2)
    def test_load_governance_config_performance(self, tmp_path: Path) -> None:
        _write_charter_yaml(
            tmp_path,
            """
governance:
  testing:
    min_coverage: 80
    tdd_required: true
    framework: pytest
  quality:
    linting: ruff
    pr_approvals: 2
""",
        )

        config = load_governance_config(tmp_path)

        assert isinstance(config, GovernanceConfig)

    @pytest.mark.timeout(2)
    def test_load_directives_config_performance(self, tmp_path: Path) -> None:
        _write_charter_yaml(
            tmp_path,
            """
directives:
  directives:
    - id: D001
      title: Coverage
    - id: D002
      title: TDD
""",
        )

        config = load_directives_config(tmp_path)

        assert isinstance(config, DirectivesConfig)
        assert {d.id for d in config.directives} == {"D001", "D002"}
