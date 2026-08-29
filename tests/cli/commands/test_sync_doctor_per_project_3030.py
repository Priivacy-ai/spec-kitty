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

WP10 correction: the historical node names are retained for CI continuity, but
the live fixture now opens one UUID-owned ``ProjectSyncStore``. The assertions
therefore prove the active project is named and that foreign project identities
cannot be selected from its journal; identity-less legacy rows belong to the
explicit migration/quarantine surface, never this live report.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_module
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

CONSENTED = "aaaaaaaa-0000-0000-0000-000000000001"
SILENT = "bbbbbbbb-0000-0000-0000-000000000002"
OPTED_OUT = "cccccccc-0000-0000-0000-000000000003"

# Rich ellipsizes an over-wide cell by default, and an ellipsized project
# identity would fail SC-004 ("names every project") while the table still
# looked fine. The renderer therefore folds instead of truncating; this width
# keeps the fold from firing so the assertions can pin whole identities.
_WIDE_TERMINAL = "220"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Pin every global path under ``tmp_path`` and keep doctor off the network.

    Also resets the process-wide ``TokenManager`` singleton, in BOTH setup and
    teardown: ``sync.status``/``sync.doctor`` unconditionally call
    ``get_token_manager()``, which lazily caches its instance for the lifetime
    of the worker process, so under a ``--dist loadfile`` run a sibling CLI
    test file that authenticates a fake session (or otherwise mutates the
    singleton) earlier in the same worker would otherwise leak into this
    file's producer-scope resolution.

    That threat model is **not the #3115 CLI failure** (FR-009, measured
    2026-08-01). The #3030 landing pass shipped this reset as self-declared
    unproven hardening (`578a659162` / `4f8e4ca781`): "could not force a live
    reproduction of the reported empty-journal CI failure locally ... this is
    defensive hardening of a credible process-global, not a
    confirmed-necessary fix." WP02's render-surface finding explains the CI
    failures instead — an 80-column dumb-terminal console folds the project
    uuid across two table lines (C-012). Measured on the arm that actually
    discriminates — WP02's ``tests/conftest.py`` seam disabled by a plugin so
    the failing ``(80, 25)`` surface is genuinely restored, under
    ``TERM=dumb FORCE_COLOR=1``, on the sibling
    ``test_sync_status_per_project_3030.py`` (this WP's shared discriminating
    probe) — the same single test reds with the same assertion text whether
    the reset is live (``1 failed, 3 passed``) or neutralised at hook level
    (``scripts/mutants/neutralise_reset_token_manager_3115.py``, suppressed=8,
    ``1 failed, 3 passed``). This file's own tests were not independently run
    on that discriminating arm; they were exercised, without changing
    outcome, when all five ``578a659162`` files ran together under the mutant
    (``65 passed``, per-site suppressed split
    24 [this file] / 8 / 18 / 50 / 30) — a composition that covers leakage
    among these five files but not from an arbitrary sibling CLI file outside
    them, which no run has placed in the same session. So the verdict is
    scoped to what was actually measured — the one discriminating file and
    the five together — not asserted flat for every session composition.
    Kept anyway: FR-006's inventory speaks only to ``tests/sync/``, not this
    ``tests/cli/`` path, so it licenses no conclusion about deletion either
    way. The width in the pinned-width runs above was the WP02 conftest
    seam's pinned ``240×50`` surface (``_plain_cli_console_seam``, autouse and
    unconditional, overriding via rich's explicit-size early return) — not
    this file's own ``COLUMNS=220``, which is set below but was not what was
    in effect. Reset in both setup and teardown so this file starts clean and
    never poisons whichever file the worker runs next — mirroring the
    existing ``reset_journal_cache()`` isolation below.
    """
    from specify_cli.auth.manager import reset_token_manager

    reset_token_manager()
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
    monkeypatch.setattr(sync_module, "_check_server_connection", lambda _url: ("[dim]Disabled[/dim]", ""))
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
    from specify_cli.sync.consent import record_project_opt_in
    import specify_cli.sync.routing as routing

    reset_journal_cache()
    record_project_opt_in(CONSENTED, actor="doctor-per-project-test")
    store = ProjectSyncStore(CONSENTED)
    authority = store.layout_generation()
    authority.begin_cutover("doctor-per-project-test")
    authority.publish_project_only("doctor-per-project-test", verify_exact=lambda: True)
    with store.unit_of_work():
        pass
    routed = SimpleNamespace(
        project_uuid=store.project_uuid,
        project_slug="consented-project",
        repo_slug="acme/consented-project",
        build_id="doctor-per-project",
        repo_root=Path.cwd(),
    )
    monkeypatch.setattr(routing, "resolve_checkout_sync_routing_readonly", lambda *_a, **_k: routed)
    try:
        yield
    finally:
        reset_token_manager()


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


class _ProjectJournalFixture:
    def __init__(self) -> None:
        self.store = ProjectSyncStore(CONSENTED)
        self.authority = self.store.layout_generation()

    def append(self, event: Event) -> None:
        with self.store.unit_of_work() as unit:
            EventJournal(unit, self.authority).append(event)

    def count(self) -> int:
        with self.store.unit_of_work() as unit:
            return int(EventJournal(unit, self.authority).count())


def _doctor_journal() -> _ProjectJournalFixture:
    """Open the exact canonical project journal that ``doctor`` resolves."""
    return _ProjectJournalFixture()


def _seed_contaminated_store() -> _ProjectJournalFixture:
    """Seed retained work in the active project without cross-project contamination."""
    journal = _doctor_journal()
    for i in range(7):
        journal.append(_event(f"evt-ok-{i}", CONSENTED, f"2026-07-01T00:00:0{i}+00:00"))
    return journal


def test_doctor_names_every_project_with_count_age_and_consent() -> None:
    """SC-004: zero hand-written SQLite queries to answer "whose data is in here?".

    Red before the fix: `_render_per_project_store` was never called, so the
    journal section was absent from doctor's output entirely and every one of
    these assertions failed on a report that was not rendered at all.
    """
    journal = _seed_contaminated_store()
    assert journal.count() == 7, "precondition: the active project retains seven events"

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "Event journal by project" in out

    # Every project is NAMED, with its count.
    assert CONSENTED in out and "7" in out
    assert SILENT not in out and OPTED_OUT not in out

    # Consent state, and the level that answered it — an operator cannot tell a
    # project-local grant from a stale machine-index cache otherwise.
    assert "consented" in out

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
    assert "have not consented to hosted sync" not in result.output


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

    monkeypatch.setattr("specify_cli.event_journal.journal.EventJournal.count", _boom, raising=True)

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

    monkeypatch.setattr("specify_cli.delivery.status_report.build_per_project_store_report", _boom)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "Issues found" in result.output
    assert "could not be grouped" in result.output
    assert "malformed" in result.output


def test_doctor_prefers_the_repo_slug_label_and_falls_back_to_the_uuid() -> None:
    """The repo slug is the name an operator recognises; the uuid is the last resort.

    **Premise corrected (#3030 WP07 cycle 4).** This docstring used to read *"a uuid
    is unusable in a purge command; the repo slug is what operators type"* — and it
    was false in the more dangerous direction. The uuid was the one selector
    ``sync purge --project`` had always accepted; ``repo_slug`` was the one it
    refused, while this very report led its label with it. So a passing test
    documented the ordering with the same false premise as the code, and the pair
    defended a report that printed names the tool rejected.

    The ordering is right for a different reason — recognition, not actionability —
    and actionability is now enforced rather than assumed:
    ``test_sync_report_label_is_a_purge_selector_3030.py`` feeds the label this test
    asserts on to the purge resolver and requires it to resolve.
    """
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
    journal.append(_event("evt-unslugged", CONSENTED, "2026-07-02T00:00:00+00:00"))

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "my-org/engagement-assistant" in result.output
    # No slug recorded for the second project, so the uuid stands in rather than
    # the row rendering blank.
    assert CONSENTED in result.output


# --- N1: the unresolved bucket must not be pinned on one named repo -----------


def _seed_three_repos_with_unresolved_identity() -> _ProjectJournalFixture:
    """Seed three source labels under the one canonical project authority."""
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
                project_uuid=CONSENTED,
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
        "no project here is known to have refused consent — their consent cannot be resolved at all, which is a different fact with a different remedy"
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
    assert CONSENTED in out
    assert "3" in out
    assert "identity unresolved" not in out


def test_doctor_still_names_a_genuine_refusal_alongside_unresolved_rows() -> None:
    """Dropping the bucket from the refusal list must not drop real refusals.

    Without this, "no project refused" could be satisfied by never reporting a
    refusal at all — the opposite failure, and just as quiet.
    """
    _seed_three_repos_with_unresolved_identity()
    from specify_cli.sync.consent import record_project_opt_out

    record_project_opt_out(CONSENTED, actor="doctor-per-project-refusal-test")

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "have not consented to hosted sync" in result.output
    assert CONSENTED in result.output

    # ...and the refusal names EXACTLY the one project that refused. Asserted by
    # reading the sentence's own name list rather than by searching the whole output
    # for "acme/app, " — that earlier form only fired when the slug was followed by
    # a comma, so it passed if a regression named acme/app last in the list.
    named = _named_refusals(result.output)
    assert named == ["acme/app"], f"the refusal sentence must name only the project known to have refused, not {named}"


# --- N1-a: a recorded project name must reach the operator -------------------


def _seed_slug_only_unresolved_rows() -> _ProjectJournalFixture:
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
                project_uuid=CONSENTED,
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
    assert "acme-app" in out
    assert "no name recorded" not in out, (
        "nothing in this journal is genuinely nameless — that label must mean what it says, or it cannot be trusted when it is the truth"
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
            project_uuid=CONSENTED,
            project_slug=None,
            repo_slug=None,
        )
    )
    assert journal.count() == 1

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    assert CONSENTED in result.output
    assert "no stored project identity" not in result.output
