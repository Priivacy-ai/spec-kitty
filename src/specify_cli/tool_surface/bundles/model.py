"""Data model for plugin bundles and pre-publish validation results.

All structures are frozen (immutable, hashable) dataclasses. Sequence fields use
``tuple`` rather than ``list`` so the dataclasses remain hashable, matching the
convention established by :mod:`specify_cli.tool_surface.model`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..enums import ToolSurfaceKind
from ..findings import SurfaceFinding

# Stable distribution-target keys. These are inert label values used to tag a
# projected bundle; they never name an install/publish channel.
TARGET_CLAUDE_CODE = "claude_code_plugin"
TARGET_COPILOT = "copilot_skill_package"
TARGET_VSCODE = "vscode_extension"


@dataclass(frozen=True)
class BundleEntry:
    """One surface included in a plugin bundle."""

    surface_kind: ToolSurfaceKind
    source_path: Path
    bundle_relative_path: str


@dataclass(frozen=True)
class PluginBundle:
    """A projected plugin bundle descriptor for one distribution target.

    This is a *declarative* artifact: it records which surfaces belong in the
    bundle and where they sit inside the package layout. Producing a
    :class:`PluginBundle` does not install, register, enable, or publish
    anything (FR-016, C-006).
    """

    distribution_target: str
    entries: tuple[BundleEntry, ...]
    manifest_path: Path | None

    def kinds(self) -> frozenset[ToolSurfaceKind]:
        """Return the set of surface kinds present in the bundle."""
        return frozenset(entry.surface_kind for entry in self.entries)


@dataclass(frozen=True)
class BundleValidationResult:
    """Outcome of validating a :class:`PluginBundle` before publication."""

    passed: bool
    missing_surfaces: tuple[SurfaceFinding, ...]
    warnings: tuple[str, ...]
    distribution_target: str
