"""Regression: an opted-out project is never captured or dispatched (#3030/#3031).

This drives the real emit -> capture -> dispatch -> receiver path with two
projects sharing one local runtime root. The consented project must be captured
and delivered; the opted-out project's envelope may be emitted for local caller
semantics, but it must not create a journal row that a later drain could ship.

The sibling ``test_dispatch_honours_drain_blocked_3031.py`` independently pins
the defence-in-depth selection rule for legacy or otherwise blocked rows. This
test covers the stronger storage boundary through the production emitter.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal import (
    CaptureGateState,
    get_journal,
    reset_coalesce_strategy,
    reset_journal_cache,
)

if TYPE_CHECKING:
    from specify_cli.sync.emitter import EventEmitter

pytestmark = [pytest.mark.regression, pytest.mark.fast]

@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """One shared ``SPEC_KITTY_HOME`` to exercise the shared-store boundary."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    reset_journal_cache()
    reset_coalesce_strategy()
    yield
    reset_journal_cache()
    reset_coalesce_strategy()


def _stub_emitter(*, project_slug: str, build_id: str) -> EventEmitter:
    """A real ``EventEmitter`` with a stubbed identity/git resolver.

    Mirrors ``tests/delivery/test_envelope.py:65-74``'s ``_stub_emitter`` but
    with real, distinct project identities rather than the envelope test's
    ``None`` placeholders. Both instances share a local runtime root so the
    test proves the capture gate, not filesystem isolation, prevents leakage.
    """
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    em = EventEmitter()
    em._identity = SimpleNamespace(
        build_id=build_id, project_uuid=uuid4(), project_slug=project_slug
    )
    em._get_git_metadata = lambda: GitMetadata()
    return em


def _open_capture_gate(_team_slug: str | None) -> CaptureGateState:
    """Force one emitter instance's journal-capture gate fully open.

    Real-world equivalent: a checkout that IS SaaS-enabled, authenticated,
    and team-resolved — i.e. genuinely ready to ship, unlike its sibling
    checkout on the same machine. This is an instance-level override
    (mirrors the ``_get_git_metadata`` override above) rather than a further
    ``is_saas_sync_enabled`` patch, because every real capture gate
    (``EventEmitter._capture_gate_state``) is machine-global in the current
    implementation — see ``test_dispatch_honours_drain_blocked_3031.py`` — so
    there is no real per-process knob that would open the gate for one
    project's checkout and not the other's. Overriding it per-instance here
    keeps both events on the SAME producer-scoped journal (``get_journal`` is
    still keyed on ``team_slug=None`` for both, since ``is_saas_sync_enabled``
    stays patched ``False`` at module scope) while giving the two rows
    different ``drain_blocked_reason`` values, so the sibling #3031 file's
    "any drain_blocked_reason row must never ship" rule and this file's
    "the consenting event must ship" rule no longer collide (Defect (a) in
    the fold that produced this fixture).
    """
    return CaptureGateState(
        saas_enabled=True,
        checkout_enabled=True,
        authenticated=True,
        team_slug="team",
    )


def _closed_capture_gate(_team_slug: str | None) -> CaptureGateState:
    """Model an explicitly opted-out project's storage gate."""
    return CaptureGateState(
        saas_enabled=True,
        checkout_enabled=False,
        authenticated=True,
        team_slug="team",
    )


def test_opted_out_project_never_reaches_shared_journal_or_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An opted-out event cannot reach a consenting project's drain."""
    from specify_cli.sync import emitter as emitter_mod

    monkeypatch.setattr(emitter_mod, "is_saas_sync_enabled", lambda: False)
    consenting = _stub_emitter(
        project_slug="engagement-assistant",
        build_id="engagement-build-1",
    )
    consenting._capture_gate_state = _open_capture_gate
    nonconsenting = _stub_emitter(
        project_slug="client-confidential", build_id="confidential-build-1"
    )
    nonconsenting._capture_gate_state = _closed_capture_gate

    consenting_envelope = consenting._emit(
        event_type="ErrorLogged",
        aggregate_id="WP04",
        aggregate_type="WorkPackage",
        payload={"error_type": "runtime", "error_message": "boom", "wp_id": "WP04"},
    )
    nonconsenting_envelope = nonconsenting._emit(
        event_type="ErrorLogged",
        aggregate_id="WP04",
        aggregate_type="WorkPackage",
        payload={"error_type": "runtime", "error_message": "boom", "wp_id": "WP04"},
    )
    assert consenting_envelope is not None, "the consenting project's emit must succeed"
    assert nonconsenting_envelope is not None, (
        "an opted-out emit remains a local caller success; consent gates storage"
    )

    journal = get_journal(team_slug=None)
    rows_by_id = {event.event_id: event for event in journal.read_all()}
    assert set(rows_by_id) == {consenting_envelope["event_id"]}

    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = registry.register(
        url="https://hosted.example.com",
        team_slug="team",
        user_email="operator@example.com",
    )
    receiver = StubReceiver()

    dispatch(journal=journal, ledger=ledger, receiver=receiver, target=target)

    received_ids = set(receiver.received_event_ids())
    assert consenting_envelope["event_id"] in received_ids, (
        "the consenting project's event must still ship — this test is not "
        "about breaking a healthy consenting drain"
    )
    assert nonconsenting_envelope["event_id"] not in received_ids, (
        "an opted-out event must be absent from the journal before dispatch, "
        "even when a consenting project shares the same local runtime root"
    )
