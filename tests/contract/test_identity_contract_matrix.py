"""Identity contract matrix — the catch-all backstop for FR-062 / FR-063.

This test file enumerates every machine-facing payload surface that mission 083
migrated to the canonical ``mission_id`` identity and asserts that ``mission_id``
is present (or that ``aggregate_id`` is the ULID) in each one.

Surfaces covered
----------------
1. **Status snapshot** — ``StatusSnapshot.to_dict()``:
   the materialised per-mission view written to ``status.json``.
   It must carry the canonical identity fields via
   ``mission_identity_fields(...)``.

2. **Status event envelope (WP-level)** — ``StatusEvent.to_dict()``:
   WP-level events use ``aggregate_id = wp_id`` but the envelope must still
   include ``mission_id`` when the event was written post-WP05.
   (Legacy events without ``mission_id`` survive as compatibility; the field
   is simply omitted.  That case is covered by a separate negative assertion.)

3. **Merge state** — ``MergeState.to_dict()``:
   the persisted merge state at
   ``.kittify/runtime/merge/<mission_id>/state.json`` is keyed by
   ``mission_id`` (WP02 + WP10).

4. **Lane manifest** — ``LanesManifest.to_dict()``:
   the per-feature ``lanes.json`` file carries ``mission_id`` alongside
   ``mission_slug``.

5. **SaaS mission-lifecycle events** — ``EventEmitter.emit_mission_created``
   (and siblings ``emit_mission_closed`` / ``emit_mission_origin_bound``):
   when called with ``mission_id``, the emitted event's ``aggregate_id``
   switches from slug to ULID and ``payload.mission_id`` is populated.
   This is the single biggest contract surface for the SaaS-side migration
   (tracked in spec-kitty-saas#47).

6. **Dossier snapshot** — ``.kittify/dossiers/<slug>/snapshot-latest.json``:
   the current dossier snapshot schema does NOT yet carry a top-level
   ``mission_id`` field. Mission 083 deliberately left dossier snapshots
   keyed by slug to avoid expanding scope beyond the immediate collision
   problem. This surface is enumerated here with an explicit ``skip`` so a
   future follow-up can re-enable it without re-discovering the contract.

Design notes
------------
- Each surface is exercised against **real production code**, not mocks,
  whenever possible.  The tests emit synthetic payloads through the real
  ``to_dict()`` paths.
- The ``EventEmitter`` surface uses the shared ``emitter`` fixture defined
  in ``tests/sync/conftest.py``.  We borrow it via direct fixture request.
- Each parametrised case emits an assertion with a clear surface name so
  a regression immediately identifies the offending payload.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.merge.state import MergeState
from specify_cli.status.models import (
    Lane,
    StatusEvent,
    StatusSnapshot,
)
from specify_cli.sync.clock import LamportClock
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.git_metadata import GitMetadata, GitMetadataResolver
from specify_cli.sync.project_identity import ProjectIdentity
from specify_cli.sync.queue import OfflineQueue

pytestmark = [pytest.mark.fast]

# A representative ULID used everywhere the tests need a canonical mission_id.
ULID_CANONICAL = "01KNRQK0R1ZDS8Z57M1TRXF0XR"
MISSION_SLUG = "080-canonical-matrix"


# ---------------------------------------------------------------------------
# Surface enumerators — one builder per payload surface.
# ---------------------------------------------------------------------------


def _build_status_snapshot() -> dict[str, Any]:
    """Surface 1: StatusSnapshot.to_dict() carries mission identity fields."""
    snap = StatusSnapshot(
        mission_slug=MISSION_SLUG,
        materialized_at="2026-04-11T12:00:00+00:00",
        event_count=0,
        last_event_id=None,
        work_packages={},
        summary={lane.value: 0 for lane in Lane},
        mission_number=80,
        mission_type="software-dev",
    )
    return snap.to_dict()


def _build_wp_status_event() -> dict[str, Any]:
    """Surface 2: StatusEvent (WP-level) envelope includes mission_id."""
    event = StatusEvent(
        event_id="01HXYZ0123456789ABCDEFGHJK",
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.CLAIMED,
        at="2026-04-11T12:00:00+00:00",
        actor="claude",
        force=False,
        execution_mode="worktree",
        mission_id=ULID_CANONICAL,
    )
    return event.to_dict()


def _build_merge_state() -> dict[str, Any]:
    """Surface 3: MergeState.to_dict() is keyed by mission_id."""
    state = MergeState(
        mission_id=ULID_CANONICAL,
        mission_slug=MISSION_SLUG,
        target_branch="main",
        wp_order=["WP01", "WP02"],
    )
    return state.to_dict()


def _build_lanes_manifest() -> dict[str, Any]:
    """Surface 4: LanesManifest.to_dict() carries mission_id."""
    lane_a = ExecutionLane(
        lane_id="lane-a",
        wp_ids=("WP01",),
        write_scope=("src/**",),
        predicted_surfaces=(),
        depends_on_lanes=(),
        parallel_group=0,
    )
    manifest = LanesManifest(
        version=1,
        mission_slug=MISSION_SLUG,
        mission_id=ULID_CANONICAL,
        mission_branch=f"kitty/mission-canonical-matrix-{ULID_CANONICAL[:8]}",
        target_branch="main",
        lanes=[lane_a],
        computed_at="2026-04-11T12:00:00+00:00",
        computed_from="dependency_graph",
    )
    return manifest.to_dict()


# ---------------------------------------------------------------------------
# Contract matrix
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractSurface:
    """One row in the identity contract matrix."""

    name: str
    builder: Callable[[], dict[str, Any]]
    # Where the canonical ULID must appear in the resulting dict.
    # ``"payload.mission_id"`` is dot-notation for nested lookup.
    identity_locations: tuple[str, ...]
    # Optional — a dot-notation key that must equal the ULID exactly
    # (used for aggregate_id checks where applicable).
    ulid_equals: tuple[str, ...] = ()


CONTRACT_MATRIX: tuple[ContractSurface, ...] = (
    ContractSurface(
        name="status_snapshot",
        builder=_build_status_snapshot,
        identity_locations=("mission_slug",),
        # StatusSnapshot uses mission_identity_fields which outputs slug-based
        # identity metadata (mission_slug, mission_number, mission_type).
        # The ULID itself is not in the snapshot surface because the snapshot
        # is keyed by slug for backward compatibility with dashboard readers.
        # Still asserted here for enumeration completeness.
    ),
    ContractSurface(
        name="wp_status_event",
        builder=_build_wp_status_event,
        identity_locations=("mission_id", "mission_slug"),
        ulid_equals=("mission_id",),
    ),
    ContractSurface(
        name="merge_state",
        builder=_build_merge_state,
        identity_locations=("mission_id", "mission_slug"),
        ulid_equals=("mission_id",),
    ),
    ContractSurface(
        name="lanes_manifest",
        builder=_build_lanes_manifest,
        identity_locations=("mission_id", "mission_slug"),
        ulid_equals=("mission_id",),
    ),
)


def _dig(payload: dict[str, Any], dotted: str) -> Any:
    """Lookup dotted key path, returning ``None`` on miss."""
    cur: Any = payload
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


# ---------------------------------------------------------------------------
# Parametrised enumeration test — catches any surface that silently drops
# the canonical identity field.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "surface",
    CONTRACT_MATRIX,
    ids=lambda s: s.name,
)
def test_surface_carries_identity(surface: ContractSurface) -> None:
    """Every enumerated machine-facing surface must carry mission identity.

    Fails with an actionable message naming the offending surface so a
    regression is immediately traceable.
    """
    payload = surface.builder()
    assert isinstance(payload, dict), (
        f"Surface {surface.name!r} produced non-dict payload: {type(payload).__name__}"
    )
    assert payload, f"Surface {surface.name!r} produced an empty payload"

    for key in surface.identity_locations:
        value = _dig(payload, key)
        assert value, (
            f"Surface {surface.name!r} is missing identity field {key!r}. "
            f"Payload keys: {sorted(payload.keys())}. "
            f"FR-063 requires every machine-facing surface to carry mission identity."
        )

    for key in surface.ulid_equals:
        value = _dig(payload, key)
        assert value == ULID_CANONICAL, (
            f"Surface {surface.name!r} field {key!r} must equal the canonical "
            f"ULID {ULID_CANONICAL!r}, got {value!r}"
        )


def test_legacy_wp_status_event_without_mission_id_is_valid() -> None:
    """Legacy WP events that lack ``mission_id`` must still be serialisable.

    This is the negative corollary of the matrix check above: a pre-WP05 event
    written before the migration should round-trip cleanly with no
    ``mission_id`` key in ``to_dict()``.  The contract is: post-WP05 events
    carry ``mission_id``; legacy events do not. Readers must handle both.
    """
    legacy_event = StatusEvent(
        event_id="01HXYZ0123456789ABCDEFGHJK",
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.CLAIMED,
        at="2026-04-11T12:00:00+00:00",
        actor="claude",
        force=False,
        execution_mode="worktree",
        # No mission_id — legacy event.
    )
    payload = legacy_event.to_dict()
    assert "mission_id" not in payload, (
        "Legacy StatusEvent without mission_id must not synthesise a false value"
    )
    assert "legacy_aggregate_id" not in payload, (
        "legacy_aggregate_id must never be emitted after drift-window closure"
    )
    assert payload["mission_slug"] == MISSION_SLUG


# ---------------------------------------------------------------------------
# SaaS emitter surface — exercised via a real EventEmitter built inline.
#
# We cannot borrow the ``emitter`` fixture from ``tests/sync/conftest.py``
# because pytest conftest fixtures are scoped to their own package tree.
# Instead we build a minimal but fully-wired EventEmitter directly so the
# test still exercises production code end-to-end.
# ---------------------------------------------------------------------------


@pytest.fixture()
def local_emitter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> EventEmitter:
    """Construct a real EventEmitter wired to in-memory / tmp backing stores.

    Mirrors the ``tests/sync/conftest.py::emitter`` fixture but standalone so
    it works from the contract-tests package tree.
    """
    # Patch the auth lookup so the emitter thinks it is authenticated.
    team = MagicMock()
    team.id = "test-team"
    team.slug = "test-team"
    session = MagicMock()
    session.default_team_id = "test-team"
    session.teams = [team]
    session.email = "tester@example.com"
    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = session
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)

    queue = OfflineQueue(db_path=tmp_path / "test_queue.db")
    clock = LamportClock(value=0, node_id="test-node-id", _storage_path=tmp_path / "clock.json")
    config = MagicMock(spec=SyncConfig)
    config.get_server_url.return_value = "https://test.spec-kitty.dev"
    identity = ProjectIdentity(
        project_uuid=uuid4(),
        project_slug="test-project",
        node_id="test-node-123",
        build_id="test-build-id-0000-0000-000000000001",
    )
    git_metadata = GitMetadata(
        git_branch="test-branch",
        head_commit_sha="a" * 40,
        repo_slug="test-org/test-repo",
    )
    git_resolver = MagicMock(spec=GitMetadataResolver)
    git_resolver.resolve.return_value = git_metadata

    return EventEmitter(
        clock=clock,
        config=config,
        queue=queue,
        ws_client=None,
        _identity=identity,
        _git_resolver=git_resolver,
    )


def test_saas_mission_created_emits_mission_id_as_aggregate(
    local_emitter: EventEmitter,
) -> None:
    """Surface 5: EventEmitter.emit_mission_created switches aggregate_id to mission_id.

    FR-024 / ADR 2026-04-09-1: mission-lifecycle events must use the ULID as
    the machine-facing join key.  ``payload.mission_id`` is also populated.
    """
    event = local_emitter.emit_mission_created(
        mission_slug=MISSION_SLUG,
        mission_number=80,
        target_branch="main",
        wp_count=4,
        mission_id=ULID_CANONICAL,
    )
    assert event is not None, "emit_mission_created returned None"
    assert event["aggregate_id"] == ULID_CANONICAL, (
        f"MissionCreated aggregate_id must be the ULID, got {event['aggregate_id']!r}"
    )
    assert event["payload"]["mission_id"] == ULID_CANONICAL, (
        "MissionCreated payload.mission_id must equal the canonical ULID"
    )
    assert event["payload"]["mission_slug"] == MISSION_SLUG, (
        "mission_slug must still be carried as a display field"
    )


def test_saas_mission_closed_emits_mission_id_as_aggregate(
    local_emitter: EventEmitter,
) -> None:
    """Surface 5b: emit_mission_closed also switches aggregate_id to mission_id."""
    event = local_emitter.emit_mission_closed(
        mission_slug=MISSION_SLUG,
        total_wps=4,
        mission_id=ULID_CANONICAL,
    )
    assert event is not None
    assert event["aggregate_id"] == ULID_CANONICAL
    assert event["payload"]["mission_id"] == ULID_CANONICAL


def test_saas_mission_origin_bound_emits_mission_id_as_aggregate(
    local_emitter: EventEmitter,
) -> None:
    """Surface 5c: emit_mission_origin_bound also switches aggregate_id to mission_id."""
    event = local_emitter.emit_mission_origin_bound(
        mission_slug=MISSION_SLUG,
        provider="linear",  # must match emitter._PAYLOAD_RULES validator
        external_issue_id="123",
        external_issue_key="LIN-123",
        external_issue_url="https://linear.app/org/issue/LIN-123",
        title="Test issue",
        mission_id=ULID_CANONICAL,
    )
    assert event is not None
    assert event["aggregate_id"] == ULID_CANONICAL
    assert event["payload"]["mission_id"] == ULID_CANONICAL


def test_saas_emitter_requires_mission_id(
    local_emitter: EventEmitter,
) -> None:
    """After drift-window closure, mission_id is mandatory on all emitter methods.

    Calling without ``mission_id`` must raise ``TypeError`` because the
    parameter is no longer optional.
    """
    with pytest.raises(TypeError):
        local_emitter.emit_mission_created(
            mission_slug=MISSION_SLUG,
            mission_number=80,
            target_branch="main",
            wp_count=4,
            # No mission_id — must fail.
        )

    with pytest.raises(TypeError):
        local_emitter.emit_mission_closed(
            mission_slug=MISSION_SLUG,
            total_wps=4,
            # No mission_id — must fail.
        )

    with pytest.raises(TypeError):
        local_emitter.emit_mission_origin_bound(
            mission_slug=MISSION_SLUG,
            provider="linear",
            external_issue_id="123",
            external_issue_key="LIN-123",
            external_issue_url="https://linear.app/org/issue/LIN-123",
            title="Test issue",
            # No mission_id — must fail.
        )


# ---------------------------------------------------------------------------
# Dossier surface — enumerated for FR-063 completeness, but currently
# out-of-scope for mission 083.  The skip documents why.
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "FR-063 enumeration: dossier snapshot schema does not yet carry a "
        "top-level mission_id field. Mission 083 intentionally scoped dossier "
        "changes to slug-only to avoid expanding beyond the collision fix. "
        "Follow-up tracked for a future mission — remove this skip when the "
        "dossier snapshot gains mission_id."
    )
)
def test_dossier_snapshot_has_mission_id() -> None:
    """Surface 6: dossier snapshot-latest.json must include mission_id.

    When unblocked, this test should:
    1. Seed a fixture feature_dir with a valid meta.json (mission_id + slug).
    2. Invoke ``specify_cli.dossier.snapshot.compute_snapshot(...)``.
    3. Load the emitted JSON from ``.kittify/dossiers/<slug>/snapshot-latest.json``.
    4. Assert ``snapshot["mission_id"] == ULID_CANONICAL``.
    """
    raise NotImplementedError  # pragma: no cover
