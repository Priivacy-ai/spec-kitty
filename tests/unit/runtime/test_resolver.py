"""Tests for the 4-tier asset resolver.

Covers:
- T018: Resolution precedence tests (G2)
- T019: Legacy resolution tests (F-Legacy)
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.runtime.resolver import (
    ResolutionResult,
    ResolutionTier,
    resolve_command,
    resolve_mission,
    resolve_template,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_file(path: Path, content: str = "placeholder") -> Path:
    """Create a file (and any missing parent dirs), return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _setup_all_tiers(
    tmp_path: Path,
    name: str = "spec-template.md",
    subdir: str = "templates",
    mission: str = "software-dev",
    *,
    global_home: Path | None = None,
    pkg_root: Path | None = None,
) -> dict[str, Path]:
    """Create the asset at every tier and return a mapping of tier->path."""
    project = tmp_path / "project"
    kittify = project / ".kittify"

    paths: dict[str, Path] = {}

    # Tier 1 -- override
    paths["override"] = _create_file(kittify / "overrides" / subdir / name)
    # Tier 2 -- legacy
    paths["legacy"] = _create_file(kittify / subdir / name)
    # Tier 3 -- global
    gh = global_home or (tmp_path / "global_home")
    paths["global"] = _create_file(gh / "missions" / mission / subdir / name)
    # Tier 4 -- package
    pr = pkg_root or (tmp_path / "pkg")
    paths["package"] = _create_file(pr / mission / subdir / name)

    return paths


# ---------------------------------------------------------------------------
# T018 -- Resolution precedence tests (G2)
# ---------------------------------------------------------------------------

class TestResolutionPrecedence:
    """Test that the 4-tier precedence chain is respected."""

    def test_override_takes_precedence(self, tmp_path: Path) -> None:
        """When the asset exists at all tiers, override (tier 1) wins."""
        project = tmp_path / "project"
        global_home = tmp_path / "global_home"
        pkg_root = tmp_path / "pkg"

        paths = _setup_all_tiers(
            tmp_path,
            name="spec-template.md",
            subdir="templates",
            global_home=global_home,
            pkg_root=pkg_root,
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
            result = resolve_template("spec-template.md", project)

        assert result.tier == ResolutionTier.OVERRIDE
        assert result.path == paths["override"]

    def test_legacy_takes_precedence_over_global(self, tmp_path: Path) -> None:
        """When override is absent, legacy (tier 2) wins over global (tier 3)."""
        project = tmp_path / "project"
        kittify = project / ".kittify"
        global_home = tmp_path / "global_home"
        pkg_root = tmp_path / "pkg"

        # Create legacy, global, package -- but NOT override
        _create_file(kittify / "templates" / "spec-template.md")
        _create_file(global_home / "missions" / "software-dev" / "templates" / "spec-template.md")
        _create_file(pkg_root / "software-dev" / "templates" / "spec-template.md")

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=global_home,
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            result = resolve_template("spec-template.md", project)

        assert result.tier == ResolutionTier.LEGACY
        # Should have emitted a DeprecationWarning
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1

    def test_global_resolves_when_no_override_or_legacy(self, tmp_path: Path) -> None:
        """When override and legacy are absent, global (tier 3) wins."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        global_home = tmp_path / "global_home"
        pkg_root = tmp_path / "pkg"

        _create_file(global_home / "missions" / "software-dev" / "templates" / "spec-template.md")
        _create_file(pkg_root / "software-dev" / "templates" / "spec-template.md")

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
            result = resolve_template("spec-template.md", project)

        assert result.tier == ResolutionTier.GLOBAL

    def test_package_default_resolves_when_no_other_tiers(self, tmp_path: Path) -> None:
        """When only the package default exists, it resolves there."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        pkg_root = tmp_path / "pkg"

        pkg_path = _create_file(pkg_root / "software-dev" / "templates" / "spec-template.md")

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "nonexistent_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            result = resolve_template("spec-template.md", project)

        assert result.tier == ResolutionTier.PACKAGE_DEFAULT
        assert result.path == pkg_path

    def test_file_not_found_when_no_tier_has_asset(self, tmp_path: Path) -> None:
        """FileNotFoundError raised when no tier has the requested asset."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "empty_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ),
        ):
            with pytest.raises(FileNotFoundError, match="not found in any resolution tier"):
                resolve_template("nonexistent.md", project)


# ---------------------------------------------------------------------------
# T018 -- resolve_command and resolve_mission tests
# ---------------------------------------------------------------------------

class TestResolveCommand:
    """Test resolve_command follows the same 4-tier chain for command-templates/."""

    def test_override_wins_for_command(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        kittify = project / ".kittify"
        pkg_root = tmp_path / "pkg"

        override_path = _create_file(kittify / "overrides" / "command-templates" / "plan.md")
        _create_file(pkg_root / "software-dev" / "command-templates" / "plan.md")

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
            result = resolve_command("plan.md", project)

        assert result.tier == ResolutionTier.OVERRIDE
        assert result.path == override_path

    def test_package_fallback_for_command(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)
        pkg_root = tmp_path / "pkg"

        pkg_path = _create_file(pkg_root / "software-dev" / "command-templates" / "implement.md")

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
            result = resolve_command("implement.md", project)

        assert result.tier == ResolutionTier.PACKAGE_DEFAULT
        assert result.path == pkg_path


class TestResolveMission:
    """Test resolve_mission for mission.yaml resolution."""

    def test_override_wins_for_mission(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        kittify = project / ".kittify"
        pkg_root = tmp_path / "pkg"

        override_path = _create_file(
            kittify / "overrides" / "missions" / "software-dev" / "mission.yaml"
        )
        _create_file(pkg_root / "software-dev" / "mission.yaml")

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
            result = resolve_mission("software-dev", project)

        assert result.tier == ResolutionTier.OVERRIDE
        assert result.path == override_path
        assert result.mission == "software-dev"

    def test_legacy_mission_emits_warning(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        kittify = project / ".kittify"

        _create_file(kittify / "missions" / "research" / "mission.yaml")

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            result = resolve_mission("research", project)

        assert result.tier == ResolutionTier.LEGACY
        assert result.mission == "research"
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1

    def test_mission_not_found(self, tmp_path: Path) -> None:
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
            with pytest.raises(FileNotFoundError, match="not found in any resolution tier"):
                resolve_mission("nonexistent", project)


# ---------------------------------------------------------------------------
# T019 -- Legacy resolution tests (F-Legacy)
# ---------------------------------------------------------------------------

class TestLegacyResolution:
    """Tests for the F-Legacy family of acceptance criteria."""

    def test_legacy_customized_resolves_with_warning(self, tmp_path: Path) -> None:
        """F-Legacy-001: A customized file in .kittify/templates/ resolves
        with a DeprecationWarning pointing the user to 'spec-kitty migrate'.
        """
        project = tmp_path / "project"
        kittify = project / ".kittify"

        legacy_path = _create_file(
            kittify / "templates" / "spec-template.md",
            content="# Custom override content\nUser-modified template.",
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            result = resolve_template("spec-template.md", project)

        assert result.tier == ResolutionTier.LEGACY
        assert result.path == legacy_path

        # Verify the exact DeprecationWarning shape
        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 1
        assert "spec-kitty migrate" in str(deprecation_warnings[0].message)
        assert "Legacy asset resolved" in str(deprecation_warnings[0].message)
        assert "next major version" in str(deprecation_warnings[0].message)

    def test_legacy_no_customization_resolves_with_warning(self, tmp_path: Path) -> None:
        """F-Legacy-002: Even an unmodified file at the legacy path resolves
        with the same deprecation warning (we don't diff against defaults).
        """
        project = tmp_path / "project"
        kittify = project / ".kittify"

        # Identical to package default -- still legacy tier
        legacy_path = _create_file(
            kittify / "command-templates" / "plan.md",
            content="# Default plan template",
        )

        pkg_root = tmp_path / "pkg"
        _create_file(
            pkg_root / "software-dev" / "command-templates" / "plan.md",
            content="# Default plan template",  # same content
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
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            result = resolve_command("plan.md", project)

        assert result.tier == ResolutionTier.LEGACY
        assert result.path == legacy_path

        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 1
        assert "Legacy asset resolved" in str(deprecation_warnings[0].message)

    def test_legacy_stale_differing_resolves_legacy_version(self, tmp_path: Path) -> None:
        """F-Legacy-003: When the legacy file differs from the global/package
        version, the legacy version is used (not global or package).
        """
        project = tmp_path / "project"
        kittify = project / ".kittify"
        global_home = tmp_path / "global_home"
        pkg_root = tmp_path / "pkg"

        legacy_path = _create_file(
            kittify / "templates" / "tasks-template.md",
            content="# Old stale legacy version",
        )
        _create_file(
            global_home / "missions" / "software-dev" / "templates" / "tasks-template.md",
            content="# Updated global version",
        )
        _create_file(
            pkg_root / "software-dev" / "templates" / "tasks-template.md",
            content="# Latest package default",
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
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            result = resolve_template("tasks-template.md", project)

        # Legacy wins over global and package
        assert result.tier == ResolutionTier.LEGACY
        assert result.path == legacy_path
        assert result.path.read_text() == "# Old stale legacy version"

        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 1


# ---------------------------------------------------------------------------
# T018 -- ResolutionResult dataclass tests
# ---------------------------------------------------------------------------

class TestResolutionResult:
    """Verify ResolutionResult is frozen and has correct defaults."""

    def test_frozen(self, tmp_path: Path) -> None:
        r = ResolutionResult(path=tmp_path, tier=ResolutionTier.OVERRIDE)
        with pytest.raises(AttributeError):
            r.path = tmp_path / "other"  # type: ignore[misc]

    def test_mission_defaults_to_none(self, tmp_path: Path) -> None:
        r = ResolutionResult(path=tmp_path, tier=ResolutionTier.GLOBAL)
        assert r.mission is None

    def test_mission_can_be_set(self, tmp_path: Path) -> None:
        r = ResolutionResult(path=tmp_path, tier=ResolutionTier.PACKAGE_DEFAULT, mission="research")
        assert r.mission == "research"


# ---------------------------------------------------------------------------
# Init integration -- _resolve_mission_command_templates_dir uses 4-tier
# ---------------------------------------------------------------------------

class TestInitResolverIntegration:
    """Prove that init template discovery respects the full 4-tier chain.

    The helper ``_resolve_mission_command_templates_dir`` from ``init.py``
    should honour override and global tiers, not just project-local and
    package defaults.
    """

    def test_override_template_selected_over_package(self, tmp_path: Path) -> None:
        """An override-tier command template is used instead of the package default."""
        from specify_cli.cli.commands.init import _resolve_mission_command_templates_dir

        project = tmp_path / "project"
        kittify = project / ".kittify"
        pkg_root = tmp_path / "pkg"

        # Package default
        _create_file(
            pkg_root / "software-dev" / "command-templates" / "plan.md",
            content="# Package default plan",
        )

        # Override tier -- should win
        _create_file(
            kittify / "overrides" / "command-templates" / "plan.md",
            content="# Custom override plan",
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
            # Also patch at the init module level (used in the discovery scan)
            patch(
                "specify_cli.cli.commands.init.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.cli.commands.init.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            resolved_dir = _resolve_mission_command_templates_dir(
                project, "software-dev", scratch_parent=tmp_path / "scratch",
            )

        plan_file = resolved_dir / "plan.md"
        assert plan_file.exists(), "plan.md should be in the resolved directory"
        assert plan_file.read_text() == "# Custom override plan"

    def test_global_template_selected_over_package(self, tmp_path: Path) -> None:
        """A global-tier command template is used when no override or legacy exists."""
        from specify_cli.cli.commands.init import _resolve_mission_command_templates_dir

        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        global_home = tmp_path / "global_home"
        pkg_root = tmp_path / "pkg"

        # Package default
        _create_file(
            pkg_root / "software-dev" / "command-templates" / "implement.md",
            content="# Package default implement",
        )

        # Global tier -- should win (no override, no legacy)
        _create_file(
            global_home / "missions" / "software-dev" / "command-templates" / "implement.md",
            content="# Global custom implement",
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
            patch(
                "specify_cli.cli.commands.init.get_kittify_home",
                return_value=global_home,
            ),
            patch(
                "specify_cli.cli.commands.init.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            resolved_dir = _resolve_mission_command_templates_dir(
                project, "software-dev", scratch_parent=tmp_path / "scratch",
            )

        impl_file = resolved_dir / "implement.md"
        assert impl_file.exists(), "implement.md should be in the resolved directory"
        assert impl_file.read_text() == "# Global custom implement"

    def test_mixed_tiers_each_file_resolved_independently(self, tmp_path: Path) -> None:
        """Different files can be resolved from different tiers simultaneously."""
        from specify_cli.cli.commands.init import _resolve_mission_command_templates_dir

        project = tmp_path / "project"
        kittify = project / ".kittify"
        global_home = tmp_path / "global_home"
        pkg_root = tmp_path / "pkg"

        # plan.md -- override wins
        _create_file(
            kittify / "overrides" / "command-templates" / "plan.md",
            content="# Override plan",
        )
        _create_file(
            pkg_root / "software-dev" / "command-templates" / "plan.md",
            content="# Package plan",
        )

        # implement.md -- global wins (no override, no legacy)
        _create_file(
            global_home / "missions" / "software-dev" / "command-templates" / "implement.md",
            content="# Global implement",
        )
        _create_file(
            pkg_root / "software-dev" / "command-templates" / "implement.md",
            content="# Package implement",
        )

        # review.md -- only at package level
        _create_file(
            pkg_root / "software-dev" / "command-templates" / "review.md",
            content="# Package review",
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
            patch(
                "specify_cli.cli.commands.init.get_kittify_home",
                return_value=global_home,
            ),
            patch(
                "specify_cli.cli.commands.init.get_package_asset_root",
                return_value=pkg_root,
            ),
        ):
            resolved_dir = _resolve_mission_command_templates_dir(
                project, "software-dev", scratch_parent=tmp_path / "scratch",
            )

        assert (resolved_dir / "plan.md").read_text() == "# Override plan"
        assert (resolved_dir / "implement.md").read_text() == "# Global implement"
        assert (resolved_dir / "review.md").read_text() == "# Package review"

    def test_empty_result_when_no_tiers_have_templates(self, tmp_path: Path) -> None:
        """Returns an empty directory when no templates exist anywhere."""
        from specify_cli.cli.commands.init import _resolve_mission_command_templates_dir

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
            patch(
                "specify_cli.cli.commands.init.get_kittify_home",
                return_value=tmp_path / "no_home",
            ),
            patch(
                "specify_cli.cli.commands.init.get_package_asset_root",
                side_effect=FileNotFoundError("no pkg"),
            ),
        ):
            resolved_dir = _resolve_mission_command_templates_dir(
                project, "software-dev", scratch_parent=tmp_path / "scratch",
            )

        assert resolved_dir.is_dir()
        assert list(resolved_dir.glob("*.md")) == []
