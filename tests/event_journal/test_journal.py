"""Append-only journal store tests (WP03 / T013-T015, T019).

These assert observable on-disk state (NFR-001): distinct rows, idempotent
re-append, no normal-path delete, no delivery/target leakage, and the
default no-op coalescing seam. They never assert internal call ordering.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from specify_cli.event_journal import (
    CoalesceDecision,
    Event,
    EventJournal,
    event_to_params,
    register_coalesce_strategy,
    reset_coalesce_strategy,
    row_to_event,
)

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _reset_seam() -> None:
    """Reset the module-level coalesce strategy so a WP08-style registration
    in one test never leaks into another (T019 edge case)."""
    reset_coalesce_strategy()
    yield
    reset_coalesce_strategy()


@pytest.fixture()
def journal(tmp_path: Path) -> EventJournal:
    return EventJournal(tmp_path / "event_journal" / "journal-test.db")


def _event(event_id: str, *, payload: bytes = b"{}", reason: str | None = None) -> Event:
    return Event(
        event_id=event_id,
        event_type="WpStatusChanged",
        payload=payload,
        occurred_at="2026-06-29T00:00:00+00:00",
        created_at="2026-06-29T00:00:01+00:00",
        coalesce_key=None,
        archived_at=None,
        drain_blocked_reason=reason,
    )


def test_append_n_distinct_events_creates_n_distinct_rows(journal: EventJournal) -> None:
    for i in range(5):
        journal.append(_event(f"evt-{i}"))
    assert journal.count() == 5
    assert {e.event_id for e in journal.read_all()} == {f"evt-{i}" for i in range(5)}


def test_row_to_event_event_to_params_roundtrip_is_lossless() -> None:
    original = Event(
        event_id="evt-roundtrip",
        event_type="ErrorLogged",
        payload=b'{"x": 1}',
        occurred_at="2026-06-29T01:02:03+00:00",
        created_at="2026-06-29T01:02:04+00:00",
        coalesce_key="grp-1",
        archived_at=None,
        drain_blocked_reason="saas_disabled",
    )
    params = event_to_params(original)
    assert row_to_event(params) == original


def test_empty_payload_and_none_coalesce_key_roundtrip(journal: EventJournal) -> None:
    journal.append(_event("evt-empty", payload=b""))
    stored = journal.read_by_id("evt-empty")
    assert stored is not None
    assert stored.payload == b""
    assert stored.coalesce_key is None


def test_reappend_same_event_id_is_idempotent_and_does_not_mutate(journal: EventJournal) -> None:
    journal.append(_event("evt-dup", payload=b'{"v": 1}'))
    journal.append(_event("evt-dup", payload=b'{"v": 999}'))
    assert journal.count() == 1
    stored = journal.read_by_id("evt-dup")
    assert stored is not None
    assert stored.payload == b'{"v": 1}'  # original bytes preserved (no UPDATE)


def test_no_normal_path_delete_surface_exists() -> None:
    for forbidden in ("delete", "delete_all", "purge", "remove", "drop", "clear", "gc"):
        assert not hasattr(EventJournal, forbidden), f"FR-001: {forbidden} must not exist"


def test_mark_archived_sets_marker_without_removing_row(journal: EventJournal) -> None:
    journal.append(_event("evt-arch"))
    journal.mark_archived("evt-arch", "2026-06-29T02:00:00+00:00")
    assert journal.count() == 1  # row not removed
    stored = journal.read_by_id("evt-arch")
    assert stored is not None
    assert stored.archived_at == "2026-06-29T02:00:00+00:00"


def test_event_model_carries_no_target_or_delivery_field() -> None:
    names = {f.name for f in dataclasses.fields(Event)}
    forbidden = {
        "target",
        "server",
        "server_url",
        "resolved_server_url",
        "delivery",
        "delivery_state",
        "delivered",
        "queue_scope",
        "derived_queue_scope",
    }
    assert not (names & forbidden), "FR-003: journal model must not know delivery/target state"


def test_event_is_immutable() -> None:
    evt = _event("evt-frozen")
    with pytest.raises(dataclasses.FrozenInstanceError):
        evt.event_id = "mutated"  # type: ignore[misc]


def test_journal_module_imports_nothing_from_delivery() -> None:
    import specify_cli.event_journal.journal as journal_mod

    src = Path(journal_mod.__file__).read_text(encoding="utf-8")
    assert "from specify_cli.delivery" not in src
    assert "import specify_cli.delivery" not in src


def test_oldest_created_at_and_count(journal: EventJournal) -> None:
    assert journal.count() == 0
    assert journal.oldest_created_at() is None
    journal.append(
        dataclasses.replace(_event("evt-a"), created_at="2026-06-29T03:00:00+00:00")
    )
    journal.append(
        dataclasses.replace(_event("evt-b"), created_at="2026-06-29T01:00:00+00:00")
    )
    assert journal.count() == 2
    assert journal.oldest_created_at() == "2026-06-29T01:00:00+00:00"


def test_read_blocked_returns_only_rows_with_reason(journal: EventJournal) -> None:
    journal.append(_event("evt-ok", reason=None))
    journal.append(_event("evt-blocked", reason="saas_disabled"))
    blocked = journal.read_blocked()
    assert [e.event_id for e in blocked] == ["evt-blocked"]
    assert blocked[0].drain_blocked_reason == "saas_disabled"


def test_record_is_an_alias_for_append(journal: EventJournal) -> None:
    journal.record(_event("evt-record"))
    assert journal.count() == 1
    assert journal.read_by_id("evt-record") is not None


def test_db_path_property_returns_configured_path(tmp_path: Path) -> None:
    db_path = tmp_path / "event_journal" / "journal-x.db"
    assert EventJournal(db_path).db_path == db_path


def test_default_coalesce_seam_is_no_op_distinct_rows(journal: EventJournal) -> None:
    # No strategy registered: every distinct event is a distinct row (IC-02).
    journal.append(_event("evt-1"))
    journal.append(_event("evt-2"))
    assert journal.count() == 2


def test_registered_strategy_can_suppress_store_without_editing_journal(
    journal: EventJournal,
) -> None:
    def _drop_strategy(_journal: EventJournal, _event: Event) -> CoalesceDecision:
        return CoalesceDecision(store_as_new=False)

    register_coalesce_strategy(_drop_strategy)
    journal.append(_event("evt-suppressed"))
    assert journal.count() == 0  # strategy decided not to store a new row

    reset_coalesce_strategy()
    journal.append(_event("evt-after-reset"))
    assert journal.count() == 1  # default no-op resumed


def test_registered_strategy_that_raises_does_not_partially_write(
    journal: EventJournal,
) -> None:
    def _boom(_journal: EventJournal, _event: Event) -> CoalesceDecision:
        raise RuntimeError("strategy failure")

    register_coalesce_strategy(_boom)
    with pytest.raises(RuntimeError):
        journal.append(_event("evt-boom"))
    reset_coalesce_strategy()
    assert journal.count() == 0  # nothing was written
