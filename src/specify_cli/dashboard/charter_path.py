"""Charter path resolution helpers for dashboard features/API."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_project_charter_path(project_dir: Path) -> Path | None:
    """Resolve the project-level charter file path.

    Routes through ``charter.sync.ensure_charter_bundle_fresh`` (FR-004
    chokepoint) so the canonical-root resolver picks up the main checkout
    even when the dashboard scans a worktree path. The return value is the
    absolute path to ``<canonical_root>/.kittify/charter/charter.md`` when
    present, ``None`` otherwise. Does not fall back to legacy locations —
    those must be migrated via ``spec-kitty upgrade``.

    Per ``contracts/chokepoint.contract.md`` Invariant 5, the chokepoint
    returns ``None`` when ``charter.md`` does not exist at the canonical
    root; we surface that as ``None`` here to preserve the dashboard's
    "no charter" UI signal.
    """
    from charter.resolution import (
        GitCommonDirUnavailableError,
        NotInsideRepositoryError,
    )
    from charter.sync import ensure_charter_bundle_fresh

    project_dir = Path(project_dir)

    # Resolver-failure path: we *must* stay loud per C-001, but the dashboard
    # surface is read-only and runs against arbitrary user paths (including
    # paths under .git/ during scanner sweeps). Re-raising would crash the
    # scanner. We log loudly and surface None ("no charter") which is the
    # exact same signal the chokepoint produces for "no charter file".
    try:
        sync_result = ensure_charter_bundle_fresh(project_dir)
    except (NotInsideRepositoryError, GitCommonDirUnavailableError) as exc:
        logger.warning(
            "Dashboard charter probe: chokepoint resolver unavailable for %s: %s",
            project_dir,
            exc,
        )
        return None

    if sync_result is None or sync_result.canonical_root is None:
        return None

    charter_path = sync_result.canonical_root / ".kittify" / "charter" / "charter.md"
    if charter_path.exists():
        return charter_path
    return None
