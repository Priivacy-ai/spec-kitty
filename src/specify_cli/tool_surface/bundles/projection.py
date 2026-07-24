"""Shared projection helpers for plugin bundle projectors.

The Claude Code, Copilot, and VS Code projectors differ only in their package
layout (manifest location, agent filename suffix). The common work -- selecting
which canonical surfaces belong in a bundle, computing each surface's
bundle-relative path, and writing the staging files -- lives here so the
per-target projectors stay thin.

**Scope guard (FR-016, C-006):** :func:`write_bundle` performs filesystem writes
*only* under the caller-supplied ``output_dir`` staging directory. It contains no
install, registration, enablement, or marketplace-publish logic; the only side
effect is creating local files inside the staging tree.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path

from ..enums import ToolSurfaceKind
from ..model import SurfacePlan
from .model import BundleEntry

# Surface kinds that belong in a plugin bundle. Session-presence kinds
# (CONTEXT_FILE, RULE) are deliberately excluded -- they are project-install
# surfaces, not bundle components (see WP09 task spec).
BUNDLE_SURFACE_KINDS: frozenset[ToolSurfaceKind] = frozenset(
    {
        ToolSurfaceKind.COMMAND_SKILL,
        ToolSurfaceKind.DOCTRINE_SKILL,
        ToolSurfaceKind.AGENT_PROFILE,
        ToolSurfaceKind.HOOK,
        ToolSurfaceKind.NATIVE_CONFIG,
    }
)

# Inert placeholder manifest version. The manifest is a declarative descriptor;
# its presence never triggers install/publish behaviour.
_MANIFEST_VERSION = "0.0.0"


def _bundle_relative_path(
    kind: ToolSurfaceKind,
    source_path: Path,
    layout: dict[ToolSurfaceKind, str],
    agent_filename: Callable[[str], str],
) -> str | None:
    """Compute the in-bundle relative path for a surface, or ``None`` to skip."""
    prefix = layout.get(kind)
    if prefix is None:
        return None
    if kind == ToolSurfaceKind.AGENT_PROFILE:
        leaf = agent_filename(source_path.stem)
        return f"{prefix}/{leaf}" if prefix else leaf
    if kind == ToolSurfaceKind.COMMAND_SKILL or kind == ToolSurfaceKind.DOCTRINE_SKILL:
        # Command/doctrine skills are ``.../<name>/SKILL.md``; preserve the
        # skill directory name inside the bundle's ``skills/`` tree.
        leaf = source_path.parent.name
        return f"{prefix}/{leaf}/{source_path.name}"
    leaf = source_path.name
    return f"{prefix}/{leaf}" if prefix else leaf


def bundle_entries_for_plans(
    plans: Sequence[SurfacePlan],
    project_root: Path,
    *,
    layout: dict[ToolSurfaceKind, str],
    agent_filename: Callable[[str], str],
    bundle_kinds: frozenset[ToolSurfaceKind],
) -> tuple[BundleEntry, ...]:
    """Project the bundleable surfaces of ``plans`` into ``BundleEntry`` tuples.

    Only surfaces whose source path lies inside ``project_root`` are bundled --
    a staging safety guard so a plugin bundle can never absorb a file from
    outside the project tree (e.g. a user-global surface). The result is
    de-duplicated on ``bundle_relative_path`` and ordered deterministically so
    repeated projections are byte-stable.
    """
    seen: dict[str, BundleEntry] = {}
    for plan in plans:
        for instance in plan.instances:
            kind = instance.definition.kind
            if kind not in bundle_kinds:
                continue
            if not _within_project(instance.path, project_root):
                continue
            rel = _bundle_relative_path(
                kind, instance.path, layout, agent_filename
            )
            if rel is None or rel in seen:
                continue
            seen[rel] = BundleEntry(
                surface_kind=kind,
                source_path=instance.path,
                bundle_relative_path=rel,
            )
    return tuple(seen[key] for key in sorted(seen))


def _within_project(path: Path, project_root: Path) -> bool:
    """Return whether ``path`` is inside ``project_root`` (best-effort)."""
    try:
        path.resolve().relative_to(project_root.resolve())
    except ValueError:
        return False
    return True


def plugin_manifest_payload(distribution_target: str) -> dict[str, object]:
    """Build the declarative ``plugin.json`` payload for a target.

    The payload is informational only; it carries no install/marketplace
    directives.
    """
    return {
        "name": "spec-kitty",
        "version": _MANIFEST_VERSION,
        "description": "Spec Kitty tool surfaces (staging bundle).",
        "distribution_target": distribution_target,
    }


def write_bundle(
    output_dir: Path,
    entries: Sequence[BundleEntry],
    manifest_relative_path: str,
    manifest: dict[str, object],
) -> None:
    """Write the manifest and each entry's content under ``output_dir``.

    Side effects are confined to the staging tree. Missing source files are
    represented by an empty placeholder so the bundle layout is complete for
    inspection without ever mutating the project source.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / manifest_relative_path
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for entry in entries:
        dest = output_dir / entry.bundle_relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_read_source(entry.source_path), encoding="utf-8")


def _read_source(source_path: Path) -> str:
    """Return the source content, or an empty string if the file is absent."""
    if source_path.exists() and source_path.is_file():
        return source_path.read_text(encoding="utf-8")
    return ""
