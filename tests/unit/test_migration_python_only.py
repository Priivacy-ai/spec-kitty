"""Tests for the m_0_10_0_python_only migration."""

from __future__ import annotations

import pytest
from pathlib import Path
from specify_cli.upgrade.migrations.m_0_10_0_python_only import PythonOnlyMigration


@pytest.fixture
def migration():
    """Create migration instance."""
    return PythonOnlyMigration()


@pytest.fixture
def mock_project_with_bash(tmp_path: Path) -> Path:
    """Create a mock project with bash scripts."""
    # Create .kittify structure
    kittify_bash = tmp_path / ".kittify" / "scripts" / "bash"
    kittify_bash.mkdir(parents=True)

    # Create package bash scripts
    scripts = [
        "create-new-feature.sh",
        "check-prerequisites.sh",
        "setup-plan.sh",
        "tasks-move-to-lane.sh",
        "accept-feature.sh",
        "merge-feature.sh",
        "common.sh",
    ]

    for script in scripts:
        (kittify_bash / script).write_text(f"#!/bin/bash\necho {script}")

    # Create PowerShell scripts
    kittify_ps = tmp_path / ".kittify" / "scripts" / "powershell"
    kittify_ps.mkdir(parents=True)

    ps_scripts = [
        "create-new-feature.ps1",
        "check-prerequisites.ps1",
    ]

    for script in ps_scripts:
        (kittify_ps / script).write_text(f"# PowerShell\nWrite-Host {script}")

    # Create command templates
    templates_dir = tmp_path / ".kittify" / "templates" / "command-templates"
    templates_dir.mkdir(parents=True)

    (templates_dir / "specify.md").write_text("""---
description: Create feature
scripts:
  sh: .kittify/scripts/bash/create-new-feature.sh --json
  ps: .kittify/scripts/powershell/create-new-feature.ps1 -Json
---
Run .kittify/scripts/bash/create-new-feature.sh to create a feature.
Use tasks_cli.py move to move tasks.
""")

    (templates_dir / "implement.md").write_text("""---
description: Implement
---
Use scripts/bash/tasks-move-to-lane.sh to move tasks.
Call .kittify/scripts/bash/validate-task-workflow.sh for validation.
""")

    return tmp_path


@pytest.fixture
def mock_project_with_worktrees(mock_project_with_bash: Path) -> Path:
    """Add worktrees with bash scripts."""
    worktrees_dir = mock_project_with_bash / ".worktrees"
    worktrees_dir.mkdir()

    # Create worktree with bash scripts
    wt1 = worktrees_dir / "001-feature-one"
    wt1_bash = wt1 / ".kittify" / "scripts" / "bash"
    wt1_bash.mkdir(parents=True)

    (wt1_bash / "create-new-feature.sh").write_text("#!/bin/bash\necho wt1")
    (wt1_bash / "common.sh").write_text("#!/bin/bash\necho common")

    # Create second worktree
    wt2 = worktrees_dir / "002-feature-two"
    wt2_bash = wt2 / ".kittify" / "scripts" / "bash"
    wt2_bash.mkdir(parents=True)

    (wt2_bash / "setup-plan.sh").write_text("#!/bin/bash\necho wt2")

    return mock_project_with_bash


def test_detect_bash_scripts(migration, mock_project_with_bash):
    """Test detection of bash scripts."""
    assert migration.detect(mock_project_with_bash) is True


def test_detect_no_bash_scripts(migration, tmp_path):
    """Test detection when no bash scripts exist."""
    assert migration.detect(tmp_path) is False


def test_detect_empty_bash_directory(migration, tmp_path):
    """Test detection with empty bash directory."""
    bash_dir = tmp_path / ".kittify" / "scripts" / "bash"
    bash_dir.mkdir(parents=True)

    assert migration.detect(tmp_path) is False


def test_can_apply(migration, mock_project_with_bash):
    """Test migration can be applied."""
    can_apply, reason = migration.can_apply(mock_project_with_bash)
    assert can_apply is True
    assert reason == ""


def test_remove_bash_scripts(migration, mock_project_with_bash):
    """Test removal of bash scripts."""
    result = migration.apply(mock_project_with_bash, dry_run=False)

    assert result.success is True
    assert len(result.changes_made) > 0

    # Verify bash scripts removed
    bash_dir = mock_project_with_bash / ".kittify" / "scripts" / "bash"
    assert not bash_dir.exists() or not any(bash_dir.iterdir())

    # Verify PowerShell scripts removed
    ps_dir = mock_project_with_bash / ".kittify" / "scripts" / "powershell"
    assert not ps_dir.exists() or not any(ps_dir.iterdir())


def test_remove_bash_scripts_dry_run(migration, mock_project_with_bash):
    """Test dry run doesn't remove scripts."""
    result = migration.apply(mock_project_with_bash, dry_run=True)

    assert result.success is True
    assert len(result.changes_made) > 0
    assert any("Would remove" in change for change in result.changes_made)

    # Verify scripts still exist
    bash_dir = mock_project_with_bash / ".kittify" / "scripts" / "bash"
    assert bash_dir.exists()
    assert any(bash_dir.glob("*.sh"))


def test_cleanup_worktree_scripts(migration, mock_project_with_worktrees):
    """Test cleanup of worktree bash scripts."""
    result = migration.apply(mock_project_with_worktrees, dry_run=False)

    assert result.success is True

    # Verify worktree bash scripts removed
    wt1_bash = mock_project_with_worktrees / ".worktrees" / "001-feature-one" / ".kittify" / "scripts" / "bash"
    assert not wt1_bash.exists() or not any(wt1_bash.iterdir())

    wt2_bash = mock_project_with_worktrees / ".worktrees" / "002-feature-two" / ".kittify" / "scripts" / "bash"
    assert not wt2_bash.exists() or not any(wt2_bash.iterdir())


def test_update_command_templates(migration, mock_project_with_bash):
    """Test updating slash command templates."""
    result = migration.apply(mock_project_with_bash, dry_run=False)

    assert result.success is True

    # Verify specify.md updated
    specify_md = mock_project_with_bash / ".kittify" / "templates" / "command-templates" / "specify.md"
    content = specify_md.read_text()

    assert "spec-kitty agent create-feature" in content
    assert ".kittify/scripts/bash/create-new-feature.sh" not in content
    # Migration replaces tasks_cli.py move with spec-kitty agent move-task
    assert "spec-kitty agent move-task" in content
    assert "tasks_cli.py move" not in content


def test_update_templates_dry_run(migration, mock_project_with_bash):
    """Test template update dry run."""
    result = migration.apply(mock_project_with_bash, dry_run=True)

    assert result.success is True
    assert any("Would update" in change for change in result.changes_made)

    # Verify templates NOT updated
    specify_md = mock_project_with_bash / ".kittify" / "templates" / "command-templates" / "specify.md"
    content = specify_md.read_text()

    assert ".kittify/scripts/bash/create-new-feature.sh" in content


def test_detect_custom_modifications(migration, tmp_path):
    """Test detection of custom bash scripts."""
    bash_dir = tmp_path / ".kittify" / "scripts" / "bash"
    bash_dir.mkdir(parents=True)

    # Add custom script
    (bash_dir / "my-custom-script.sh").write_text("#!/bin/bash\necho custom")

    # Add templates directory so migration doesn't fail
    templates_dir = tmp_path / ".kittify" / "templates" / "command-templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "test.md").write_text("Test template")

    result = migration.apply(tmp_path, dry_run=False)

    assert result.success is True
    assert len(result.warnings) > 0
    assert any("my-custom-script.sh" in warning for warning in result.warnings)


def test_idempotent_migration(migration, mock_project_with_bash):
    """Test migration is idempotent."""
    # Run migration twice
    result1 = migration.apply(mock_project_with_bash, dry_run=False)
    assert result1.success is True

    result2 = migration.apply(mock_project_with_bash, dry_run=False)
    assert result2.success is True

    # Second run should warn about already migrated
    assert len(result2.warnings) > 0


def test_template_replacement_patterns(migration, tmp_path):
    """Test all bash → Python replacement patterns."""
    templates_dir = tmp_path / ".kittify" / "templates" / "command-templates"
    templates_dir.mkdir(parents=True)

    test_template = templates_dir / "test.md"
    test_template.write_text("""
Use .kittify/scripts/bash/create-new-feature.sh for creation.
Run scripts/bash/check-prerequisites.sh for validation.
Call tasks_cli.py move to move tasks.
Use tasks_cli.py list to list tasks.
""")

    result = migration.apply(tmp_path, dry_run=False)

    assert result.success is True

    content = test_template.read_text()
    assert "spec-kitty agent create-feature" in content
    assert "spec-kitty agent check-prerequisites" in content
    # Migration replaces tasks_cli.py move/list with spec-kitty agent commands
    assert "spec-kitty agent move-task" in content
    assert "spec-kitty agent list-tasks" in content


def test_migration_with_missing_templates_dir(migration, tmp_path):
    """Test migration handles missing templates directory."""
    bash_dir = tmp_path / ".kittify" / "scripts" / "bash"
    bash_dir.mkdir(parents=True)

    (bash_dir / "create-new-feature.sh").write_text("#!/bin/bash\necho test")

    result = migration.apply(tmp_path, dry_run=False)

    # Should succeed gracefully with message about missing templates
    # (Behavior changed in v0.10.9 to defer to repair migration)
    assert result.success is True
    assert len(result.errors) == 0
    assert any("Templates directory not found" in change for change in result.changes_made)


def test_migration_result_structure(migration, mock_project_with_bash):
    """Test migration result has correct structure."""
    result = migration.apply(mock_project_with_bash, dry_run=False)

    assert hasattr(result, "success")
    assert hasattr(result, "changes_made")
    assert hasattr(result, "errors")
    assert hasattr(result, "warnings")

    assert isinstance(result.changes_made, list)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)


def test_package_scripts_list(migration):
    """Test PACKAGE_SCRIPTS constant is complete."""
    expected_scripts = {
        "common.sh",
        "create-new-feature.sh",
        "check-prerequisites.sh",
        "setup-plan.sh",
        "update-agent-context.sh",
        "accept-feature.sh",
        "merge-feature.sh",
        "tasks-move-to-lane.sh",
        "tasks-list-lanes.sh",
        "mark-task-status.sh",
        "tasks-add-history-entry.sh",
        "tasks-rollback-move.sh",
        "validate-task-workflow.sh",
        "move-task-to-doing.sh",
    }

    assert set(migration.PACKAGE_SCRIPTS) == expected_scripts


def test_command_replacements_mapping(migration):
    """Test COMMAND_REPLACEMENTS has all necessary mappings."""
    replacements = migration.COMMAND_REPLACEMENTS

    # Test key patterns exist
    assert any("create-new-feature" in pattern for pattern in replacements.keys())
    assert any("check-prerequisites" in pattern for pattern in replacements.keys())
    assert any("tasks-move-to-lane" in pattern for pattern in replacements.keys())
    assert any("tasks_cli" in pattern and "move" in pattern for pattern in replacements.keys())

    # Test all map to spec-kitty agent commands
    assert all(value.startswith("spec-kitty agent") for value in replacements.values())
