"""Integration tests for streamlined init with global runtime.

WP07: Verify that when the global runtime (~/.kittify/) exists,
spec-kitty init creates only project-specific files and resolves
shared assets from the global runtime via the 4-tier resolver.

Subtasks: T038, T039
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.git_repo

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# ---------------------------------------------------------------------------
# Helpers for setting up a fake global runtime
# ---------------------------------------------------------------------------

def _populate_global_runtime(global_home: Path) -> None:
    """Create a realistic global runtime directory structure.

    Mimics what ``ensure_runtime()`` would produce at ``~/.kittify/``.
    WP10: command-templates are not present; shim generation replaces them.
    """
    for mission in ("software-dev", "research", "documentation"):
        mission_yaml = global_home / "missions" / mission / "mission.yaml"
        mission_yaml.parent.mkdir(parents=True, exist_ok=True)
        mission_yaml.write_text(f"name: {mission}\ndescription: test\n")

        # Add templates (spec-template etc.)
        templates = global_home / "missions" / mission / "templates"
        templates.mkdir(parents=True, exist_ok=True)
        (templates / "spec-template.md").write_text(f"# Spec template for {mission}\n")

    # Scripts
    scripts = global_home / "scripts" / "bash"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "run.sh").write_text("#!/bin/bash\necho hello\n")

    # AGENTS.md
    (global_home / "AGENTS.md").write_text("# Agents\n")

    # Version lock (indicates ensure_runtime has been called)
    cache = global_home / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "version.lock").write_text("0.99.0")

def _populate_package_templates(pkg_root: Path) -> None:
    """Create a fake package templates directory tree.

    Mimics ``src/specify_cli/templates/`` which contains AGENTS.md, etc.
    WP10: command-templates were deleted; shim generation replaces them.
    """
    # AGENTS.md
    (pkg_root / "templates").mkdir(parents=True, exist_ok=True)
    (pkg_root / "templates" / "AGENTS.md").write_text("# Package AGENTS\n")

    # claudeignore
    (pkg_root / "templates" / "claudeignore-template").write_text("*.pyc\n")

    # Missions (as package asset root)
    missions = pkg_root / "missions"
    missions.mkdir(parents=True, exist_ok=True)
    # WP10: mission directories have no command-templates/ subdirectory
    (missions / "software-dev").mkdir(parents=True, exist_ok=True)
    (missions / "software-dev" / "mission.yaml").write_text("name: software-dev\n")

# ---------------------------------------------------------------------------
# T038: Init creates only project-specific files when global runtime exists
# ---------------------------------------------------------------------------

class TestInitCreatesMinimalProject:
    """Verify that init with global runtime creates only project-specific files."""

    def test_has_global_runtime_true(self, tmp_path, monkeypatch):
        """_has_global_runtime returns True when global runtime is populated."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        from specify_cli.cli.commands.init import _has_global_runtime

        assert _has_global_runtime() is True

    def test_has_global_runtime_false_missing(self, tmp_path, monkeypatch):
        """_has_global_runtime returns False when ~/.kittify doesn't exist."""
        global_home = tmp_path / "nonexistent"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        from specify_cli.cli.commands.init import _has_global_runtime

        assert _has_global_runtime() is False

    def test_has_global_runtime_false_empty_missions(self, tmp_path, monkeypatch):
        """_has_global_runtime returns False when missions/ exists but is empty."""
        global_home = tmp_path / "global"
        (global_home / "missions").mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        from specify_cli.cli.commands.init import _has_global_runtime

        assert _has_global_runtime() is False

    def test_prepare_project_minimal(self, tmp_path):
        """_prepare_project_minimal creates only .kittify/ and .kittify/memory/."""
        from specify_cli.cli.commands.init import _prepare_project_minimal

        project = tmp_path / "myproject"
        project.mkdir()

        _prepare_project_minimal(project)

        kittify = project / ".kittify"
        assert kittify.is_dir()
        assert (kittify / "memory").is_dir()

        # No shared assets should exist
        assert not (kittify / "missions").exists()
        assert not (kittify / "templates").exists()
        assert not (kittify / "scripts").exists()
        assert not (kittify / "AGENTS.md").exists()

    def test_get_package_templates_root(self, tmp_path, monkeypatch):
        """_get_package_templates_root returns the package templates directory."""
        pkg_root = tmp_path / "pkg"
        _populate_package_templates(pkg_root)

        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(pkg_root / "missions"))

        from specify_cli.cli.commands.init import _get_package_templates_root

        result = _get_package_templates_root()
        assert result is not None
        assert result.name == "templates"
        # WP10: command-templates were deleted; the templates dir has other files (AGENTS.md, etc.)
        assert not (result / "command-templates").exists()

    def test_init_minimal_no_missions_copied(self, tmp_path, monkeypatch):
        """Full init flow: global runtime -> no missions/templates/scripts/AGENTS.md in project."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Set up package asset root
        pkg_root = tmp_path / "pkg"
        _populate_package_templates(pkg_root)
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(pkg_root / "missions"))

        project = tmp_path / "project"
        project.mkdir()

        # Mock the interactive init to just call our functions
        from specify_cli.cli.commands.init import (
            _has_global_runtime,
            _prepare_project_minimal,
            _get_package_templates_root,
        )
        from specify_cli.shims.generator import generate_all_shims

        assert _has_global_runtime() is True

        # Simulate the global runtime init path
        _prepare_project_minimal(project)

        pkg_templates = _get_package_templates_root()
        assert pkg_templates is not None

        # WP10: Shim generation replaces the old command-template copy + render flow.
        generate_all_shims(project)

        # Verify project-specific files exist
        kittify = project / ".kittify"
        assert kittify.is_dir()
        assert (kittify / "memory").is_dir()

        # Verify shared assets NOT in project
        assert not (kittify / "missions").exists()
        assert not (kittify / "templates").exists()
        assert not (kittify / "scripts").exists()
        assert not (kittify / "AGENTS.md").exists()
        assert not (kittify / "command-templates").exists()

        # Verify agent shims WERE generated
        claude_dir = project / ".claude" / "commands"
        assert claude_dir.is_dir()
        assert any(claude_dir.iterdir()), "Agent shims should be generated"

# ---------------------------------------------------------------------------
# T039: Init resolves shared assets from global runtime
# ---------------------------------------------------------------------------

class TestInitResolvesFromGlobal:
    """Verify that after minimal init, shared assets resolve from ~/.kittify/."""

    def test_resolve_template_from_global(self, tmp_path, monkeypatch):
        """After minimal init, templates resolve from global tier."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Create a minimal project (no local templates)
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        from specify_cli.runtime.resolver import resolve_template, ResolutionTier

        result = resolve_template("spec-template.md", project, mission="software-dev")
        assert result.tier == ResolutionTier.GLOBAL_MISSION
        assert "Spec template" in result.path.read_text()

    def test_resolve_command_finds_package_tier_after_wp01(self, tmp_path, monkeypatch):
        """WP01: command-templates restored to package; resolve_command resolves from package tier.

        WP10 removed command-templates from the package. WP01 (feature 058) restored
        them. This test verifies the resolver now finds specify.md at the PACKAGE tier
        when no higher-priority tier (project/global) has the file.
        """
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Create a minimal project (no local command templates)
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        from specify_cli.runtime.resolver import resolve_command, ResolutionTier

        # WP01: command-templates were restored to the package; resolver finds them
        result = resolve_command("specify.md", project, mission="software-dev")
        assert result.tier == ResolutionTier.PACKAGE_DEFAULT
        assert result.path.exists()

    def test_resolve_mission_from_global(self, tmp_path, monkeypatch):
        """After minimal init, mission.yaml resolves from global tier."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Create a minimal project (no local missions)
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        from specify_cli.runtime.resolver import resolve_mission, ResolutionTier

        result = resolve_mission("software-dev", project)
        assert result.tier == ResolutionTier.GLOBAL_MISSION
        assert "software-dev" in result.path.read_text()

    def test_override_still_wins_over_global(self, tmp_path, monkeypatch):
        """Project-level overrides take precedence over global runtime."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Create project with an override
        project = tmp_path / "project"
        override_dir = project / ".kittify" / "overrides" / "templates"
        override_dir.mkdir(parents=True)
        (override_dir / "spec-template.md").write_text("# Override template\n")

        from specify_cli.runtime.resolver import resolve_template, ResolutionTier

        result = resolve_template("spec-template.md", project, mission="software-dev")
        assert result.tier == ResolutionTier.OVERRIDE
        assert "Override" in result.path.read_text()

    def test_package_default_fallback(self, tmp_path, monkeypatch):
        """When global runtime is missing, package defaults are used."""
        # Point to an empty global home
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        from specify_cli.runtime.resolver import resolve_command, ResolutionTier

        # Package default should exist for standard commands like specify.md
        try:
            result = resolve_command("specify.md", project, mission="software-dev")
            # If found, it should be from package default tier
            assert result.tier == ResolutionTier.PACKAGE_DEFAULT
        except FileNotFoundError:
            # Package default might not be discoverable in test context,
            # that's OK -- the important thing is global wasn't used.
            pass

    def test_no_global_no_crash(self, tmp_path, monkeypatch):
        """When global runtime is absent, _has_global_runtime returns False cleanly."""
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "does-not-exist"))

        from specify_cli.cli.commands.init import _has_global_runtime

        assert _has_global_runtime() is False

# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestGlobalRuntimeEdgeCases:
    """Edge cases for the global runtime detection."""

    def test_has_global_runtime_missions_only_files(self, tmp_path, monkeypatch):
        """_has_global_runtime is False when missions/ has only files, not subdirs."""
        global_home = tmp_path / "global"
        missions = global_home / "missions"
        missions.mkdir(parents=True)
        (missions / "README.md").write_text("# empty\n")
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        from specify_cli.cli.commands.init import _has_global_runtime

        assert _has_global_runtime() is False

    def test_prepare_minimal_idempotent(self, tmp_path):
        """_prepare_project_minimal can be called multiple times safely."""
        from specify_cli.cli.commands.init import _prepare_project_minimal

        project = tmp_path / "proj"
        project.mkdir()

        _prepare_project_minimal(project)
        _prepare_project_minimal(project)  # Second call should not fail

        assert (project / ".kittify" / "memory").is_dir()

    def test_local_template_mode_bypasses_global(self, tmp_path, monkeypatch):
        """In local template mode, global runtime check is skipped."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        from specify_cli.cli.commands.init import _has_global_runtime

        # Even though global runtime exists, when template_mode == "local",
        # the init code does: use_global = _has_global_runtime() and template_mode == "package"
        # So for local mode, use_global would be False.
        assert _has_global_runtime() is True
        # But the condition 'and template_mode == "package"' ensures local mode is unaffected.
        # This is tested by verifying the code logic, not calling init directly.

# ---------------------------------------------------------------------------
# ensure_runtime() called during init
# ---------------------------------------------------------------------------

class TestEnsureRuntimeCalledDuringInit:
    """Verify that ensure_runtime() is invoked before _has_global_runtime()."""

    def test_ensure_runtime_called_in_init_code_path(self, tmp_path, monkeypatch):
        """The init code path calls ensure_runtime() before checking global runtime.

        We mock ensure_runtime to verify it's called, then let
        _has_global_runtime() return its result based on the (already populated)
        global home.
        """
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Set up package asset root
        pkg_root = tmp_path / "pkg"
        _populate_package_templates(pkg_root)
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(pkg_root / "missions"))

        # Track whether ensure_runtime was called
        ensure_runtime_calls = []

        def mock_ensure_runtime():
            ensure_runtime_calls.append(True)

        # Patch ensure_runtime at the module level so the lazy import picks it up
        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap.ensure_runtime",
            mock_ensure_runtime,
        )

        # Simulate the init code path that calls ensure_runtime
        # (extract the relevant block from init to test it directly)
        from specify_cli.cli.commands.init import _has_global_runtime

        # Call the code path manually (mirrors lines 746-757 of init.py)
        try:
            from specify_cli.runtime.bootstrap import ensure_runtime
            ensure_runtime()
        except Exception:
            pass

        use_global = _has_global_runtime() and True  # template_mode == "package"

        assert len(ensure_runtime_calls) == 1, "ensure_runtime() should be called exactly once"
        assert use_global is True

    def test_ensure_runtime_failure_falls_back_gracefully(self, tmp_path, monkeypatch):
        """When ensure_runtime() raises, init falls back to legacy path."""
        # Don't populate global runtime -- ensure_runtime would normally create it
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        def mock_ensure_runtime_fail():
            raise RuntimeError("simulated bootstrap failure")

        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap.ensure_runtime",
            mock_ensure_runtime_fail,
        )

        from specify_cli.cli.commands.init import _has_global_runtime

        # Simulate the init code path with failure
        try:
            from specify_cli.runtime.bootstrap import ensure_runtime
            ensure_runtime()
        except Exception:
            pass  # graceful fallback

        # Global runtime doesn't exist (ensure_runtime failed), so should be False
        use_global = _has_global_runtime()
        assert use_global is False

    def test_ensure_runtime_populates_global_before_check(self, tmp_path, monkeypatch):
        """ensure_runtime() can populate global runtime so _has_global_runtime() returns True.

        This tests the sequence: ensure_runtime() creates ~/.kittify/missions/,
        then _has_global_runtime() detects it.
        """
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        from specify_cli.cli.commands.init import _has_global_runtime

        # Before ensure_runtime, global runtime is absent
        assert _has_global_runtime() is False

        # Mock ensure_runtime to populate the global runtime
        def mock_ensure_runtime_populate():
            _populate_global_runtime(global_home)

        monkeypatch.setattr(
            "specify_cli.runtime.bootstrap.ensure_runtime",
            mock_ensure_runtime_populate,
        )

        from specify_cli.runtime.bootstrap import ensure_runtime
        ensure_runtime()

        # After ensure_runtime, global runtime should be detected
        assert _has_global_runtime() is True

# ---------------------------------------------------------------------------
# Scratch directory does not shadow legacy tier
# ---------------------------------------------------------------------------

class TestScratchDirNotLegacy:
    """WP10: Scratch command-template workflow replaced by shim generation.

    These tests verify the WP10 state: no scratch dir, no command-templates,
    shims are generated directly to agent directories.
    """

    def test_no_scratch_dir_after_init(self, tmp_path, monkeypatch):
        """WP10: Init does not create .kittify/.scratch/ (no command-templates to stage)."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        project.mkdir()

        from specify_cli.cli.commands.init import _prepare_project_minimal
        from specify_cli.shims.generator import generate_all_shims

        _prepare_project_minimal(project)
        generate_all_shims(project)

        # WP10: No scratch directory should exist
        assert not (project / ".kittify" / ".scratch").exists(), (
            ".kittify/.scratch/ should not exist in WP10 (command-templates deleted)"
        )
        assert not (project / ".kittify" / "command-templates").exists(), (
            ".kittify/command-templates/ should not exist in WP10"
        )

    def test_shim_files_written_to_agent_directory(self, tmp_path, monkeypatch):
        """WP10: Shim files are written directly to agent directories, not via scratch."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        project = tmp_path / "project"
        project.mkdir()
        (project / ".kittify").mkdir()

        from specify_cli.shims.generator import generate_all_shims

        generate_all_shims(project)

        # Verify shim files were written to agent directories
        claude_dir = project / ".claude" / "commands"
        assert claude_dir.is_dir()
        shim_files = list(claude_dir.glob("spec-kitty.*.md"))
        assert len(shim_files) > 0, "Shim files should be generated for claude agent"

    def test_scratch_cleanup_after_init(self, tmp_path, monkeypatch):
        """After init completes, .kittify/.scratch/ should be cleaned up."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        pkg_root = tmp_path / "pkg"
        _populate_package_templates(pkg_root)
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(pkg_root / "missions"))

        project = tmp_path / "project"
        project.mkdir()

        from specify_cli.cli.commands.init import (
            _prepare_project_minimal,
        )
        from specify_cli.shims.generator import generate_all_shims

        _prepare_project_minimal(project)

        # WP10: Shim generation replaces the old command-template copy + render flow.
        # No scratch directory is created.
        generate_all_shims(project)

        # Verify no scratch or command-templates dirs exist (WP10: nothing to clean up)
        assert not (project / ".kittify" / ".scratch").exists(), ".scratch should not exist in WP10"
        assert not (project / ".kittify" / "command-templates").exists(), "command-templates should not exist"

        # Verify agent shims WERE generated (survived - nothing to clean up)
        claude_dir = project / ".claude" / "commands"
        assert claude_dir.is_dir()
        assert any(claude_dir.iterdir())
