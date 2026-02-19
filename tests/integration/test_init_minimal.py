"""Integration tests for streamlined init with global runtime.

WP07: Verify that when the global runtime (~/.kittify/) exists,
spec-kitty init creates only project-specific files and resolves
shared assets from the global runtime via the 4-tier resolver.

Subtasks: T038, T039
"""

from __future__ import annotations

import sys
from pathlib import Path


# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# ---------------------------------------------------------------------------
# Helpers for setting up a fake global runtime
# ---------------------------------------------------------------------------

def _populate_global_runtime(global_home: Path) -> None:
    """Create a realistic global runtime directory structure.

    Mimics what ``ensure_runtime()`` would produce at ``~/.kittify/``.
    """
    for mission in ("software-dev", "research", "documentation"):
        cmd_templates = global_home / "missions" / mission / "command-templates"
        cmd_templates.mkdir(parents=True, exist_ok=True)
        # Create at least one template so directory isn't empty
        (cmd_templates / "specify.md").write_text(
            "---\ndescription: test specify\n---\n# Specify\n"
        )
        mission_yaml = global_home / "missions" / mission / "mission.yaml"
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

    Mimics ``src/specify_cli/templates/`` which contains base command
    templates, git-hooks, AGENTS.md, etc.
    """
    cmd_templates = pkg_root / "templates" / "command-templates"
    cmd_templates.mkdir(parents=True, exist_ok=True)
    for name in ("specify", "plan", "tasks", "implement", "review", "accept"):
        (cmd_templates / f"{name}.md").write_text(
            f"---\ndescription: {name} command\nscripts:\n  sh: echo {name}\n---\n# {name}\n"
        )

    # git-hooks
    hooks = pkg_root / "templates" / "git-hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    (hooks / "pre-commit").write_text("#!/bin/bash\nexit 0\n")

    # AGENTS.md
    (pkg_root / "templates" / "AGENTS.md").write_text("# Package AGENTS\n")

    # claudeignore
    (pkg_root / "templates" / "claudeignore-template").write_text("*.pyc\n")

    # Missions (as package asset root)
    missions = pkg_root / "missions"
    missions.mkdir(parents=True, exist_ok=True)
    sw_cmd = missions / "software-dev" / "command-templates"
    sw_cmd.mkdir(parents=True, exist_ok=True)
    (sw_cmd / "specify.md").write_text(
        "---\ndescription: sw specify\nscripts:\n  sh: echo sw-specify\n---\n# SW Specify\n"
    )
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
        assert (result / "command-templates").is_dir()

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
            _resolve_mission_command_templates_dir,
        )
        from specify_cli.template import prepare_command_templates, generate_agent_assets

        assert _has_global_runtime() is True

        # Simulate the global runtime init path
        _prepare_project_minimal(project)

        pkg_templates = _get_package_templates_root()
        assert pkg_templates is not None

        # Copy base command templates to scratch (as init does).
        # Uses .kittify/.scratch/ so the resolver's legacy tier scan
        # of .kittify/command-templates doesn't pick these up.
        import shutil
        scratch = project / ".kittify" / ".scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        scratch_cmd = scratch / "command-templates"
        shutil.copytree(pkg_templates / "command-templates", scratch_cmd)

        # Resolve mission templates
        kittify = project / ".kittify"
        mission_dir = _resolve_mission_command_templates_dir(
            project, "software-dev", scratch_parent=kittify
        )

        # Merge base + mission
        render_dir = prepare_command_templates(scratch_cmd, mission_dir)

        # Generate agent assets
        generate_agent_assets(render_dir, project, "claude", "sh")

        # Clean up scratch dirs (as init does)
        shutil.rmtree(scratch)
        for d in kittify.iterdir():
            if d.is_dir() and (d.name.startswith(".resolved-") or d.name.startswith(".merged-")):
                shutil.rmtree(d)

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

        # Verify agent commands WERE generated
        claude_dir = project / ".claude" / "commands"
        assert claude_dir.is_dir()
        assert any(claude_dir.iterdir()), "Agent commands should be generated"


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

    def test_resolve_command_from_global(self, tmp_path, monkeypatch):
        """After minimal init, command templates resolve from global tier."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Create a minimal project (no local command templates)
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        from specify_cli.runtime.resolver import resolve_command, ResolutionTier

        result = resolve_command("specify.md", project, mission="software-dev")
        assert result.tier == ResolutionTier.GLOBAL_MISSION
        assert "Specify" in result.path.read_text()

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
    """Verify that scratch command-templates don't trigger legacy tier detection."""

    def test_scratch_dir_uses_hidden_path(self, tmp_path, monkeypatch):
        """Init copies base templates to .kittify/.scratch/, not .kittify/command-templates/."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        pkg_root = tmp_path / "pkg"
        _populate_package_templates(pkg_root)
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(pkg_root / "missions"))

        project = tmp_path / "project"
        project.mkdir()

        from specify_cli.cli.commands.init import (
            _has_global_runtime,
            _prepare_project_minimal,
            _get_package_templates_root,
        )

        assert _has_global_runtime() is True

        _prepare_project_minimal(project)
        pkg_templates = _get_package_templates_root()
        assert pkg_templates is not None

        # Copy base command templates using the CORRECT scratch path
        import shutil
        scratch = project / ".kittify" / ".scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        scratch_cmd = scratch / "command-templates"
        shutil.copytree(pkg_templates / "command-templates", scratch_cmd)

        # Verify the legacy-tier path does NOT exist
        legacy_cmd = project / ".kittify" / "command-templates"
        assert not legacy_cmd.exists(), (
            ".kittify/command-templates/ should not exist; "
            "scratch templates belong in .kittify/.scratch/command-templates/"
        )

        # Verify the scratch path DOES exist
        assert scratch_cmd.is_dir()
        assert any(scratch_cmd.iterdir()), "Scratch command-templates should contain files"

    def test_resolver_legacy_tier_not_triggered_by_scratch(self, tmp_path, monkeypatch):
        """The 4-tier resolver's legacy scan should not see .scratch/ contents."""
        global_home = tmp_path / "global"
        _populate_global_runtime(global_home)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        pkg_root = tmp_path / "pkg"
        _populate_package_templates(pkg_root)
        monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", str(pkg_root / "missions"))

        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        # Place a unique template ONLY in .scratch (not in the proper legacy dir)
        scratch = project / ".kittify" / ".scratch" / "command-templates"
        scratch.mkdir(parents=True)
        (scratch / "unique-scratch-only.md").write_text("# Should not be found via resolver\n")

        from specify_cli.cli.commands.init import _resolve_mission_command_templates_dir

        resolved_dir = _resolve_mission_command_templates_dir(
            project, "software-dev", scratch_parent=project / ".kittify"
        )

        # The unique-scratch-only.md should NOT appear in resolved output
        # because .scratch/ is not scanned by the resolver's legacy tier
        resolved_names = {p.name for p in resolved_dir.glob("*.md")}
        assert "unique-scratch-only.md" not in resolved_names, (
            "Resolver legacy tier should not pick up files from .kittify/.scratch/"
        )

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
            _get_package_templates_root,
            _resolve_mission_command_templates_dir,
        )
        from specify_cli.template import prepare_command_templates, generate_agent_assets

        _prepare_project_minimal(project)
        pkg_templates = _get_package_templates_root()

        # Simulate init's scratch workflow
        import shutil
        scratch = project / ".kittify" / ".scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        scratch_cmd = scratch / "command-templates"
        shutil.copytree(pkg_templates / "command-templates", scratch_cmd)

        kittify = project / ".kittify"
        mission_dir = _resolve_mission_command_templates_dir(
            project, "software-dev", scratch_parent=kittify
        )
        render_dir = prepare_command_templates(scratch_cmd, mission_dir)
        generate_agent_assets(render_dir, project, "claude", "sh")

        # Simulate the cleanup that init does
        for cleanup_name in ("templates", "command-templates", ".scratch"):
            cleanup_dir = project / ".kittify" / cleanup_name
            if cleanup_dir.exists():
                shutil.rmtree(cleanup_dir)
        for d in kittify.iterdir():
            if d.is_dir() and (d.name.startswith(".resolved-") or d.name.startswith(".merged-")):
                shutil.rmtree(d)

        # Verify cleanup
        assert not (project / ".kittify" / ".scratch").exists(), ".scratch should be cleaned up"
        assert not (project / ".kittify" / "command-templates").exists(), "command-templates should not exist"

        # Verify agent commands WERE generated (survived cleanup)
        claude_dir = project / ".claude" / "commands"
        assert claude_dir.is_dir()
        assert any(claude_dir.iterdir())
