"""Integration tests for ``spec-kitty config --show-origin``.

Covers:
- T027: Verify tier labels match actual resolution behavior (1A-14, 1A-15)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.runtime.show_origin import collect_origins


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_file(path: Path, content: str = "placeholder") -> Path:
    """Create a file (and any missing parent dirs), return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# T027 -- Integration: tier labels match actual resolution
# ---------------------------------------------------------------------------


class TestShowOriginLabelsMatchResolution:
    """Each tier label corresponds to actual resolved file (1A-14, 1A-15)."""

    def test_override_and_global_tiers_together(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Override and global tiers coexist correctly in one run."""
        project = tmp_path / "project"
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        # Place spec-template.md at override tier
        override_path = _create_file(
            project / ".kittify" / "overrides" / "templates" / "spec-template.md",
            content="override",
        )

        # Place plan-template.md at global tier
        global_path = _create_file(
            global_home / "missions" / "software-dev" / "templates" / "plan-template.md",
            content="global",
        )

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            side_effect=FileNotFoundError("no pkg"),
        ):
            entries = collect_origins(project)

        spec_entry = next(e for e in entries if e.name == "spec-template.md")
        assert spec_entry.tier == "override"
        assert spec_entry.resolved_path == override_path

        plan_entry = next(e for e in entries if e.name == "plan-template.md")
        assert plan_entry.tier == "global_mission"
        assert plan_entry.resolved_path == global_path

    def test_package_default_tier(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Package-default tier resolves when no higher tiers provide the asset."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        pkg_root = tmp_path / "pkg"
        pkg_path = _create_file(
            pkg_root / "software-dev" / "templates" / "spec-template.md",
        )

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            return_value=pkg_root,
        ):
            entries = collect_origins(project)

        spec_entry = next(e for e in entries if e.name == "spec-template.md")
        assert spec_entry.tier == "package_default"
        assert spec_entry.resolved_path == pkg_path

    def test_not_found_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Assets not found at any tier have None path and tier, with error message."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        global_home = tmp_path / "global"
        monkeypatch.setenv("SPEC_KITTY_HOME", str(global_home))

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            side_effect=FileNotFoundError("no pkg"),
        ), patch(
            "specify_cli.runtime.show_origin.get_package_asset_root",
            side_effect=FileNotFoundError("no pkg"),
        ):
            entries = collect_origins(project)

        # Resolver-based entries (template, command, mission) should be not found
        resolver_entries = [
            e for e in entries if e.asset_type in ("template", "command", "mission")
        ]
        assert len(resolver_entries) > 0, "Should have template/command/mission entries"
        for entry in resolver_entries:
            assert entry.resolved_path is None
            assert entry.tier is None
            assert entry.error is not None
            assert "not found" in entry.error.lower()

        # AGENTS.md is present -- it's always discoverable from the installed
        # package (uses ``import specify_cli`` internally, not the resolver).
        # Dedicated tests in TestShowOriginExtendedAssets cover AGENTS.md behaviour.
        agents_entries = [e for e in entries if e.name == "AGENTS.md"]
        assert len(agents_entries) == 1


# ---------------------------------------------------------------------------
# T027b -- Extended asset coverage (PRD §6.4)
# ---------------------------------------------------------------------------


class TestShowOriginExtendedAssets:
    """Verify collect_origins covers scripts, AGENTS.md, and dynamic discovery."""

    def test_agents_md_from_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AGENTS.md resolved from project .kittify/ directory."""
        project = tmp_path / "project"
        agents_file = project / ".kittify" / "AGENTS.md"
        agents_file.parent.mkdir(parents=True)
        agents_file.write_text("# Agents\n")

        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "global"))

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            side_effect=FileNotFoundError("no pkg"),
        ):
            entries = collect_origins(project)

        agents_entries = [e for e in entries if e.name == "AGENTS.md"]
        assert len(agents_entries) == 1
        assert agents_entries[0].asset_type == "file"
        assert agents_entries[0].tier == "project"
        assert agents_entries[0].resolved_path == agents_file

    def test_scripts_from_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scripts in .kittify/scripts/ are discovered."""
        project = tmp_path / "project"
        scripts_dir = project / ".kittify" / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "validate_encoding.py").write_text("# script\n")

        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "global"))

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            side_effect=FileNotFoundError("no pkg"),
        ):
            entries = collect_origins(project)

        script_entries = [e for e in entries if e.asset_type == "script"]
        assert any(e.name == "validate_encoding.py" for e in script_entries)

    def test_dynamic_command_discovery(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Command templates are dynamically discovered from package defaults."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "global"))

        pkg_root = tmp_path / "pkg"
        cmd_dir = pkg_root / "software-dev" / "command-templates"
        cmd_dir.mkdir(parents=True)
        for name in ["specify.md", "plan.md", "tasks.md", "implement.md",
                      "review.md", "accept.md", "merge.md", "dashboard.md",
                      "analyze.md", "checklist.md", "clarify.md", "constitution.md"]:
            (cmd_dir / name).write_text(f"# {name}\n")

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            return_value=pkg_root,
        ):
            # Also patch the discovery function's call to get_package_asset_root
            with patch(
                "specify_cli.runtime.show_origin.get_package_asset_root",
                return_value=pkg_root,
            ):
                entries = collect_origins(project)

        command_entries = [e for e in entries if e.asset_type == "command"]
        command_names = {e.name for e in command_entries}
        # Should include dynamically discovered commands beyond the old hardcoded list
        assert "analyze.md" in command_names
        assert "checklist.md" in command_names
        assert "clarify.md" in command_names
        assert "constitution.md" in command_names

    def test_all_missions_discovered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All mission directories are discovered dynamically."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "global"))

        pkg_root = tmp_path / "pkg"
        for mission in ["software-dev", "research", "documentation"]:
            mission_dir = pkg_root / mission
            mission_dir.mkdir(parents=True)
            (mission_dir / "mission.yaml").write_text(f"name: {mission}\n")

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            return_value=pkg_root,
        ):
            with patch(
                "specify_cli.runtime.show_origin.get_package_asset_root",
                return_value=pkg_root,
            ):
                entries = collect_origins(project)

        mission_entries = [e for e in entries if e.asset_type == "mission"]
        mission_names = {e.name for e in mission_entries}
        assert mission_names == {"software-dev", "research", "documentation"}

    def test_collect_origins_includes_all_required_asset_types(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PRD §6.4: collect_origins returns templates, commands, missions, scripts, and files."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "global"))

        with patch(
            "specify_cli.runtime.resolver.get_package_asset_root",
            side_effect=FileNotFoundError("no pkg"),
        ):
            with patch(
                "specify_cli.runtime.show_origin.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ):
                entries = collect_origins(project)

        asset_types = {e.asset_type for e in entries}
        # Must have templates, commands, missions, and file (AGENTS.md)
        assert "template" in asset_types
        assert "command" in asset_types
        assert "mission" in asset_types
        assert "file" in asset_types  # AGENTS.md
