"""SYNTHESIZE stage for ``sync import-history`` (WP-Y3, #2262).

Turns a :class:`~specify_cli.sync.history_import.scan.MissionScan` into the
ordered TeamSpace envelope stream

    MissionCreated → WPCreated[] → WPStatusChanged[]

that the SaaS materializer accepts (INV-3). Event ids are deterministic
(INV-4): the synthesized creation prefix is minted from source facts via
:func:`deterministic_ulid` under a dedicated ``import:`` namespace (so it never
collides with the migration dry-run's ``teamspace-dry-run:`` ids or across
re-runs), while replayed ``WPStatusChanged`` envelopes keep their real on-disk
``event_id`` — both paths dedup cleanly on the server.

Reuse (spec §3.3 stage 5):

* ``WPStatusChanged`` envelopes are built by the existing
  :func:`~specify_cli.migration.envelope_seam.status_event_to_teamspace_envelope`
  (via the deliberate ``migration.envelope_seam`` surface), so the lane
  back-fill and the historical-evidence synthesis (required by the TeamSpace
  5.0.0 contract on ``approved``/``done``) are not re-implemented here.
* ``MissionCreated`` / ``WPCreated`` payloads are built by the canonical
  ``build_mission_created_payload`` and ``WPCreatedPayload`` so the wire shapes
  cannot drift from the producers the rest of the CLI uses.

The synthesizer is pure: it takes the project-identity trio as arguments and
returns envelope dicts. Dry-run passes a synthetic offline ``project_uuid``;
WP-Y4 injects the persisted real UUID at the same seam (INV-5). This module
does not validate, persist, or upload — WP-Y5 owns preflight/upload.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from spec_kitty_events.project_lifecycle import WPCreatedPayload

from kernel.clock import UTC, datetime, parse_iso
from specify_cli.core.mission_payload import build_mission_created_payload
from specify_cli.migration.envelope_seam import (
    build_teamspace_envelope,
    deterministic_ulid,
    status_event_to_teamspace_envelope,
)
from specify_cli.status import MISSION_CREATED, WP_CREATED
from specify_cli.sync.history_import.scan import MissionScan, ScannedWorkPackage

# Envelope provenance. build_id/node_id are metadata the SaaS materializer does
# not route on (it dispatches on event_type and reads project_uuid/slug/repo_slug),
# so branding the synthesized prefix as "import-history" is honest provenance and
# harmless alongside the reused status builder's own tag.
_BUILD_ID = "import-history"
_NODE_ID = "import-history"

_AGG_MISSION = "Mission"
_AGG_WORK_PACKAGE = "WorkPackage"

_DEFAULT_TARGET_BRANCH = "main"
# A historical mission with no recoverable timestamp anywhere: a deterministic
# epoch sentinel keeps synthesis pure (never `now()`), honest (unknown time),
# and keeps MissionCreated ordered at or before everything else.
_UNKNOWN_TIMESTAMP = "1970-01-01T00:00:00+00:00"

_ACTOR = "spec-kitty sync import-history"

# The dedicated deterministic-id namespace for the synthesized creation prefix.
# Load-bearing: it MUST stay distinct from the migration dry-run's
# ``teamspace-dry-run:`` seeds (INV-4), so it is a single named constant — a
# typo in one of its three call sites would silently split the id namespace and
# break cross-run dedup.
_IMPORT_ID_NAMESPACE = "import:"


def synthesize_mission_stream(
    scan: MissionScan,
    *,
    project_uuid: uuid.UUID,
    project_slug: str,
    repo_slug: str,
) -> list[dict[str, Any]]:
    """Synthesize one mission's ordered, deterministic envelope stream.

    Lamport clocks are per-mission and monotonic: ``MissionCreated`` is ``1``,
    the ``WPCreated`` events follow (in the scan's deterministic WP order), then
    the ``WPStatusChanged`` events in ``(at, event_id)`` order — so a status
    change can never carry a lower clock than its work package's creation.
    """
    mission_ts = _earliest_timestamp(scan)
    correlation_id = deterministic_ulid(f"{_IMPORT_ID_NAMESPACE}{_identity_key(scan)}:correlation")
    identity = _EnvelopeIdentity(
        project_uuid=str(project_uuid),
        project_slug=project_slug,
        repo_slug=repo_slug,
        correlation_id=correlation_id,
    )

    stream: list[dict[str, Any]] = []
    lamport = 1

    stream.append(_mission_created_envelope(scan, mission_ts, lamport, identity))
    lamport += 1

    for wp in scan.work_packages:
        stream.append(_wp_created_envelope(scan, wp, mission_ts, lamport, identity))
        lamport += 1

    ordered_transitions = sorted(scan.lane_transitions, key=lambda event: (event.at, event.event_id))
    for status_event in ordered_transitions:
        status_envelope = status_event_to_teamspace_envelope(
            status_event,
            project_uuid=project_uuid,
            lamport_clock=lamport,
            project_slug=project_slug,
            repo_slug=repo_slug,
        )
        stream.append(_rebrand_as_import(status_envelope, identity))
        lamport += 1

    return stream


def synthesize_streams(
    scans: Sequence[MissionScan],
    *,
    project_uuid: uuid.UUID,
    project_slug: str,
    repo_slug: str,
) -> list[dict[str, Any]]:
    """Concatenate per-mission streams (lamport clocks restart per mission)."""
    envelopes: list[dict[str, Any]] = []
    for scan in scans:
        envelopes.extend(
            synthesize_mission_stream(
                scan,
                project_uuid=project_uuid,
                project_slug=project_slug,
                repo_slug=repo_slug,
            )
        )
    return envelopes


def dry_run_project_uuid(mission_slugs: Sequence[str]) -> uuid.UUID:
    """Synthetic offline ``project_uuid`` for dry-run (mirrors ``teamspace_dry_run``).

    WP-Y4 replaces this with the persisted real UUID (INV-5); the synthetic id
    must never reach the server on ``--apply``.
    """
    seed = "spec-kitty:teamspace-dry-run:" + "|".join(mission_slugs)
    return uuid.uuid5(uuid.NAMESPACE_URL, seed)


# ── internals ─────────────────────────────────────────────────────────────────


class _EnvelopeIdentity:
    """The envelope keys shared across every event in one mission's stream."""

    __slots__ = ("project_uuid", "project_slug", "repo_slug", "correlation_id")

    def __init__(self, *, project_uuid: str, project_slug: str, repo_slug: str, correlation_id: str) -> None:
        self.project_uuid = project_uuid
        self.project_slug = project_slug
        self.repo_slug = repo_slug
        self.correlation_id = correlation_id


def _mission_created_envelope(
    scan: MissionScan,
    mission_ts: str,
    lamport: int,
    identity: _EnvelopeIdentity,
) -> dict[str, Any]:
    payload = build_mission_created_payload(
        mission_slug=scan.mission_slug,
        target_branch=scan.target_branch or _DEFAULT_TARGET_BRANCH,
        mission_type=scan.mission_type,
        wp_count=len(scan.work_packages),
        mission_id=scan.canonical_mission_id,
        mission_number=scan.mission_number,
        friendly_name=scan.name,
        purpose_tldr=scan.purpose_tldr,
        purpose_context=scan.purpose_context,
        created_at=mission_ts,
    )
    return _envelope(
        event_id=deterministic_ulid(f"{_IMPORT_ID_NAMESPACE}{_identity_key(scan)}:MissionCreated"),
        event_type=MISSION_CREATED,
        aggregate_id=scan.canonical_mission_id or scan.mission_slug,
        aggregate_type=_AGG_MISSION,
        payload=payload,
        timestamp=mission_ts,
        lamport=lamport,
        identity=identity,
    )


def _wp_created_envelope(
    scan: MissionScan,
    wp: ScannedWorkPackage,
    mission_ts: str,
    lamport: int,
    identity: _EnvelopeIdentity,
) -> dict[str, Any]:
    parsed_created_at = _parse_timestamp(wp.created_at)
    payload = WPCreatedPayload(
        mission_slug=scan.mission_slug,
        mission_number=scan.mission_number,
        wp_id=wp.wp_id,
        wp_title=wp.wp_title,
        wp_path=wp.wp_path,
        depends_on=list(wp.depends_on),
        actor=_ACTOR,
        created_at=parsed_created_at,
    ).model_dump(mode="json", exclude_none=False)
    aware_created_at = _as_aware_utc(parsed_created_at)
    # The envelope timestamp and the payload's created_at must reach the SAME
    # verdict on wp.created_at. Previously the envelope let the raw string
    # pass through (`wp.created_at or mission_ts`) while the payload nulled
    # the exact same unparseable value — one envelope, two verdicts (#2884
    # finding C). Both now derive from the one `parsed_created_at`, and the
    # envelope's is the normalized ISO form (aware isoformat) consistent with
    # what ``_earliest_timestamp`` already emits — never a raw passthrough.
    timestamp = aware_created_at.isoformat() if aware_created_at is not None else mission_ts
    return _envelope(
        event_id=deterministic_ulid(f"{_IMPORT_ID_NAMESPACE}{_identity_key(scan)}:WPCreated:{wp.wp_id}"),
        event_type=WP_CREATED,
        aggregate_id=wp.wp_id,
        aggregate_type=_AGG_WORK_PACKAGE,
        payload=payload,
        timestamp=timestamp,
        lamport=lamport,
        identity=identity,
    )


def _envelope(
    *,
    event_id: str,
    event_type: str,
    aggregate_id: str,
    aggregate_type: str,
    payload: dict[str, Any],
    timestamp: str,
    lamport: int,
    identity: _EnvelopeIdentity,
) -> dict[str, Any]:
    """Assemble the creation-prefix TeamSpace envelope via the shared shell.

    The 15-key envelope shell is owned by ``build_teamspace_envelope`` (the same
    owner the migration ``WPStatusChanged`` builder uses, re-exported through
    ``envelope_seam``) — #2891, so the two replay producers cannot drift on the
    envelope-level fields. This builder only supplies the import producer's
    ``build_id``/``node_id``/``correlation_id`` values.
    """
    # ``build_teamspace_envelope`` returns the canonical ``_TeamspaceEnvelope``
    # model (CP001/CP002, #2884); ``.model_dump()`` is this function's
    # serialization boundary back to the wire-format dict the rest of the
    # import pipeline (mutation in ``_rebrand_as_import``, hashing, upload)
    # expects. Explicit annotation: under the project's ``follow_imports =
    # "skip"`` mypy config the cross-module call is seen as ``Any`` regardless;
    # re-narrow it here.
    envelope: dict[str, Any] = build_teamspace_envelope(
        event_id=event_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        payload=payload,
        timestamp=timestamp,
        build_id=_BUILD_ID,
        node_id=_NODE_ID,
        lamport_clock=lamport,
        project_uuid=identity.project_uuid,
        project_slug=identity.project_slug,
        repo_slug=identity.repo_slug,
        correlation_id=identity.correlation_id,
    ).model_dump()
    return envelope


def _rebrand_as_import(envelope: dict[str, Any], identity: _EnvelopeIdentity) -> dict[str, Any]:
    """Unify a reused status envelope's operation-identity fields.

    ``status_event_to_teamspace_envelope`` was written for the migration
    dry-run, so it stamps its own ``build_id``/``node_id`` and a per-event
    ``teamspace-dry-run:`` correlation. In the import context the whole stream
    is one operation, so we re-stamp those three (non-load-bearing) fields to
    match the synthesized prefix. Everything the builder computed — payload,
    real ``event_id``, lane back-fill, historical evidence — is left intact.
    """
    envelope["build_id"] = _BUILD_ID
    envelope["node_id"] = _NODE_ID
    envelope["correlation_id"] = identity.correlation_id
    return envelope


def _identity_key(scan: MissionScan) -> str:
    """Seed/dedup key: the canonical mission id when present, else the slug.

    The deterministic import ``event_id``s must key on the same identity the
    envelopes' ``aggregate_id`` trusts (mission 083 moved identity onto
    ``mission_id``). Seeding on the slug alone would let a deleted-then-recreated
    same-slug mission hash an identical creation prefix, so the server dedups the
    new mission's ``MissionCreated`` as a duplicate and it silently never
    materializes (its WPs orphan).
    """
    return scan.canonical_mission_id or scan.mission_slug


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string to ``datetime`` for the ``WPCreated`` payload.

    The scan carries ``created_at`` as a string (on-disk) or ``None``
    (synthesized), while ``WPCreatedPayload.created_at`` is typed ``datetime``.
    An unparseable value degrades to ``None`` rather than aborting synthesis.
    """
    if not value:
        return None
    try:
        return parse_iso(value)
    except ValueError:
        return None


def _as_aware_utc(value: datetime | None) -> datetime | None:
    """Normalize a ``datetime`` to an aware, UTC-offset instant.

    The three writers behind ``_earliest_timestamp``'s candidates (mission
    ``meta.json``, WP ``WPCreated`` payloads, and lane-transition ``at``
    fields) do not all use the same UTC offset convention. A naive value is
    assumed to already be UTC (the codebase's own writer, ``now_utc_iso()``,
    only ever produces offset-aware strings — a naive value would only occur
    for hand-authored or legacy data). An aware value with a NON-UTC offset
    is converted to UTC via ``astimezone`` — merely tagging ``tzinfo`` would
    leave the wall-clock time unconverted (e.g. ``08:00+02:00`` would render
    as ``08:00+00:00``, two hours off) and defeat the whole comparison
    (#2884 finding B).
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _earliest_timestamp(scan: MissionScan) -> str:
    """Earliest known timestamp across mission/WP/lane sources (deterministic).

    Candidates come from three different writers using different ISO-8601
    suffix conventions (a literal ``Z``, ``+00:00``, or another UTC offset). A
    raw string ``min()`` compares candidates lexicographically, which picks
    the wrong instant across those forms — e.g. ``"...07:00:00Z"`` sorts
    before ``"...08:00:00+02:00"`` even though the latter (06:00 UTC) is
    actually earlier (#2884 finding B). Parse every candidate to an aware
    ``datetime`` first and compare true instants; a candidate that fails to
    parse is excluded rather than let back in via the raw string.
    """
    candidates: list[str] = []
    if scan.created_at:
        candidates.append(scan.created_at)
    candidates.extend(wp.created_at for wp in scan.work_packages if wp.created_at)
    candidates.extend(event.at for event in scan.lane_transitions if event.at)

    parsed = [_as_aware_utc(_parse_timestamp(value)) for value in candidates]
    aware = [dt for dt in parsed if dt is not None]
    if not aware:
        return _UNKNOWN_TIMESTAMP
    return min(aware).isoformat()
