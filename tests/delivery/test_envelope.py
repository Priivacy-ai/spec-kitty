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
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import StubReceiver, _build_payload
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal import (
    get_journal,
    reset_coalesce_strategy,
    reset_journal_cache,
)

if TYPE_CHECKING:
    from specify_cli.sync.emitter import EventEmitter

pytestmark = pytest.mark.fast

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
    em._identity = SimpleNamespace(
        build_id="build-1", project_uuid=None, project_slug=None
    )
    em._get_git_metadata = lambda: GitMetadata()  # type: ignore[method-assign]
    return em


def test_journal_stores_full_envelope_so_dispatch_posts_contract_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Emit → capture → dispatch → receiver yields a contract-shaped wire event."""
    from specify_cli.sync import emitter as emitter_mod

    monkeypatch.setattr(emitter_mod, "is_saas_sync_enabled", lambda: False)
    em = _stub_emitter()

    inner = {"error_type": "runtime", "error_message": "boom", "wp_id": "WP01"}
    envelope = em._emit(
        event_type="ErrorLogged",
        aggregate_id="WP01",
        aggregate_type="WorkPackage",
        payload=dict(inner),
    )
    assert envelope is not None

    # Drain the producer journal through the real dispatcher + a real stub receiver.
    journal = get_journal(team_slug=None)
    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = registry.register(
        url="https://a.example.com", team_slug="team", user_email="u@example.com"
    )
    receiver = StubReceiver()

    summary = dispatch(journal=journal, ledger=ledger, receiver=receiver, target=target)
    assert summary.selected == 1
    assert summary.delivered == 1

    # The receiver received exactly the per-event wire object the dispatcher built
    # from the journal BLOB — it must carry the WHOLE envelope, not the inner payload.
    received = receiver.received_events()
    assert len(received) == 1
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
