"""Tests for manifest script filtering to prevent false positives."""

import platform
from specify_cli.manifest import FileManifest


def test_filters_cli_commands(tmp_path):
    """Ensure CLI commands like spec-kitty and git are not treated as scripts."""
    # Setup
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)
    
    # Create active-mission indicator
    (kittify_dir / "active-mission").write_text("software-dev")
    
    # Create mission.yaml
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")
    
    # Create a command template with CLI commands (should be filtered out)
    command_content = """---
description: Test command
ps: spec-kitty agent --json
sh: spec-kitty agent --json
---

# Test Command
"""
    (commands_dir / "test.md").write_text(command_content)
    
    # Test
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()
    
    # Verify CLI commands are filtered out
    assert "spec-kitty" not in scripts
    assert len(scripts) == 0


def test_includes_kittify_scripts(tmp_path):
    """Ensure actual .kittify/scripts/ files are included."""
    # Setup
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)
    
    # Create active-mission indicator
    (kittify_dir / "active-mission").write_text("software-dev")
    
    # Create mission.yaml
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")
    
    # Create actual script files
    scripts_dir = kittify_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "helper.sh").write_text("#!/bin/bash\necho 'test'")
    (scripts_dir / "setup.ps1").write_text("Write-Host 'test'")
    
    # Create command template referencing actual scripts
    command_content = """---
description: Test command
ps: .kittify/scripts/setup.ps1
sh: .kittify/scripts/helper.sh
---

# Test Command
"""
    (commands_dir / "test.md").write_text(command_content)
    
    # Test
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()
    
    # Verify actual scripts are included (platform-specific)
    # Also verify opposite platform's script is NOT included
    if platform.system() == 'Windows':
        assert "scripts/setup.ps1" in scripts
        assert "scripts/helper.sh" not in scripts  # Verify cross-platform exclusion
    else:
        assert "scripts/helper.sh" in scripts
        assert "scripts/setup.ps1" not in scripts  # Verify cross-platform exclusion
    
    # Should have exactly one script (for current platform)
    assert len(scripts) == 1


def test_filters_system_commands(tmp_path):
    """Ensure system commands like git, python are not treated as scripts."""
    # Setup
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)
    
    # Create active-mission indicator
    (kittify_dir / "active-mission").write_text("software-dev")
    
    # Create mission.yaml
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")
    
    # Create command template with various system commands
    command_content = """---
description: Test command
ps: git status
sh: python3 -c "print('test')"
---

# Test Command
"""
    (commands_dir / "test.md").write_text(command_content)
    
    # Test
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()
    
    # Verify system commands are filtered out
    assert "git" not in scripts
    assert "python3" not in scripts
    assert len(scripts) == 0


def test_ignores_non_scripts_directory_paths(tmp_path):
    """Ensure paths not in .kittify/scripts/ are ignored."""
    # Setup
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)
    
    # Create active-mission indicator
    (kittify_dir / "active-mission").write_text("software-dev")
    
    # Create mission.yaml
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")
    
    # Create command template referencing non-script paths
    command_content = """---
description: Test command
ps: .kittify/memory/something.md
sh: .kittify/templates/plan.md
---

# Test Command
"""
    (commands_dir / "test.md").write_text(command_content)
    
    # Test
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()
    
    # Verify non-script paths are filtered out
    assert "memory/something.md" not in scripts
    assert "templates/plan.md" not in scripts
    assert len(scripts) == 0


def test_mixed_commands_and_scripts(tmp_path):
    """Ensure mix of CLI commands and real scripts are properly filtered."""
    # Setup
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)
    
    # Create active-mission indicator
    (kittify_dir / "active-mission").write_text("software-dev")
    
    # Create mission.yaml
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")
    
    # Create actual script
    scripts_dir = kittify_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "real-script.ps1").write_text("Write-Host 'test'")
    
    # Create command template with mix of CLI and script
    command_content = """---
description: Test command
ps: .kittify/scripts/real-script.ps1
---

# Test Command
"""
    (commands_dir / "cmd1.md").write_text(command_content)
    
    # Create another command with CLI commands
    cli_command_content = """---
description: CLI command
ps: spec-kitty agent --json
---

# CLI Command
"""
    (commands_dir / "cmd2.md").write_text(cli_command_content)
    
    # Test
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()
    
    # Verify only real script is included (for current platform)
    if platform.system() == 'Windows':
        assert "scripts/real-script.ps1" in scripts
        assert len(scripts) == 1
    else:
        # On non-Windows, the ps: line is ignored, so no scripts
        assert len(scripts) == 0
    
    # Verify CLI commands are always excluded regardless of platform
    assert "spec-kitty" not in scripts


def test_filters_cli_commands_with_path_prefixes(tmp_path):
    """Ensure CLI commands with path prefixes are filtered (./git, /usr/bin/python)."""
    # Setup
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)
    
    # Create active-mission indicator
    (kittify_dir / "active-mission").write_text("software-dev")
    
    # Create mission.yaml
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")
    
    # Create command template with CLI commands that have path prefixes
    command_content = """---
description: Test command with path-prefixed CLI commands
ps: ./spec-kitty agent --json
sh: /usr/bin/python3 script.py
---

# Test Command
"""
    (commands_dir / "test.md").write_text(command_content)
    
    # Test
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()
    
    # Verify path-prefixed CLI commands are filtered out
    assert "spec-kitty" not in scripts
    assert "python3" not in scripts
    assert "./spec-kitty" not in scripts
    assert "/usr/bin/python3" not in scripts
    assert len(scripts) == 0


def test_handles_windows_backslash_paths(tmp_path):
    """Ensure Windows-style backslash paths are normalized and handled correctly."""
    # Setup
    kittify_dir = tmp_path / ".kittify"
    missions_dir = kittify_dir / "missions" / "software-dev"
    commands_dir = missions_dir / "command-templates"
    commands_dir.mkdir(parents=True)
    
    # Create active-mission indicator
    (kittify_dir / "active-mission").write_text("software-dev")
    
    # Create mission.yaml
    (missions_dir / "mission.yaml").write_text("name: software-dev\n")
    
    # Create actual script files for both platforms
    scripts_dir = kittify_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "helper.ps1").write_text("Write-Host 'test'")
    (scripts_dir / "helper.sh").write_text("#!/bin/bash\necho 'test'")
    
    # Create command template with Windows-style backslash paths
    # Note: Using raw string to preserve backslashes
    command_content = """---
description: Test command with Windows paths
ps: .kittify\\scripts\\helper.ps1
sh: .kittify\\scripts\\helper.sh
---

# Test Command
"""
    (commands_dir / "test.md").write_text(command_content)
    
    # Test
    manifest = FileManifest(kittify_dir)
    scripts = manifest._get_referenced_scripts()
    
    # Verify backslash paths are normalized and scripts are included
    if platform.system() == 'Windows':
        assert "scripts/helper.ps1" in scripts
        assert len(scripts) == 1
    else:
        # On non-Windows, sh: line is used with normalized backslash path
        assert "scripts/helper.sh" in scripts
        assert len(scripts) == 1