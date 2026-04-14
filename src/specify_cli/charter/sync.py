"""Charter sync orchestrator (``specify_cli`` twin).

As of WP03 of the
``unified-charter-bundle-chokepoint-01KP5Q2G`` mission this module is a
thin re-export of :mod:`charter.sync` so the ``specify_cli`` surface and
the canonical ``charter`` surface share a single sync orchestrator. The
pre-WP03 parallel implementation has been deleted to avoid drift between
the two packages — the duplicate had its own ``ensure_charter_bundle_fresh``
that bypassed ``charter.resolution.resolve_canonical_repo_root`` (FR-003)
and would make worktree readers see the wrong bundle. See plan D-5
"twin-package lockstep" and WP03 occurrence artifact.
"""

from __future__ import annotations

from charter.sync import (
    SyncResult,
    ensure_charter_bundle_fresh,
    load_directives_config,
    load_governance_config,
    post_save_hook,
    sync,
)

__all__ = [
    "SyncResult",
    "ensure_charter_bundle_fresh",
    "load_directives_config",
    "load_governance_config",
    "post_save_hook",
    "sync",
]
