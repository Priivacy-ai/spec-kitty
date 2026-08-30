"""NFR-002's second half: an empty selection ENDS the pass, so starvation is permanent.

Intended location: ``tests/delivery/test_nfr002_loop_permanence_3030.py``.

NFR-002 has two clauses. The first — "a drain delivers consented events regardless of
how many non-consented rows precede them in FIFO order" — is pinned by
``test_liveness_predicate_before_limit_3030.py`` and by
``test_dispatch_window_consent_3030.py``, and mutation ``mutB2_limit_first_current``
reds both. The second clause is the parenthetical that makes the first a P0 rather
than a throughput complaint: *"filtering after LIMIT starves the drain
**permanently**"*. Nothing pinned that. A test proving one drain delivers 10 of 2,010
says nothing about what the loop would have done had the selection been empty — and
if the loop simply tried again, starvation would be a delay, not a permanent stop.

**The requirement cites a corpse for the mechanism.** ``_should_stop_sync_loop``
lives in ``sync/batch.py`` and has exactly one caller, ``sync_all_queued_events`` —
the legacy queue drain FR-012 retired, which
``tests/sync/test_no_queue_drain_constructed_3030.py`` actively forbids ``sync now``
from reaching. This is the same dead target NFR-007 was retargeted away from on
2026-07-30. The live break is in ``cli/commands/sync.py::_run_dispatch_batches``:

    if batch.selected == 0 or not advanced:
        break

That break is what these tests pin, since it is what the permanence claim rests on.

Note the loop has *two* independent reasons to stop on an empty selection —
``batch.selected == 0`` and ``not advanced`` (an empty batch makes no terminal
progress and adds nothing to the skip set). Both must be removed for the drain to
spin, which is exactly the shape of the tempting cheap fix the SC-002 pin warns
about: "loop a few more times and it'll pick them up". Mutant
``mutG_loop_retries_on_empty`` does precisely that and this file reds under it.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from specify_cli.cli.commands import sync as sync_module
from specify_cli.delivery import dispatcher as dispatcher_module
from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    DeliveryResult,
    OutboundEvent,
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
#: Never given a consent record. Absence, not opt-out — a predicate that reads
#: silence as consent is the #3030 defect itself.
NEVER_OPTED_IN = "bbbbbbbb-0000-0000-0000-00000000000b"

#: A pass that cannot make progress must stop, so the dispatch count is bounded. The
#: cap turns "the loop spins" into a clean red instead of a CI timeout: a hang is not
#: a measurement, and a suite that hangs cannot tell you which invariant broke.
DISPATCH_CALL_CAP = 25


class _RecordingIngress:
    """A real receiver that records every batch, so "no POST" is observable state."""

    def __init__(self) -> None:
        self.batches: list[tuple[str, ...]] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__permanence-ingress__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Sequence[OutboundEvent]) -> list[DeliveryResult]:
        events = list(batch)
        self.batches.append(tuple(event.event_id for event in events))
        return [DeliveryResult(event_id=event.event_id, outcome=DeliveryOutcome.SUCCESS, http_status=200) for event in events]


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
            authority.begin_cutover("nfr002-test")
            authority.publish_project_only("nfr002-test", verify_exact=lambda: True)
    record_project_opt_in(CONSENTED, actor="nfr002-test")
    record_project_opt_out(NEVER_OPTED_IN, actor="nfr002-test")
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
    """Count the real ``dispatch`` calls one pass makes, and cap the loop.

    ``_run_dispatch_batches`` imports ``dispatch`` inside the function body, so the
    name resolves against the dispatcher module on every call and patching it here
    reaches the live loop. The wrapper delegates to the real implementation — this
    counts the loop's iterations, it does not fake selection.
    """
    calls: list[int | None] = []
    real = dispatcher_module.dispatch

    def counting(**kwargs: Any) -> Any:
        calls.append(kwargs.get("limit"))
        if len(calls) > DISPATCH_CALL_CAP:
            raise AssertionError(
                f"the drain loop did not stop: dispatch was called more than "
                f"{DISPATCH_CALL_CAP} times over a store where nothing is deliverable. "
                "NFR-002's permanence claim rests on the loop breaking on an empty "
                "selection; a loop that retries instead turns starvation into a spin "
                "(and turns this suite into a hang)"
            )
        return real(**kwargs)

    monkeypatch.setattr(dispatcher_module, "dispatch", counting)
    return calls


def test_an_empty_selection_ends_the_pass_after_one_dispatch(
    tmp_path: Path,
    target: DeliveryTarget,
    counted_dispatch: list[int | None],
) -> None:
    """The mechanism NFR-002 names: one empty selection ends the pass.

    The store holds nothing deliverable — every row belongs to a project that never
    opted in — so the selection is empty on the first look and can never become
    non-empty without operator action. The loop must therefore stop after exactly one
    dispatch, issue no POST, and report zero. That stop is *why* a starved window is
    permanent rather than a delay: within a pass nothing looks again, and the next
    `sync now` re-reads the same store to the same answer.
    """
    del tmp_path
    store = ProjectSyncStore(CONSENTED)
    denied_store = ProjectSyncStore(NEVER_OPTED_IN)
    _append_many(
        denied_store,
        [_event(f"evt-denied-{index}", NEVER_OPTED_IN, ordinal=index) for index in range(12)],
    )

    ingress = _RecordingIngress()
    runtime = SimpleNamespace(store=store, context=store.create_context())

    summary = sync_module._run_dispatch_batches(runtime, ingress, target)

    # The fixture records the ``limit`` of every dispatch call, so assert the calls
    # themselves rather than how many there were: one look, and it looked through
    # the FULL window. A single call at a shrunk limit is the same count and a
    # different claim — the pass would have concluded "nothing deliverable" from a
    # partial window, and NFR-002's permanence rests on that conclusion being final.
    assert counted_dispatch == [sync_module._EVENT_SYNC_DISPATCH_BATCH_LIMIT], (
        "an empty selection must end the pass immediately, after exactly one "
        f"full-window look: dispatch was called with limits {counted_dispatch!r} "
        "over a store whose answer cannot change"
    )
    assert summary.selected == 0
    assert summary.delivered == 0
    assert ingress.batches == [], "no POST may be issued for an empty selection"
    with denied_store.unit_of_work() as unit:
        assert EventJournal(unit, denied_store.layout_generation()).count() == 12, "C-002: filtering is not deletion"


def test_the_first_pass_is_the_only_chance_a_consented_backlog_gets(
    tmp_path: Path,
    target: DeliveryTarget,
    counted_dispatch: list[int | None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Permanence, stated as a consequence: a later pass rescues nothing.

    SC-002's shape, scaled to the window: eight non-consented rows OLDER than four
    consented ones, and a window exactly the size of the deliverable population. A
    predicate applied after the limit fills the window with the eight, strips them,
    and hands back an empty selection — and because the loop breaks on that, the four
    consented events are not merely late, they never ship.

    Both halves are asserted: the first pass must deliver all four, and the second
    pass over the unchanged store must add nothing. The second half is what makes the
    first load-bearing — if repetition could rescue a starved window, delivering on
    the first pass would be an optimisation rather than the whole requirement.
    """
    del tmp_path
    store = ProjectSyncStore(CONSENTED)
    denied_store = ProjectSyncStore(NEVER_OPTED_IN)
    _append_many(
        denied_store,
        [_event(f"evt-denied-{index}", NEVER_OPTED_IN, ordinal=index) for index in range(8)],
    )
    consented_ids = [f"evt-ok-{index}" for index in range(4)]
    _append_many(
        store,
        [_event(event_id, CONSENTED, ordinal=8 + index) for index, event_id in enumerate(consented_ids)],
    )

    # The window is exactly the deliverable population, so a window occupied by
    # non-consented rows is a detectable under-fill rather than a rounding error.
    monkeypatch.setattr(sync_module, "_EVENT_SYNC_DISPATCH_BATCH_LIMIT", len(consented_ids))
    runtime = SimpleNamespace(store=store, context=store.create_context())

    first_ingress = _RecordingIngress()
    first = sync_module._run_dispatch_batches(runtime, first_ingress, target)
    assert first.delivered == len(consented_ids), (
        "the first pass must deliver every consented event: it is the only pass that "
        "will ever look. A window filled with the eight older non-consented rows "
        "yields an empty selection, the loop breaks on it, and these four never ship "
        f"(NFR-002). delivered={first.delivered}"
    )
    assert set(consented_ids) == {event_id for batch in first_ingress.batches for event_id in batch}

    second_ingress = _RecordingIngress()
    second = sync_module._run_dispatch_batches(runtime, second_ingress, target)
    assert second.delivered == 0
    assert second_ingress.batches == [], (
        "the second pass must find nothing to send — re-running the drain is not a "
        "remedy for a window the predicate mis-filled, which is why starvation is "
        "permanent rather than delayed"
    )
    with store.unit_of_work() as unit, denied_store.unit_of_work() as denied_unit:
        assert EventJournal(unit, store.layout_generation()).count() == 4
        assert EventJournal(denied_unit, denied_store.layout_generation()).count() == 8
