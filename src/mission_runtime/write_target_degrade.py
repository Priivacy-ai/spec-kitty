"""Shared write-target degrade helper (FR-005, C-004).

Unifies the ``_mission_meta_exists`` pre-gate and port-resolution logic across
three call sites, extracting a single kind-parameterized helper while preserving
each caller's distinct degrade policy (fail-open vs. fail-closed).

The three callers:
* ``decision_log._resolve_default_target`` (fail-open) — passes a concrete
  ``degrade_ref``; an unresolvable mission returns that ref.
* ``bookkeeping_commit._resolve_bookkeeping_commit_target`` (fail-closed) —
  passes ``degrade_ref=branch`` (which may be ``None``); an unresolvable
  mission with no ``branch`` raises ``ActionContextError``.
* ``status_transition._resolve_write_target`` (WP05, fail-closed) — adds pre-gate; preserves degrade

Resolution is always attempted FIRST regardless of ``degrade_ref`` — a
resolvable mission returns the placement-port target even when the caller
passed ``degrade_ref=None`` (fail-closed callers still get the real target
whenever one exists; ``degrade_ref``/the raise is consulted only once
resolution has genuinely failed). This preserves the pre-WP04 semantics of
the two callers this helper replaces.

See spec: FR-005, C-004; plan IC-06a, IC-06b.
"""

from __future__ import annotations

from pathlib import Path

from mission_runtime import (
    ActionContextError,
    CommitTarget,
    MissionArtifactKind,
    resolve_placement_only,
)

__all__ = ["resolve_write_target_or_degrade"]

# NOTE on the ``specify_cli.missions._read_path_resolver`` imports below: they
# are deliberately LOCAL (function-scoped), matching the established
# ``mission_runtime -> specify_cli`` upward-edge convention every other site
# under the ledgered "missions" exception uses (see
# ``resolution.py``'s repeated in-function
# ``from specify_cli.missions._read_path_resolver import (...)`` calls and
# ``tests/architectural/test_layer_rules.py``'s
# ``_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI["missions"]`` ledger entry). A
# MODULE-LEVEL import here creates a genuine circular import: whenever
# ``specify_cli.missions._read_path_resolver`` is the module that FIRST
# touches the ``mission_runtime`` package (its own line importing
# ``MissionArtifactKind`` triggers ``mission_runtime/__init__.py``, which
# imports this module, which would then import BACK from
# ``_read_path_resolver`` while it is still mid-initialization -- an
# ``ImportError: cannot import name 'StatusReadPathNotFound' from partially
# initialized module`` at whatever call site happens to touch
# ``specify_cli.acceptance`` (or any other consumer) first). Deferring the
# import to call time (well after both modules have finished initializing)
# closes that hole exactly the way every sibling ``resolution.py`` call site
# already does.

# Mirrors mission_runtime.resolution's private ``_FEATURE_CONTEXT_UNRESOLVED_CODE``
# (not exported at the package root) for the fail-closed error raised below when
# a caller supplies no ``degrade_ref`` and the mission genuinely cannot resolve.
_WRITE_TARGET_UNRESOLVED_CODE = "FEATURE_CONTEXT_UNRESOLVED"


def resolve_write_target_or_degrade(
    repo_root: Path,
    mission_slug: str,
    kind: MissionArtifactKind,
    *,
    degrade_ref: str | None,
) -> CommitTarget:
    """Resolve write target via the placement port, or degrade to a caller-supplied ref.

    Unifies port-resolution + the ``_mission_meta_exists`` pre-gate (NOT the degrade
    policy). Each caller supplies its own ``degrade_ref`` so that fail-open vs.
    fail-closed behavior is preserved at the call site.

    Resolution is attempted first: when ``mission_slug`` has a ``meta.json`` and
    ``resolve_placement_only`` succeeds, its target is returned regardless of
    ``degrade_ref`` — including when ``degrade_ref`` is ``None``. ``degrade_ref``
    (or the fail-closed raise) is consulted only once resolution has actually
    failed (no ``meta.json`` yet, or a caught resolution error).

    Args:
        repo_root: Path to the primary git repository.
        mission_slug: The mission slug to resolve.
        kind: The artifact kind (determines partition routing: PRIMARY_METADATA → primary
            ``target_branch``; other kinds → topology-routed destination, e.g. COORD).
        degrade_ref: The ref to return if the mission cannot be resolved (no ``meta.json``
            yet, or an ad-hoc fixture outside a resolvable mission). The caller decides
            the policy: fail-open passes a concrete ref, fail-closed passes ``None`` to
            raise instead of silently degrading.

    Returns:
        A ``CommitTarget`` resolved for ``kind`` through the placement port, or
        ``CommitTarget(ref=degrade_ref)`` if the mission is not resolvable and
        ``degrade_ref`` is not ``None``.

    Raises:
        ``ActionContextError`` when the mission cannot be resolved AND
        ``degrade_ref`` is ``None`` (fail-closed policy — never silently
        degrades to a null ref). Note: a *caught-set* resolution failure
        (``ActionContextError`` / ``StatusReadPathNotFound`` / ``FileNotFoundError``)
        with ``degrade_ref is None`` is re-raised as a **fresh**
        ``ActionContextError`` (code ``_WRITE_TARGET_UNRESOLVED_CODE``) — the
        original exception is not preserved. Only failures *outside* the caught
        set (ambiguous/malformed mission, etc.) propagate verbatim.
    """
    from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

    if _mission_meta_exists(repo_root, mission_slug):
        try:
            return resolve_placement_only(repo_root, mission_slug, kind=kind)
        except (ActionContextError, StatusReadPathNotFound, FileNotFoundError):
            pass
    if degrade_ref is None:
        raise ActionContextError(
            _WRITE_TARGET_UNRESOLVED_CODE,
            f"resolve_write_target_or_degrade: mission {mission_slug!r} requires "
            "a degrade-path ref because it could not be resolved via the "
            "placement port and no degrade_ref was supplied (fail-closed).",
        )
    return CommitTarget(ref=degrade_ref)


def _mission_meta_exists(repo_root: Path, mission_slug: str) -> bool:
    """Return True when ``mission_slug`` has a primary ``meta.json`` on disk.

    A cheap, read-only existence gate — NOT a ref derivation — that
    distinguishes a genuinely bootstrapped mission from an ad-hoc fixture or
    the create→first-write window. ``resolve_placement_only`` never raises
    for a merely-absent mission (:func:`candidate_feature_dir_for_mission`'s
    own contract): it silently degrades to the repo's generic default branch
    instead of signalling unresolvability, so this gate is checked BEFORE
    consulting the classifier rather than relying on an exception that would
    never fire.
    """
    from specify_cli.missions._read_path_resolver import (
        candidate_feature_dir_for_mission,
    )

    try:
        # Explicit ``Path`` annotation: under the project's
        # ``follow_imports = "skip"`` mypy config the cross-module
        # ``candidate_feature_dir_for_mission`` return is seen as ``Any``; the
        # annotation re-narrows it (the function IS typed ``-> Path``).
        candidate: Path = candidate_feature_dir_for_mission(repo_root, mission_slug)
    except Exception:  # noqa: BLE001 — any resolution hiccup means "not resolvable"
        return False
    return (candidate / "meta.json").exists()
