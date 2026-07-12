"""Shared path-relativization helpers for the agent-profiles manifest (#2589).

Both :mod:`.manifest` (``output_path``, the manifest key) and :mod:`.projection`
(``source_path``, provenance) need the identical "store repo-relative on disk,
fall back to absolute when the path is genuinely outside the project" idiom.
Extracting it here (rather than duplicating the ``relative_to`` /
``ValueError`` dance in both call sites) keeps the two serializers in lock
step and avoids a circular import: this module has no dependency on either
``manifest.py`` or ``projection.py``, so both can import it freely.

All functions in this module are intentionally private to the
``tool_surface.profiles`` subpackage (note the leading underscore in the
module name), mirroring the ``_render_helpers.py`` convention.
"""

from __future__ import annotations

from pathlib import Path


def relativize_under_root(path: Path, project_root: Path) -> str:
    """Return ``path`` as a repo-root-relative POSIX string when possible.

    Falls back to the resolved absolute path (as a string) when ``path``
    does not live under ``project_root`` -- an out-of-tree profile is a
    legitimate, if unusual, configuration and must still round-trip.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def absolutize_from_root(value: str, project_root: Path) -> Path:
    """Reconstruct an absolute path from a manifest-stored ``value``.

    ``value`` is either a repo-relative POSIX string written by the current
    serializer, or a legacy absolute path from a manifest written before
    #2589 -- passed through unchanged so old manifests keep resolving
    without a migration step.
    """
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return project_root / candidate
