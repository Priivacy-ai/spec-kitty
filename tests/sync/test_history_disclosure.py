"""WP03 acceptance tests for immutable sealed-history capabilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.sync.consent import allocate_capture_sequence, record_project_opt_in
from specify_cli.sync.history_disclosure import (
    HistoryDisclosureCapability,
    HistoryDisclosureError,
    confirm_history_disclosure,
    consume_history_disclosure,
    preview_sealed_history,
    preview_sealed_history_cohort,
)
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _runtime_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))


def _capture(store: ProjectSyncStore, entry_id: str, payload: str) -> None:
    with store.unit_of_work() as unit:
        assignment = allocate_capture_sequence(unit)
        unit.execute(
            "INSERT INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                entry_id,
                PROJECT_UUID,
                assignment.epoch_id,
                assignment.capture_sequence,
                payload,
            ),
        )


def _store_with_sealed_history() -> ProjectSyncStore:
    store = ProjectSyncStore(PROJECT_UUID)
    _capture(store, "old-1", '{"secret":"one"}')
    _capture(store, "old-2", '{"secret":"two"}')
    record_project_opt_in(PROJECT_UUID, actor="operator:alice")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, "
            "binding_audience) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                PROJECT_UUID,
                "https://app.spec-kitty.ai",
                "account-1",
                "teamspace-1",
                1,
                "admitted",
                "admission-1",
                "audience-1",
            ),
        )
    return store


def test_preview_is_stable_exact_and_does_not_create_authority() -> None:
    store = _store_with_sealed_history()

    first = preview_sealed_history(store)
    second = preview_sealed_history(store)

    assert first == second
    assert first.row_ids == ("old-1", "old-2")
    assert first.preview_count == 2
    assert len(first.preview_hash) == 64
    assert len(first.source_epoch_ids) == 1
    with store.unit_of_work() as unit:
        count = unit.execute("SELECT COUNT(*) FROM history_disclosure_actions").fetchone()
    assert count == (0,)


def test_confirmation_is_idempotent_and_consumption_revalidates_authority() -> None:
    store = _store_with_sealed_history()
    preview = preview_sealed_history(store)
    context = store.create_context()

    first = confirm_history_disclosure(
        store,
        preview,
        actor="operator:alice",
        idempotency_key="history-operation-1",
        context=context,
    )
    retry = confirm_history_disclosure(
        store,
        preview,
        actor="operator:alice",
        idempotency_key="history-operation-1",
        context=context,
    )
    consumed = consume_history_disclosure(
        store,
        action_id=first.action_id,
        context=context,
    )

    assert isinstance(consumed, HistoryDisclosureCapability)
    assert first == retry == consumed
    with pytest.raises(TypeError, match="explicit confirmation"):
        HistoryDisclosureCapability()


def test_filtered_preview_excludes_unrelated_sealed_epochs() -> None:
    store = _store_with_sealed_history()
    with store.unit_of_work() as unit:
        tail = unit.execute(
            "SELECT next_sequence FROM capture_sequences WHERE project_uuid = ?",
            (PROJECT_UUID,),
        ).fetchone()
        assert tail is not None
        next_sequence = int(tail[0]) + 1
        epoch = unit.execute("SELECT COALESCE(MAX(epoch_id), 0) FROM consent_epochs").fetchone()
        assert epoch is not None
        epoch_id = int(epoch[0]) + 1
        unit.execute(
            "INSERT INTO consent_epochs "
            "(epoch_id, project_uuid, opened_at_tail, state, consent_generation, "
            "sealed_at_tail, sealed_at, reason) "
            "VALUES (?, ?, ?, 'sealed', 1, ?, '2026-08-11T00:00:00Z', "
            "'history_import_confirmation')",
            (epoch_id, PROJECT_UUID, next_sequence - 1, next_sequence),
        )
        unit.execute(
            "INSERT INTO journal_entries "
            "(entry_id, project_uuid, epoch_id, capture_sequence, payload_json) "
            "VALUES ('import-1', ?, ?, ?, '{\"event_id\":\"import-1\"}')",
            (PROJECT_UUID, epoch_id, next_sequence),
        )
        unit.execute(
            "UPDATE capture_sequences SET next_sequence = ? WHERE project_uuid = ?",
            (next_sequence, PROJECT_UUID),
        )

    preview = preview_sealed_history_cohort(store, ("import-1",))

    assert preview.row_ids == ("import-1",)
    assert preview.source_epoch_ids == (epoch_id,)
    assert preview_sealed_history(store).row_ids == ("old-1", "old-2", "import-1")


def test_changed_or_terminal_cohort_cannot_be_resurrected() -> None:
    store = _store_with_sealed_history()
    preview = preview_sealed_history(store)
    context = store.create_context()
    capability = confirm_history_disclosure(
        store,
        preview,
        actor="operator:alice",
        idempotency_key="history-operation-1",
        context=context,
    )
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE journal_entries SET payload_json = ? WHERE entry_id = ?",
            ('{"secret":"changed"}', "old-1"),
        )

    with pytest.raises(HistoryDisclosureError, match="cohort changed"):
        consume_history_disclosure(
            store,
            action_id=capability.action_id,
            context=context,
        )


def test_stale_target_generation_fails_closed_with_preview_guidance() -> None:
    store = _store_with_sealed_history()
    preview = preview_sealed_history(store)
    context = store.create_context()
    capability = confirm_history_disclosure(
        store,
        preview,
        actor="operator:alice",
        idempotency_key="history-operation-1",
        context=context,
    )
    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE project_target_admissions SET configuration_generation = 2 WHERE project_uuid = ?",
            (PROJECT_UUID,),
        )

    with pytest.raises(HistoryDisclosureError, match="preview again"):
        consume_history_disclosure(
            store,
            action_id=capability.action_id,
            context=context,
        )
