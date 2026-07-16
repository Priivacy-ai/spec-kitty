"""Tests for the 4-tier asset resolver.

Covers:
- T018: Resolution precedence tests (G2)
- T019: Legacy resolution tests (F-Legacy)
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from charter.mission_type_profiles import ResolvedMissionType
from specify_cli.runtime.resolver import (
    ResolutionResult,
    ResolutionTier,
    TemplateConfigurationError,
    resolve_command,
    resolve_configured_template,
    resolve_mission,
    resolve_template,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.unit, pytest.mark.fast]


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


def _resolved_mission_type(
    *,
    mission_type: str | None = "software-dev",
    template_set: dict[str, str] | None = None,
) -> ResolvedMissionType:
    """Build a narrow activated-context fixture without reading doctrine files."""
    mapping = {"spec": "configured-spec.md"} if template_set is None else template_set
    return ResolvedMissionType(
        mission_type=mission_type,
        governance_text="",
        action_sequence=[],
        provenance="builtin",
        _template_set_thunk=lambda: mapping,
    )


# ---------------------------------------------------------------------------
# Configured content-template selection (issue #2658)
# ---------------------------------------------------------------------------


class TestConfiguredTemplateResolution:
    """Artifact keys resolve through activated mission configuration."""

    @pytest.mark.parametrize(
        "mission_type",
        [
            "",
            "   ",
            "../..",
            "/absolute/type",
            "nested/type",
            r"nested\type",
            r"C:\missions\type",
            "C:type",
            ".",
            ".hidden-type",
        ],
        ids=[
            "empty",
            "whitespace",
            "parent-traversal",
            "absolute-posix",
            "nested-forward-separator",
            "nested-windows-separator",
            "windows-absolute-drive",
            "windows-drive-relative",
            "dot-segment",
            "hidden-segment",
        ],
    )
    def test_unsafe_mission_type_fails_before_mapping_or_file_resolution(
        self,
        tmp_path: Path,
        mission_type: str,
    ) -> None:
        mapping_resolver = Mock(
            side_effect=AssertionError("unsafe mission type read its template mapping")
        )
        context = ResolvedMissionType(
            mission_type=mission_type,
            governance_text="",
            action_sequence=[],
            provenance="forged-test-context",
            _template_set_thunk=mapping_resolver,
        )

        with (
            patch("specify_cli.runtime.resolver.resolve_template") as file_resolver,
            pytest.raises(TemplateConfigurationError) as exc_info,
        ):
            resolve_configured_template("spec", tmp_path, context)

        error = exc_info.value
        assert error.mission_type == mission_type
        assert error.artifact_kind == "spec"
        assert error.mapped_filename is None
        assert "unsafe mission type" in str(error)
        assert repr(mission_type) in str(error)
        assert isinstance(error.__cause__, ValueError)
        mapping_resolver.assert_not_called()
        file_resolver.assert_not_called()

    def test_safe_unactivated_forged_mission_type_cannot_escape_paths(
        self,
        tmp_path: Path,
    ) -> None:
        """Path safety is local; activation authenticity remains caller-owned."""
        mission_type = "forged-but-safe-custom"
        mapped_filename = "spec-template.md"
        context = _resolved_mission_type(
            mission_type=mission_type,
            template_set={"spec": mapped_filename},
        )
        expected = ResolutionResult(
            path=tmp_path / mapped_filename,
            tier=ResolutionTier.PACKAGE_DEFAULT,
            mission=mission_type,
        )

        with patch(
            "specify_cli.runtime.resolver.resolve_template",
            return_value=expected,
        ) as file_resolver:
            result = resolve_configured_template("spec", tmp_path, context)

        assert result is expected
        file_resolver.assert_called_once_with(
            mapped_filename,
            tmp_path,
            mission=mission_type,
        )

    def test_mapped_filename_preserves_project_override_precedence(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        override = _create_file(
            project / ".kittify" / "overrides" / "templates" / "configured-spec.md",
            "override",
        )
        _create_file(
            tmp_path
            / "global_home"
            / "missions"
            / "software-dev"
            / "templates"
            / "configured-spec.md",
            "global",
        )

        with patch(
            "specify_cli.runtime.resolver.get_kittify_home",
            return_value=tmp_path / "global_home",
        ):
            result = resolve_configured_template(
                "spec", project, _resolved_mission_type()
            )

        assert result == ResolutionResult(
            path=override,
            tier=ResolutionTier.OVERRIDE,
            mission="software-dev",
        )

    def test_mapped_filename_preserves_package_default_tier(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        package_root = tmp_path / "package"
        configured = _create_file(
            package_root
            / "software-dev"
            / "templates"
            / "configured-spec.md",
            "package",
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "empty-home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                return_value=package_root,
            ),
        ):
            result = resolve_configured_template(
                "spec", project, _resolved_mission_type()
            )

        assert result.path == configured
        assert result.tier is ResolutionTier.PACKAGE_DEFAULT
        assert result.mission == "software-dev"

    @pytest.mark.parametrize("template_set", [None, {}])
    def test_null_or_missing_mapping_fails_before_file_resolution(
        self,
        tmp_path: Path,
        template_set: dict[str, str] | None,
    ) -> None:
        context = ResolvedMissionType(
            mission_type="documentation",
            governance_text="",
            action_sequence=[],
            provenance="builtin",
            _template_set_thunk=lambda: template_set,
        )

        with (
            patch("specify_cli.runtime.resolver.resolve_template") as file_resolver,
            pytest.raises(TemplateConfigurationError) as exc_info,
        ):
            resolve_configured_template("spec", tmp_path, context)

        assert exc_info.value.mission_type == "documentation"
        assert exc_info.value.artifact_kind == "spec"
        assert "documentation" in str(exc_info.value)
        assert "spec" in str(exc_info.value)
        file_resolver.assert_not_called()

    @pytest.mark.parametrize("mapped_filename", ["", "   "])
    def test_blank_mapped_filename_fails_before_file_resolution(
        self, tmp_path: Path, mapped_filename: str
    ) -> None:
        context = _resolved_mission_type(template_set={"plan": mapped_filename})

        with (
            patch("specify_cli.runtime.resolver.resolve_template") as file_resolver,
            pytest.raises(TemplateConfigurationError, match="software-dev.*plan"),
        ):
            resolve_configured_template("plan", tmp_path, context)

        file_resolver.assert_not_called()

    @pytest.mark.parametrize(
        "mapped_filename",
        [
            "/etc/spec-template.md",
            "../spec-template.md",
            "nested/spec-template.md",
            r"nested\spec-template.md",
            r"C:\templates\spec-template.md",
            "C:spec-template.md",
            ".",
            ".spec-template.md",
            " spec-template.md",
            "spec-template.md ",
        ],
        ids=[
            "absolute-posix",
            "parent-traversal",
            "nested-forward-separator",
            "nested-windows-separator",
            "windows-absolute-drive",
            "windows-drive-relative",
            "dot-segment",
            "hidden-file",
            "leading-whitespace",
            "trailing-whitespace",
        ],
    )
    def test_unsafe_mapped_filename_fails_before_file_resolution(
        self,
        tmp_path: Path,
        mapped_filename: str,
    ) -> None:
        context = _resolved_mission_type(template_set={"spec": mapped_filename})

        with (
            patch("specify_cli.runtime.resolver.resolve_template") as file_resolver,
            pytest.raises(TemplateConfigurationError) as exc_info,
        ):
            resolve_configured_template("spec", tmp_path, context)

        error = exc_info.value
        assert error.mission_type == "software-dev"
        assert error.artifact_kind == "spec"
        assert error.mapped_filename == mapped_filename
        assert "unsafe filename" in str(error)
        assert repr(mapped_filename) in str(error)
        assert isinstance(error.__cause__, ValueError)
        file_resolver.assert_not_called()

    @pytest.mark.parametrize(
        "mapped_filename",
        [
            "CON",
            "con.md",
            "PrN.txt",
            "AUX.tar.gz",
            "nul.md",
            "CLOCK$.yaml",
            "COM1.md",
            "com9.MD",
            "LPT1",
            "lPt9.template",
            "spec-template.md.",
            "plan-template.md ",
        ],
        ids=[
            "con-bare",
            "con-extension-lowercase",
            "prn-extension-mixed-case",
            "aux-multiple-extensions",
            "nul-extension-lowercase",
            "clock-dollar-extension",
            "com-first",
            "com-last-lowercase",
            "lpt-first",
            "lpt-last-mixed-case",
            "trailing-dot",
            "trailing-space",
        ],
    )
    def test_windows_unsafe_mapped_filename_fails_before_file_resolution(
        self,
        tmp_path: Path,
        mapped_filename: str,
    ) -> None:
        context = _resolved_mission_type(template_set={"spec": mapped_filename})

        with (
            patch("specify_cli.runtime.resolver.resolve_template") as file_resolver,
            pytest.raises(TemplateConfigurationError) as exc_info,
        ):
            resolve_configured_template("spec", tmp_path, context)

        error = exc_info.value
        assert error.mission_type == "software-dev"
        assert error.artifact_kind == "spec"
        assert error.mapped_filename == mapped_filename
        assert "unsafe filename" in str(error)
        assert repr(mapped_filename) in str(error)
        assert isinstance(error.__cause__, ValueError)
        file_resolver.assert_not_called()

    @pytest.mark.parametrize("mapped_filename", ["spec-template.md", "plan-template.md"])
    def test_portable_mapped_filename_reaches_file_resolution(
        self,
        tmp_path: Path,
        mapped_filename: str,
    ) -> None:
        context = _resolved_mission_type(template_set={"spec": mapped_filename})
        expected = ResolutionResult(
            path=tmp_path / mapped_filename,
            tier=ResolutionTier.PACKAGE_DEFAULT,
            mission="software-dev",
        )

        with patch(
            "specify_cli.runtime.resolver.resolve_template",
            return_value=expected,
        ) as file_resolver:
            result = resolve_configured_template("spec", tmp_path, context)

        assert result is expected
        file_resolver.assert_called_once_with(
            mapped_filename,
            tmp_path,
            mission="software-dev",
        )

    def test_unresolved_mapped_filename_adds_configuration_context(
        self, tmp_path: Path
    ) -> None:
        context = _resolved_mission_type(
            template_set={"plan": "configured-plan.md"}
        )

        with (
            patch(
                "specify_cli.runtime.resolver.get_kittify_home",
                return_value=tmp_path / "empty-home",
            ),
            patch(
                "specify_cli.runtime.resolver.get_package_asset_root",
                side_effect=FileNotFoundError("no package"),
            ),
            pytest.raises(TemplateConfigurationError) as exc_info,
        ):
            resolve_configured_template("plan", tmp_path / "project", context)

        error = exc_info.value
        assert error.mission_type == "software-dev"
        assert error.artifact_kind == "plan"
        assert error.mapped_filename == "configured-plan.md"
        assert "configured-plan.md" in str(error)
        assert isinstance(error.__cause__, FileNotFoundError)

    def test_typeless_context_fails_without_software_development_inference(
        self, tmp_path: Path
    ) -> None:
        context = _resolved_mission_type(
            mission_type=None,
            template_set={"spec": "configured-spec.md"},
        )

        with (
            patch("specify_cli.runtime.resolver.resolve_template") as file_resolver,
            pytest.raises(TemplateConfigurationError) as exc_info,
        ):
            resolve_configured_template("spec", tmp_path, context)

        assert exc_info.value.mission_type == "<typeless>"
        assert exc_info.value.artifact_kind == "spec"
        assert "<typeless>" in str(exc_info.value)
        file_resolver.assert_not_called()

    def test_mission_shim_reexports_configured_template_seam(self) -> None:
        from specify_cli.cli.commands.agent import mission

        assert mission.resolve_configured_template is resolve_configured_template


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

        assert result.tier == ResolutionTier.GLOBAL_MISSION

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
            ),pytest.raises(FileNotFoundError, match="not found in any resolution tier")
        ):
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
            ),pytest.raises(FileNotFoundError, match="not found in any resolution tier")
        ):
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
