"""Route ``agent config`` install-state queries through the surface contract.

Historically ``agent config list/status/sync`` recomputed "does this tool's
managed surface exist?" with its own ad-hoc directory probes, duplicating logic
that the :mod:`specify_cli.tool_surface` bounded context already owns. This
module is the single seam that lets the CLI consult a :class:`SurfacePlan`
instead of recomputing its own list of surfaces.

Separation of concerns:

* **Policy (the plan).** :class:`SurfacePlanBuilder` answers *which* surface
  kinds a configured tool exposes. ``agent config`` no longer maintains a
  parallel list of "what should exist" -- it reads the plan.
* **Path resolution (shared resolvers).** *Where* a managed surface lives is a
  shared dependency (``get_global_command_dir`` for user-global slash commands,
  the project ``.agents/skills`` root for command skills). The index resolves
  roots through the same injectable resolvers ``agent config`` already binds, so
  the rollup stays patch-consistent with the command layer and does not silently
  fall back to the developer's real home directory in tests.

The presence *rollup* preserves the legacy ``agent config`` semantics (a tool is
"present" when its managed location *directory* exists), even where that differs
from the finer-grained per-file probing the surface contract performs for
``doctor tool-surfaces``. The WP07 contract requires the external ``agent
config`` interface -- markers, columns, exit codes -- to stay byte-for-byte
stable.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from specify_cli.runtime.agent_commands import get_global_command_dir
from specify_cli.skills.manifest_errors import ManifestError
from specify_cli.tool_surface.enums import ToolSurfaceKind
from specify_cli.tool_surface.model import SurfacePlan
from specify_cli.tool_surface.plan import SurfacePlanBuilder
from specify_cli.tool_surface.service import build_providers, build_registry

GlobalCommandDirResolver = Callable[[str], Path]

_PROJECT_SKILLS_REL = (".agents", "skills")

# Sentinel paths emitted by providers for tools with no known implementation of
# a surface kind. A plan that contains only the sentinel for a kind means the
# tool has no adapter for it, so that kind contributes no presence root (mirrors
# the legacy ``_agent_location`` behaviour where unsupported kinds were skipped).
_SENTINEL_PATHS = frozenset({"<unsupported>"})


@dataclass(frozen=True)
class ToolSurfacePresence:
    """Per-tool rollup of the managed-directory roots the contract expects."""

    tool_key: str
    roots: tuple[Path, ...]

    @property
    def exists(self) -> bool:
        """Mirror the legacy ``_agent_location`` directory-existence check."""
        return any(root.exists() for root in self.roots)


class SurfacePresenceIndex:
    """Resolve per-tool surface presence from a single :class:`SurfacePlan` pass.

    The index is the authoritative ``agent config`` answer to "is this tool's
    managed surface present?"; the surface plan decides which kinds apply and the
    command layer never re-derives the list of surfaces by hand.
    """

    def __init__(self, roots_by_tool: dict[str, tuple[Path, ...]]) -> None:
        self._roots_by_tool = roots_by_tool

    @classmethod
    def build(
        cls,
        project_root: Path,
        tool_keys: Sequence[str],
        *,
        global_command_dir: GlobalCommandDirResolver | None = None,
    ) -> SurfacePresenceIndex:
        """Build the index for ``tool_keys`` by expanding the surface plan.

        ``agent config list/status`` only reports directory-level presence, so a
        corrupt skills manifest must not crash those read-only commands the way
        it never did before this refactor. If expanding the plan raises a
        :class:`ManifestError`, presence degrades to the static per-tool roots
        derived from the same applicability rules the providers use.
        """
        resolver = global_command_dir or get_global_command_dir
        ordered = list(dict.fromkeys(tool_keys))
        try:
            roots_by_tool = cls._roots_from_plan(project_root, ordered, resolver)
        except ManifestError:
            roots_by_tool = {
                tool_key: _static_roots(tool_key, project_root, resolver)
                for tool_key in ordered
            }
        return cls(roots_by_tool)

    @staticmethod
    def _roots_from_plan(
        project_root: Path,
        ordered: Sequence[str],
        resolver: GlobalCommandDirResolver,
    ) -> dict[str, tuple[Path, ...]]:
        registry = build_registry(ordered)
        builder = SurfacePlanBuilder(registry, build_providers())
        plans = builder.build(ordered, project_root)
        return {
            plan.tool_key: _roots_for_plan(plan, project_root, resolver)
            for plan in plans
        }

    def presence(self, tool_key: str) -> ToolSurfacePresence:
        """Return the presence rollup for ``tool_key`` (empty if unplanned)."""
        return ToolSurfacePresence(
            tool_key=tool_key,
            roots=self._roots_by_tool.get(tool_key, ()),
        )

    def exists(self, tool_key: str) -> bool:
        """Convenience accessor for the per-tool directory-existence rollup."""
        return self.presence(tool_key).exists


def _static_roots(
    tool_key: str,
    project_root: Path,
    resolver: GlobalCommandDirResolver,
) -> tuple[Path, ...]:
    """Degraded per-tool roots when the plan cannot be expanded.

    Applicability mirrors the providers exactly: a tool exposes a command-file
    surface iff it has an ``AGENT_COMMAND_CONFIG`` entry, and a command-skill
    surface iff it is one of ``command_installer.SUPPORTED_AGENTS``.
    """
    from specify_cli.core.config import AGENT_COMMAND_CONFIG
    from specify_cli.skills import command_installer

    roots: list[Path] = []
    if tool_key in AGENT_COMMAND_CONFIG:
        roots.append(resolver(tool_key))
    if tool_key in command_installer.SUPPORTED_AGENTS:
        roots.append(project_root.joinpath(*_PROJECT_SKILLS_REL))
    return tuple(roots)


def _kinds_for_plan(plan: SurfacePlan) -> set[ToolSurfaceKind]:
    """Return the surface kinds the plan expanded to a *real* instance.

    Sentinel ("unsupported") instances are excluded: a tool whose only
    command-file instance is a sentinel has no slash-command adapter, so the
    kind must not contribute a presence root.
    """
    return {
        instance.definition.kind
        for instance in plan.instances
        if str(instance.path) not in _SENTINEL_PATHS
    }


def _roots_for_plan(
    plan: SurfacePlan,
    project_root: Path,
    resolver: GlobalCommandDirResolver,
) -> tuple[Path, ...]:
    """Map a plan's surface kinds to the directories legacy presence checked.

    The legacy ``_agent_location`` probe answered presence at the *managed
    directory* level, not the per-file level:

    * slash commands (``command_file``) -> the user-global commands directory.
    * command skills (``command_skill``) -> the project ``.agents/skills`` root.
    """
    kinds = _kinds_for_plan(plan)
    roots: list[Path] = []
    if ToolSurfaceKind.COMMAND_FILE in kinds:
        roots.append(resolver(plan.tool_key))
    if ToolSurfaceKind.COMMAND_SKILL in kinds:
        roots.append(project_root.joinpath(*_PROJECT_SKILLS_REL))
    return tuple(roots)


__all__ = [
    "SurfacePresenceIndex",
]
