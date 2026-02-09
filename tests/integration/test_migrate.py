"""Tests for specify_cli.runtime.migrate -- migration classification and execution.

Covers:
- T020: classify_asset() classification accuracy
- T021: execute_migration() dry-run and actual execution
- T023: Dry-run correctness and idempotency (G3, 1A-03, 1A-04)
- T024: Customized files moved to overrides (F-Legacy-003, 1A-05)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.runtime.migrate import (
    AssetDisposition,
    MigrationReport,
    classify_asset,
    execute_migration,
)


# ---------------------------------------------------------------------------
# Helpers: set up project and global directory structures
# ---------------------------------------------------------------------------


def _setup_global(global_home: Path, mission: str = "software-dev") -> None:
    """Create a minimal global runtime directory with sample shared assets."""
    mission_dir = global_home / "missions" / mission
    # templates/spec.md
    (mission_dir / "templates").mkdir(parents=True, exist_ok=True)
    (mission_dir / "templates" / "spec.md").write_text("global spec content")
    # templates/plan.md
    (mission_dir / "templates" / "plan.md").write_text("global plan content")
    # command-templates/implement.md
    (mission_dir / "command-templates").mkdir(parents=True, exist_ok=True)
    (mission_dir / "command-templates" / "implement.md").write_text(
        "global implement content"
    )
    # AGENTS.md at global root
    (global_home / "AGENTS.md").write_text("global agents content")
    # scripts/deploy.sh
    (mission_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (mission_dir / "scripts" / "deploy.sh").write_text("global deploy script")


def _setup_project_kittify(
    project_dir: Path,
    *,
    identical_files: dict[str, str] | None = None,
    customized_files: dict[str, str] | None = None,
    project_specific_files: dict[str, str] | None = None,
    unknown_files: dict[str, str] | None = None,
) -> Path:
    """Create a per-project .kittify/ directory with controlled content.

    Args:
        identical_files: rel_path -> content matching global exactly
        customized_files: rel_path -> content differing from global
        project_specific_files: rel_path -> content in project-specific paths
        unknown_files: rel_path -> content in unknown paths

    Returns:
        Path to the .kittify/ directory.
    """
    kittify = project_dir / ".kittify"
    for file_map in [
        identical_files,
        customized_files,
        project_specific_files,
        unknown_files,
    ]:
        if file_map:
            for rel, content in file_map.items():
                p = kittify / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
    return kittify


# ---------------------------------------------------------------------------
# T020: classify_asset() tests
# ---------------------------------------------------------------------------


class TestClassifyAsset:
    """Test the classify_asset() function for all disposition types."""

    def test_project_specific_config_yaml(self, tmp_path: Path) -> None:
        """config.yaml is always PROJECT_SPECIFIC."""
        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "config.yaml"
        f.parent.mkdir(parents=True)
        f.write_text("agents:\n  available:\n    - claude\n")
        global_home = tmp_path / "global"
        global_home.mkdir()

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.PROJECT_SPECIFIC

    def test_project_specific_metadata_yaml(self, tmp_path: Path) -> None:
        """metadata.yaml is always PROJECT_SPECIFIC."""
        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "metadata.yaml"
        f.parent.mkdir(parents=True)
        f.write_text("version: 1.0\n")
        global_home = tmp_path / "global"
        global_home.mkdir()

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.PROJECT_SPECIFIC

    def test_project_specific_memory_dir(self, tmp_path: Path) -> None:
        """Files under memory/ are always PROJECT_SPECIFIC."""
        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "memory" / "notes.md"
        f.parent.mkdir(parents=True)
        f.write_text("some notes")
        global_home = tmp_path / "global"
        global_home.mkdir()

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.PROJECT_SPECIFIC

    def test_project_specific_workspaces(self, tmp_path: Path) -> None:
        """Files under workspaces/ are always PROJECT_SPECIFIC."""
        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "workspaces" / "state.json"
        f.parent.mkdir(parents=True)
        f.write_text("{}")
        global_home = tmp_path / "global"
        global_home.mkdir()

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.PROJECT_SPECIFIC

    def test_project_specific_logs(self, tmp_path: Path) -> None:
        """Files under logs/ are always PROJECT_SPECIFIC."""
        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "logs" / "2026-02-09.log"
        f.parent.mkdir(parents=True)
        f.write_text("log entry")
        global_home = tmp_path / "global"
        global_home.mkdir()

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.PROJECT_SPECIFIC

    def test_project_specific_overrides(self, tmp_path: Path) -> None:
        """Files under overrides/ are always PROJECT_SPECIFIC (already migrated)."""
        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "overrides" / "templates" / "spec.md"
        f.parent.mkdir(parents=True)
        f.write_text("custom override")
        global_home = tmp_path / "global"
        global_home.mkdir()

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.PROJECT_SPECIFIC

    def test_identical_file(self, tmp_path: Path) -> None:
        """File byte-identical to global counterpart is IDENTICAL."""
        global_home = tmp_path / "global"
        _setup_global(global_home)

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "templates" / "spec.md"
        f.parent.mkdir(parents=True)
        f.write_text("global spec content")  # Same as global

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.IDENTICAL

    def test_customized_file(self, tmp_path: Path) -> None:
        """File differing from global counterpart is CUSTOMIZED."""
        global_home = tmp_path / "global"
        _setup_global(global_home)

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "templates" / "spec.md"
        f.parent.mkdir(parents=True)
        f.write_text("customized spec content")  # Differs from global

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.CUSTOMIZED

    def test_customized_file_no_global_counterpart(self, tmp_path: Path) -> None:
        """Shared asset with no global counterpart is CUSTOMIZED."""
        global_home = tmp_path / "global"
        global_home.mkdir()

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "templates" / "custom-template.md"
        f.parent.mkdir(parents=True)
        f.write_text("user-created template")

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.CUSTOMIZED

    def test_agents_md_identical(self, tmp_path: Path) -> None:
        """AGENTS.md byte-identical to global is IDENTICAL."""
        global_home = tmp_path / "global"
        _setup_global(global_home)

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "AGENTS.md"
        f.parent.mkdir(parents=True)
        f.write_text("global agents content")  # Same as global

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.IDENTICAL

    def test_agents_md_customized(self, tmp_path: Path) -> None:
        """AGENTS.md differing from global is CUSTOMIZED."""
        global_home = tmp_path / "global"
        _setup_global(global_home)

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "AGENTS.md"
        f.parent.mkdir(parents=True)
        f.write_text("my custom agents list")  # Differs from global

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.CUSTOMIZED

    def test_command_templates_identical(self, tmp_path: Path) -> None:
        """command-templates file identical to global is IDENTICAL."""
        global_home = tmp_path / "global"
        _setup_global(global_home)

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "command-templates" / "implement.md"
        f.parent.mkdir(parents=True)
        f.write_text("global implement content")  # Same as global

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.IDENTICAL

    def test_scripts_identical(self, tmp_path: Path) -> None:
        """scripts/ file identical to global is IDENTICAL."""
        global_home = tmp_path / "global"
        _setup_global(global_home)

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "scripts" / "deploy.sh"
        f.parent.mkdir(parents=True)
        f.write_text("global deploy script")  # Same as global

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.IDENTICAL

    def test_unknown_path(self, tmp_path: Path) -> None:
        """File in an unrecognized path is UNKNOWN."""
        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "random-stuff" / "notes.txt"
        f.parent.mkdir(parents=True)
        f.write_text("something")
        global_home = tmp_path / "global"
        global_home.mkdir()

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.UNKNOWN

    def test_filecmp_uses_shallow_false(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify filecmp.cmp is called with shallow=False (byte comparison, not just stat)."""
        import filecmp as _filecmp

        calls: list[dict] = []
        original_cmp = _filecmp.cmp

        def tracking_cmp(f1, f2, shallow=True):
            calls.append({"f1": f1, "f2": f2, "shallow": shallow})
            return original_cmp(f1, f2, shallow=shallow)

        monkeypatch.setattr("specify_cli.runtime.migrate.filecmp.cmp", tracking_cmp)

        global_home = tmp_path / "global"
        _setup_global(global_home)

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "templates" / "spec.md"
        f.parent.mkdir(parents=True)
        f.write_text("global spec content")

        classify_asset(f, global_home, kittify)

        assert len(calls) == 1
        assert calls[0]["shallow"] is False


# ---------------------------------------------------------------------------
# T021: execute_migration() tests
# ---------------------------------------------------------------------------


class TestExecuteMigration:
    """Test the execute_migration() function."""

    def test_returns_migration_report(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """execute_migration returns a MigrationReport instance."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        _setup_project_kittify(
            project,
            project_specific_files={"config.yaml": "agents: [claude]"},
        )

        report = execute_migration(project, dry_run=True)
        assert isinstance(report, MigrationReport)

    def test_mixed_dispositions(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reports correct counts for mixed file types."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        _setup_project_kittify(
            project,
            identical_files={
                "templates/spec.md": "global spec content",
                "templates/plan.md": "global plan content",
            },
            customized_files={
                "templates/tasks.md": "my custom tasks template",
            },
            project_specific_files={
                "config.yaml": "agents: [claude]",
                "memory/notes.md": "project notes",
            },
            unknown_files={
                "random/stuff.txt": "mystery file",
            },
        )

        report = execute_migration(project, dry_run=True)
        assert len(report.removed) == 2  # spec.md + plan.md are identical
        assert len(report.moved) == 1  # tasks.md is customized
        assert len(report.kept) == 2  # config.yaml + memory/notes.md
        assert len(report.unknown) == 1  # random/stuff.txt

    def test_actual_execution_removes_identical(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-dry-run removes identical files from filesystem."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            identical_files={"templates/spec.md": "global spec content"},
            project_specific_files={"config.yaml": "keep me"},
        )

        report = execute_migration(project, dry_run=False)

        assert len(report.removed) == 1
        # Identical file should be gone from filesystem
        assert not (kittify / "templates" / "spec.md").exists()
        # Project-specific file should still exist
        assert (kittify / "config.yaml").exists()

    def test_actual_execution_moves_customized_to_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-dry-run moves customized files to overrides/."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            customized_files={"templates/spec.md": "customized spec content"},
        )

        report = execute_migration(project, dry_run=False)

        assert len(report.moved) == 1
        # Original should be gone
        assert not (kittify / "templates" / "spec.md").exists()
        # Override should exist with correct content
        override = kittify / "overrides" / "templates" / "spec.md"
        assert override.exists()
        assert override.read_text() == "customized spec content"

    def test_cleanup_empty_dirs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After removing all files, empty shared asset dirs are cleaned up."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            identical_files={"templates/spec.md": "global spec content"},
        )

        execute_migration(project, dry_run=False)

        # templates/ dir should be cleaned up (it's empty now)
        assert not (kittify / "templates").exists()

    def test_cleanup_does_not_remove_project_specific_dirs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cleanup does NOT remove project-specific directories even if empty."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            project_specific_files={"config.yaml": "keep me"},
        )
        # Create an empty project-specific dir
        (kittify / "memory").mkdir(exist_ok=True)

        execute_migration(project, dry_run=False)

        # memory/ should still exist even though it's empty
        assert (kittify / "memory").exists()


# ---------------------------------------------------------------------------
# T023: Dry-run and idempotency tests (G3, 1A-03, 1A-04)
# ---------------------------------------------------------------------------


class TestMigrateDryRun:
    """Dry-run reports correct dispositions without modifying FS (G3, 1A-03)."""

    def test_dry_run_no_filesystem_changes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dry-run must not modify any files on the filesystem."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            identical_files={"templates/spec.md": "global spec content"},
            customized_files={"templates/tasks.md": "my custom tasks"},
            project_specific_files={"config.yaml": "keep me"},
        )

        # Capture filesystem state before
        files_before = set(kittify.rglob("*"))

        report = execute_migration(project, dry_run=True)

        # Verify report has correct dispositions
        assert len(report.removed) == 1
        assert len(report.moved) == 1
        assert len(report.kept) == 1
        assert report.dry_run is True

        # Verify filesystem is UNCHANGED
        files_after = set(kittify.rglob("*"))
        assert files_before == files_after

        # Verify all original files still exist with original content
        assert (kittify / "templates" / "spec.md").read_text() == "global spec content"
        assert (kittify / "templates" / "tasks.md").read_text() == "my custom tasks"
        assert (kittify / "config.yaml").read_text() == "keep me"


class TestMigrateIdempotent:
    """Running migrate twice produces identical outcome (G3, 1A-04)."""

    def test_migrate_idempotent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Second run on already-migrated project is a no-op."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        _setup_project_kittify(
            project,
            identical_files={
                "templates/spec.md": "global spec content",
                "templates/plan.md": "global plan content",
            },
            customized_files={
                "templates/tasks.md": "my custom tasks",
            },
            project_specific_files={
                "config.yaml": "keep me",
            },
        )

        # First migration
        report1 = execute_migration(project, dry_run=False)
        assert len(report1.removed) == 2
        assert len(report1.moved) == 1

        # Capture state after first migration
        kittify = project / ".kittify"
        state_after_first = {
            str(p.relative_to(kittify)): p.read_text()
            for p in kittify.rglob("*")
            if p.is_file()
        }

        # Second migration: should be a no-op
        report2 = execute_migration(project, dry_run=False)

        # No files should be removed or moved on second run
        assert len(report2.removed) == 0
        assert len(report2.moved) == 0
        # The override is now project-specific (under overrides/)
        # config.yaml is project-specific
        assert len(report2.kept) >= 1

        # Filesystem state should be identical
        state_after_second = {
            str(p.relative_to(kittify)): p.read_text()
            for p in kittify.rglob("*")
            if p.is_file()
        }
        assert state_after_first == state_after_second

    def test_no_errors_on_empty_kittify(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Migration on an empty .kittify/ dir produces no errors."""
        global_home = tmp_path / "global"
        global_home.mkdir()
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        report = execute_migration(project, dry_run=False)
        assert len(report.removed) == 0
        assert len(report.moved) == 0
        assert len(report.kept) == 0
        assert len(report.unknown) == 0


# ---------------------------------------------------------------------------
# T024: Customized files moved to overrides (F-Legacy-003, 1A-05)
# ---------------------------------------------------------------------------


class TestCustomizedFilesMovedToOverrides:
    """Customized files moved to .kittify/overrides/ (F-Legacy-003, 1A-05)."""

    def test_customized_files_moved_to_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Customized files end up in .kittify/overrides/ with correct relative path."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            customized_files={"templates/spec.md": "customized content"},
        )

        report = execute_migration(project)

        # Verify: customized file moved to overrides
        assert len(report.moved) == 1
        src, dst = report.moved[0]
        assert src == kittify / "templates" / "spec.md"
        assert dst == kittify / "overrides" / "templates" / "spec.md"

        # Verify on filesystem
        assert (kittify / "overrides" / "templates" / "spec.md").exists()
        assert (
            (kittify / "overrides" / "templates" / "spec.md").read_text()
            == "customized content"
        )
        # Verify: original location removed
        assert not (kittify / "templates" / "spec.md").exists()

    def test_multiple_customized_files_preserve_hierarchy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multiple customized files maintain their directory hierarchy under overrides/."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            customized_files={
                "templates/spec.md": "custom spec",
                "command-templates/implement.md": "custom implement",
                "scripts/deploy.sh": "custom deploy",
            },
        )

        report = execute_migration(project)

        assert len(report.moved) == 3

        # All should exist under overrides/
        assert (kittify / "overrides" / "templates" / "spec.md").exists()
        assert (kittify / "overrides" / "command-templates" / "implement.md").exists()
        assert (kittify / "overrides" / "scripts" / "deploy.sh").exists()

        # Content preserved
        assert (
            (kittify / "overrides" / "templates" / "spec.md").read_text()
            == "custom spec"
        )
        assert (
            (kittify / "overrides" / "command-templates" / "implement.md").read_text()
            == "custom implement"
        )
        assert (
            (kittify / "overrides" / "scripts" / "deploy.sh").read_text()
            == "custom deploy"
        )

    def test_customized_agents_md_moved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Customized AGENTS.md (root-level shared file) is moved to overrides/."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            customized_files={"AGENTS.md": "my custom agents list"},
        )

        report = execute_migration(project)

        assert len(report.moved) == 1
        assert (kittify / "overrides" / "AGENTS.md").exists()
        assert (kittify / "overrides" / "AGENTS.md").read_text() == "my custom agents list"
        assert not (kittify / "AGENTS.md").exists()

    def test_mix_of_identical_and_customized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Identical files removed, customized moved; project-specific untouched."""
        global_home = tmp_path / "global"
        _setup_global(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        kittify = _setup_project_kittify(
            project,
            identical_files={"templates/spec.md": "global spec content"},
            customized_files={"templates/plan.md": "my custom plan"},
            project_specific_files={"config.yaml": "my config"},
        )

        report = execute_migration(project)

        # Identical removed
        assert len(report.removed) == 1
        assert not (kittify / "templates" / "spec.md").exists()

        # Customized moved
        assert len(report.moved) == 1
        assert (kittify / "overrides" / "templates" / "plan.md").exists()
        assert (kittify / "overrides" / "templates" / "plan.md").read_text() == "my custom plan"

        # Project-specific kept
        assert len(report.kept) == 1
        assert (kittify / "config.yaml").exists()
        assert (kittify / "config.yaml").read_text() == "my config"


# ---------------------------------------------------------------------------
# T020 extended: classify_asset with global fallback path
# ---------------------------------------------------------------------------


class TestClassifyAssetGlobalFallback:
    """Test classify_asset falls back to direct global path when mission path missing."""

    def test_falls_back_to_global_root(self, tmp_path: Path) -> None:
        """When mission-specific path doesn't exist, tries global root."""
        global_home = tmp_path / "global"
        # Put AGENTS.md only at global root (not under missions/)
        (global_home / "AGENTS.md").parent.mkdir(parents=True, exist_ok=True)
        (global_home / "AGENTS.md").write_text("global agents")

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "AGENTS.md"
        f.parent.mkdir(parents=True)
        f.write_text("global agents")  # Identical

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.IDENTICAL

    def test_mission_path_takes_precedence(self, tmp_path: Path) -> None:
        """Mission-specific path is checked before global root."""
        global_home = tmp_path / "global"
        # Same filename at both locations with different content
        mission_dir = global_home / "missions" / "software-dev" / "templates"
        mission_dir.mkdir(parents=True)
        (mission_dir / "spec.md").write_text("mission version")
        (global_home / "templates").mkdir(parents=True)
        (global_home / "templates" / "spec.md").write_text("root version")

        kittify = tmp_path / "project" / ".kittify"
        f = kittify / "templates" / "spec.md"
        f.parent.mkdir(parents=True)
        f.write_text("mission version")  # Matches mission-specific

        result = classify_asset(f, global_home, kittify)
        assert result == AssetDisposition.IDENTICAL


# ---------------------------------------------------------------------------
# MigrationReport dataclass tests
# ---------------------------------------------------------------------------


class TestMigrationReport:
    """Test MigrationReport dataclass defaults and behavior."""

    def test_default_values(self) -> None:
        """Report has empty lists and dry_run=False by default."""
        report = MigrationReport()
        assert report.removed == []
        assert report.moved == []
        assert report.kept == []
        assert report.unknown == []
        assert report.dry_run is False

    def test_dry_run_flag(self) -> None:
        """dry_run flag can be set at construction."""
        report = MigrationReport(dry_run=True)
        assert report.dry_run is True
