"""`sync doctor` must name whose data is in the journal (#3030 WP07 / T021, SC-004).

The absence of this file is why the WP shipped a per-project renderer that
`doctor` never called. `_render_per_project_store` existed, was fully unit-tested
at the report layer, and `grep` found exactly one reference to it: its own `def`.
Every report-layer assertion still passed. The operator surface — the one thing
FR-015 is about — rendered nothing.

So these tests drive the **command**, through `typer.testing.CliRunner`, over a
journal that a real `_open_event_sync_runtime_readonly()` resolves for itself. A
test that stubbed the opener would re-open the same hole one layer down.

They also pin the three failure paths, because a section that silently vanishes is
indistinguishable from "nothing to report" — which is precisely the false-green
`doctor` produced throughout the 2026-07-27 incident, when it read *healthy* off
an `OfflineQueue` that `sync migrate` had already emptied while 9,133 journal
events (1,322 of them from projects that never opted in) sat untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_module
from specify_cli.cli.commands.sync import app
from specify_cli.event_journal.journal import EventJournal, resolve_journal_path
from specify_cli.event_journal.models import Event

pytestmark = pytest.mark.fast

runner = CliRunner()

CONSENTED = "aaaaaaaa-0000-0000-0000-000000000001"
SILENT = "bbbbbbbb-0000-0000-0000-000000000002"
OPTED_OUT = "cccccccc-0000-0000-0000-000000000003"

# Rich ellipsizes an over-wide cell by default, and an ellipsized project
# identity would fail SC-004 ("names every project") while the table still
# looked fine. The renderer therefore folds instead of truncating; this width
# keeps the fold from firing so the assertions can pin whole identities.
_WIDE_TERMINAL = "220"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin every global path under ``tmp_path`` and keep doctor off the network."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    monkeypatch.setenv("COLUMNS", _WIDE_TERMINAL)
    # Doctor's own reachability probe short-circuits while SaaS sync is off, but
    # pin it anyway so no test in this file can ever reach a real host.
    monkeypatch.setattr(
        sync_module, "_check_server_connection", lambda _url: ("[dim]Disabled[/dim]", "")
    )
    # This suite runs from a checkout that IS teamspace-connected, so doctor's
    # step-6 recovery would exit 4 on the unauthenticated tmp home and mask the
    # journal section entirely. Neutralise the recovery, not the section.
    from specify_cli.cli.commands._auth_recovery import RecoveryOutcome

    monkeypatch.setattr(
        sync_module,
        "handle_unauthenticated_with_teamspace",
        lambda **_: RecoveryOutcome.NO_TEAMSPACE,
    )
    # Other worktrees' live `run_sync_daemon` processes would otherwise leak an
    # unrelated orphan-daemon issue into these assertions.
    monkeypatch.setattr("specify_cli.sync.daemon.scan_sync_daemons", lambda: None)
    from specify_cli.event_journal.journal import reset_journal_cache

    reset_journal_cache()


def _event(event_id: str, uuid: str | None, created_at: str) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
    )


def _named_refusals(output: str) -> list[str]:
    """The exact name list from doctor's "have not consented" sentence.

    Reads the sentence's own payload so a test can constrain WHICH projects are
    named, instead of grepping the whole report for a slug plus punctuation — that
    form silently passes when a regression names the slug last. Returns ``[]`` when
    no refusal was reported at all. Rich wraps at the console width, so whitespace
    is normalised before slicing.
    """
    flat = " ".join(output.split())
    marker = "have not consented to hosted sync: "
    if marker not in flat:
        return []
    tail = flat.split(marker, 1)[1]
    return [name.strip() for name in tail.split(".", 1)[0].split(",") if name.strip()]


def _doctor_journal() -> EventJournal:
    """Open the journal doctor itself will resolve, at the same producer scope."""
    scope = sync_module._current_event_sync_scope()
    return EventJournal(
        resolve_journal_path(user_id=scope.user_id, team_slug=scope.team_slug)
    )


def _seed_contaminated_store() -> EventJournal:
    """The incident's shape: one consenting project, two that never shipped, one anon."""
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(CONSENTED, True)
    set_project_consent(OPTED_OUT, False)
    # SILENT deliberately gets no record at all — absence, not refusal, is the
    # population the incident turned on.

    journal = _doctor_journal()
    for i in range(7):
        journal.append(_event(f"evt-ok-{i}", CONSENTED, f"2026-07-01T00:00:0{i}+00:00"))
    for i in range(4):
        journal.append(_event(f"evt-silent-{i}", SILENT, f"2026-06-01T00:00:0{i}+00:00"))
    for i in range(2):
        journal.append(_event(f"evt-out-{i}", OPTED_OUT, f"2026-06-15T00:00:0{i}+00:00"))
    journal.append(_event("evt-anon-0", None, "2026-05-01T00:00:00+00:00"))
    return journal


def test_doctor_names_every_project_with_count_age_and_consent() -> None:
    """SC-004: zero hand-written SQLite queries to answer "whose data is in here?".

    Red before the fix: `_render_per_project_store` was never called, so the
    journal section was absent from doctor's output entirely and every one of
    these assertions failed on a report that was not rendered at all.
    """
    journal = _seed_contaminated_store()
    assert journal.count() == 14, "precondition: the store really is contaminated"

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "Event journal by project" in out

    # Every project is NAMED, with its count.
    for uuid, count in ((CONSENTED, "7"), (SILENT, "4"), (OPTED_OUT, "2")):
        assert uuid in out, f"{uuid} is in the journal but doctor did not name it"
        assert count in out

    # Identity-less rows are their own row, not silently dropped (FR-011).
    assert "identity unresolved" in out

    # Consent state, and the level that answered it — an operator cannot tell a
    # project-local grant from a stale machine-index cache otherwise.
    assert "consented" in out
    assert "denied" in out
    assert "absent" in out

    # Oldest-event AGE, not a raw timestamp (FR-015 asks for age).
    assert "Oldest" in out


def test_doctor_raises_the_non_consenting_projects_as_issues() -> None:
    """The table alone is not enough: doctor's `Issues found` list must name them.

    `doctor` printed "No issues detected. Sync is healthy." throughout the
    incident. A per-project table that renders while the summary still says
    healthy would reproduce that, one scroll-height away.
    """
    _seed_contaminated_store()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "Issues found" in result.output
    assert "No issues detected" not in result.output
    assert "have not consented to hosted sync" in result.output
    assert "no stored project identity" in result.output
    assert "sync purge" in result.output


def test_doctor_says_so_when_the_journal_is_empty() -> None:
    """F3: an empty journal prints an explicit row, never an absent section.

    Red before the fix: `if not report.rows: return` — the section vanished, and
    "the journal holds nothing" was indistinguishable from "doctor never looked".
    """
    journal = _doctor_journal()
    assert journal.count() == 0

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "Event journal by project" in result.output
    assert "no events" in result.output.lower()


def test_doctor_does_not_call_an_uncountable_journal_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A journal whose count() fails must not render as "no events retained".

    `build_per_project_store_report` reports ``-1`` for an unanswerable count, so
    the report does not reconcile against zero grouped rows. Red before the fix:
    the renderer returned early on `not report.rows` and never reached the
    reconciliation warning, so an unreadable journal printed the same reassuring
    line as an empty one.
    """
    _doctor_journal()  # the file exists, so the runtime opens

    def _boom(_self: object) -> int:
        raise RuntimeError("database disk image is malformed")

    monkeypatch.setattr(
        "specify_cli.event_journal.journal.EventJournal.count", _boom, raising=True
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "Issues found" in result.output
    assert "do not reconcile" in result.output


def test_doctor_names_the_journal_it_could_not_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F3: a journal doctor cannot open must become an issue, not a missing section.

    The realistic trigger is doctor resolving a different producer scope than the
    daemon, or a locked / permission-denied / corrupt DB file. Red before the fix:
    a bare `except Exception: return`, so the run printed the usual healthy table,
    no journal section, and exit 0.
    """
    _seed_contaminated_store()

    def _boom() -> object:
        raise PermissionError("journal.db: permission denied")

    monkeypatch.setattr(sync_module, "_open_journal_readonly", _boom)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "Issues found" in result.output
    assert "could not be opened" in result.output
    assert "permission denied" in result.output


def test_doctor_names_the_journal_it_could_not_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F3: a projection read that fails mid-group must be reported, not swallowed."""
    _seed_contaminated_store()

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("database disk image is malformed")

    monkeypatch.setattr(
        "specify_cli.delivery.status_report.build_per_project_store_report", _boom
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "Issues found" in result.output
    assert "could not be grouped" in result.output
    assert "malformed" in result.output


def test_doctor_prefers_the_repo_slug_label_and_falls_back_to_the_uuid() -> None:
    """A uuid is unusable in a purge command; the repo slug is what operators type."""
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(CONSENTED, True)
    journal = _doctor_journal()
    journal.append(
        Event(
            event_id="evt-slugged",
            event_type="WorkPackageApproved",
            payload=b"{}",
            occurred_at="2026-07-01T00:00:00+00:00",
            created_at="2026-07-01T00:00:00+00:00",
            project_uuid=CONSENTED,
            repo_slug="my-org/engagement-assistant",
        )
    )
    journal.append(_event("evt-unslugged", SILENT, "2026-07-02T00:00:00+00:00"))

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "my-org/engagement-assistant" in result.output
    # No slug recorded for the second project, so the uuid stands in rather than
    # the row rendering blank.
    assert SILENT in result.output


# --- N1: the unresolved bucket must not be pinned on one named repo -----------


def _seed_three_repos_with_unresolved_identity() -> EventJournal:
    """Three identity-less rows, one per repo — the `sync migrate` legacy shape."""
    journal = _doctor_journal()
    for index, (slug, repo) in enumerate(
        (
            ("acme-app", "acme/app"),
            ("beta-svc", "beta/svc"),
            ("gamma-tool", "gamma/tool"),
        )
    ):
        journal.append(
            Event(
                event_id=f"evt-anon-{index}",
                event_type="WorkPackageApproved",
                payload=b"{}",
                occurred_at=f"2026-07-01T00:00:0{index}+00:00",
                created_at=f"2026-07-01T00:00:0{index}+00:00",
                project_uuid=None,
                project_slug=slug,
                repo_slug=repo,
            )
        )
    return journal


def test_doctor_does_not_tell_the_operator_one_named_repo_refused_consent() -> None:
    """The false fact that closes an incident early.

    Red before the fix: the unresolved bucket adopted the first row's repo slug and
    landed in `non_consenting_rows`, so doctor printed "1 project(s) in the journal
    have not consented to hosted sync: acme/app ... `sync purge --project <slug>`
    removes them". An operator purges `acme/app`, sees a clean report, and closes
    the confidentiality incident with `beta/svc` and `gamma/tool` still on disk.
    """
    journal = _seed_three_repos_with_unresolved_identity()
    assert journal.count() == 3

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "have not consented to hosted sync" not in out, (
        "no project here is known to have refused consent — their consent cannot "
        "be resolved at all, which is a different fact with a different remedy"
    )
    # The count must not claim one project either.
    assert "1 project(s) in the journal have not consented" not in out


def test_doctor_names_every_repo_behind_the_unresolved_rows() -> None:
    """SC-004 must hold for this population too, with per-repo counts.

    The slugs are on the rows and in the projection already; requiring a
    hand-written SQLite query to learn which repos are present is precisely the
    gap SC-004 closes.
    """
    _seed_three_repos_with_unresolved_identity()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    out = result.output
    for repo in ("acme/app", "beta/svc", "gamma/tool"):
        assert repo in out, f"{repo} has payloads in the journal but was never named"
    # Still surfaced as the fail-closed denial it is (FR-011).
    assert "identity unresolved" in out
    assert "no stored project identity" in out
    assert "Issues found" in out


def test_doctor_still_names_a_genuine_refusal_alongside_unresolved_rows() -> None:
    """Dropping the bucket from the refusal list must not drop real refusals.

    Without this, "no project refused" could be satisfied by never reporting a
    refusal at all — the opposite failure, and just as quiet.
    """
    _seed_three_repos_with_unresolved_identity()
    journal = _doctor_journal()
    journal.append(_event("evt-silent-0", SILENT, "2026-07-02T00:00:00+00:00"))

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "have not consented to hosted sync" in result.output
    assert SILENT in result.output

    # ...and the refusal names EXACTLY the one project that refused. Asserted by
    # reading the sentence's own name list rather than by searching the whole output
    # for "acme/app, " — that earlier form only fired when the slug was followed by
    # a comma, so it passed if a regression named acme/app last in the list.
    named = _named_refusals(result.output)
    assert named == [SILENT], (
        f"the refusal sentence must name only the project known to have refused, "
        f"not {named}"
    )


# --- N1-a: a recorded project name must reach the operator -------------------


def _seed_slug_only_unresolved_rows() -> EventJournal:
    """Rows carrying ``project_slug`` but no ``repo_slug`` — a production shape.

    The emitter resolves the three identity columns independently: ``project_slug``
    walks a chain over the envelope and the payload, ``repo_slug`` is a single
    top-level lookup, and a nil-sentinel uuid normalises to ``None``. A row with a
    resolvable project name and neither uuid nor repo slug is therefore ordinary.
    """
    journal = _doctor_journal()
    for index, slug in enumerate(("acme-app", "acme-app", "beta-svc")):
        journal.append(
            Event(
                event_id=f"evt-slugonly-{index}",
                event_type="WorkPackageApproved",
                payload=b"{}",
                occurred_at=f"2026-07-01T00:00:0{index}+00:00",
                created_at=f"2026-07-01T00:00:0{index}+00:00",
                project_uuid=None,
                project_slug=slug,
                repo_slug=None,
            )
        )
    return journal


def test_doctor_names_projects_that_recorded_only_a_project_slug() -> None:
    """SC-004 must not depend on which of the two name columns happens to be set.

    Red before the fix: both surfaces labelled with
    ``candidate.repo_slug or '<no repo recorded>'``, dropping the
    ``project_slug`` fallback that the named-refusal path at ``sync.py`` already
    had. Two nameable projects were present, both names were in the projection,
    and the operator was shown ``<no repo recorded> (3)`` — told to open SQLite by
    the very report whose job is to make that unnecessary.
    """
    _seed_slug_only_unresolved_rows()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    out = result.output
    for name in ("acme-app", "beta-svc"):
        assert name in out, f"{name} has payloads in the journal but was never named"
    assert "no name recorded" not in out, (
        "nothing in this journal is genuinely nameless — that label must mean what "
        "it says, or it cannot be trusted when it is the truth"
    )


def test_doctor_still_says_no_name_recorded_when_nothing_was_recorded() -> None:
    """The guard against over-correcting N1-a.

    Legacy `sync migrate` imports genuinely carry no identity at all
    (``_build_event`` sets none of the three columns). For those the label is
    correct and the remedy is an identity backfill, so a fix that removed it —
    or invented a name for them — would trade one wrong label for another.

    The wording is now "no NAME recorded", not "no repo recorded": with candidates
    keyed on the (repo_slug, project_slug) pair, an unnamed candidate is one that
    recorded neither, and the narrower label would understate that.
    """
    journal = _doctor_journal()
    journal.append(
        Event(
            event_id="evt-nameless",
            event_type="WorkPackageApproved",
            payload=b"{}",
            occurred_at="2026-07-01T00:00:00+00:00",
            created_at="2026-07-01T00:00:00+00:00",
            project_uuid=None,
            project_slug=None,
            repo_slug=None,
        )
    )
    assert journal.count() == 1

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "no name recorded" in result.output
    assert "no stored project identity" in result.output
