"""Coordination-aware resolution of the canonical status read/write directory.

Lane-based missions commit canonical status to a per-mission *coordination
worktree* (``.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/``). The
runtime must read (and non-transactionally write) status there, not from the
primary checkout's stale mission directory — otherwise ``move-task``/``next``
read an empty log and report "no canonical status" (#1589 facet 3).

``workflow`` and ``acceptance`` already resolve reads this way; this module is
the shared, low-level resolver so the status store and ``lane_reader`` agree.

Resolution is **path-cheap on the hot path**: mid8 is derived from the mission
directory name's trailing token first (no I/O); ``meta.json`` is only read as a
fallback. For legacy/no-coord missions (and paths already inside a ``-coord``
worktree) the input is returned unchanged, so behavior is identical.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["resolve_status_dir"]


def _mid8_for(feature_dir: Path) -> str:
    """Best-effort mid8 for *feature_dir*; trailing slug token first, then meta."""
    tail = feature_dir.name.rsplit("-", 1)[-1] if "-" in feature_dir.name else ""
    if len(tail) == 8 and tail.isalnum() and tail.isupper():
        return tail
    try:
        from specify_cli.mission_metadata import load_meta

        meta = load_meta(feature_dir)
        if isinstance(meta, dict):
            mid8 = meta.get("mid8")
            if mid8:
                return str(mid8)
            mid = meta.get("mission_id")
            if isinstance(mid, str) and len(mid) >= 8:
                return mid[:8]
    except Exception:  # noqa: BLE001 — missing/corrupt meta is legacy; degrade
        pass
    return ""


def resolve_status_dir(feature_dir: Path) -> Path:
    """Resolve *feature_dir* to the canonical status directory.

    Returns the coordination worktree's mission directory when one exists on
    disk; otherwise returns *feature_dir* unchanged (legacy/no-coord missions,
    or when *feature_dir* is already inside a ``-coord`` worktree).
    """
    feature_dir = Path(feature_dir)
    if feature_dir.parent.name != "kitty-specs":
        return feature_dir
    # Already inside a coordination worktree — never double-resolve.
    for candidate in (feature_dir, *feature_dir.parents):
        if candidate.parent.name == ".worktrees" and candidate.name.endswith("-coord"):
            return feature_dir
    mid8 = _mid8_for(feature_dir)
    if not mid8:
        return feature_dir
    try:
        from specify_cli.missions._read_path_resolver import resolve_mission_read_path

        resolved: Path = resolve_mission_read_path(
            feature_dir.parent.parent, feature_dir.name, mid8
        )
    except Exception:  # noqa: BLE001 — never let read-path resolution break a read
        return feature_dir
    # Only redirect when the resolver actually found a coordination worktree.
    # When none exists it returns a *recomposed* primary candidate (``<slug>-
    # <mid8>``) which can differ from the on-disk dir name; in that case we must
    # return the original ``feature_dir`` unchanged (true no-op for legacy /
    # bare-slug missions) rather than a non-existent recomposed path.
    for candidate in (resolved, *resolved.parents):
        if candidate.parent.name == ".worktrees" and candidate.name.endswith("-coord"):
            return resolved
    return feature_dir
