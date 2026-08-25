"""T050/WP11 contract pins: CLI outbound wire shapes vs the canonical SaaS contract.

Fail-closed:

- **Batch-event envelope**: the per-event wire object the real dispatcher
   produces must carry every contract-required envelope field. The required
   field set is reused from ``tests/delivery/test_envelope.py`` (the P1 #2131
   regression pin) rather than redeclared. On top of the envelope, the #3030 admission proof
   fields (``project_uuid``/``admission_generation``/``binding_audience``) and
   the WP06 delivery identity must ride every event.
"""

from __future__ import annotations

import gzip
import json
from typing import Any

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.receivers import StubReceiver, _build_payload
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.migration.envelope_seam import build_teamspace_envelope
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore
from tests.delivery.test_envelope import _REQUIRED_ENVELOPE_FIELDS

pytestmark = [pytest.mark.contract, pytest.mark.fast]

#: #3030/WP06 fields the dispatcher must add on top of the emitted envelope:
#: the admission proof triple plus the wire type and the SaaS-native delivery
#: identity used for idempotent result correlation.
_REQUIRED_PROOF_FIELDS = frozenset(
    {
        "project_uuid",
        "admission_generation",
        "binding_audience",
        "type",
        "spec_kitty_delivery_identity",
    }
)

PROJECT_UUID = "aaaaaaaa-0000-0000-0000-00000000000a"
EVENT_ID = "01WP11CONTRACTENVELOPE0001"
_ACTOR = "cli-saas-contract-pin"


def _contract_envelope() -> dict[str, Any]:
    """A real teamspace envelope, built by the production envelope seam."""
    envelope: dict[str, Any] = build_teamspace_envelope(
        event_id=EVENT_ID,
        event_type="WPStatusChanged",
        aggregate_id="WP11",
        aggregate_type="WorkPackage",
        build_id="build-wp11",
        payload={
            "wp_id": "WP11",
            "from_lane": "in_progress",
            "to_lane": "for_review",
            "actor": _ACTOR,
        },
        node_id="node-wp11",
        lamport_clock=1,
        causation_id=None,
        correlation_id=EVENT_ID,
        timestamp="2026-08-12T00:00:00+00:00",
        project_uuid=PROJECT_UUID,
        project_slug="wp11-contract",
        repo_slug="private/wp11",
    ).model_dump()
    return envelope


def test_dispatcher_batch_event_carries_every_contract_required_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """capture -> dispatch -> receiver yields the full contract wire envelope."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    store = ProjectSyncStore(PROJECT_UUID)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover(_ACTOR)
        authority.publish_project_only(_ACTOR, verify_exact=lambda: True)
    record_project_opt_in(PROJECT_UUID, actor=_ACTOR)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
            "'admitted', '1', 'private-teamspace:team')",
            (PROJECT_UUID,),
        )

    envelope = _contract_envelope()
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, authority)
        journal.append(
            Event(
                event_id=EVENT_ID,
                event_type="WPStatusChanged",
                payload=json.dumps(envelope).encode("utf-8"),
                occurred_at="2026-08-12T00:00:00+00:00",
                created_at="2026-08-12T00:00:00+00:00",
                project_uuid=PROJECT_UUID,
            )
        )
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None

    receiver = StubReceiver()
    summary = dispatch(store=store, receiver=receiver, target=target, context=store.create_context())
    assert summary.selected == 1
    assert summary.delivered == 1

    received = receiver.received_events()
    assert len(received) == 1  # golden-count: cardinality-is-contract
    wire = dict(received[0].payload)

    missing_envelope = _REQUIRED_ENVELOPE_FIELDS - wire.keys()
    assert not missing_envelope, f"wire event missing contract envelope fields: {sorted(missing_envelope)}"
    missing_proof = _REQUIRED_PROOF_FIELDS - wire.keys()
    assert not missing_proof, f"wire event missing admission-proof fields: {sorted(missing_proof)}"

    # The values are the envelope's and the admitted authority's — not defaults.
    assert wire["event_id"] == EVENT_ID
    assert wire["event_type"] == "WPStatusChanged"
    assert wire["aggregate_id"] == "WP11"
    assert wire["payload"] == envelope["payload"]
    assert wire["type"] == "event"
    assert wire["spec_kitty_delivery_identity"] == EVENT_ID
    assert wire["project_uuid"] == PROJECT_UUID
    assert wire["admission_generation"] == 1
    assert wire["binding_audience"] == "private-teamspace:team"

    # And the serialized batch body — the exact bytes an HTTP receiver would
    # gzip and POST — carries the same complete per-event object (§3.1).
    body = json.loads(gzip.decompress(gzip.compress(_build_payload(received))).decode("utf-8"))
    event_body = body["events"][0]
    assert (_REQUIRED_ENVELOPE_FIELDS | _REQUIRED_PROOF_FIELDS).issubset(event_body.keys())
    assert event_body["payload"] == envelope["payload"]
