"""Tests for m_2_0_7_fix_stale_overrides migration.

Covers:
- Stale override detection and removal
- Genuine user customizations preserved
- Idempotency (second run is no-op)
- Edge cases (no overrides dir, no package root)
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def package_assets(tmp_path: Path) -> Path:
    """Create a minimal package asset tree for comparison."""
    pkg = tmp_path / "pkg" / "software-dev"
    (pkg / "templates").mkdir(parents=True)
    (pkg / "templates" / "spec.md").write_text("current spec content")
    (pkg / "templates" / "plan.md").write_text("current plan content")
    (pkg / "command-templates").mkdir(parents=True)
    (pkg / "command-templates" / "implement.md").write_text("current implement content")
    (pkg / "scripts").mkdir(parents=True)
    (pkg / "scripts" / "deploy.sh").write_text("current deploy script")
    # AGENTS.md at package root (not under mission)
    (tmp_path / "pkg" / "AGENTS.md").write_text("current agents content")
    return tmp_path / "pkg"


@pytest.fixture()
def project_with_stale_overrides(tmp_path: Path, package_assets: Path) -> Path:
    """Create a project with stale overrides (matching current package defaults)."""
    project = tmp_path / "project"
    overrides = project / ".kittify" / "overrides"

    # Stale overrides: byte-identical to current package defaults
    (overrides / "templates").mkdir(parents=True)
    (overrides / "templates" / "spec.md").write_text("current spec content")
    (overrides / "templates" / "plan.md").write_text("current plan content")
    (overrides / "command-templates").mkdir(parents=True)
    (overrides / "command-templates" / "implement.md").write_text("current implement content")

    # Genuine customization: differs from package defaults
    (overrides / "templates" / "tasks.md").write_text("my custom tasks template")

    # Project-specific config
    (project / ".kittify" / "config.yaml").parents[0].mkdir(parents=True, exist_ok=True)
    (project / ".kittify" / "config.yaml").write_text("agents: [claude]")

    return project


class TestFixStaleOverridesDetect:
    """Test detect() logic."""

    def test_detects_stale_overrides(
        self, project_with_stale_overrides: Path, package_assets: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))
        migration = FixStaleOverridesMigration()
        assert migration.detect(project_with_stale_overrides) is True

    def test_no_detection_when_no_overrides_dir(self, tmp_path: Path) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        migration = FixStaleOverridesMigration()
        assert migration.detect(project) is False

    def test_no_detection_when_all_genuine_customizations(
        self, tmp_path: Path, package_assets: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))
        project = tmp_path / "project"
        overrides = project / ".kittify" / "overrides"
        (overrides / "templates").mkdir(parents=True)
        (overrides / "templates" / "spec.md").write_text("genuinely customized content")

        migration = FixStaleOverridesMigration()
        assert migration.detect(project) is False


class TestFixStaleOverridesApply:
    """Test apply() logic."""

    def test_removes_stale_overrides(
        self, project_with_stale_overrides: Path, package_assets: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))
        migration = FixStaleOverridesMigration()
        result = migration.apply(project_with_stale_overrides)

        assert result.success is True
        overrides = project_with_stale_overrides / ".kittify" / "overrides"

        # Stale overrides removed
        assert not (overrides / "templates" / "spec.md").exists()
        assert not (overrides / "templates" / "plan.md").exists()
        assert not (overrides / "command-templates" / "implement.md").exists()

        # Genuine customization preserved
        assert (overrides / "templates" / "tasks.md").exists()
        assert (overrides / "templates" / "tasks.md").read_text() == "my custom tasks template"

    def test_preserves_genuine_customizations(
        self, tmp_path: Path, package_assets: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))
        project = tmp_path / "project"
        overrides = project / ".kittify" / "overrides"
        (overrides / "templates").mkdir(parents=True)
        (overrides / "templates" / "spec.md").write_text("my unique customization")

        migration = FixStaleOverridesMigration()
        result = migration.apply(project)

        assert result.success is True
        assert (overrides / "templates" / "spec.md").exists()
        assert (overrides / "templates" / "spec.md").read_text() == "my unique customization"

    def test_dry_run_no_filesystem_changes(
        self, project_with_stale_overrides: Path, package_assets: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))
        overrides = project_with_stale_overrides / ".kittify" / "overrides"
        files_before = {str(p.relative_to(overrides)) for p in overrides.rglob("*") if p.is_file()}

        migration = FixStaleOverridesMigration()
        result = migration.apply(project_with_stale_overrides, dry_run=True)

        assert result.success is True
        # Should report changes
        assert any("stale override" in c for c in result.changes_made)

        # Filesystem unchanged
        files_after = {str(p.relative_to(overrides)) for p in overrides.rglob("*") if p.is_file()}
        assert files_before == files_after

    def test_idempotent(
        self, project_with_stale_overrides: Path, package_assets: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))
        migration = FixStaleOverridesMigration()

        # First run: removes stale overrides
        result1 = migration.apply(project_with_stale_overrides)
        assert result1.success is True
        assert any("stale override" in c for c in result1.changes_made)

        # Second run: no-op
        result2 = migration.apply(project_with_stale_overrides)
        assert result2.success is True
        assert any("nothing to do" in c.lower() for c in result2.changes_made)

    def test_no_overrides_dir(self, tmp_path: Path) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        migration = FixStaleOverridesMigration()
        result = migration.apply(project)
        assert result.success is True
        assert any("nothing to do" in c.lower() for c in result.changes_made)

    def test_cleans_up_empty_dirs(
        self, tmp_path: Path, package_assets: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))
        project = tmp_path / "project"
        overrides = project / ".kittify" / "overrides"
        # Only stale overrides, no genuine customizations
        (overrides / "templates").mkdir(parents=True)
        (overrides / "templates" / "spec.md").write_text("current spec content")

        migration = FixStaleOverridesMigration()
        migration.apply(project)

        # Empty overrides directory should be cleaned up
        assert not overrides.exists()

    def test_preserves_user_created_files_without_package_counterpart(
        self, tmp_path: Path, package_assets: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Files in overrides/ that have no package counterpart are preserved."""
        from specify_cli.upgrade.migrations.m_2_0_7_fix_stale_overrides import (
            FixStaleOverridesMigration,
        )

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(package_assets))
        project = tmp_path / "project"
        overrides = project / ".kittify" / "overrides"
        (overrides / "templates").mkdir(parents=True)
        (overrides / "templates" / "my-custom-template.md").write_text("user-created content")

        migration = FixStaleOverridesMigration()
        result = migration.apply(project)

        assert result.success is True
        # User-created file preserved (no package counterpart to match against)
        assert (overrides / "templates" / "my-custom-template.md").exists()
