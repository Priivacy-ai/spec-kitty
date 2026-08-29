"""WP03 acceptance tests for transactional capture sequences and epochs."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.sync.consent import (
    allocate_capture_sequence,
    record_project_opt_in,
    record_project_opt_out,
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


def _capture(store: ProjectSyncStore, entry_id: str) -> tuple[int, int]:
    with store.unit_of_work() as unit:
        assignment = allocate_capture_sequence(unit)
        unit.execute(
            "INSERT INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                entry_id,
                PROJECT_UUID,
                assignment.epoch_id,
                assignment.capture_sequence,
                f'{{"entry_id":"{entry_id}"}}',
            ),
        )
    return assignment.capture_sequence, assignment.epoch_id


def _row(store: ProjectSyncStore, entry_id: str) -> tuple[int, int, str]:
    with store.unit_of_work() as unit:
        row = unit.execute(
            "SELECT j.capture_sequence, j.epoch_id, e.state "
            "FROM journal_entries AS j JOIN consent_epochs AS e "
            "ON e.project_uuid = j.project_uuid AND e.epoch_id = j.epoch_id "
            "WHERE j.entry_id = ?",
            (entry_id,),
        ).fetchone()
    assert row is not None
    return int(row[0]), int(row[1]), str(row[2])


def test_capture_committed_before_opt_in_stays_at_or_below_the_sealed_tail() -> None:
    store = ProjectSyncStore(PROJECT_UUID)
    before_sequence, before_epoch = _capture(store, "before")

    grant = record_project_opt_in(PROJECT_UUID, actor="operator:alice")
    after_sequence, after_epoch = _capture(store, "after")

    assert before_sequence == grant.opened_at_tail
    assert after_sequence > grant.opened_at_tail
    assert before_epoch != after_epoch
    assert _row(store, "before")[2] == "sealed"
    assert _row(store, "after")[2] == "eligible"


def test_opt_in_committed_before_capture_assigns_only_the_new_eligible_epoch() -> None:
    store = ProjectSyncStore(PROJECT_UUID)
    grant = record_project_opt_in(PROJECT_UUID, actor="operator:alice")

    sequence, epoch = _capture(store, "after")

    assert grant.opened_at_tail == 0
    assert sequence == 1
    assert sequence > grant.opened_at_tail
    assert epoch == grant.epoch_id


def test_opt_out_seals_without_deleting_and_reopt_in_never_relabels() -> None:
    store = ProjectSyncStore(PROJECT_UUID)
    record_project_opt_in(PROJECT_UUID, actor="operator:alice")
    eligible_sequence, eligible_epoch = _capture(store, "eligible")

    refusal = record_project_opt_out(PROJECT_UUID, actor="operator:alice")
    refused_sequence, refused_epoch = _capture(store, "refused-period")
    regrant = record_project_opt_in(PROJECT_UUID, actor="operator:alice")
    regranted_sequence, regranted_epoch = _capture(store, "regranted")

    assert refusal.generation == 2
    assert regrant.generation == 3
    assert eligible_sequence < refused_sequence < regranted_sequence
    assert len({eligible_epoch, refused_epoch, regranted_epoch}) == 3
    assert _row(store, "eligible") == (eligible_sequence, eligible_epoch, "sealed")
    assert _row(store, "refused-period") == (
        refused_sequence,
        refused_epoch,
        "sealed",
    )
    assert _row(store, "regranted") == (
        regranted_sequence,
        regranted_epoch,
        "eligible",
    )
