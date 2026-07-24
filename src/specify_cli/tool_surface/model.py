"""Core data structures for the tool surface contract bounded context.

All structures are frozen (immutable, hashable) dataclasses. Sequence fields use
``tuple`` rather than ``list`` so the dataclasses remain hashable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .enums import (
    ActivationMode,
    InstallScope,
    RequiredPolicy,
    SourceKind,
    ToolSurfaceKind,
)


@dataclass(frozen=True)
class SurfaceDefinition:
    """Policy description of a surface that should exist for a tool.

    A definition is the *should* side of the contract: it declares where a
    surface lives (``path_pattern``), how it activates, and what provider knows
    how to expand, probe, and repair it.
    """

    kind: ToolSurfaceKind
    source_kind: SourceKind
    install_scope: InstallScope
    path_pattern: str
    required_policy: RequiredPolicy
    activation_mode: ActivationMode
    provider_key: str
    repair_hint: str


@dataclass(frozen=True)
class SurfaceInstance:
    """A concrete materialization of a :class:`SurfaceDefinition` at a path."""

    definition: SurfaceDefinition
    path: Path
    exists: bool
    file_hash: str | None
    owner: str
    surface_id: str | None = None


@dataclass(frozen=True)
class SurfacePlan:
    """The full set of surface instances computed for one tool."""

    tool_key: str
    instances: tuple[SurfaceInstance, ...]
    computed_at: str


@dataclass(frozen=True)
class NativeAgentProfile:
    """A native agent profile projected into a tool-specific output file.

    Provenance fields (``source_path``/``source_hash``/``projection_version``,
    added for #1940) are optional with ``None`` defaults so legacy 6-field
    manifest entries deserialize without them; they are populated on the next
    projection write. ``source_hash`` tracks the *source* profile YAML and is
    independent of ``file_hash`` which tracks the *rendered* output.
    """

    profile_urn: str
    source_layer: str
    tool_key: str
    output_path: Path
    format: str
    file_hash: str | None
    source_path: str | None = None
    source_hash: str | None = None
    projection_version: int | None = None
