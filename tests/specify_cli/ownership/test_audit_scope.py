"""Tests for codebase-wide audit scope in ownership validation.

Covers:
- T018: scope field in frontmatter (optional, backward compatible)
- T019: Relaxed ownership validation for codebase-wide WPs
- T020: Audit template targets covering all agent dirs + docs
- T021: Finalize-time coverage validation (warnings for uncovered targets)
- T022: All test scenarios from the WP specification
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.ownership.audit_targets import (
    AUDIT_TEMPLATE_TARGETS,
    get_audit_targets,
    validate_audit_coverage,
)
from specify_cli.ownership.models import (
    ExecutionMode,
    OwnershipManifest,
    SCOPE_CODEBASE_WIDE,
)
from specify_cli.ownership.validation import (
    validate_all,
    validate_authoritative_surface,
    validate_execution_mode_consistency,
    validate_no_overlap,
)


def _manifest(
    mode: ExecutionMode = ExecutionMode.CODE_CHANGE,
    owned: tuple[str, ...] = ("src/foo/**",),
    surface: str = "src/foo/",
    scope: str | None = None,
) -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=mode,
        owned_files=owned,
        authoritative_surface=surface,
        scope=scope,
    )


def _codebase_wide_manifest(
    mode: ExecutionMode = ExecutionMode.CODE_CHANGE,
    owned: tuple[str, ...] = ("**/*",),
    surface: str = "/",
) -> OwnershipManifest:
    return _manifest(mode=mode, owned=owned, surface=surface, scope=SCOPE_CODEBASE_WIDE)


# ---------------------------------------------------------------------------
# T018: scope field on OwnershipManifest
# ---------------------------------------------------------------------------


class TestScopeField:
    def test_scope_field_default_is_none(self) -> None:
        """Omitting scope produces None (backward compatible)."""
        m = _manifest()
        assert m.scope is None
        assert not m.is_codebase_wide

    def test_scope_codebase_wide(self) -> None:
        m = _codebase_wide_manifest()
        assert m.scope == "codebase-wide"
        assert m.is_codebase_wide

    def test_from_frontmatter_without_scope(self) -> None:
        """WP without scope field passes validation normally."""
        data = {
            "execution_mode": "code_change",
            "owned_files": ["src/foo/**"],
            "authoritative_surface": "src/foo/",
        }
        m = OwnershipManifest.from_frontmatter(data)
        assert m.scope is None
        assert not m.is_codebase_wide

    def test_from_frontmatter_with_scope(self) -> None:
        """scope: codebase-wide is parsed correctly from frontmatter."""
        data = {
            "execution_mode": "code_change",
            "owned_files": ["**/*"],
            "authoritative_surface": "/",
            "scope": "codebase-wide",
        }
        m = OwnershipManifest.from_frontmatter(data)
        assert m.scope == "codebase-wide"
        assert m.is_codebase_wide

    def test_to_frontmatter_without_scope(self) -> None:
        """Narrow WP does not include scope in frontmatter output."""
        m = _manifest()
        fm = m.to_frontmatter()
        assert "scope" not in fm

    def test_to_frontmatter_with_scope(self) -> None:
        """Codebase-wide WP includes scope in frontmatter output."""
        m = _codebase_wide_manifest()
        fm = m.to_frontmatter()
        assert fm["scope"] == "codebase-wide"

    def test_empty_scope_string_treated_as_none(self) -> None:
        """Empty string scope is normalized to None."""
        data = {
            "execution_mode": "code_change",
            "owned_files": ["src/**"],
            "authoritative_surface": "src/",
            "scope": "",
        }
        m = OwnershipManifest.from_frontmatter(data)
        assert m.scope is None
        assert not m.is_codebase_wide


# ---------------------------------------------------------------------------
# T019: Relaxed validation for codebase-wide scope
# ---------------------------------------------------------------------------


class TestCodebaseWidePassesOverlapValidation:
    """test_codebase_wide_passes_overlap_validation:
    Two WPs with overlapping files where one is codebase-wide -- no error."""

    def test_codebase_wide_skips_overlap(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/foo/**",), surface="src/foo/"),
            "WP02": _codebase_wide_manifest(owned=("**/*",), surface="/"),
        }
        errors = validate_no_overlap(manifests)
        assert errors == []

    def test_two_codebase_wide_no_overlap_error(self) -> None:
        """Two codebase-wide WPs do not conflict with each other."""
        manifests = {
            "WP01": _codebase_wide_manifest(),
            "WP02": _codebase_wide_manifest(),
        }
        errors = validate_no_overlap(manifests)
        assert errors == []


class TestNarrowWPsStillFailOverlap:
    """test_narrow_wps_still_fail_overlap:
    Two narrow WPs with overlap -- error as before."""

    def test_narrow_overlap_still_errors(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/foo/**",), surface="src/foo/"),
            "WP02": _manifest(owned=("src/foo/**",), surface="src/foo/"),
        }
        errors = validate_no_overlap(manifests)
        assert len(errors) >= 1
        assert "WP01" in errors[0] and "WP02" in errors[0]


class TestCodebaseWideSkipsAuthoritativeSurface:
    """test_codebase_wide_skips_authoritative_surface:
    WP with scope: codebase-wide and broad authoritative_surface passes."""

    def test_broad_surface_passes(self) -> None:
        m = _codebase_wide_manifest(surface="/")
        errors = validate_authoritative_surface(m)
        assert errors == []

    def test_empty_surface_passes_for_codebase_wide(self) -> None:
        """Empty authoritative_surface is fine for codebase-wide WPs."""
        m = OwnershipManifest(
            execution_mode=ExecutionMode.CODE_CHANGE,
            owned_files=("**/*",),
            authoritative_surface="",
            scope=SCOPE_CODEBASE_WIDE,
        )
        errors = validate_authoritative_surface(m)
        assert errors == []

    def test_narrow_empty_surface_still_errors(self) -> None:
        """Narrow WPs with empty surface still get errors."""
        m = _manifest(surface="")
        errors = validate_authoritative_surface(m)
        assert len(errors) == 1
        assert "empty" in errors[0].lower()


class TestCodebaseWideSkipsExecutionModeConsistency:
    """Codebase-wide WPs skip execution mode consistency checks."""

    def test_code_change_with_planning_paths_no_warning(self) -> None:
        """Audit WP can be code_change but touch kitty-specs/."""
        m = _codebase_wide_manifest(
            mode=ExecutionMode.CODE_CHANGE,
            owned=("kitty-specs/**", "src/**"),
        )
        warnings = validate_execution_mode_consistency(m)
        assert warnings == []

    def test_planning_artifact_with_src_no_warning(self) -> None:
        """Audit WP can be planning_artifact but scan src/."""
        m = _codebase_wide_manifest(
            mode=ExecutionMode.PLANNING_ARTIFACT,
            owned=("src/specify_cli/**",),
        )
        warnings = validate_execution_mode_consistency(m)
        assert warnings == []

    def test_narrow_planning_with_src_still_warns(self) -> None:
        """Narrow WPs still get mode consistency warnings."""
        m = _manifest(
            mode=ExecutionMode.PLANNING_ARTIFACT,
            owned=("src/specify_cli/ownership/**",),
            surface="src/specify_cli/ownership/",
        )
        warnings = validate_execution_mode_consistency(m)
        assert len(warnings) == 1


class TestScopeFieldOptional:
    """test_scope_field_optional:
    WP without scope field passes validation normally."""

    def test_no_scope_passes_all_validations(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/alpha/**",), surface="src/alpha/"),
            "WP02": _manifest(owned=("src/beta/**",), surface="src/beta/"),
        }
        result = validate_all(manifests)
        assert result.passed


class TestMixedScopeMission:
    """test_mixed_scope_mission:
    Mission with both narrow and codebase-wide WPs validates correctly."""

    def test_mixed_scope_passes(self) -> None:
        manifests = {
            "WP01": _manifest(owned=("src/alpha/**",), surface="src/alpha/"),
            "WP02": _manifest(owned=("src/beta/**",), surface="src/beta/"),
            "WP03": _codebase_wide_manifest(owned=("**/*",), surface="/"),
        }
        result = validate_all(manifests)
        assert result.passed
        assert result.errors == []

    def test_mixed_scope_narrow_overlap_still_detected(self) -> None:
        """Even with a codebase-wide WP, narrow WPs that overlap still fail."""
        manifests = {
            "WP01": _manifest(owned=("src/foo/**",), surface="src/foo/"),
            "WP02": _manifest(owned=("src/foo/**",), surface="src/foo/"),
            "WP03": _codebase_wide_manifest(),
        }
        result = validate_all(manifests)
        assert not result.passed
        assert any("WP01" in e and "WP02" in e for e in result.errors)

    def test_codebase_wide_no_mode_warnings(self) -> None:
        """Codebase-wide WPs produce zero warnings in validate_all."""
        manifests = {
            "WP01": _codebase_wide_manifest(
                mode=ExecutionMode.CODE_CHANGE,
                owned=("kitty-specs/**", "docs/**"),
            ),
        }
        result = validate_all(manifests)
        assert result.passed
        # Should have no warnings since codebase-wide WPs skip mode checks
        assert not any("WP01" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# T020: Audit template targets
# ---------------------------------------------------------------------------


class TestAuditTemplateTargets:
    """test_audit_targets_include_agent_dirs:
    Verify AUDIT_TEMPLATE_TARGETS covers all 12+ agents."""

    def test_includes_all_agent_dirs(self) -> None:
        from specify_cli.agent_utils.directories import AGENT_DIRS

        for agent_root, subdir in AGENT_DIRS:
            target = f"{agent_root}/{subdir}/"
            assert target in AUDIT_TEMPLATE_TARGETS, (
                f"Missing agent target: {target}"
            )

    def test_includes_docs(self) -> None:
        assert "docs/" in AUDIT_TEMPLATE_TARGETS

    def test_includes_command_templates(self) -> None:
        assert "src/specify_cli/missions/*/command-templates/" in AUDIT_TEMPLATE_TARGETS

    def test_get_audit_targets_filters_existing(self, tmp_path: Path) -> None:
        """get_audit_targets() only returns directories that exist."""
        # Create just a couple of directories
        (tmp_path / "docs").mkdir()
        (tmp_path / ".claude" / "commands").mkdir(parents=True)

        targets = get_audit_targets(tmp_path)
        target_strs = [str(t) for t in targets]
        assert str(tmp_path / "docs") in target_strs
        assert str(tmp_path / ".claude" / "commands") in target_strs

    def test_get_audit_targets_empty_repo(self, tmp_path: Path) -> None:
        """Empty repo returns no targets."""
        targets = get_audit_targets(tmp_path)
        assert targets == []


# ---------------------------------------------------------------------------
# T021: Finalize-time validation for template/doc coverage
# ---------------------------------------------------------------------------


class TestFinalizeWarnsUncoveredTargets:
    """test_finalize_warns_uncovered_targets:
    Mission with audit WP that does not cover docs/ -- warning emitted."""

    def test_uncovered_target_warns(self, tmp_path: Path) -> None:
        """Audit WP that does not cover docs/ produces a warning."""
        (tmp_path / "docs").mkdir()
        (tmp_path / ".claude" / "commands").mkdir(parents=True)

        # Only cover .claude, not docs
        warnings = validate_audit_coverage(
            codebase_wide_owned_files=[[".claude/**"]],
            repo_root=tmp_path,
        )
        # Should warn about uncovered docs/
        assert any("docs" in w for w in warnings)

    def test_wildcard_covers_all(self, tmp_path: Path) -> None:
        """scope: codebase-wide with owned_files: ['**/*'] covers all targets."""
        (tmp_path / "docs").mkdir()
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        (tmp_path / ".codex" / "prompts").mkdir(parents=True)

        warnings = validate_audit_coverage(
            codebase_wide_owned_files=[["**/*"]],
            repo_root=tmp_path,
        )
        assert warnings == []

    def test_warning_is_nonblocking(self, tmp_path: Path) -> None:
        """Warning is non-blocking -- returns warnings, not exceptions."""
        (tmp_path / "docs").mkdir()

        warnings = validate_audit_coverage(
            codebase_wide_owned_files=[["src/**"]],
            repo_root=tmp_path,
        )
        # This should just be a list of strings, never raises
        assert isinstance(warnings, list)
        assert len(warnings) > 0

    def test_no_codebase_wide_wps_no_warnings(self, tmp_path: Path) -> None:
        """If no codebase-wide WPs exist, no coverage warnings."""
        (tmp_path / "docs").mkdir()

        warnings = validate_audit_coverage(
            codebase_wide_owned_files=[],
            repo_root=tmp_path,
        )
        assert warnings == []

    def test_multiple_codebase_wide_wps_combined_coverage(self, tmp_path: Path) -> None:
        """Multiple codebase-wide WPs can jointly cover all targets."""
        (tmp_path / "docs").mkdir()
        (tmp_path / ".claude" / "commands").mkdir(parents=True)

        warnings = validate_audit_coverage(
            codebase_wide_owned_files=[
                ["docs/**"],
                [".claude/**"],
            ],
            repo_root=tmp_path,
        )
        assert warnings == []
