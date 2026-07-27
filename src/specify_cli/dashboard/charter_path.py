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
    the project has a charter, ``None`` otherwise. Does not fall back to
    legacy locations — those must be migrated via ``spec-kitty upgrade``.

    charter-preflight-remediation (WP04 cycle 2): presence is answered by
    the canonical, non-mutating seam (:func:`charter.bundle.
    charter_yaml_present`), not by a raw ``charter.md`` existence check —
    the same separation of "is charter.yaml present" (gate) from "path to
    charter.md for content-loading" (the resolved value) already
    established in ``cli/commands/charter/_common.py::_resolve_charter_path``.
    Before this fix, a legacy bundle (``charter.md`` present,
    ``charter.yaml`` absent) made this resolver report "present" while the
    freshness gate reported "missing" — the mission's User Story 2 symptom,
    reproduced live on the dashboard's HTTP API and per-feature scanner
    output.
    """
    from charter.bundle import charter_yaml_present
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

    if not charter_yaml_present(sync_result.canonical_root):
        return None

    return sync_result.canonical_root / ".kittify" / "charter" / "charter.md"
