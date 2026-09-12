"""Unit tests for ``tool_surface.bundles.model``."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from specify_cli.tool_surface.enums import ToolSurfaceKind
from specify_cli.tool_surface.bundles.model import (
    TARGET_CLAUDE_CODE,
    BundleEntry,
    BundleValidationResult,
    PluginBundle,
)
from specify_cli.tool_surface.findings import make_finding

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _entry(kind: ToolSurfaceKind, rel: str) -> BundleEntry:
    return BundleEntry(
        surface_kind=kind, source_path=Path("/p") / rel, bundle_relative_path=rel
    )


def test_dataclasses_are_frozen() -> None:
    entry = _entry(ToolSurfaceKind.COMMAND_SKILL, "skills/a/SKILL.md")
    with pytest.raises(FrozenInstanceError):
        entry.bundle_relative_path = "x"  # type: ignore[misc]


def test_plugin_bundle_kinds_collects_distinct_kinds() -> None:
    bundle = PluginBundle(
        distribution_target=TARGET_CLAUDE_CODE,
        entries=(
            _entry(ToolSurfaceKind.COMMAND_SKILL, "skills/a/SKILL.md"),
            _entry(ToolSurfaceKind.COMMAND_SKILL, "skills/b/SKILL.md"),
            _entry(ToolSurfaceKind.AGENT_PROFILE, "agents/x.md"),
        ),
        manifest_path=Path("/p/.claude-plugin/plugin.json"),
    )
    assert bundle.kinds() == frozenset(
        {ToolSurfaceKind.COMMAND_SKILL, ToolSurfaceKind.AGENT_PROFILE}
    )


def test_bundle_validation_result_passed() -> None:
    result = BundleValidationResult(
        passed=True,
        missing_surfaces=(),
        warnings=(),
        distribution_target=TARGET_CLAUDE_CODE,
    )
    assert result.passed is True
    assert result.missing_surfaces == ()


def test_bundle_validation_result_failed_with_missing() -> None:
    finding = make_finding(
        "bundle-component-missing", "error", "missing command skills"
    )
    result = BundleValidationResult(
        passed=False,
        missing_surfaces=(finding,),
        warnings=("heads up",),
        distribution_target=TARGET_CLAUDE_CODE,
    )
    assert result.passed is False
    assert result.missing_surfaces[0].code == "bundle-component-missing"
    assert result.warnings == ("heads up",)
