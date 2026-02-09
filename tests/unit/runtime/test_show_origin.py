"""Tests for the show_origin module.

Covers:
- T025: collect_origins() function
- T027: Tier labels match actual resolution (1A-14, 1A-15)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.runtime.show_origin import (
    COMMAND_NAMES,
    MISSION_NAMES,
    TEMPLATE_NAMES,
    OriginEntry,
    collect_origins,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_file(path: Path, content: str = "placeholder") -> Path:
    """Create a file (and any missing parent dirs), return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# T025 -- collect_origins() basic tests
# ---------------------------------------------------------------------------


class TestCollectOriginsBasic:
    """Test that collect_origins() returns entries for all known assets."""

    def test_returns_entries_for_all_known_assets(self, tmp_path: Path) -> None:
        """collect_origins returns an entry for every template, command, and mission."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        pkg_root = tmp_path / "pkg"

        # Place all templates, commands, and missions at package tier
        for name in TEMPLATE_NAMES:
            _create_file(pkg_root / "software-dev" / "templates" / name)
        for name in COMMAND_NAMES:
            _create_file(pkg_root / "software-dev" / "command-templates" / name)
        for name in MISSION_NAMES:
            _create_file(pkg_root / name / "mission.yaml")

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            entries = collect_origins(project)

        expected_count = len(TEMPLATE_NAMES) + len(COMMAND_NAMES) + len(MISSION_NAMES)
        assert len(entries) == expected_count

    def test_all_entries_are_origin_entry_instances(self, tmp_path: Path) -> None:
        """All returned items are OriginEntry dataclass instances."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ),
        ):
            entries = collect_origins(project)

        for entry in entries:
            assert isinstance(entry, OriginEntry)

    def test_missing_assets_have_error_and_no_path(self, tmp_path: Path) -> None:
        """When no tier provides an asset, error is set and path/tier are None."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ),
        ):
            entries = collect_origins(project)

        for entry in entries:
            assert entry.resolved_path is None
            assert entry.tier is None
            assert entry.error is not None

    def test_asset_types_are_correct(self, tmp_path: Path) -> None:
        """Each entry has the correct asset_type field."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ),
        ):
            entries = collect_origins(project)

        template_entries = [e for e in entries if e.asset_type == "template"]
        command_entries = [e for e in entries if e.asset_type == "command"]
        mission_entries = [e for e in entries if e.asset_type == "mission"]

        assert len(template_entries) == len(TEMPLATE_NAMES)
        assert len(command_entries) == len(COMMAND_NAMES)
        assert len(mission_entries) == len(MISSION_NAMES)


# ---------------------------------------------------------------------------
# T027 -- Tier labels match actual resolution (1A-14, 1A-15)
# ---------------------------------------------------------------------------


class TestShowOriginTierLabels:
    """Each tier label corresponds to actual resolved file (1A-14, 1A-15)."""

    def test_override_tier_label(self, tmp_path: Path) -> None:
        """Override-tier asset gets 'override' label."""
        project = tmp_path / "project"
        override_path = _create_file(
            project / ".kittify" / "overrides" / "templates" / "spec-template.md",
            content="override",
        )
        pkg_root = tmp_path / "pkg"
        _create_file(pkg_root / "software-dev" / "templates" / "spec-template.md")

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            entries = collect_origins(project)

        spec_entry = next(e for e in entries if e.name == "spec-template.md")
        assert spec_entry.tier == "override"
        assert spec_entry.resolved_path == override_path

    def test_global_tier_label(self, tmp_path: Path) -> None:
        """Global-tier asset gets 'global' label."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        global_home = tmp_path / "global_home"

        global_path = _create_file(
            global_home / "missions" / "software-dev" / "templates" / "plan-template.md",
            content="global",
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=global_home,
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ),
        ):
            entries = collect_origins(project)

        plan_entry = next(e for e in entries if e.name == "plan-template.md")
        assert plan_entry.tier == "global"
        assert plan_entry.resolved_path == global_path

    def test_package_default_tier_label(self, tmp_path: Path) -> None:
        """Package-default-tier asset gets 'package_default' label."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        pkg_root = tmp_path / "pkg"

        pkg_path = _create_file(
            pkg_root / "software-dev" / "templates" / "tasks-template.md",
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            entries = collect_origins(project)

        tasks_entry = next(e for e in entries if e.name == "tasks-template.md")
        assert tasks_entry.tier == "package_default"
        assert tasks_entry.resolved_path == pkg_path

    def test_mixed_tiers_in_single_call(self, tmp_path: Path) -> None:
        """Different assets can resolve at different tiers in the same call."""
        project = tmp_path / "project"
        global_home = tmp_path / "global_home"
        pkg_root = tmp_path / "pkg"

        # spec-template.md at override tier
        _create_file(
            project / ".kittify" / "overrides" / "templates" / "spec-template.md",
            content="override",
        )

        # plan-template.md at global tier only
        _create_file(
            global_home / "missions" / "software-dev" / "templates" / "plan-template.md",
            content="global",
        )

        # tasks-template.md at package tier only
        _create_file(
            pkg_root / "software-dev" / "templates" / "tasks-template.md",
            content="package",
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=global_home,
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            entries = collect_origins(project)

        spec_entry = next(e for e in entries if e.name == "spec-template.md")
        plan_entry = next(e for e in entries if e.name == "plan-template.md")
        tasks_entry = next(e for e in entries if e.name == "tasks-template.md")

        assert spec_entry.tier == "override"
        assert plan_entry.tier == "global"
        assert tasks_entry.tier == "package_default"

    def test_command_tier_labels(self, tmp_path: Path) -> None:
        """Command templates also get correct tier labels."""
        project = tmp_path / "project"
        pkg_root = tmp_path / "pkg"

        # Put specify.md at override
        _create_file(
            project / ".kittify" / "overrides" / "command-templates" / "specify.md",
        )
        # Put plan.md at package only
        _create_file(
            pkg_root / "software-dev" / "command-templates" / "plan.md",
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            entries = collect_origins(project)

        specify_cmd = next(
            e for e in entries if e.asset_type == "command" and e.name == "specify.md"
        )
        plan_cmd = next(
            e for e in entries if e.asset_type == "command" and e.name == "plan.md"
        )

        assert specify_cmd.tier == "override"
        assert plan_cmd.tier == "package_default"

    def test_mission_tier_labels(self, tmp_path: Path) -> None:
        """Mission configs get correct tier labels."""
        project = tmp_path / "project"
        pkg_root = tmp_path / "pkg"

        # software-dev at override
        _create_file(
            project / ".kittify" / "overrides" / "missions" / "software-dev" / "mission.yaml",
        )
        # research at package
        _create_file(
            pkg_root / "research" / "mission.yaml",
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            entries = collect_origins(project)

        sw_entry = next(
            e for e in entries if e.asset_type == "mission" and e.name == "software-dev"
        )
        res_entry = next(
            e for e in entries if e.asset_type == "mission" and e.name == "research"
        )

        assert sw_entry.tier == "override"
        assert res_entry.tier == "package_default"

    def test_custom_mission_parameter(self, tmp_path: Path) -> None:
        """collect_origins respects the mission parameter for templates/commands."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        pkg_root = tmp_path / "pkg"

        # Create template under research mission
        _create_file(
            pkg_root / "research" / "templates" / "spec-template.md",
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            entries = collect_origins(project, mission="research")

        spec_entry = next(e for e in entries if e.name == "spec-template.md")
        assert spec_entry.tier == "package_default"
        assert spec_entry.resolved_path is not None
