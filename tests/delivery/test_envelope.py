"""P1-envelope regression: the journal must store the FULL wire envelope.

Adversarial review of PR #2131 confirmed a P1 defect — the producer journal
stored only the **inner** ``payload`` of an emitted event, so when the WP07
dispatcher drained those rows and the WP06 receiver POSTed them, every batch
event was missing the contract-required envelope fields (``event_id``,
``event_type``, ``aggregate_id``, ``payload``, ``timestamp``, ``node_id``,
``lamport_clock``, ``schema_version``) and the server contract rejected them.

This drives the **real** emit → capture → dispatch → receiver path end to end
(no hand-built journal rows) and asserts the per-event wire object the receiver
would POST carries the whole envelope, with the original event-specific data
nested under ``payload``. Capture-first durability (FR-017) is unaffected: the
envelope is assembled before the capture write, so the durable fact still lands
before any delivery gate.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.receivers import StubReceiver, _build_payload
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal import (
    EventJournal,
    reset_coalesce_strategy,
    reset_journal_cache,
)
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

if TYPE_CHECKING:
    from specify_cli.sync.emitter import EventEmitter

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

# The full set of envelope fields the batch API contract requires per event.
_REQUIRED_ENVELOPE_FIELDS = {
    "event_id",
    "event_type",
    "aggregate_id",
    "payload",
    "timestamp",
    "node_id",
    "lamport_clock",
    "schema_version",
}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    reset_journal_cache()
    reset_coalesce_strategy()
    yield
    reset_journal_cache()
    reset_coalesce_strategy()


def _stub_emitter() -> EventEmitter:
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    em = EventEmitter()
    em._identity = SimpleNamespace(build_id="build-1", project_uuid=None, project_slug=None)
    em._get_git_metadata = lambda: GitMetadata()
    return em


def test_journal_stores_full_envelope_so_dispatch_posts_contract_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Emit → capture → dispatch → receiver yields a contract-shaped wire event."""
    from specify_cli.sync import emitter as emitter_mod

    monkeypatch.setattr(emitter_mod, "is_saas_sync_enabled", lambda: False)
    # The WP06 transport lease reads the machine kill switch through
    # ``feature_flags`` directly (not the emitter's patched name); dispatch's
    # egress eligibility requires it armed. Arming is NOT consent (#3030) —
    # the explicit opt-in below still decides. The receiver is a stub, so no
    # network is reachable either way.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    # #3030 T006: capture is gated on per-project consent, and WP01 made an unrecorded
    # checkout a denial. This test is about envelope shape surviving capture→drain, so
    # it consents explicitly — via the real ``set_project_consent`` record below. The
    # cwd-derived ``is_sync_enabled_for_checkout`` override that used to stand in for
    # that record was removed with M1-1: the emitter no longer imports the name, so
    # patching it asserted nothing. The non-consenting path is pinned by
    # tests/sync/test_sync_consent_capture_gap_3031.py.
    em = _stub_emitter()
    # #3030 WP06: the stored project_uuid is the sole authority for selection, so
    # an identity-less capture is unselectable and this test's drain would find
    # nothing. Give the stub a real identity and consent to it — the subject here
    # is envelope shape surviving capture->drain, not consent.
    from types import SimpleNamespace
    from uuid import uuid4

    project_uuid = str(uuid4())
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("envelope-test")
        authority.publish_project_only("envelope-test", verify_exact=lambda: True)
    em._identity = SimpleNamespace(build_id="build-envelope", project_uuid=project_uuid, project_slug="envelope")
    record_project_opt_in(project_uuid, actor="envelope-test")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://a.example.com', 'u@example.com', 'team', 1, "
            "'admitted', '1', 'private-teamspace:team')",
            (project_uuid,),
        )

    # The capture gate is forced open so the row lands with
    # drain_blocked_reason=None. is_saas_sync_enabled stays patched False only to
    # keep this test off the network and on the team_slug=None journal; without the
    # override the row would be stamped saas_disabled, which #3030 T003 classifies
    # as terminal (the operator's policy did not permit shipping it) and selection
    # therefore excludes. Same instance-level override the sibling consent pins use.
    from specify_cli.event_journal import CaptureGateState

    em._capture_gate_state = lambda _team, **_kwargs: CaptureGateState(saas_enabled=True, checkout_enabled=True, authenticated=True, team_slug="team")

    inner = {"error_type": "runtime", "error_message": "boom", "wp_id": "WP01"}
    envelope = em._emit(
        event_type="ErrorLogged",
        aggregate_id="WP01",
        aggregate_type="WorkPackage",
        payload=dict(inner),
    )
    assert envelope is not None

    # Drain the producer journal through the real dispatcher + a real stub receiver.
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, authority)
        assert journal.count() == 1
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    receiver = StubReceiver()

    summary = dispatch(
        store=store,
        receiver=receiver,
        target=target,
        context=store.create_context(),
    )
    assert summary.selected == 1
    assert summary.delivered == 1

    # The receiver received exactly the per-event wire object the dispatcher built
    # from the journal BLOB — it must carry the WHOLE envelope, not the inner payload.
    received = receiver.received_events()
    assert len(received) == 1  # golden-count: cardinality-is-contract
    wire = dict(received[0].payload)
    missing = _REQUIRED_ENVELOPE_FIELDS - wire.keys()
    assert not missing, f"wire event missing contract envelope fields: {missing}"

    # Envelope fields carry the emitted values; the event-specific data is nested
    # under ``payload`` (NOT flattened onto the envelope root).
    assert wire["event_id"] == envelope["event_id"]
    assert wire["event_type"] == "ErrorLogged"
    assert wire["aggregate_id"] == "WP01"
    assert wire["schema_version"] == "3.0.0"
    assert wire["payload"] == inner

    # And the serialized batch body the receiver POSTs is well-formed with the
    # full envelope as the per-event object (§3.1 wire shape).
    body = json.loads(_build_payload(received).decode("utf-8"))
    assert _REQUIRED_ENVELOPE_FIELDS.issubset(body["events"][0].keys())
    assert body["events"][0]["payload"] == inner
