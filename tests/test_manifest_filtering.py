"""Tests for manifest script filtering to prevent false positives."""

from pathlib import Path
import tempfile
import shutil
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
    import platform
    if platform.system() == 'Windows':
        assert "scripts/setup.ps1" in scripts
    else:
        assert "scripts/helper.sh" in scripts
    
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
    
    # Verify only real script is included
    import platform
    if platform.system() == 'Windows':
        assert "scripts/real-script.ps1" in scripts
        assert len(scripts) == 1
    else:
        # On non-Windows, the ps: line is ignored, so no scripts
        assert len(scripts) == 0
    
    # Verify CLI commands are excluded
    assert "spec-kitty" not in scripts
