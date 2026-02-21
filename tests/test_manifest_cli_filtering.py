"""Test that CLI commands in frontmatter are not treated as missing scripts.

TDD test to verify the issue described in PR #82:
When command templates have frontmatter like 'ps: spec-kitty agent --json',
the system should NOT treat 'spec-kitty' as a missing script file.
"""

import platform
from pathlib import Path

from specify_cli.manifest import FileManifest


def test_cli_commands_not_treated_as_scripts(tmp_path: Path):
    """
    GIVEN a command template with 'sh: spec-kitty agent --json' frontmatter
    WHEN _get_referenced_scripts() is called
    THEN 'spec-kitty' should NOT be in the returned scripts list
    """
    # Setup: Create minimal .kittify structure
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)

    # Create active-mission indicator
    (kittify_dir / "active-mission").write_text("software-dev")

    # Create mission.yaml
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")

    # Create a command template with CLI command in frontmatter
    # This is the pattern that was reportedly causing false positives
    command_content = """---
description: Test command that references CLI tools
ps: spec-kitty agent --json
sh: spec-kitty agent --json
---

# Test Command

This command uses spec-kitty CLI.
"""
    (commands_dir / "test-command.md").write_text(command_content)

    # Test: Get referenced scripts
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()

    # Assert: CLI commands should NOT be treated as scripts
    assert "spec-kitty" not in scripts, f"'spec-kitty' should not be in scripts list, got: {scripts}"
    assert len(scripts) == 0, f"No scripts should be detected for CLI commands, got: {scripts}"


def test_actual_kittify_scripts_are_included(tmp_path: Path):
    """
    GIVEN a command template referencing an actual .kittify/scripts/ file
    WHEN _get_referenced_scripts() is called
    THEN the script should be included in the returned list
    """
    # Setup
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)

    (kittify_dir / "active-mission").write_text("software-dev")
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")

    # Create actual script file
    scripts_dir = kittify_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "helper.sh").write_text("#!/bin/bash\necho 'test'")
    (scripts_dir / "helper.ps1").write_text("Write-Host 'test'")

    # Create command template referencing actual script
    command_content = """---
description: Test command with actual script
ps: .kittify/scripts/helper.ps1
sh: .kittify/scripts/helper.sh
---

# Test Command
"""
    (commands_dir / "test-command.md").write_text(command_content)

    # Test
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()

    # Assert: Actual scripts SHOULD be included (platform-specific)
    if platform.system() == "Windows":
        assert "scripts/helper.ps1" in scripts
    else:
        assert "scripts/helper.sh" in scripts


def test_other_system_commands_filtered(tmp_path: Path):
    """
    GIVEN command templates with various system CLI commands
    WHEN _get_referenced_scripts() is called
    THEN none of them should be treated as scripts
    """
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)

    (kittify_dir / "active-mission").write_text("software-dev")
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")

    # Test various CLI commands that might appear in frontmatter
    command_content = """---
description: Test with git command
sh: git status
ps: git status
---
# Git command
"""
    (commands_dir / "git-cmd.md").write_text(command_content)

    command_content2 = """---
description: Test with python command
sh: python3 -c "print('test')"
ps: python -c "print('test')"
---
# Python command
"""
    (commands_dir / "python-cmd.md").write_text(command_content2)

    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()

    assert "git" not in scripts
    assert "python" not in scripts
    assert "python3" not in scripts
    assert len(scripts) == 0
