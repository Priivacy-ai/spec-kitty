"""Per-project operator reporting at the UUID-owned physical-store boundary."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from specify_cli.delivery.status_report import build_per_project_store_report
from specify_cli.event_journal.journal import EventIdentityRow, EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.queue import LegacyQueueMigrationRequiredError, default_queue_db_path

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast, pytest.mark.usefixtures("canonical_home"),
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"
OTHER = "bbbbbbbb-0000-0000-0000-000000000002"


def _event(
    event_id: str,
    created_at: str,
    *,
    project_uuid: str | None = PROJECT,
    project_slug: str | None = "engagement-assistant",
    repo_slug: str | None = "Priivacy-ai/spec-kitty",
) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=project_uuid,
        project_slug=project_slug,
        repo_slug=repo_slug,
    )


# R1b (#3121): home isolation is provided by the canonical SPEC_KITTY_HOME owner
# (``canonical_home``) via the module-level ``usefixtures`` mark above, replacing a local ``_home``
# autouse fixture that pinned the identical ``tmp_path/"home"``.


@pytest.fixture
def store() -> ProjectSyncStore:
    value = ProjectSyncStore(PROJECT)
    authority = value.layout_generation()
    authority.begin_cutover("per-project-report-tests")
    authority.publish_project_only("per-project-report-tests", verify_exact=lambda: True)
    record_project_opt_in(PROJECT, actor="test")
    return value


@pytest.fixture
def journal(store: ProjectSyncStore) -> Iterator[EventJournal]:
    with store.unit_of_work() as unit:
        yield EventJournal(unit, store.layout_generation())


def _seed(journal: EventJournal, count: int = 14) -> None:
    for index in range(count):
        journal.append(_event(f"evt-{index:02d}", f"2026-07-01T00:00:{index:02d}Z"))


def test_sc004_report_names_every_project_with_count_age_and_consent(
    journal: EventJournal,
) -> None:
    _seed(journal, 7)
    result = build_per_project_store_report(journal)
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.project_uuid == PROJECT
    assert row.event_count == 7
    assert row.consent_granted is True
    assert row.oldest_created_at == "2026-07-01T00:00:00Z"


def test_the_report_reconciles_against_the_journals_retained_count(
    journal: EventJournal,
) -> None:
    _seed(journal)
    result = build_per_project_store_report(journal)
    assert result.retained_event_count == 14
    assert result.counted_event_total == 14
    assert result.reconciles is True


def test_identity_less_rows_are_counted_not_dropped(journal: EventJournal) -> None:
    with pytest.raises(ValueError, match="owner"):
        journal.append(_event("evt-anon", "2026-05-01T00:00:00Z", project_uuid=None))
    result = build_per_project_store_report(journal)
    assert result.unresolved_identity_count == 0
    assert result.reconciles is True


def test_non_consenting_projects_are_flagged_for_the_operator(
    store: ProjectSyncStore,
) -> None:
    record_project_opt_out(PROJECT, actor="test")
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        journal.append(_event("evt-refused", "2026-06-01T00:00:00Z"))
        result = build_per_project_store_report(journal)
    assert [row.project_uuid for row in result.named_non_consenting_rows] == [PROJECT]


def test_the_unresolved_identity_bucket_sorts_last(journal: EventJournal) -> None:
    _seed(journal, 2)
    result = build_per_project_store_report(journal)
    assert result.rows[-1].project_uuid == PROJECT
    assert not result.rows[-1].is_unresolved_identity


def test_report_distinguishes_which_consent_level_answered(
    journal: EventJournal,
) -> None:
    _seed(journal, 1)
    assert build_per_project_store_report(journal).rows[0].consent_level == "project_store"


def test_an_empty_journal_reconciles_trivially(journal: EventJournal) -> None:
    result = build_per_project_store_report(journal)
    assert result.rows == ()
    assert result.reconciles is True


def test_report_does_not_read_the_legacy_offline_queue(journal: EventJournal) -> None:
    _seed(journal, 3)
    with pytest.raises(LegacyQueueMigrationRequiredError):
        default_queue_db_path()
    result = build_per_project_store_report(journal)
    assert result.retained_event_count == 3
    assert result.reconciles is True


class _DisagreeingJournal:
    def __init__(self, rows: list[object], true_count: int) -> None:
        self._rows = rows
        self._true_count = true_count
        self.project_uuid = PROJECT

    def read_identity_projection_for_report(self) -> list[object]:
        return list(self._rows)

    def count(self) -> int:
        return self._true_count

    def owner_consent_projection(self) -> tuple[str, int]:
        return "granted", 1


def _identity_row(index: int) -> EventIdentityRow:
    return EventIdentityRow(
        event_id=f"evt-{index}",
        created_at=f"2026-07-01T00:00:0{index}Z",
        project_uuid=PROJECT,
        repo_slug=None,
        drain_blocked_reason=None,
    )


def test_reconciliation_fails_when_the_projection_omits_rows() -> None:
    report = build_per_project_store_report(_DisagreeingJournal([_identity_row(index) for index in range(3)], 10))
    assert report.counted_event_total == 3
    assert report.retained_event_count == 10
    assert report.reconciles is False


def test_reconciliation_holds_when_the_two_sources_agree() -> None:
    report = build_per_project_store_report(_DisagreeingJournal([_identity_row(0)], 1))
    assert report.reconciles is True


def test_the_report_carries_the_stored_project_slug(journal: EventJournal) -> None:
    journal.append(_event("evt-slugged", "2026-07-01T00:00:00Z"))
    row = build_per_project_store_report(journal).rows[0]
    assert row.project_slug == "engagement-assistant"
    assert row.repo_slug == "Priivacy-ai/spec-kitty"


def test_both_identity_projections_expose_the_project_slug(
    journal: EventJournal,
) -> None:
    journal.append(_event("evt-slugged", "2026-07-01T00:00:00Z"))
    (reported,) = journal.read_identity_projection_for_report()
    (drained,) = journal.read_identity_projection(project_uuids=[PROJECT])
    assert reported.project_slug == drained.project_slug == "engagement-assistant"


def test_a_restricted_report_groups_only_the_named_events(
    journal: EventJournal,
) -> None:
    _seed(journal, 5)
    result = build_per_project_store_report(journal, event_ids=["evt-01", "evt-03"])
    assert result.rows[0].event_count == 2
    assert result.retained_event_count == 2
    assert result.reconciles is True


def test_a_restricted_report_does_not_reconcile_when_a_named_event_is_missing(
    journal: EventJournal,
) -> None:
    _seed(journal, 1)
    result = build_per_project_store_report(journal, event_ids=["evt-00", "evt-never-landed"])
    assert result.counted_event_total == 1
    assert result.retained_event_count == 2
    assert result.reconciles is False


def test_the_unresolved_bucket_is_never_attributed_to_one_arbitrary_repo(
    journal: EventJournal,
) -> None:
    with pytest.raises(ValueError, match="owner"):
        journal.append(_event("evt-anon", "2026-07-01T00:00:00Z", project_uuid=None))
    assert build_per_project_store_report(journal).rows == ()


def test_the_unresolved_bucket_names_every_candidate_repo_with_its_count(
    journal: EventJournal,
) -> None:
    for index, repo in enumerate(("acme/app", "beta/svc")):
        with pytest.raises(ValueError, match="owner"):
            journal.append(
                _event(
                    f"evt-anon-{index}",
                    f"2026-07-01T00:00:0{index}Z",
                    project_uuid=None,
                    repo_slug=repo,
                )
            )
    assert build_per_project_store_report(journal).unresolved_identity_count == 0


def test_an_empty_project_uuid_is_identity_less_and_counted_exactly_once(
    journal: EventJournal,
) -> None:
    for value in (None, "", "   "):
        with pytest.raises(ValueError, match="owner"):
            journal.append(_event("evt-blank", "2026-05-01T00:00:00Z", project_uuid=value))
    assert journal.count() == 0


def test_a_resolved_project_carries_no_unresolved_candidates(
    journal: EventJournal,
) -> None:
    _seed(journal, 1)
    assert build_per_project_store_report(journal).rows[0].unresolved_candidates == ()


def test_candidates_split_on_project_slug_when_no_repo_slug_was_recorded(
    journal: EventJournal,
) -> None:
    journal.append(
        _event(
            "evt-slug-only",
            "2026-07-01T00:00:00Z",
            project_slug="acme-app",
            repo_slug=None,
        )
    )
    row = build_per_project_store_report(journal).rows[0]
    assert row.project_slug == "acme-app"
    assert row.repo_slug is None
    assert row.unresolved_candidates == ()


def test_no_candidate_ever_spans_two_distinct_recorded_names(
    journal: EventJournal,
) -> None:
    journal.append(_event("evt-a", "2026-07-01T00:00:00Z", project_slug="acme-app"))
    journal.append(_event("evt-b", "2026-07-01T00:00:01Z", project_slug="renamed-app"))
    row = build_per_project_store_report(journal).rows[0]
    assert row.project_uuid == PROJECT
    assert row.event_count == 2
    assert row.unresolved_candidates == ()
