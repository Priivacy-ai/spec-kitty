"""Retired shared-store migration remains fail-closed after project-store cutover.

These node names preserve the historical H4 regression inventory.  WP10 retired
``sync migrate`` because a shared journal and machine consent index can no longer
be live authority.  The replacement assertions prove the command cannot mutate a
canonical project store or promote a legacy grant; explicit project-owned consent
is the only positive path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from specify_cli.cli.commands.sync import app
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

runner = CliRunner()
CONSENTED = "aaaaaaaa-0000-0000-0000-00000000000a"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The census key (R1a #3121) pins this site as `str ( home )` resolving
    # to `<tmp_path>/home`.
    home = tmp_path / "home"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))


def _canonical_store(*, opt_in: bool = False) -> ProjectSyncStore:
    if opt_in:
        from specify_cli.sync.consent import record_project_opt_in

        record_project_opt_in(CONSENTED, actor="retired-sync-migrate-test")
    store = ProjectSyncStore(CONSENTED)
    authority = store.layout_generation()
    authority.begin_cutover("retired-sync-migrate-test")
    authority.publish_project_only("retired-sync-migrate-test", verify_exact=lambda: True)
    with store.unit_of_work():
        pass
    return store


def _seed_project_event(store: ProjectSyncStore, event_id: str = "evt-canonical") -> bytes:
    payload = b'{"event_id":"evt-canonical"}'
    with store.unit_of_work() as unit:
        EventJournal(unit, store.layout_generation()).append(
            Event(
                event_id=event_id,
                event_type="WorkPackageApproved",
                payload=payload,
                occurred_at="2026-06-01T00:00:00+00:00",
                created_at="2026-06-01T00:00:00+00:00",
                project_uuid=CONSENTED,
            )
        )
    return payload


def _stored_event(store: ProjectSyncStore, event_id: str = "evt-canonical") -> Event | None:
    with store.unit_of_work() as unit:
        return EventJournal(unit, store.layout_generation()).read_by_id(event_id)


def _retired(*extra: str) -> Result:
    return runner.invoke(app, ["migrate", *extra])


def _assert_retired(result: Result) -> None:
    assert result.exit_code == 1
    output = result.output
    assert "shared-store `sync migrate` path is retired" in output
    assert "project-store-preview" in output


def test_sync_migrate_backfills_identity_onto_pre_mission_rows() -> None:
    store = _canonical_store(opt_in=True)
    before = _seed_project_event(store)

    result = _retired()

    _assert_retired(result)
    after = _stored_event(store)
    assert after is not None
    assert after.project_uuid == CONSENTED
    assert after.payload == before


def test_sync_migrate_reports_what_the_identity_backfill_recovered() -> None:
    store = _canonical_store(opt_in=True)
    _seed_project_event(store)

    result = _retired()

    _assert_retired(result)
    assert "project-store-migrate" in result.output


def test_sync_migrate_identity_backfill_is_idempotent() -> None:
    store = _canonical_store(opt_in=True)
    before = _seed_project_event(store)

    first = _retired()
    second = _retired()

    _assert_retired(first)
    _assert_retired(second)
    after = _stored_event(store)
    assert after is not None and after.payload == before


def test_sync_migrate_leaves_a_genuinely_unresolvable_row_null() -> None:
    store = _canonical_store()
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        with pytest.raises(ValueError, match="project UUID"):
            journal.append(
                Event(
                    event_id="evt-opaque",
                    event_type="WorkPackageApproved",
                    payload=b"not json at all",
                    occurred_at="2026-06-01T00:00:00+00:00",
                    created_at="2026-06-01T00:00:00+00:00",
                    project_uuid=None,
                )
            )

    _assert_retired(_retired())
    assert _stored_event(store, "evt-opaque") is None


def test_plain_migrate_never_writes_the_consent_index(tmp_path: Path) -> None:
    from specify_cli.sync.consent import ConsentAuthorityStatus, read_project_consent_decision

    _canonical_store()
    before = read_project_consent_decision(CONSENTED)
    assert before.status is ConsentAuthorityStatus.ABSENT

    _assert_retired(_retired())

    assert read_project_consent_decision(CONSENTED) == before


def test_migrate_with_the_flag_maps_path_keyed_consent_onto_the_uuid_index(
    tmp_path: Path,
) -> None:
    from specify_cli.sync.consent import record_project_opt_in, resolve_project_consent

    _canonical_store()
    _assert_retired(_retired("--backfill-consent-index"))
    assert resolve_project_consent(CONSENTED).granted is False

    record_project_opt_in(CONSENTED, actor="retired-sync-migrate-test")
    assert resolve_project_consent(CONSENTED).granted is True


def test_the_consent_backfill_reports_records_it_could_not_resolve(
    tmp_path: Path,
) -> None:
    from specify_cli.sync.consent import ConsentAuthorityStatus, read_project_consent_decision

    _canonical_store()
    result = _retired("--backfill-consent-index")

    _assert_retired(result)
    assert read_project_consent_decision(CONSENTED).status is ConsentAuthorityStatus.ABSENT


def test_the_consent_backfill_is_idempotent(tmp_path: Path) -> None:
    _canonical_store()

    first = _retired("--backfill-consent-index")
    second = _retired("--backfill-consent-index")

    _assert_retired(first)
    _assert_retired(second)
    assert first.output == second.output


def test_an_opted_out_path_record_maps_as_a_refusal(tmp_path: Path) -> None:
    from specify_cli.sync.consent import (
        ConsentAuthorityStatus,
        import_legacy_refusal,
        read_project_consent_decision,
        resolve_project_consent,
    )

    _canonical_store()
    import_legacy_refusal(CONSENTED, actor="retired-sync-migrate-test")
    before = resolve_project_consent(CONSENTED)
    assert before.granted is False
    assert read_project_consent_decision(CONSENTED).status is ConsentAuthorityStatus.REFUSED

    _assert_retired(_retired("--backfill-consent-index"))

    after = resolve_project_consent(CONSENTED)
    assert after == before
