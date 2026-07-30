"""T020 / NFR-007: the recording ingress must exercise the REAL dispatch window.

NFR-007 was retargeted on 2026-07-30 (spec.md:247) because its original target was
a corpse: ``max_events_per_batch`` / ``_should_probe_advertised_limits`` live only
in ``sync/batch.py``, whose queue drain WP02 retired. A fake advertising batch
limits would test an unreachable path.

The live window is the local constant ``_EVENT_SYNC_DISPATCH_BATCH_LIMIT`` in
``cli/commands/sync.py::_run_dispatch_batches``, halved on HTTP 413 and regrown
after terminal progress. It must be exercised **with a non-consent dimension**,
because that window is what decides whether a non-consented row can occupy a
selection slot. Two independent failure modes hang off it, and neither is visible
from a report-layer test:

1. **Leak through a resized window.** Selection is correct at the default limit
   but a halved or regrown re-selection takes a different path. Every batch the
   ingress ever sees is recorded here, halved ones included, and none may carry a
   non-consented id.

2. **Starvation (NFR-002).** If a LIMIT were pushed down into the journal read,
   non-consented rows would fill the window and be stripped afterwards — an empty
   or under-full batch with consented work sitting behind it. The second test
   places the non-consented rows FIRST in ``created_at`` order so that a
   filter-after-limit implementation yields an empty first window.

An earlier revision of this WP labelled a report-layer test
(``test_report_does_not_read_the_legacy_offline_queue``) as T020. That test never
touches ``_EVENT_SYNC_DISPATCH_BATCH_LIMIT``, never enters
``_run_dispatch_batches``, stands up no ingress and exercises no 413 halving; it
is a fine FR-015/#3004 test under its own name.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from specify_cli.cli.commands import sync as sync_module
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    DeliveryResult,
    OutboundEvent,
    map_batch_response,
)
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event

if TYPE_CHECKING:
    from specify_cli.delivery.interfaces import DeliveryTarget

pytestmark = [pytest.mark.fast]

CONSENTED = "aaaaaaaa-0000-0000-0000-00000000000a"
#: No consent record is ever written for this one. Absence, not an explicit
#: opt-out — a predicate that reads silence as consent is the actual #3030 defect,
#: and an opted-out fixture would pass code that has that bug.
NEVER_OPTED_IN = "bbbbbbbb-0000-0000-0000-00000000000b"

_HTTP_PAYLOAD_TOO_LARGE = 413


class _RecordingIngress:
    """A real ``DeliveryReceiver`` that records every batch it is handed.

    Recording the batches — not the dispatcher's internals — is what makes the
    assertions observable-state assertions (NFR-001). ``oversize_at`` makes the
    ingress answer HTTP 413 for any batch at or above that size, which is the
    documented "retry with a smaller batch" signal ``_run_dispatch_batches``
    halves on, so the resized window is genuinely traversed rather than simulated.
    """

    def __init__(self, *, oversize_at: int | None = None) -> None:
        self.batches: list[tuple[str, ...]] = []
        self.rejected_sizes: list[int] = []
        self._oversize_at = oversize_at

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__recording-ingress__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Sequence[OutboundEvent]) -> list[DeliveryResult]:
        events = list(batch)
        self.batches.append(tuple(event.event_id for event in events))
        if self._oversize_at is not None and len(events) >= self._oversize_at:
            self.rejected_sizes.append(len(events))
            return map_batch_response(
                events, http_status=_HTTP_PAYLOAD_TOO_LARGE, body=None
            )
        return [
            DeliveryResult(
                event_id=event.event_id,
                outcome=DeliveryOutcome.SUCCESS,
                http_status=200,
            )
            for event in events
        ]

    def every_id_seen(self) -> set[str]:
        """Every id that ever entered the window, across every batch and resize."""
        return {event_id for batch in self.batches for event_id in batch}


@pytest.fixture(autouse=True)
def _consent_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(CONSENTED, True)


def _event(event_id: str, uuid: str, *, ordinal: int) -> Event:
    """A journal event whose ``created_at`` fixes its position in the universe."""
    created_at = f"2026-06-29T00:00:{ordinal:02d}+00:00"
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=json.dumps({"event_id": event_id}).encode("utf-8"),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
    )


@pytest.fixture
def ledger() -> SqliteDeliveryLedger:
    led = SqliteDeliveryLedger(":memory:")
    yield led
    led.close()


@pytest.fixture
def target(tmp_path: Path) -> DeliveryTarget:
    registry = SqliteDeliveryTargetRegistry(":memory:")
    yield registry.register(
        url="https://hosted.example.com",
        team_slug="team",
        user_email="operator@example.com",
    )
    registry.close()


def test_no_non_consented_event_ever_enters_the_live_dispatch_window(
    tmp_path: Path,
    ledger: SqliteDeliveryLedger,
    target: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFR-007: the window is traversed at full, halved and regrown size, and a
    project that never opted in occupies none of it.

    The population is interleaved and spans several batches on purpose: a leak
    that only appears in the second batch, or only in a re-selection after a 413
    shrank the limit, is invisible to a single-batch test.
    """
    journal = EventJournal(tmp_path / "journal.db")
    consented_ids: list[str] = []
    denied_ids: list[str] = []
    for index in range(9):
        consented = f"evt-ok-{index}"
        denied = f"evt-leak-{index}"
        journal.append(_event(consented, CONSENTED, ordinal=index * 2))
        journal.append(_event(denied, NEVER_OPTED_IN, ordinal=index * 2 + 1))
        consented_ids.append(consented)
        denied_ids.append(denied)
    assert journal.count() == 18, "precondition: one shared, contaminated journal"

    # The real window, shrunk so the test spans batches in a readable number of
    # POSTs. `oversize_at=4` makes the ingress 413 any full-size batch, so the
    # loop halves 4 -> 2, delivers, regrows to 4, 413s again — every one of those
    # sizes is a distinct re-selection the leak could ride.
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 4)
    ingress = _RecordingIngress(oversize_at=4)
    runtime = SimpleNamespace(journal=journal, ledger=ledger)

    summary = sync_module._run_dispatch_batches(runtime, ingress, target)

    # The REAL window was exercised, not a fake advertising a limit.
    assert ingress.batches, "the ingress was never called — no window was exercised"
    assert max(len(batch) for batch in ingress.batches) == 4, (
        "no batch ever reached the configured window size, so the limit was not "
        "the thing under test"
    )
    assert 4 in ingress.rejected_sizes, "the 413 halving path was never triggered"
    assert min(len(batch) for batch in ingress.batches) == 2, (
        "the halved window (4 -> 2) was never traversed"
    )

    # THE property. Every id that ever entered the window, at any size, in any
    # re-selection, including the batches the ingress rejected.
    leaked = ingress.every_id_seen() & set(denied_ids)
    assert not leaked, (
        f"{len(leaked)} event(s) from a project that never opted in entered the "
        f"dispatch window: {sorted(leaked)}. Selection at the default limit being "
        "correct does not make a halved or regrown re-selection correct."
    )

    # And the healthy drain still completes — a predicate that starves the
    # consenting project would satisfy the assertion above trivially.
    assert ingress.every_id_seen() == set(consented_ids)
    assert summary.delivered == len(consented_ids)


def test_the_window_is_filled_with_consented_events_not_wasted_on_denied_ones(
    tmp_path: Path,
    ledger: SqliteDeliveryLedger,
    target: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFR-002 starvation, expressed through the window (the other half of NFR-007).

    The eight non-consented rows are the OLDEST in the journal, so they sort first
    in the universe read. An implementation that pushed the window's LIMIT down
    into the journal SQL and filtered afterwards would select those eight, strip
    them, and hand the ingress an empty batch — reporting "nothing to send" with
    four consented events sitting behind them. The window must instead be filled
    with the four rows that are actually deliverable.
    """
    journal = EventJournal(tmp_path / "journal.db")
    for index in range(8):
        journal.append(_event(f"evt-leak-{index}", NEVER_OPTED_IN, ordinal=index))
    consented_ids = [f"evt-ok-{index}" for index in range(4)]
    for index, event_id in enumerate(consented_ids):
        journal.append(_event(event_id, CONSENTED, ordinal=8 + index))

    # The production default (1000) would swallow the distinction: the whole
    # universe fits one window, so nothing is proven about slot occupancy. 4 makes
    # the window exactly the size of the deliverable population, so an under-full
    # first batch is a detectable failure.
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 4)
    ingress = _RecordingIngress()
    runtime = SimpleNamespace(journal=journal, ledger=ledger)

    summary = sync_module._run_dispatch_batches(runtime, ingress, target)

    assert ingress.batches, (
        "the ingress was never called: the window was filled with rows the "
        "predicate then stripped, which is NFR-002's starvation"
    )
    assert ingress.batches[0] == tuple(consented_ids), (
        "the first window must be filled with the deliverable rows, not with the "
        "older non-consented ones that happen to sort ahead of them"
    )
    assert summary.delivered == 4
    assert not ingress.every_id_seen() & {f"evt-leak-{i}" for i in range(8)}
