"""T021/SC-004 + T020/NFR-007: operator visibility (#3030 WP07).

`sync doctor` read **healthy** throughout the 2026-07-27 incident. Its queue-health
block reads `OfflineQueue().get_queue_stats()`, which is empty after `sync migrate`,
so the operator saw "Queue size 0" while 9,133 events sat in the journal — 1,322 of
them belonging to projects that had never opted in. A fix the operator cannot verify
is not a fix, and a report rendered from the wrong store reproduces the same
false-green.

So the load-bearing assertion here is **reconciliation**: the per-project totals must
account for every retained journal row. A report that silently omits rows is the
incident's failure mode wearing a new table.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.delivery.status_report import build_per_project_store_report
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event

pytestmark = [pytest.mark.fast]

CONSENTED = "aaaaaaaa-0000-0000-0000-000000000001"
SILENT = "bbbbbbbb-0000-0000-0000-000000000002"
OPTED_OUT = "cccccccc-0000-0000-0000-000000000003"


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(CONSENTED, True)
    set_project_consent(OPTED_OUT, False)
    # SILENT deliberately gets no record — absence, not refusal.


def _event(
    event_id: str,
    uuid: str | None,
    created_at: str,
    *,
    project_slug: str | None = None,
    repo_slug: str | None = None,
) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
        project_slug=project_slug,
        repo_slug=repo_slug,
    )


def _seeded_journal(tmp_path: Path) -> EventJournal:
    journal = EventJournal(tmp_path / "journal.db")
    for i in range(7):
        journal.append(_event(f"evt-ok-{i}", CONSENTED, f"2026-07-01T00:00:0{i}Z"))
    for i in range(4):
        journal.append(_event(f"evt-silent-{i}", SILENT, f"2026-06-01T00:00:0{i}Z"))
    for i in range(2):
        journal.append(_event(f"evt-out-{i}", OPTED_OUT, f"2026-06-15T00:00:0{i}Z"))
    journal.append(_event("evt-anon-0", None, "2026-05-01T00:00:00Z"))
    return journal


def test_sc004_report_names_every_project_with_count_age_and_consent(
    tmp_path: Path,
) -> None:
    report = _seeded_journal(tmp_path)
    result = build_per_project_store_report(report)

    by_uuid = {row.project_uuid: row for row in result.rows}
    assert set(by_uuid) == {CONSENTED, SILENT, OPTED_OUT, None}

    assert by_uuid[CONSENTED].event_count == 7
    assert by_uuid[CONSENTED].consent_granted is True
    assert by_uuid[CONSENTED].oldest_created_at == "2026-07-01T00:00:00Z"

    assert by_uuid[SILENT].event_count == 4
    assert by_uuid[SILENT].consent_granted is False, "absence of a record is not consent"

    assert by_uuid[OPTED_OUT].event_count == 2
    assert by_uuid[OPTED_OUT].consent_granted is False


def test_the_report_reconciles_against_the_journals_retained_count(
    tmp_path: Path,
) -> None:
    """FR-015's load-bearing property — no row may go uncounted.

    The incident's false-green was a report that rendered from a store holding
    nothing. A per-project table that omits rows is the same failure with a nicer
    layout, so reconciliation is asserted rather than assumed.
    """
    journal = _seeded_journal(tmp_path)

    result = build_per_project_store_report(journal)

    assert result.retained_event_count == 14
    assert result.counted_event_total == 14
    assert result.reconciles is True


def test_identity_less_rows_are_counted_not_dropped(tmp_path: Path) -> None:
    """FR-011: fail-closed denial must be observable, not silent data loss."""
    journal = _seeded_journal(tmp_path)

    result = build_per_project_store_report(journal)

    assert result.unresolved_identity_count == 1
    anon = next(row for row in result.rows if row.is_unresolved_identity)
    assert anon.event_count == 1
    assert anon.consent_granted is False
    assert "unselectable" in anon.consent_reason


def test_non_consenting_projects_are_flagged_for_the_operator(tmp_path: Path) -> None:
    """Only projects KNOWN to have withheld consent may be named as such.

    This asserted ``{SILENT, OPTED_OUT, None}`` before N1 — it included the
    unresolved-identity bucket, which is how the CLI came to name one of that
    bucket's member repos as a project that had refused. The bucket is still
    reported, and asserted below to be: it is a row of the report, it counts toward
    ``unresolved_identity_count``, and it never reads as consented. What it is not
    is a NAMED refusal, because with no uuid there was no decision to read.
    """
    journal = _seeded_journal(tmp_path)
    result = build_per_project_store_report(journal)

    named = {row.project_uuid for row in result.named_non_consenting_rows}
    assert named == {SILENT, OPTED_OUT}

    # The bucket is not dropped by that exclusion — it is surfaced its own way.
    bucket = next(row for row in result.rows if row.is_unresolved_identity)
    assert bucket.consent_granted is False, "it must never read as consented"
    assert result.unresolved_identity_count == 1


def test_the_unresolved_identity_bucket_sorts_last(tmp_path: Path) -> None:
    """It must not hide at the top of a long table."""
    journal = _seeded_journal(tmp_path)
    result = build_per_project_store_report(journal)
    assert result.rows[-1].is_unresolved_identity


def test_report_distinguishes_which_consent_level_answered(tmp_path: Path) -> None:
    """Without this an operator cannot tell a project-local grant from a stale cache."""
    journal = _seeded_journal(tmp_path)
    result = build_per_project_store_report(journal)

    by_uuid = {row.project_uuid: row for row in result.rows}
    assert by_uuid[CONSENTED].consent_level == "machine_index"
    assert by_uuid[SILENT].consent_level == "absent"
    assert by_uuid[None].consent_level == "unresolved_identity"


def test_an_empty_journal_reconciles_trivially(tmp_path: Path) -> None:
    result = build_per_project_store_report(EventJournal(tmp_path / "empty.db"))
    assert result.rows == ()
    assert result.reconciles is True


# --- FR-015 / #3004: the report must not read the retired store --------------


def test_report_does_not_read_the_legacy_offline_queue(tmp_path: Path) -> None:
    """The incident's false-green, pinned.

    `OfflineQueue().get_queue_stats()` is empty after `sync migrate`. If the
    per-project report ever reads it, a contaminated store shows as healthy again.
    This asserts the report is built purely from the journal by proving it still
    reports correctly when the legacy queue is untouched and empty.

    NOT T020/NFR-007, despite an earlier revision of this file labelling it so.
    NFR-007 is about the live dispatch window (`_EVENT_SYNC_DISPATCH_BATCH_LIMIT`
    in `_run_dispatch_batches`) and a recording ingress, neither of which this
    test touches: `build_per_project_store_report` takes a journal and holds no
    `OfflineQueue` reference at all, which makes the `legacy.size() == 0` line
    below a precondition, not the property. T020 lives in
    tests/delivery/test_dispatch_window_consent_3030.py.
    """
    journal = _seeded_journal(tmp_path)

    from specify_cli.sync.queue import OfflineQueue

    legacy = OfflineQueue()
    assert legacy.size() == 0, "precondition: the legacy queue is empty"

    result = build_per_project_store_report(journal)

    assert result.retained_event_count == 14, (
        "the report must derive from the journal, not the retired queue — an "
        "empty legacy queue must never make a contaminated journal look healthy"
    )
    # Two named refusals plus the unresolved bucket — three populations the
    # contaminated store holds, none of them dropped by the N1 split.
    assert len(result.named_non_consenting_rows) == 2
    assert result.unresolved_identity_count == 1
    # ...and the bucket is a ROW, asserted from `rows` itself. The line above is
    # derived from the projection (`unselectable_identity_count`), so it survives a
    # report that drops the bucket from `rows` entirely — which means the pair alone
    # cannot support the "none of them dropped" claim this comment makes. The
    # retired `len(non_consenting_rows) == 3` did catch that; this restores it.
    assert sum(1 for row in result.rows if row.is_unresolved_identity) == 1
    assert result.reconciles, "a dropped bucket must also break reconciliation"


# --- F2: reconciliation must be falsifiable ---------------------------------


class _DisagreeingJournal:
    """A journal whose projection read omits rows that ``count()`` still sees.

    This is the failure FR-015 exists to catch and the one the report's own
    reconciliation was blind to: the *read* returning the wrong universe. The
    first implementation derived both sides of the comparison from the single
    projection read, making ``reconciles`` a mathematical identity that no input
    could falsify — the incident's false-green with a nicer layout.

    Concretely this models a projection that silently drops rows (a stale
    prepared statement, a WHERE clause added to the projection SQL, a partially
    written column) while the table still holds them.
    """

    def __init__(self, rows: list[object], true_count: int) -> None:
        self._rows = rows
        self._true_count = true_count

    def read_identity_projection_for_report(self) -> list[object]:
        return list(self._rows)

    def count(self) -> int:
        return self._true_count


def test_reconciliation_fails_when_the_projection_omits_rows() -> None:
    """The report must NOT reconcile when its read disagrees with the journal.

    Red before the fix: both operands were computed from the projection, so this
    returned True with 3 rows reported against 10 actually stored.
    """
    from specify_cli.event_journal.journal import EventIdentityRow

    rows = [
        EventIdentityRow(
            event_id=f"evt-{i}",
            created_at=f"2026-07-01T00:00:0{i}Z",
            project_uuid=CONSENTED,
            repo_slug=None,
            drain_blocked_reason=None,
        )
        for i in range(3)
    ]
    journal = _DisagreeingJournal(rows, true_count=10)

    report = build_per_project_store_report(journal)

    assert report.counted_event_total == 3
    assert report.retained_event_count == 10, (
        "retained count must come from an INDEPENDENT source, not from the "
        "projection the report was built from"
    )
    assert report.reconciles is False, (
        "a report that accounts for 3 of 10 stored events must not claim to "
        "reconcile — this is exactly the omission FR-015 exists to surface"
    )


def test_reconciliation_holds_when_the_two_sources_agree() -> None:
    """The negative case, so the check is not merely always-False either."""
    from specify_cli.event_journal.journal import EventIdentityRow

    rows = [
        EventIdentityRow(
            event_id="evt-0",
            created_at="2026-07-01T00:00:00Z",
            project_uuid=CONSENTED,
            repo_slug=None,
            drain_blocked_reason=None,
        )
    ]
    report = build_per_project_store_report(_DisagreeingJournal(rows, true_count=1))
    assert report.reconciles is True


# --- F7: project_slug must be real data, not a hardcoded None ---------------


def test_the_report_carries_the_stored_project_slug(tmp_path: Path) -> None:
    """A declared field that is always ``None`` is a lie the caller cannot detect.

    Red before the fix: ``ProjectStoreRow.project_slug`` was declared, hardcoded
    ``project_slug=None`` at construction, and ``SELECT_IDENTITY_PROJECTION_SQL``
    did not select the column — so the field existed purely as documentation of
    an intention.
    """
    journal = EventJournal(tmp_path / "slugged.db")
    journal.append(
        _event(
            "evt-slugged",
            CONSENTED,
            "2026-07-01T00:00:00+00:00",
            project_slug="engagement-assistant",
            repo_slug="my-org/engagement-assistant",
        )
    )

    result = build_per_project_store_report(journal)

    row = next(r for r in result.rows if r.project_uuid == CONSENTED)
    assert row.project_slug == "engagement-assistant"
    assert row.repo_slug == "my-org/engagement-assistant"


def test_both_identity_projections_expose_the_project_slug(tmp_path: Path) -> None:
    """The projection is the only seam that can populate the field above.

    Asserted on BOTH reads. There are two since #3030 split them: the drain's
    ``read_identity_projection`` takes a mandatory uuid filter so it cannot scan
    (NFR-003), and ``read_identity_projection_for_report`` is unfiltered because
    FR-015/SC-004 must name projects that are not known to consent and must surface
    NULL-identity rows. They share ``_IDENTITY_PROJECTION_COLUMNS``, and this pins
    that they keep sharing it — a column added to one and not the other is how the
    report would start reporting a project as nameless again (N1-a).
    """
    journal = EventJournal(tmp_path / "projection.db")
    journal.append(
        _event(
            "evt-slugged",
            CONSENTED,
            "2026-07-01T00:00:00+00:00",
            project_slug="engagement-assistant",
        )
    )

    (reported,) = journal.read_identity_projection_for_report()
    assert reported.project_slug == "engagement-assistant"

    (drained,) = journal.read_identity_projection(project_uuids=[CONSENTED])
    assert drained.project_slug == "engagement-assistant"


# --- FR-015 on `sync migrate`: the composition of what it MOVED -------------


def test_a_restricted_report_groups_only_the_named_events(tmp_path: Path) -> None:
    """`sync migrate` must report what IT moved, not the whole journal.

    A migration that imported 2 rows into a journal already holding 14 would
    otherwise report all 14 as "moved", which is a different (and false) claim.
    """
    journal = _seeded_journal(tmp_path)

    result = build_per_project_store_report(
        journal, event_ids=["evt-silent-0", "evt-silent-1", "evt-out-0"]
    )

    by_uuid = {row.project_uuid: row for row in result.rows}
    assert set(by_uuid) == {SILENT, OPTED_OUT}
    assert by_uuid[SILENT].event_count == 2
    assert by_uuid[OPTED_OUT].event_count == 1
    assert result.reconciles is True


def test_a_restricted_report_does_not_reconcile_when_a_named_event_is_missing(
    tmp_path: Path,
) -> None:
    """The falsifiable half: the caller's tally is the independent operand.

    A migration that claims to have imported an event the journal cannot show is
    exactly the "reported success, row never landed" failure the reconciliation
    exists to surface. The operands stay independent here too — the requested id
    count comes from the caller, the rows from the journal's own read.
    """
    journal = _seeded_journal(tmp_path)

    result = build_per_project_store_report(
        journal, event_ids=["evt-silent-0", "evt-never-landed"]
    )

    assert result.counted_event_total == 1
    assert result.retained_event_count == 2
    assert result.reconciles is False


# --- N1: the unresolved bucket spans projects and must not be attributed to one --


def test_the_unresolved_bucket_is_never_attributed_to_one_arbitrary_repo(
    tmp_path: Path,
) -> None:
    """Identity-less rows from three repos must not be reported as one named repo.

    Red before the fix: the bucket took ``next((r.repo_slug for r in group ...))``,
    so it carried ``acme/app`` — whichever row happened to sort first — and
    ``non_consenting_rows`` then had the CLI tell the operator that ``acme/app``
    refused consent and should be purged. Purging it leaves ``beta/svc`` and
    ``gamma/tool`` on disk, unnamed, while the report reads clean: the 2026-07-27
    false-green rebuilt inside the fix for it.

    Reachable in production: ``emitter.py`` resolves ``project_uuid`` and
    ``repo_slug`` independently and gates capture on ``checkout_enabled``, not on
    uuid resolvability, so a consenting checkout whose uuid resolution fails writes
    exactly this row.
    """
    journal = EventJournal(tmp_path / "unresolved-multi.db")
    for index, (slug, repo) in enumerate(
        (
            ("acme-app", "acme/app"),
            ("beta-svc", "beta/svc"),
            ("gamma-tool", "gamma/tool"),
        )
    ):
        journal.append(
            _event(
                f"evt-anon-{index}",
                None,
                f"2026-07-01T00:00:0{index}+00:00",
                project_slug=slug,
                repo_slug=repo,
            )
        )

    result = build_per_project_store_report(journal)

    (bucket,) = result.rows
    assert bucket.is_unresolved_identity
    assert bucket.event_count == 3
    # The lie at its source: the bucket must claim NO single identity, because it
    # does not have one.
    assert bucket.repo_slug is None, "the bucket must not adopt one member's repo slug"
    assert bucket.project_slug is None

    # And it is not a project that refused consent — its consent is UNRESOLVABLE,
    # which is a different fact with a different remedy.
    assert result.named_non_consenting_rows == ()


def test_the_unresolved_bucket_names_every_candidate_repo_with_its_count(
    tmp_path: Path,
) -> None:
    """SC-004 for this population: zero hand-written SQL to answer "whose data?".

    The slugs are already on the rows and already in the identity projection, so
    an operator having to open SQLite to find out which repos the unresolved rows
    came from is exactly the gap SC-004 forbids.
    """
    journal = EventJournal(tmp_path / "unresolved-counts.db")
    seeds = (
        ("acme-app", "acme/app"),
        ("acme-app", "acme/app"),
        ("beta-svc", "beta/svc"),
        (None, None),
    )
    for index, (slug, repo) in enumerate(seeds):
        journal.append(
            _event(
                f"evt-anon-{index}",
                None,
                f"2026-07-01T00:00:0{index}+00:00",
                project_slug=slug,
                repo_slug=repo,
            )
        )

    (bucket,) = build_per_project_store_report(journal).rows

    by_label = {c.repo_slug: c for c in bucket.unresolved_candidates}
    assert set(by_label) == {"acme/app", "beta/svc", None}
    assert by_label["acme/app"].event_count == 2
    assert by_label["beta/svc"].event_count == 1
    # Rows carrying no slug at all are their own candidate rather than being
    # dropped or folded into a named one — they genuinely cannot be attributed.
    assert by_label[None].event_count == 1
    assert by_label[None].project_slug is None

    # Counts reconcile with the bucket, so the breakdown cannot hide a row.
    assert sum(c.event_count for c in bucket.unresolved_candidates) == bucket.event_count
    assert by_label["acme/app"].project_slug == "acme-app"
    assert by_label["acme/app"].oldest_created_at == "2026-07-01T00:00:00+00:00"


def test_a_resolved_project_carries_no_unresolved_candidates(tmp_path: Path) -> None:
    """The field is meaningful only for the bucket; a named project has one identity."""
    journal = _seeded_journal(tmp_path)
    result = build_per_project_store_report(journal)

    for row in result.rows:
        if row.is_unresolved_identity:
            continue
        assert row.unresolved_candidates == ()


# --- N1-a / N1-b: a recorded name must never be dropped or merged -------------


def test_candidates_split_on_project_slug_when_no_repo_slug_was_recorded(
    tmp_path: Path,
) -> None:
    """N1-a/N1-b: ``repo_slug`` null does not mean nameless.

    The three identity columns are resolved INDEPENDENTLY at capture:
    ``project_slug`` walks a three-path chain over the envelope and the payload,
    while ``repo_slug`` is a single top-level ``.get()``. A nil-sentinel uuid also
    normalises to ``None`` while the slug resolves fine. So
    ``(uuid=None, project_slug='acme-app', repo_slug=None)`` is a production row,
    not a contrivance.

    Red before the fix, twice over:

    * N1-a — candidates were keyed on ``repo_slug`` alone, so every such row
      collapsed into the ``None`` key and rendered as ``<no repo recorded>``, with
      the name sitting unread in the adjacent column.
    * N1-b — that single candidate then took
      ``next((r.project_slug for r in rows if r.project_slug), None)``, publishing
      ``project_slug='acme-app'`` for a group spanning ``acme-app`` AND
      ``beta-svc``. Structurally the same first-found attribution N1 rejected one
      level up, and the count sum-check cannot see it: 3 == 3 reconciles while two
      distinct names are merged.
    """
    journal = EventJournal(tmp_path / "slug-only.db")
    for index, slug in enumerate(("acme-app", "acme-app", "beta-svc")):
        journal.append(
            _event(
                f"evt-anon-{index}",
                None,
                f"2026-07-01T00:00:0{index}+00:00",
                project_slug=slug,
                repo_slug=None,
            )
        )

    (bucket,) = build_per_project_store_report(journal).rows

    by_slug = {c.project_slug: c for c in bucket.unresolved_candidates}
    assert set(by_slug) == {"acme-app", "beta-svc"}, (
        "both recorded names must survive as their own candidate; neither may be "
        "merged into the other nor collapsed into an unnamed bucket"
    )
    assert by_slug["acme-app"].event_count == 2
    assert by_slug["beta-svc"].event_count == 1
    # Nothing here is genuinely nameless, so no candidate may claim to be.
    assert all(c.repo_slug is None for c in bucket.unresolved_candidates)
    assert sum(c.event_count for c in bucket.unresolved_candidates) == 3


def test_no_candidate_ever_spans_two_distinct_recorded_names(tmp_path: Path) -> None:
    """The invariant, over a population mixing every combination of the two columns.

    ``status_report`` states the governing rule for a resolved group — "a
    disagreement among them is not a licence to invent a third value" — and it
    binds the candidate breakdown just as hard. A candidate is a *recorded
    identity*, so two rows may share one only if they agree on both columns.

    The count sum-check does not imply this: merging two names keeps the totals
    reconciled. This asserts the names directly.
    """
    journal = EventJournal(tmp_path / "mixed-identity.db")
    population = (
        ("acme-app", "acme/app"),
        ("acme-app", "acme/app"),
        ("acme-app", None),  # same project name, no repo recorded
        ("beta-svc", None),
        (None, "gamma/tool"),  # repo recorded, no project name
        (None, None),  # genuinely nameless
    )
    for index, (slug, repo) in enumerate(population):
        journal.append(
            _event(
                f"evt-anon-{index}",
                None,
                f"2026-07-01T00:00:0{index}+00:00",
                project_slug=slug,
                repo_slug=repo,
            )
        )

    (bucket,) = build_per_project_store_report(journal).rows
    candidates = bucket.unresolved_candidates

    identities = [(c.repo_slug, c.project_slug) for c in candidates]
    assert len(identities) == len(set(identities)), "candidates must be distinct"
    assert set(identities) == {
        ("acme/app", "acme-app"),
        (None, "acme-app"),
        (None, "beta-svc"),
        ("gamma/tool", None),
        (None, None),
    }
    assert next(c for c in candidates if c.repo_slug == "acme/app").event_count == 2
    # Every row accounted for, and exactly one genuinely-nameless candidate.
    assert sum(c.event_count for c in candidates) == bucket.event_count == 6
    nameless = [c for c in candidates if not c.repo_slug and not c.project_slug]
    assert len(nameless) == 1 and nameless[0].event_count == 1
