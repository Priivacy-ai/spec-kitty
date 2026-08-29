"""Tests for the SYNTHESIZE stage of ``sync import-history`` — WP-Y3 (#2262).

The load-bearing assertion is *conformance*: every synthesized envelope must
pass the SAME two-step validation the migration dry-run uses
(``Event.model_validate`` + ``validate_event`` against the per-type payload
model), so the SaaS materializer cannot silently reject the batch. The
ordering (INV-3), determinism (INV-4), and identity threading are pinned on top
of that.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from spec_kitty_events import Event
from spec_kitty_events.conformance import validate_event

from specify_cli.status.models import StatusEvent
from specify_cli.sync.history_import.scan import (
    MissionScan,
    PrefixSource,
    ScannedWorkPackage,
    scan_mission,
)
from specify_cli.sync.history_import.synthesize import (
    deterministic_ulid,
    dry_run_project_uuid,
    synthesize_mission_stream,
    synthesize_streams,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS = _REPO_ROOT / "kitty-specs"
_LEGACY = _SPECS / "032-identity-aware-cli-event-sync"
_PREFIXED = _SPECS / "single-mission-surface-resolver-01KVGCE8"

_MISSION_ID = "01HZABCDEFGH1234567890JKMN"
_PROJECT_UUID = uuid.UUID("8a4a7da6-a97c-4bb4-893a-b31664abfee4")


# ── fixtures ──────────────────────────────────────────────────────────────────


def _status_event(wp_id: str, from_lane: str, to_lane: str, at: str, event_id: str) -> StatusEvent:
    return StatusEvent.from_dict(
        {
            "event_id": event_id,
            "mission_slug": "demo-mission",
            "mission_id": _MISSION_ID,
            "wp_id": wp_id,
            "from_lane": from_lane,
            "to_lane": to_lane,
            "at": at,
            "actor": "claude",
            "force": False,
            "execution_mode": "worktree",
            "evidence": None,
            "reason": None,
            "review_ref": None,
            "policy_metadata": None,
        }
    )


def _demo_scan() -> MissionScan:
    return MissionScan(
        mission_slug="demo-mission",
        canonical_mission_id=_MISSION_ID,
        mission_number=7,
        name="Demo Mission",
        mission_type="software-dev",
        purpose_tldr="Demonstrate import synthesis.",
        purpose_context="Context for the demo mission.",
        target_branch="main",
        created_at="2026-02-01T00:00:00+00:00",
        prefix_source=PrefixSource.SYNTHESIZED,
        work_packages=(
            ScannedWorkPackage("WP01", "First WP", (), None, None, PrefixSource.SYNTHESIZED),
            ScannedWorkPackage("WP02", "Second WP", ("WP01",), None, None, PrefixSource.SYNTHESIZED),
        ),
        lane_transitions=(
            _status_event("WP01", "planned", "claimed", "2026-02-02T00:00:00Z", "01HZ0000000000000000000001"),
            _status_event("WP02", "planned", "claimed", "2026-02-03T00:00:00Z", "01HZ0000000000000000000002"),
        ),
    )


def _assert_all_conform(stream: list[dict]) -> None:
    """Every envelope passes both validation steps the real pipeline runs."""
    for env in stream:
        Event.model_validate(env)  # raises on an invalid envelope
        result = validate_event(env["payload"], env["event_type"])
        assert result.valid, f"{env['event_type']} payload invalid: {getattr(result, 'model_violations', result)}"


# ── conformance (the non-fakeable proof) ──────────────────────────────────────


def test_every_synthesized_envelope_conforms():
    stream = synthesize_mission_stream(_demo_scan(), project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty")
    _assert_all_conform(stream)


def test_import_and_status_envelopes_share_one_top_level_key_set():
    """Guard against envelope-shape drift (Paula's #2884 M1): the hand-built
    creation-prefix envelope (``_envelope``) and the reused migration status
    envelope (``status_event_to_teamspace_envelope``) must carry the SAME
    top-level key set. If they drift, one import stream ships two shapes — the
    server could accept the WPStatusChanged rows while rejecting the
    MissionCreated/WPCreated prefix, orphaning every WP. This is the cheap
    parity guard the full-consolidation follow-up (#2262) can later subsume."""
    stream = synthesize_mission_stream(
        _demo_scan(), project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty"
    )
    mission_created = next(env for env in stream if env["event_type"] == "MissionCreated")
    wp_created = next(env for env in stream if env["event_type"] == "WPCreated")
    wp_status = next(env for env in stream if env["event_type"] == "WPStatusChanged")
    assert set(mission_created) == set(wp_status), "creation-prefix vs status envelope keys drifted"
    assert set(wp_created) == set(wp_status), "WPCreated vs status envelope keys drifted"


# ── ordering + INV-3 ──────────────────────────────────────────────────────────


def test_stream_is_ordered_creation_before_status():
    stream = synthesize_mission_stream(_demo_scan(), project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty")
    types = [env["event_type"] for env in stream]
    assert types == ["MissionCreated", "WPCreated", "WPCreated", "WPStatusChanged", "WPStatusChanged"]

    # Lamport is per-mission, monotonic 1..N.
    assert [env["lamport_clock"] for env in stream] == [1, 2, 3, 4, 5]

    # INV-3: each WPStatusChanged's WP has a WPCreated at a strictly lower clock.
    created_clock = {env["aggregate_id"]: env["lamport_clock"] for env in stream if env["event_type"] == "WPCreated"}
    for env in stream:
        if env["event_type"] == "WPStatusChanged":
            wp_id = env["aggregate_id"]
            assert wp_id in created_clock, f"{wp_id} has no WPCreated"
            assert created_clock[wp_id] < env["lamport_clock"]


def test_status_order_is_sorted_by_at_then_event_id_not_input_order():
    """Ordering witness (T1, #2884): the transitions arrive deliberately OUT of
    ``(at, event_id)`` order — including an ``at`` tie that only the
    ``event_id`` tie-break resolves — so deleting the ``sorted(...)`` in
    ``synthesize_mission_stream`` makes this test fail."""
    import dataclasses

    scan = dataclasses.replace(
        _demo_scan(),
        lane_transitions=(
            # input order: 09 (tied at), 01 (earliest), 05 (tied at, lower id)
            _status_event("WP02", "planned", "claimed", "2026-02-05T00:00:00Z", "01HZ0000000000000000000009"),
            _status_event("WP01", "planned", "claimed", "2026-02-02T00:00:00Z", "01HZ0000000000000000000001"),
            _status_event("WP02", "claimed", "in_progress", "2026-02-05T00:00:00Z", "01HZ0000000000000000000005"),
        ),
    )
    stream = synthesize_mission_stream(scan, project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty")

    status_ids = [env["event_id"] for env in stream if env["event_type"] == "WPStatusChanged"]
    assert status_ids == [
        "01HZ0000000000000000000001",  # earliest at
        "01HZ0000000000000000000005",  # at-tie broken by event_id ...
        "01HZ0000000000000000000009",  # ... not by input position
    ]


def test_multi_mission_stream_event_ids_are_unique():
    """Stream-wide id uniqueness (T2, #2884): two missions × two WPs each, with
    the same wp_ids repeating across missions. A seed regression that dropped
    ``wp.wp_id`` collides the two WPCreated ids WITHIN a mission; one that
    dropped the mission identity collides WP01 ACROSS missions."""
    kwargs = {"project_uuid": _PROJECT_UUID, "project_slug": "p", "repo_slug": "p"}

    def _scan(mission_id: str, slug: str) -> MissionScan:
        return MissionScan(
            mission_slug=slug,
            canonical_mission_id=mission_id,
            mission_number=None,
            name=slug,
            mission_type="software-dev",
            purpose_tldr=None,
            purpose_context=None,
            target_branch="main",
            created_at="2026-02-01T00:00:00+00:00",
            prefix_source=PrefixSource.SYNTHESIZED,
            work_packages=(
                ScannedWorkPackage("WP01", "First WP", (), None, None, PrefixSource.SYNTHESIZED),
                ScannedWorkPackage("WP02", "Second WP", (), None, None, PrefixSource.SYNTHESIZED),
            ),
            lane_transitions=(),
        )

    stream = synthesize_streams(
        [_scan("01AAAAAAAAAAAAAAAAAAAAAAAA", "m-a"), _scan("01BBBBBBBBBBBBBBBBBBBBBBBB", "m-b")],
        **kwargs,
    )

    # 2 × (MissionCreated + 2 WPCreated), in order — the content contract.
    assert [env["event_type"] for env in stream] == ["MissionCreated", "WPCreated", "WPCreated"] * 2

    ids = [env["event_id"] for env in stream]
    assert len(set(ids)) == len(ids), f"duplicate event_ids in the synthesized stream: {ids}"


def test_aggregate_conventions():
    stream = synthesize_mission_stream(_demo_scan(), project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty")
    mission_created = stream[0]
    assert mission_created["aggregate_type"] == "Mission"
    assert mission_created["aggregate_id"] == _MISSION_ID

    wp_created = [env for env in stream if env["event_type"] == "WPCreated"]
    assert {env["aggregate_id"] for env in wp_created} == {"WP01", "WP02"}
    assert all(env["aggregate_type"] == "WorkPackage" for env in wp_created)


# ── determinism (INV-4) + identity threading ──────────────────────────────────


def test_event_ids_are_deterministic_and_namespaced():
    kwargs = {"project_uuid": _PROJECT_UUID, "project_slug": "spec-kitty", "repo_slug": "acme/spec-kitty"}
    first = synthesize_mission_stream(_demo_scan(), **kwargs)
    second = synthesize_mission_stream(_demo_scan(), **kwargs)

    assert [env["event_id"] for env in first] == [env["event_id"] for env in second]
    # Creation-prefix ids live in the `import:` namespace and seed on the
    # canonical mission id (not the slug — see the collision test below).
    assert first[0]["event_id"] == deterministic_ulid(f"import:{_MISSION_ID}:MissionCreated")
    assert first[1]["event_id"] == deterministic_ulid(f"import:{_MISSION_ID}:WPCreated:WP01")
    # Replayed status events keep their real on-disk event_id.
    assert first[3]["event_id"] == "01HZ0000000000000000000001"


def test_creation_prefix_ids_seed_on_canonical_id_not_slug():
    """Two missions sharing a slug but with different canonical ids must NOT
    produce colliding creation-prefix event_ids — otherwise a deleted-then-
    recreated same-slug mission would dedup as a duplicate and never
    materialize (Stijn's #2884 review, fix #2)."""
    kwargs = {"project_uuid": _PROJECT_UUID, "project_slug": "p", "repo_slug": "p"}

    def _scan(mission_id: str) -> MissionScan:
        return MissionScan(
            mission_slug="reused-slug",
            canonical_mission_id=mission_id,
            mission_number=None,
            name="Reused Slug",
            mission_type="software-dev",
            purpose_tldr=None,
            purpose_context=None,
            target_branch="main",
            created_at="2026-02-01T00:00:00+00:00",
            prefix_source=PrefixSource.SYNTHESIZED,
            work_packages=(),
            lane_transitions=(),
        )

    a = synthesize_mission_stream(_scan("01AAAAAAAAAAAAAAAAAAAAAAAA"), **kwargs)
    b = synthesize_mission_stream(_scan("01BBBBBBBBBBBBBBBBBBBBBBBB"), **kwargs)
    assert a[0]["event_type"] == b[0]["event_type"] == "MissionCreated"
    assert a[0]["event_id"] != b[0]["event_id"]


def test_project_identity_is_threaded_into_every_envelope():
    stream = synthesize_mission_stream(_demo_scan(), project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty")
    assert all(env["project_uuid"] == str(_PROJECT_UUID) for env in stream)
    assert all(env["project_slug"] == "spec-kitty" for env in stream)
    assert all(env["repo_slug"] == "acme/spec-kitty" for env in stream)
    # The whole stream is one coherent import operation: unified correlation id
    # and build id across the synthesized prefix AND the reused status envelopes.
    assert len({env["correlation_id"] for env in stream}) == 1  # golden-count: cardinality-is-contract
    assert {env["build_id"] for env in stream} == {"import-history"}


def test_dry_run_project_uuid_is_deterministic():
    a = dry_run_project_uuid(["demo-mission", "other"])
    b = dry_run_project_uuid(["demo-mission", "other"])
    assert a == b
    assert a == uuid.uuid5(uuid.NAMESPACE_URL, "spec-kitty:teamspace-dry-run:demo-mission|other")


# ── timestamp correctness (#2884 findings B/C) ────────────────────────────────


def test_earliest_timestamp_compares_true_instants_not_lexicographic_strings():
    """Mixed ISO-8601 suffix forms (``Z`` / ``+00:00`` / another offset) must
    compare by true instant, not lexicographically (finding B, #2884): a raw
    string ``min()`` would pick ``"...07:00:00Z"`` over ``"...08:00:00+02:00"``
    even though the latter (06:00 UTC) is the actual earlier instant."""
    import dataclasses

    scan = dataclasses.replace(
        _demo_scan(),
        created_at=None,
        work_packages=(
            ScannedWorkPackage("WP01", "First WP", (), None, "2026-02-01T07:00:00Z", PrefixSource.SYNTHESIZED),
            ScannedWorkPackage("WP02", "Second WP", (), None, "2026-02-01T08:00:00+02:00", PrefixSource.SYNTHESIZED),
        ),
        lane_transitions=(),
    )
    stream = synthesize_mission_stream(
        scan, project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty"
    )
    mission_created = stream[0]
    # 2026-02-01T08:00:00+02:00 == 06:00 UTC, earlier than 07:00:00Z — a
    # lexicographic min would have picked the Z candidate instead.
    assert mission_created["timestamp"] == "2026-02-01T06:00:00+00:00"


def test_wp_created_envelope_timestamp_matches_normalized_created_at():
    """The ``WPCreated`` envelope timestamp and its payload ``created_at``
    must agree on the same INSTANT (finding C, #2884): a parseable
    ``created_at`` with a non-UTC offset must produce an envelope timestamp
    normalized to UTC (consistent with what ``_earliest_timestamp`` emits
    elsewhere), and it must name the exact same moment the payload's
    ``created_at`` datetime does — not a raw, un-normalized passthrough."""
    import dataclasses

    from kernel.clock import parse_iso

    scan = dataclasses.replace(
        _demo_scan(),
        work_packages=(
            ScannedWorkPackage("WP01", "First WP", (), None, "2026-02-01T08:00:00+02:00", PrefixSource.ON_DISK),
        ),
        lane_transitions=(),
    )
    stream = synthesize_mission_stream(
        scan, project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty"
    )
    wp_created = next(env for env in stream if env["event_type"] == "WPCreated")
    # 08:00+02:00 == 06:00 UTC — the envelope timestamp is the normalized form.
    assert wp_created["timestamp"] == "2026-02-01T06:00:00+00:00"
    # The payload keeps its own (pydantic-serialized) datetime, but it must
    # name the SAME instant as the envelope timestamp — never a differing
    # verdict on the same underlying created_at.
    assert parse_iso(wp_created["payload"]["created_at"]) == parse_iso(
        wp_created["timestamp"]
    )


def test_wp_created_envelope_falls_back_to_mission_ts_when_created_at_unparseable():
    """An unparseable ``created_at`` must fall back to ``mission_ts`` for BOTH
    the envelope timestamp and the payload verdict. Previously the envelope
    let the raw garbage string pass straight through
    (``wp.created_at or mission_ts``) while the payload nulled the exact same
    value — one envelope, two verdicts (finding C, #2884)."""
    import dataclasses

    scan = dataclasses.replace(
        _demo_scan(),
        created_at="2026-02-01T00:00:00+00:00",
        work_packages=(ScannedWorkPackage("WP01", "First WP", (), None, "not-a-timestamp", PrefixSource.ON_DISK),),
        lane_transitions=(),
    )
    stream = synthesize_mission_stream(
        scan, project_uuid=_PROJECT_UUID, project_slug="spec-kitty", repo_slug="acme/spec-kitty"
    )
    mission_created = stream[0]
    wp_created = next(env for env in stream if env["event_type"] == "WPCreated")
    assert wp_created["payload"]["created_at"] is None
    assert wp_created["timestamp"] == mission_created["timestamp"]


# ── real fixtures end-to-end ──────────────────────────────────────────────────


@pytest.mark.skipif(not _LEGACY.is_dir(), reason="legacy fixture 032 not present")
def test_legacy_fixture_synthesizes_a_conforming_stream():
    scan = scan_mission(_LEGACY)
    uuid_ = dry_run_project_uuid([scan.mission_slug])
    stream = synthesize_mission_stream(scan, project_uuid=uuid_, project_slug="spec-kitty", repo_slug="acme/spec-kitty")

    _assert_all_conform(stream)
    assert stream[0]["event_type"] == "MissionCreated"
    n_wp_created = sum(1 for env in stream if env["event_type"] == "WPCreated")
    assert n_wp_created >= 6  # WP01..WP06 synthesized from tasks/


@pytest.mark.skipif(not _PREFIXED.is_dir(), reason="prefixed fixture not present")
def test_prefixed_fixture_synthesizes_a_conforming_stream():
    scan = scan_mission(_PREFIXED)
    uuid_ = dry_run_project_uuid([scan.mission_slug])
    stream = synthesize_streams([scan], project_uuid=uuid_, project_slug="spec-kitty", repo_slug="acme/spec-kitty")

    _assert_all_conform(stream)
    assert stream[0]["event_type"] == "MissionCreated"
