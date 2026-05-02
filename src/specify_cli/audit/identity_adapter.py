"""Identity adapter: convert IdentityState objects to MissionFinding records.

This module is the **only** coupling point between the audit engine and the
existing ``specify_cli.status.identity_audit`` module.  It imports
``IdentityState`` internally and never re-exports it — callers outside this
module must not import ``IdentityState`` directly.

Public functions
----------------
``identity_state_to_findings``
    Maps a single ``IdentityState`` to zero or more ``MissionFinding`` records.
    Only the ``orphan`` state emits a finding here; ``legacy``, ``pending``,
    and ``assigned`` are handled by the meta-JSON classifier or emit nothing.

``prefix_groups_to_findings``
    Converts ``find_duplicate_prefixes()`` output to ``DUPLICATE_PREFIX``
    findings.

``selector_groups_to_findings``
    Converts ``find_ambiguous_selectors()`` output to ``AMBIGUOUS_SELECTOR``
    findings.

``duplicate_ids_to_findings``
    Detects missions that share the same ``mission_id`` value and emits
    ``DUPLICATE_MISSION_ID`` findings.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

# Internal import — IdentityState is NOT re-exported from this module.
from specify_cli.status.identity_audit import IdentityState

from .models import MissionFinding, Severity


# ---------------------------------------------------------------------------
# Single-state adapter
# ---------------------------------------------------------------------------


def identity_state_to_findings(
    state: IdentityState,
    mission_dir: Path,  # noqa: ARG001  (kept for call-site symmetry)
) -> list[MissionFinding]:
    """Convert a single ``IdentityState`` to audit findings.

    State → finding mapping:

    - ``orphan``: ``meta.json`` is absent or unreadable — emits
      ``IDENTITY_MISSING`` (error).
    - ``legacy``: ``meta.json`` exists but has no ``mission_id``.  **No
      finding emitted here** — ``classify_meta_json()`` (WP03) will emit
      ``IDENTITY_MISSING`` when it processes the file contents.  Emitting
      here too would produce a duplicate finding.
    - ``pending``: ``mission_id`` present, ``mission_number`` null.  Valid
      pre-merge state — no finding.
    - ``assigned``: both ``mission_id`` and ``mission_number`` present — no
      finding.

    ``IDENTITY_INVALID`` (non-ULID ``mission_id``) is NOT this adapter's
    responsibility.  It is detected exclusively by ``classify_meta_json()``
    via direct regex check.

    Args:
        state: The ``IdentityState`` produced by
            :func:`specify_cli.status.identity_audit.classify_mission`.
        mission_dir: Absolute path to the mission directory.  Retained for
            call-site symmetry; not used to construct findings (the finding
            ``artifact_path`` is always ``"meta.json"``).

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Empty list for ``legacy``, ``pending``, and ``assigned`` states.
    """
    if state.state == "orphan":
        return [
            MissionFinding(
                code="IDENTITY_MISSING",
                severity=Severity.ERROR,
                artifact_path="meta.json",
                detail="meta.json absent",
            )
        ]
    # legacy: meta classifier handles IDENTITY_MISSING for this case
    # pending, assigned: no finding
    return []


# ---------------------------------------------------------------------------
# Repo-level group adapters
# ---------------------------------------------------------------------------


def prefix_groups_to_findings(
    groups: dict[str, list[IdentityState]],
    slug_to_dir: dict[str, Path],  # noqa: ARG001
) -> list[MissionFinding]:
    """Convert ``find_duplicate_prefixes()`` output to ``DUPLICATE_PREFIX`` findings.

    For each prefix that is shared by two or more missions, one finding is
    emitted *per mission* in the group.  The ``detail`` field lists the other
    missions sharing the same prefix (sorted, comma-separated).

    Args:
        groups: Mapping of ``{prefix: [IdentityState, ...]}`` with ≥ 2 members,
            as returned by
            :func:`specify_cli.status.identity_audit.find_duplicate_prefixes`.
        slug_to_dir: Mapping of mission slug to its directory path.  Used to
            attach findings to the right mission directory.

    Returns:
        A flat list of ``DUPLICATE_PREFIX`` findings (one per mission per
        duplicated prefix).
    """
    findings: list[MissionFinding] = []
    for prefix, states in groups.items():
        if len(states) < 2:
            continue
        all_slugs = sorted(s.slug for s in states)
        for state in states:
            other_slugs = ", ".join(s for s in all_slugs if s != state.slug)
            findings.append(
                MissionFinding(
                    code="DUPLICATE_PREFIX",
                    severity=Severity.WARNING,
                    artifact_path="meta.json",
                    detail=f"prefix {prefix!r} shared with: {other_slugs}",
                )
            )
    return findings


def selector_groups_to_findings(
    groups: dict[str, list[IdentityState]],
    slug_to_dir: dict[str, Path],  # noqa: ARG001
) -> list[MissionFinding]:
    """Convert ``find_ambiguous_selectors()`` output to ``AMBIGUOUS_SELECTOR`` findings.

    For each handle that resolves to two or more missions, one finding is
    emitted *per mission* in the group.

    Args:
        groups: Mapping of ``{handle: [IdentityState, ...]}`` with ≥ 2 members,
            as returned by
            :func:`specify_cli.status.identity_audit.find_ambiguous_selectors`.
        slug_to_dir: Mapping of mission slug to its directory path.

    Returns:
        A flat list of ``AMBIGUOUS_SELECTOR`` findings.
    """
    findings: list[MissionFinding] = []
    for handle, states in groups.items():
        if len(states) < 2:
            continue
        all_slugs = sorted(s.slug for s in states)
        for state in states:
            other_slugs = ", ".join(s for s in all_slugs if s != state.slug)
            findings.append(
                MissionFinding(
                    code="AMBIGUOUS_SELECTOR",
                    severity=Severity.WARNING,
                    artifact_path="meta.json",
                    detail=f"handle {handle!r} also matches: {other_slugs}",
                )
            )
    return findings


def duplicate_ids_to_findings(
    states: list[IdentityState],
    slug_to_dir: dict[str, Path],  # noqa: ARG001
) -> list[MissionFinding]:
    """Detect missions with identical ``mission_id`` values and emit findings.

    Groups all states by ``mission_id`` (ignoring ``None``).  Any group with
    ≥ 2 members indicates two missions with the same ULID, which is a data
    integrity error.

    Args:
        states: All ``IdentityState`` objects for the repository (e.g. from
            :func:`specify_cli.status.identity_audit.audit_repo`).
        slug_to_dir: Mapping of mission slug to its directory path.

    Returns:
        A flat list of ``DUPLICATE_MISSION_ID`` findings (one per mission in
        each group).
    """
    # Group by mission_id, skipping None values (orphan / legacy states).
    by_id: dict[str, list[IdentityState]] = defaultdict(list)
    for state in states:
        if state.mission_id is not None:
            by_id[state.mission_id].append(state)

    findings: list[MissionFinding] = []
    for mission_id, group in by_id.items():
        if len(group) < 2:
            continue
        all_slugs = sorted(s.slug for s in group)
        for state in group:
            other_slugs = ", ".join(s for s in all_slugs if s != state.slug)
            findings.append(
                MissionFinding(
                    code="DUPLICATE_MISSION_ID",
                    severity=Severity.ERROR,
                    artifact_path="meta.json",
                    detail=f"mission_id {mission_id!r} also used by: {other_slugs}",
                )
            )
    return findings
