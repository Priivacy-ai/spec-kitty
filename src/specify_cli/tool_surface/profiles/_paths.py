"""Shared path-relativization helpers for the agent_profiles manifest (#2589).

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
import os
import stat

from ..operations import FileState
from specify_cli.skills.manifest_store import fingerprint_file


def relativize_under_root(path: Path, project_root: Path) -> str:
    """Return ``path`` as a repo-root-relative POSIX string when possible.

    Falls back to the original absolute path (as a string) when ``path``
    does not live under ``project_root`` -- an out-of-tree profile is a
    legitimate, if unusual, configuration and must still round-trip.
    """
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path)


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


def observe_node(path: Path) -> FileState:
    """Read one node without following its final component."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return FileState("absent")
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return FileState("symlink", target=os.readlink(path), mode=mode, mtime_ns=info.st_mtime_ns)
    if stat.S_ISDIR(info.st_mode):
        return FileState("directory", mode=mode, mtime_ns=info.st_mtime_ns)
    if stat.S_ISREG(info.st_mode):
        return FileState("file", sha256=str(fingerprint_file(path)), mode=mode, mtime_ns=info.st_mtime_ns)
    raise ValueError(f"Unsupported filesystem node: {path}")


def confined_path(path: Path, root: Path) -> str:
    """Require lexical confinement and directory-only existing parents."""
    relative = path.relative_to(root)
    if not relative.parts or any(p in {".", ".."} or ":" in p or "\\" in p for p in relative.parts):
        raise ValueError(f"Unconfined profile path: {path}")
    parent = root
    for part in relative.parts[:-1]:
        if observe_node(parent).kind not in {"directory", "absent"}:
            raise ValueError(f"Unsafe profile parent: {parent}")
        parent = parent / part
    if observe_node(parent).kind not in {"directory", "absent"}:
        raise ValueError(f"Unsafe profile parent: {parent}")
    return relative.as_posix()


def observe_tree(root: Path) -> tuple[tuple[Path, FileState], ...]:
    """Fingerprint the whole input tree, including additions and dangling links."""
    state = observe_node(root)
    result = [(root, state)]
    if state.kind == "directory":
        for child in sorted(root.iterdir()):
            result.extend(observe_tree(child))
    return tuple(result)
