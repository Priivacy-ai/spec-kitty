"""Action-grain aggregation — the single canonical action-grain union module.

A mission type's *action grain* is the union, across every action a mission
type defines, of the doctrine artifacts scoped to that action (an
``ActionIndex`` per ``<mission_type>/actions/<action>/index.yaml``,
``src/doctrine/missions/action_index.py``). Three consumers each need this
union:

* the resolver (``charter.mission_type_profiles.resolve_mission_type_context``,
  WP03) — threads the real action grain into ``ResolvedGovernance.from_grains``
  instead of the placeholder ``_EMPTY_GRAIN``;
* the integrity gate (WP04) — asserts no artifact URN is declared in both the
  type grain and the action grain (FR-013);
* the reconciled test tier (WP05).

This module is the **single** home of that union logic (C-002) — no other
module re-implements the ``actions/*/index.yaml`` scan or the per-kind
concatenation.

Layer rule
----------
``src/charter/`` MUST NOT import ``specify_cli`` (C-001); importing from
``doctrine`` is the canonical dependency direction and is used here
(:mod:`doctrine.missions.action_index`).

Circular-import guard
----------------------
``charter.mission_type_profiles`` owns the canonical ``_GOVERNANCE_KINDS``
governance-kind list and will (WP03) import :func:`aggregate_action_grain`
back to thread the real action grain into its resolver. To avoid a
module-level import cycle, every reference this module makes to
``charter.mission_type_profiles`` (or the sibling
``charter.mission_type_profile_repository``) is a **lazy, function-local**
import — the same ``# noqa: PLC0415`` convention ``mission_type_profiles``
itself already uses for its own cycle-prone imports. Do not hoist these to
module level.

Scope cap
---------
Aggregation reads the **built-in** missions root only
(``MissionTypeProfileRepository._default_built_in_dir()`` =
``src/doctrine/missions``). No project/org action-index overlay exists today;
building a multi-root or field-merge engine here is explicitly out of scope
for this module.
"""

from __future__ import annotations

from pathlib import Path

from doctrine.missions.action_index import ActionIndex, load_action_index

__all__ = [
    "action_index_to_mapping",
    "aggregate_action_grain",
    "scan_builtin_cross_grain_duplicates",
]


def action_index_to_mapping(index: ActionIndex) -> dict[str, list[str]]:
    """Project an :class:`ActionIndex` onto the canonical governance-kind keys.

    Pure, no I/O. ``ActionIndex``'s seven doctrine-artifact fields
    (``directives`` / ``tactics`` / ``paradigms`` / ``styleguides`` /
    ``toolguides`` / ``procedures`` / ``agent_profiles``) map 1:1 onto
    ``charter.mission_type_profiles._GOVERNANCE_KINDS`` by field name, so the
    keys (and their order) are read from that single source rather than
    re-declared here.

    Parameters
    ----------
    index:
        The loaded (or fallback-empty) action index.

    Returns
    -------
    dict[str, list[str]]
        One list per governance kind, each a fresh copy of the corresponding
        ``index`` field. An empty ``ActionIndex`` yields all-empty lists.
    """
    from charter.mission_type_profiles import _GOVERNANCE_KINDS  # noqa: PLC0415 — lazy; avoids charter.action_grain <-> charter.mission_type_profiles import cycle (T004)

    return {kind: list(getattr(index, kind)) for kind in _GOVERNANCE_KINDS}


def aggregate_action_grain(built_in_dir: Path, mission_type: str) -> dict[str, list[str]]:
    """Union every action's grain for ``mission_type`` into one mapping per kind.

    Enumerates ``<built_in_dir>/<mission_type>/actions/*`` (sorted for
    deterministic ordering), loads each action's :class:`ActionIndex` via
    :func:`~doctrine.missions.action_index.load_action_index`, and
    concatenates the per-action mappings (:func:`action_index_to_mapping`)
    for each governance kind.

    De-duplication is deliberately **not** performed here: collapsing a
    cross-action or cross-grain repeat would hide a double declaration that
    ``ResolvedGovernance.from_grains`` / ``_merge_disjoint_grain`` (the
    caller) is responsible for detecting (FR-013). Concatenation only.

    A mission type with no ``actions/`` directory at all degrades to an
    empty-content mapping (every shipped type currently has an ``actions/``
    directory; this branch exists as a defensive fallback and is exercised
    by a synthetic fixture, not a real built-in type). A mission type whose
    action indexes are all *intentionally* empty (e.g. ``plan``) also
    resolves to an empty-content mapping — that is empty content, not a
    missing directory.

    Parameters
    ----------
    built_in_dir:
        The shipped missions root (``MissionTypeProfileRepository._default_built_in_dir()``
        == ``src/doctrine/missions``), **not** a project ``repo_root``.
    mission_type:
        The mission type key (e.g. ``"software-dev"``).

    Returns
    -------
    dict[str, list[str]]
        One list per governance kind, keyed by
        ``charter.mission_type_profiles._GOVERNANCE_KINDS``, each the
        concatenation of every action's contribution (order: actions sorted
        by directory name, kinds in ``_GOVERNANCE_KINDS`` order).
    """
    from charter.mission_type_profiles import _GOVERNANCE_KINDS  # noqa: PLC0415 — lazy; avoids charter.action_grain <-> charter.mission_type_profiles import cycle (T005)

    merged: dict[str, list[str]] = {kind: [] for kind in _GOVERNANCE_KINDS}

    actions_dir = built_in_dir / mission_type / "actions"
    if not actions_dir.is_dir():
        return merged

    action_names = sorted(p.name for p in actions_dir.iterdir() if p.is_dir())
    for action_name in action_names:
        index = load_action_index(built_in_dir, mission_type, action_name)
        mapping = action_index_to_mapping(index)
        for kind in _GOVERNANCE_KINDS:
            merged[kind].extend(mapping[kind])

    return merged


def scan_builtin_cross_grain_duplicates(built_in_dir: Path | None = None) -> list[str]:
    """Assert no cross-grain URN duplicate exists for any shipped mission type.

    IC-11 dup-scan: for each of the four canonical (shipped) mission types
    (``charter.mission_type_profiles.CANONICAL_MISSION_TYPES``), loads the
    type grain (``governance-profile.yaml`` ``selected_*``) and the action
    grain (:func:`aggregate_action_grain`) and unions them through
    ``ResolvedGovernance.from_grains`` — the same union the resolver uses —
    which raises :class:`~charter.mission_type_profiles.CrossGrainDoubleDeclarationError`
    the moment one artifact URN appears in both grains (FR-013). This is the
    **single** dup-scan authority (C-002): WP04's integrity gate calls this
    function rather than re-implementing the union/collision check.

    Parameters
    ----------
    built_in_dir:
        The shipped missions root. Defaults to
        ``MissionTypeProfileRepository._default_built_in_dir()``
        (``src/doctrine/missions``).

    Returns
    -------
    list[str]
        The mission types that were scanned and confirmed disjoint — always
        all four canonical types on success (never a partial list, since a
        collision raises instead of being skipped).

    Raises
    ------
    charter.mission_type_profiles.CrossGrainDoubleDeclarationError
        If any artifact URN is declared in both the type grain and the
        action grain for any shipped mission type.
    """
    from charter.mission_type_profile_repository import (  # noqa: PLC0415 — lazy; avoids charter.action_grain <-> charter.mission_type_profile_repository import cycle (T006)
        MissionTypeProfileRepository,
    )
    from charter.mission_type_profiles import (  # noqa: PLC0415 — lazy; avoids charter.action_grain <-> charter.mission_type_profiles import cycle (T006)
        CANONICAL_MISSION_TYPES,
        ResolvedGovernance,
        _load_mission_type_profile,
        _profile_type_grain,
    )

    root = built_in_dir if built_in_dir is not None else MissionTypeProfileRepository._default_built_in_dir()  # noqa: SLF001 — the WP-documented root authority; MissionTypeProfileRepository has no public accessor for it.

    scanned: list[str] = []
    for mission_type in CANONICAL_MISSION_TYPES:
        profile = _load_mission_type_profile(mission_type)
        type_grain = _profile_type_grain(profile)
        action_grain = aggregate_action_grain(root, mission_type)
        ResolvedGovernance.from_grains(type_grain=type_grain, action_grain=action_grain)
        scanned.append(mission_type)

    return scanned
