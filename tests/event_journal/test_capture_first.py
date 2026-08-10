"""Capture-first durability tests (WP03 / T016-T019, contract §2 + SC-009).

Observable acceptance (NFR-001): with sync disabled or missing auth/team, a
Teamspace-bound fact is durably journaled with a ``drain_blocked_reason`` and
no delivery is attempted. We assert the *result* (a row exists even though the
gate blocked), never the internal call order.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.event_journal import (
    DRAIN_BLOCKED_MISSING_AUTH,
    DRAIN_BLOCKED_MISSING_TEAM,
    DRAIN_BLOCKED_REASONS,
    DRAIN_BLOCKED_SAAS_DISABLED,
    CaptureGateState,
    EventJournal,
    TeamspaceBoundDropError,
    capture_teamspace_bound,
    classify_drain_blocked_reason,
    get_journal,
    reset_coalesce_strategy,
    reset_journal_cache,
    resolve_journal_path,
)
from specify_cli.sync.project_store import ProjectSyncStore

pytestmark = pytest.mark.fast

PROJECT = "cccccccc-0000-0000-0000-00000000000c"


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("capture-first-tests")
    authority.publish_project_only("capture-first-tests", verify_exact=lambda: True)


@pytest.fixture(autouse=True)
def _isolated_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    reset_journal_cache()
    reset_coalesce_strategy()
    yield
    reset_journal_cache()
    reset_coalesce_strategy()


@pytest.fixture()
def journal(tmp_path: Path) -> Iterator[EventJournal]:
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    with store.unit_of_work() as unit:
        yield EventJournal(unit, store.layout_generation())


def _gate(
    *,
    saas: bool = True,
    checkout: bool = True,
    auth: bool = True,
    team: str | None = "team-x",
) -> CaptureGateState:
    return CaptureGateState(
        saas_enabled=saas, checkout_enabled=checkout, authenticated=auth, team_slug=team
    )


# ── classify_drain_blocked_reason (gate → journal reason) ──────────────


def test_classify_saas_disabled_takes_precedence() -> None:
    assert classify_drain_blocked_reason(_gate(saas=False, auth=False, team=None)) == (
        DRAIN_BLOCKED_SAAS_DISABLED
    )
    assert classify_drain_blocked_reason(_gate(checkout=False)) == DRAIN_BLOCKED_SAAS_DISABLED


def test_classify_missing_auth_then_missing_team() -> None:
    assert classify_drain_blocked_reason(_gate(auth=False)) == DRAIN_BLOCKED_MISSING_AUTH
    assert classify_drain_blocked_reason(_gate(team=None)) == DRAIN_BLOCKED_MISSING_TEAM


def test_classify_all_gates_open_is_none() -> None:
    assert classify_drain_blocked_reason(_gate()) is None


def test_reason_vocabulary_is_closed() -> None:
    for reason in (DRAIN_BLOCKED_SAAS_DISABLED, DRAIN_BLOCKED_MISSING_AUTH, DRAIN_BLOCKED_MISSING_TEAM):
        assert reason in DRAIN_BLOCKED_REASONS


# ── capture_teamspace_bound (contract §2 required scenarios) ──────────


def test_disabled_sync_keeps_event_durable_with_reason(journal: EventJournal) -> None:
    event = capture_teamspace_bound(
        journal=journal,
        event_id="evt-disabled",
        event_type="WpStatusChanged",
        payload=b'{"wp": "WP01"}',
        occurred_at="2026-06-29T00:00:00+00:00",
        gate=_gate(saas=False, auth=False, team=None),
        project_uuid=PROJECT,
    )
    assert event.drain_blocked_reason == DRAIN_BLOCKED_SAAS_DISABLED
    stored = journal.read_by_id("evt-disabled")
    assert stored is not None
    assert stored.payload == b'{"wp": "WP01"}'
    assert stored.drain_blocked_reason == DRAIN_BLOCKED_SAAS_DISABLED


def test_missing_auth_and_team_keeps_event_durable_with_diagnostics(
    journal: EventJournal,
) -> None:
    capture_teamspace_bound(
        journal=journal,
        event_id="evt-noauth",
        event_type="WpStatusChanged",
        payload=b"{}",
        occurred_at="2026-06-29T00:00:00+00:00",
        gate=_gate(auth=False, team=None),
        project_uuid=PROJECT,
    )
    blocked = journal.read_blocked()
    assert [e.event_id for e in blocked] == ["evt-noauth"]
    assert blocked[0].drain_blocked_reason == DRAIN_BLOCKED_MISSING_AUTH


def test_capture_produces_distinct_rows_even_when_blocked(journal: EventJournal) -> None:
    for i in range(4):
        capture_teamspace_bound(
            journal=journal,
            event_id=f"evt-{i}",
            event_type="WpStatusChanged",
            payload=b"{}",
            occurred_at="2026-06-29T00:00:00+00:00",
            gate=_gate(saas=False),
            project_uuid=PROJECT,
        )
    assert journal.count() == 4  # no coalescing


def test_teamspace_bound_family_cannot_be_silently_dropped(journal: EventJournal) -> None:
    with pytest.raises(TeamspaceBoundDropError):
        capture_teamspace_bound(
            journal=journal,
            event_id="evt-dropped",
            event_type="WpStatusChanged",
            payload=b"{}",
            occurred_at="2026-06-29T00:00:00+00:00",
            gate=_gate(),
            is_teamspace_bound=True,
            skip_journal=True,
            project_uuid=PROJECT,
        )
    assert journal.count() == 0  # guard fired before any write


# ── producer-scoped path (never server-scoped) ───────────────────────


def test_legacy_journal_path_is_named_input_not_a_live_scope(tmp_path: Path) -> None:
    authed = resolve_journal_path(user_id="dev@example.com", team_slug="team-x")
    anon = resolve_journal_path()
    assert authed == anon
    assert str(tmp_path) in str(authed)
    assert "event_journal" in authed.parts
    # The retained helper names one WP10 migration input; user/team/server
    # attributes can no longer select a live payload store.
    assert "fly.dev" not in str(authed)
    assert "https" not in str(authed)
    assert anon.name == "journal-local.db"


# ── live emit-path integration (capture-first is actually wired) ─────


def test_live_factory_requires_explicit_store_capabilities(
    tmp_path: Path,
    journal: EventJournal,
) -> None:
    del tmp_path
    with pytest.raises(TypeError):
        get_journal()
    assert journal.project_uuid == PROJECT


def test_disabled_capture_keeps_each_fact_distinct(journal: EventJournal) -> None:
    for i in range(3):
        capture_teamspace_bound(
            journal=journal,
            event_id=f"emit-{i}",
            event_type="WpStatusChanged",
            payload=f'{{"i":{i}}}'.encode(),
            occurred_at="2026-06-29T00:00:00+00:00",
            gate=_gate(saas=False),
            project_uuid=PROJECT,
        )

    rows = journal.read_all()
    assert len(rows) == 3
    assert len({row.event_id for row in rows}) == 3
    assert all(row.drain_blocked_reason == DRAIN_BLOCKED_SAAS_DISABLED for row in rows)
