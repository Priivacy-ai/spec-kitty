"""Pure dependency-readiness verdict over a reduced status snapshot (WP04).

The emit shells are the verdict supplier for the FSM's dependency guard
(spec FR-013; contract ``contracts/dependency-guard.md`` §4). Each shell
reduces its WRITE surface exactly once per emit (NFR-004) and hands that
snapshot here, together with the dependencies the WP file declares on the
planning surface; the verdict is threaded into
``GuardContext.dependency_ready`` by ``transition_pipeline.prepare_transition``.

This module is pure: no file, lock, git or log I/O. The gating semantics are
NOT reimplemented here -- ``core.dependency_graph.dependency_readiness_for_wp``
stays the single authority (FR-014: ``approved`` OR ``done`` OR
``canceled``-with-operator-provenance satisfies). The reducer never sees any
of this (C-005 replay purity).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from .models import Lane, StatusSnapshot

if TYPE_CHECKING:
    from specify_cli.core.dependency_graph import DependencyReadiness


def wp_lanes_from_snapshot(snapshot: StatusSnapshot) -> dict[str, str]:
    """Current lane per WP from a reduced snapshot (a lane-less state is ``genesis``).

    Mirrors ``emit._derive_from_lane``'s reading of the same snapshot so the
    guard's view of a dependency's lane cannot disagree with the shell's view
    of the WP's own ``from_lane``.
    """
    return {wp_id: str(state.get("lane") or Lane.GENESIS.value) for wp_id, state in snapshot.work_packages.items()}


def readiness_from_snapshot(
    snapshot: StatusSnapshot,
    wp_id: str,
    dependencies: Iterable[str],
) -> DependencyReadiness:
    """Return the dependency verdict for *wp_id* against *snapshot* (pure).

    A WP that declares no dependencies gets a *satisfied* verdict -- still a
    verdict, never ``None``: the shells always supply one, and ``None`` is
    reserved for direct guard-level callers that supply nothing (C-004).
    Per-dependency provenance is threaded from the snapshot so a
    ``canceled``-with-operator-provenance dependency counts as resolved
    (FR-014, same as every pre-flight site).
    """
    # Lazy: ``core.dependency_graph`` imports the ``status`` facade at module
    # load, so a top-level import here would cycle during package init.
    from specify_cli.core.dependency_graph import dependency_readiness_for_wp  # noqa: PLC0415

    return dependency_readiness_for_wp(
        wp_id,
        dependencies,
        wp_lanes_from_snapshot(snapshot),
        provenance=snapshot.work_packages,
    )


UNRESOLVABLE_MARKER = "<unresolvable>"


def unresolvable_readiness(wp_id: str, reason: str) -> DependencyReadiness:
    """An *unsatisfied* verdict for a WP whose declared dependencies cannot be read.

    Used by the shells when the WP prompt file is unreadable or its
    ``dependencies`` value is one ``WPMetadata`` would also refuse. The verdict
    refuses the two guarded entry edges (``planned -> claimed``,
    ``claimed -> in_progress``) exactly like an unsatisfied dependency would --
    so ``force`` + actor + reason still bypasses at ``check_transition`` and
    every non-guarded edge (``-> blocked``, ``-> canceled``, review edges) is
    untouched. ``dependencies`` is empty because nothing could be read;
    ``unsatisfied`` carries one self-describing marker (never a WP id) so
    ``satisfied`` is ``False`` and the failure reason travels with the verdict.
    """
    from specify_cli.core.dependency_graph import DependencyReadiness  # noqa: PLC0415

    return DependencyReadiness(wp_id=wp_id, dependencies=(), unsatisfied=(f"{UNRESOLVABLE_MARKER} {reason}",))


# ``UNRESOLVABLE_MARKER`` and ``wp_lanes_from_snapshot`` stay module-level (tests pin
# them) but are not part of the public surface: no src/ caller outside this module
# (dead-symbol gate, #470).
__all__ = ["readiness_from_snapshot", "unresolvable_readiness"]
