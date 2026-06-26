"""Shared coordination-topology teardown seam (FR-004 / FR-005, #2119).

The single place the **persist-before-destroy** invariant lives. Three
production call sites previously each open-coded a
``CoordinationWorkspace.teardown(...)`` inside a best-effort
``except Exception`` swallow:

* merge cleanup  — ``cli/commands/merge.py`` (``_run_lane_based_merge_locked``)
* merge ``--abort`` — ``cli/commands/merge.py`` (the ``--abort`` branch)
* mission close / ``--discard`` — ``cli/commands/mission_type.py``
  (``_teardown_coordination_worktree``)

That duplication is exactly why the ordering bug existed in one path (merge:
the coordination worktree was destroyed inside ``_run_lane_based_merge_locked``
*before* ``run_retrospective_postcondition`` fired in the outer ``merge()``) and
was absent in another (close/abort: no persist step at all). Consolidating the
three sites onto this one seam makes the invariant attachable once and provable
by destroy-step fault injection.

Ordering reconciliation (DIR-003 / ADR Binding B)
-------------------------------------------------
ADR Binding B states **persist → flatten → destroy**. This base does NOT carry
a separate ``_flatten_discarded_mission`` / ``_verify_discard_complete`` discard
sub-pipeline (that topology — and the ``merge/executor.py`` split the WP prompt
referenced — does not exist here; the merge cleanup lives in
``cli/commands/merge.py`` and the discard path's branch/lane-worktree deletion
lives in ``mission_type._discard_mission``). On THIS base both the merge path
and the discard path reduce to **persist → destroy**:

* **merge path**: ``persist → destroy`` (this seam persists the retrospective to
  its durable PRIMARY home, then destroys the coordination worktree).
* **discard path**: the close command keeps its existing branch + lane-worktree
  deletion (``_discard_mission``) ahead of this seam; the seam itself is invoked
  for the coordination-worktree leg and runs ``persist → destroy``. No flatten
  step exists to reorder, so verify-before-flatten is vacuously preserved.

The shipped seam therefore matches ADR Binding B's load-bearing invariant
(persist precedes destroy) for both paths on this base. The "flatten" middle
term in Binding B's wording has no anchor in this tree; if a future base
re-introduces a flatten sub-pipeline, the seam — not the call sites — is where
the persist→flatten→destroy ordering must be reasserted.

Acyclic-import discipline (alphonso)
------------------------------------
The retrospective-persist import is **function-local / lazy** (mirroring the
convention at ``retrospective/gate.py``), so importing ``coordination`` never
drags in ``retrospective`` at module-import time. The seam symbol is
deliberately **NOT** added to ``coordination/__init__.__all__`` — it is reachable
only via this module path, keeping ``coordination/__init__`` free of the
retrospective dependency and the ``coordination → retrospective`` import edge out
of the package's public surface.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _persist_retrospective(repo_root: Path, mission_slug: str) -> None:
    """Persist any pending retrospective to its durable PRIMARY home.

    Routes through the post-merge terminus, which resolves the durable home via
    the WP03 ``resolve_retrospective_home`` authority and writes
    ``kitty-specs/<slug>/retrospective.yaml`` (idempotent: a no-op when the
    record already exists). The import is function-local to keep ``coordination``
    acyclic (see module docstring).

    This runs OUTSIDE the destroy best-effort swallow: the retrospective MUST be
    durable before the coordination worktree is destroyed. ``run_retrospective_
    postcondition`` is itself fail-open for *capture* failures (it records a
    ``capture_failed`` event rather than aborting), so the persist step does not
    block teardown on a genuine generator/IO failure — but an unexpected error in
    the persist machinery surfaces here instead of being masked by the destroy
    handler.
    """
    from specify_cli.post_merge.retrospective_terminus import (  # noqa: PLC0415
        run_retrospective_postcondition,
    )

    run_retrospective_postcondition(mission_slug=mission_slug, repo_root=repo_root)


def _destroy_coordination_worktree(
    repo_root: Path, mission_slug: str, mid8: str
) -> bool:
    """Destroy the coordination worktree (best-effort). Returns ``True`` on success.

    Wraps ``CoordinationWorkspace.teardown`` in the best-effort ``except
    Exception`` swallow that the three former call sites each carried: a teardown
    failure is non-fatal and never blocks a successful merge / close / abort. The
    import is function-local for symmetry with the persist leg.
    """
    try:
        from specify_cli.coordination.workspace import (  # noqa: PLC0415
            CoordinationWorkspace,
        )

        CoordinationWorkspace.teardown(repo_root, mission_slug, mid8)
        return True
    except Exception as exc:  # noqa: BLE001 — destroy is best-effort cleanup
        logger.warning(
            "Coordination worktree teardown failed (non-fatal) for %s-%s: %s",
            mission_slug,
            mid8,
            exc,
        )
        return False


def teardown_coordination_topology(
    repo_root: Path,
    mission_slug: str,
    mid8: str,
    *,
    persist: bool = True,
) -> bool:
    """Persist the retrospective, then destroy the coordination worktree.

    The single shared teardown seam (FR-004). Ordered steps:

    1. **persist** (``persist=True``, OUTSIDE the swallow) — write any pending
       retrospective to its durable PRIMARY home
       (``kitty-specs/<slug>/retrospective.yaml``) via the WP03 authority, so the
       learning record survives the worktree destruction (FR-005).
    2. **destroy** (best-effort, swallowed) — remove the coordination worktree;
       its failure is non-fatal.

    Args:
        repo_root: Primary repo root (NOT a lane / coordination worktree).
        mission_slug: Canonical mission directory name (already re-keyed by the
            caller to ``feature_dir.name`` — the seam composes no handles).
        mid8: The mid8 disambiguator from ``meta.json``. An empty value means the
            mission never had a coordination worktree (legacy); the destroy leg is
            then a documented no-op and persist still runs.
        persist: When ``False``, skip the persist leg (e.g. callers that have
            already persisted, or paths with no retrospective semantics).

    Returns:
        ``True`` when the destroy leg succeeded (or no-op'd cleanly), ``False``
        when destroy raised and was swallowed.

    Note:
        Persist is intentionally NOT wrapped in the destroy swallow: an
        unexpected persist-machinery error surfaces to the caller rather than
        being silently absorbed as "teardown was best-effort".
    """
    if persist:
        # OUTSIDE the destroy swallow — persist-before-destroy (FR-005).
        _persist_retrospective(repo_root, mission_slug)

    if not mid8:
        # Legacy / never-coordinated mission: nothing to destroy. Persist (above)
        # still ran. Mirror CoordinationWorkspace.teardown's idempotent no-op.
        return True

    return _destroy_coordination_worktree(repo_root, mission_slug, mid8)
