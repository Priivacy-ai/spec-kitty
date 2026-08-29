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

FR-018 / WP11 (T033): both loop-driving tests below also gain a hard cap on the
recorded ``dispatch`` call count, via the ``counted_dispatch`` fixture --
mirroring ``DISPATCH_CALL_CAP = 25`` in
``tests/delivery/test_nfr002_loop_permanence_3030.py:69``, asserted at
``:154-157``. **A pin whose failure mode is a hang is not a pin**: measured
during ``#3030``, a mutant produced 1,603 retried empty selections and the
suite reported nothing until forced with ``--timeout-method=signal``. The cap
turns a defect that stops ``_run_dispatch_batches`` from making progress into
a named red -- on the counter, never on a wall-clock backstop -- and is
demonstrated red-first under ``scripts/mutants/nonterminating_dispatch_3115.py``
(a hook-level pytest plugin, not a source edit, per C-003).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

from specify_cli.cli.commands import sync as sync_module
from specify_cli.delivery import dispatcher as dispatcher_module
from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    DeliveryResult,
    OutboundEvent,
    map_batch_response,
)
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

if TYPE_CHECKING:
    from specify_cli.delivery.interfaces import DeliveryTarget

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

CONSENTED = "aaaaaaaa-0000-0000-0000-00000000000a"
#: No consent record is ever written for this one. Absence, not an explicit
#: opt-out — a predicate that reads silence as consent is the actual #3030 defect,
#: and an opted-out fixture would pass code that has that bug.
NEVER_OPTED_IN = "bbbbbbbb-0000-0000-0000-00000000000b"

_HTTP_PAYLOAD_TOO_LARGE = 413

#: FR-018 / T033: a hard cap on the recorded ``dispatch`` call count, mirroring
#: ``DISPATCH_CALL_CAP`` in ``test_nfr002_loop_permanence_3030.py:69``. A pass
#: that cannot make progress must stop; the cap turns "the loop spins" into a
#: clean red naming the count instead of a hang -- a hang is not a measurement,
#: and a suite that hangs cannot tell you which invariant broke.
#: Measured headroom: the two tests below make 8 and 2 legitimate calls
#: respectively (halving/regrowth included), so 25 is ~3.1x the worst-case
#: legitimate count here -- not itself a bug, and nothing trips if a future
#: change grows the legitimate batch count somewhat.
DISPATCH_CALL_CAP = 25


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
            return cast(
                list[DeliveryResult],
                map_batch_response(events, http_status=_HTTP_PAYLOAD_TOO_LARGE, body=None),
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
    # The WP06 transport lease binds egress eligibility only while the machine
    # kill switch is armed (arming is NOT consent — #3030; the per-project
    # consent rows below still decide what ships).
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    for project_uuid in (CONSENTED, NEVER_OPTED_IN):
        store = ProjectSyncStore(project_uuid)
        authority = store.layout_generation()
        if authority.read_state().mode is LayoutMode.LEGACY:
            authority.begin_cutover("dispatch-window-test")
            authority.publish_project_only("dispatch-window-test", verify_exact=lambda: True)
    record_project_opt_in(CONSENTED, actor="dispatch-window-test")
    record_project_opt_out(NEVER_OPTED_IN, actor="dispatch-window-test")
    store = ProjectSyncStore(CONSENTED)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
            "'admitted', '1', 'private-teamspace:team')",
            (CONSENTED,),
        )


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
def target() -> DeliveryTarget:
    store = ProjectSyncStore(CONSENTED)
    with store.unit_of_work() as unit:
        current = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert current is not None
    return current


def _append_many(store: ProjectSyncStore, events: list[Event]) -> None:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        for event in events:
            journal.append(event)


@pytest.fixture
def counted_dispatch(monkeypatch: pytest.MonkeyPatch) -> list[int | None]:
    """Count the real ``dispatch`` calls one drain pass makes, and cap the loop.

    FR-018 (T033): termination must be asserted by a counter, never a timeout.
    Mirrors ``test_nfr002_loop_permanence_3030.py``'s ``counted_dispatch``
    fixture -- "``#3030`` already adopted this shape for exactly this reason,
    reuse over reinvention." ``_run_dispatch_batches`` imports ``dispatch``
    inside the function body, so the name resolves against the dispatcher
    module on every call and patching the attribute here reaches the live
    loop (it is the only production, ``src/``, name ``dispatch`` is reachable
    by -- see the per-site note in
    ``scripts/mutants/nonterminating_dispatch_3115.py``). The wrapper delegates
    to whatever is currently bound as the real implementation, so this counts
    the loop's iterations without faking selection.
    """
    calls: list[int | None] = []
    real = dispatcher_module.dispatch

    def counting(**kwargs: Any) -> Any:
        calls.append(kwargs.get("limit"))
        if len(calls) > DISPATCH_CALL_CAP:
            raise AssertionError(
                f"the drain loop did not stop: dispatch was called "
                f"{len(calls)} times, more than the {DISPATCH_CALL_CAP}-call "
                "cap, over a window this test's fixed, finite journal cannot "
                "legitimately exhaust that many times. FR-018: termination "
                "must be asserted by a counter, never a timeout -- this red "
                "names the count and is not `Failed: Timeout`."
            )
        return real(**kwargs)

    monkeypatch.setattr(dispatcher_module, "dispatch", counting)
    return calls


def test_no_non_consented_event_ever_enters_the_live_dispatch_window(
    tmp_path: Path,
    target: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
    counted_dispatch: list[int | None],
) -> None:
    """NFR-007: the window is traversed at full, halved and regrown size, and a
    project that never opted in occupies none of it.

    The population is interleaved and spans several batches on purpose: a leak
    that only appears in the second batch, or only in a re-selection after a 413
    shrank the limit, is invisible to a single-batch test.
    """
    del tmp_path
    store = ProjectSyncStore(CONSENTED)
    denied_store = ProjectSyncStore(NEVER_OPTED_IN)
    consented_ids: list[str] = []
    denied_ids: list[str] = []
    consented_events: list[Event] = []
    denied_events: list[Event] = []
    for index in range(9):
        consented = f"evt-ok-{index}"
        denied = f"evt-leak-{index}"
        consented_events.append(_event(consented, CONSENTED, ordinal=index * 2))
        denied_events.append(_event(denied, NEVER_OPTED_IN, ordinal=index * 2 + 1))
        consented_ids.append(consented)
        denied_ids.append(denied)
    _append_many(store, consented_events)
    _append_many(denied_store, denied_events)

    # The real window, shrunk so the test spans batches in a readable number of
    # POSTs. `oversize_at=4` makes the ingress 413 any full-size batch, so the
    # loop halves 4 -> 2, delivers, regrows to 4, 413s again — every one of those
    # sizes is a distinct re-selection the leak could ride.
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 4)
    ingress = _RecordingIngress(oversize_at=4)
    runtime = SimpleNamespace(store=store, context=store.create_context())

    summary = sync_module._run_dispatch_batches(runtime, ingress, target)

    # The REAL window was exercised, not a fake advertising a limit.
    assert ingress.batches, "the ingress was never called — no window was exercised"
    assert max(len(batch) for batch in ingress.batches) == 4, "no batch ever reached the configured window size, so the limit was not the thing under test"
    assert 4 in ingress.rejected_sizes, "the 413 halving path was never triggered"
    assert min(len(batch) for batch in ingress.batches) == 2, "the halved window (4 -> 2) was never traversed"

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
    target: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
    counted_dispatch: list[int | None],
) -> None:
    """NFR-002 starvation, expressed through the window (the other half of NFR-007).

    The eight non-consented rows are the OLDEST in the journal, so they sort first
    in the universe read. An implementation that pushed the window's LIMIT down
    into the journal SQL and filtered afterwards would select those eight, strip
    them, and hand the ingress an empty batch — reporting "nothing to send" with
    four consented events sitting behind them. The window must instead be filled
    with the four rows that are actually deliverable.
    """
    del tmp_path
    store = ProjectSyncStore(CONSENTED)
    denied_store = ProjectSyncStore(NEVER_OPTED_IN)
    _append_many(
        denied_store,
        [_event(f"evt-leak-{index}", NEVER_OPTED_IN, ordinal=index) for index in range(8)],
    )
    consented_ids = [f"evt-ok-{index}" for index in range(4)]
    _append_many(
        store,
        [_event(event_id, CONSENTED, ordinal=8 + index) for index, event_id in enumerate(consented_ids)],
    )

    # The production default (1000) would swallow the distinction: the whole
    # universe fits one window, so nothing is proven about slot occupancy. 4 makes
    # the window exactly the size of the deliverable population, so an under-full
    # first batch is a detectable failure.
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", 4)
    ingress = _RecordingIngress()
    runtime = SimpleNamespace(store=store, context=store.create_context())

    summary = sync_module._run_dispatch_batches(runtime, ingress, target)

    assert ingress.batches, "the ingress was never called: the window was filled with rows the predicate then stripped, which is NFR-002's starvation"
    assert ingress.batches[0] == tuple(consented_ids), (
        "the first window must be filled with the deliverable rows, not with the older non-consented ones that happen to sort ahead of them"
    )
    assert summary.delivered == 4
    assert not ingress.every_id_seen() & {f"evt-leak-{i}" for i in range(8)}
