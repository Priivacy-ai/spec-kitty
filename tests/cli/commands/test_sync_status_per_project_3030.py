"""`sync status` must name whose data is in the journal (#3030 WP07 / T021, SC-004).

The sibling file `test_sync_doctor_per_project_3030.py` opens by recording why it
exists: *"The absence of this file is why the WP shipped a per-project renderer
that `doctor` never called."* This file exists because that absence survived one
surface over. `_render_per_project_store` has two call sites — `doctor` and
`status` — and until now `grep -rl "Event journal by project" tests/` returned the
doctor file alone. A mutant that deleted **only** the `status` call site recorded
four real invocations of the mutated site and killed nothing across
`tests/cli tests/delivery`.

FR-015 names three surfaces: `sync doctor`, `sync status` **and** `sync migrate`.
`doctor` and `migrate` are pinned at command level. This is `status`.

Why the unpinned site was worth a blocker rather than a nit: `status()` is a
540-line `# noqa: C901` function, and the per-project section sits immediately
below

    Queue empty -- all events synced.

which is read off the legacy `OfflineQueue` that `sync migrate` empties. Drop the
one call and CI stays fully green while `status` reverts to printing that
sentence with nothing contradicting it — the 2026-07-27 false-green verbatim,
where an operator saw an empty queue while 9,133 journal events, 1,322 of them
from projects that never opted in, sat untouched.

So these tests drive the **command** through `typer.testing.CliRunner`. Calling
`_render_per_project_store` directly would pass with the call site deleted, which
is the entire defect.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
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

#: Rich folds rather than ellipsizes in this table, but only because the renderer
#: asks it to; keep the terminal wide enough that the assertions pin whole
#: identities instead of a prefix a fold happened to leave intact.
_WIDE_TERMINAL = "220"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Pin every global path under ``tmp_path`` and keep `status` off the network.

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
    ``TERM=dumb FORCE_COLOR=1``, on this file — the same single test reds
    with the same assertion text whether the reset is live (``1 failed,
    3 passed``) or neutralised at hook level
    (``scripts/mutants/neutralise_reset_token_manager_3115.py``, suppressed=8,
    ``1 failed, 3 passed``). This file is also exercised, without changing
    outcome, when all five ``578a659162`` files run together under the mutant
    (``65 passed``, per-site suppressed split 24 / 8 [this file] / 18 / 50 /
    30) — a composition that covers leakage among these five files but not
    from an arbitrary sibling CLI file outside them, which no run has placed
    in the same session. So the verdict is scoped to what was actually
    measured — this single discriminating file and the five together — not
    asserted flat for every session composition. Kept anyway: FR-006's
    inventory speaks only to ``tests/sync/``, not this ``tests/cli/`` path,
    so it licenses no conclusion about deletion either way. The width in the
    pinned-width runs above was the WP02 conftest seam's pinned ``240×50``
    surface (``_plain_cli_console_seam``, autouse and unconditional,
    overriding via rich's explicit-size early return) — not this file's own
    ``COLUMNS=220``, which is set below but was not what was in effect.
    Reset in both setup and teardown so this file starts clean and never
    poisons whichever file the worker runs next — mirroring the existing
    ``reset_journal_cache()`` isolation below.
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
    # Other worktrees' live `run_sync_daemon` processes would otherwise leak an
    # unrelated orphan-daemon block into these assertions.
    monkeypatch.setattr("specify_cli.sync.daemon.scan_sync_daemons", lambda: None)
    from specify_cli.event_journal.journal import reset_journal_cache

    reset_journal_cache()
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


def _status_journal() -> EventJournal:
    """Open the journal `status` itself will resolve, at the same producer scope."""
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

    journal = _status_journal()
    for i in range(7):
        journal.append(_event(f"evt-ok-{i}", CONSENTED, f"2026-07-01T00:00:0{i}+00:00"))
    for i in range(4):
        journal.append(_event(f"evt-silent-{i}", SILENT, f"2026-06-01T00:00:0{i}+00:00"))
    for i in range(2):
        journal.append(_event(f"evt-out-{i}", OPTED_OUT, f"2026-06-15T00:00:0{i}+00:00"))
    journal.append(_event("evt-anon-0", None, "2026-05-01T00:00:00+00:00"))
    return journal


def test_status_names_every_project_with_count_age_and_consent() -> None:
    """FR-015/SC-004 on the `status` surface, driven through the command.

    Kills the "delete only the `status` call site" mutant. The mutant leaves
    `doctor`, the renderer and every report-layer unit test untouched, so before
    this file it recorded four invocations of a site whose removal nothing
    noticed.
    """
    journal = _seed_contaminated_store()
    assert journal.count() == 14, "precondition: the store really is contaminated"

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    out = result.output
    assert "Event journal by project" in out

    # Every project is NAMED, with its count — a project row, not just the title.
    for uuid, count in ((CONSENTED, "7"), (SILENT, "4"), (OPTED_OUT, "2")):
        assert uuid in out, f"{uuid} is in the journal but `status` did not name it"
        assert count in out

    # Identity-less rows are their own row, not silently dropped (FR-011).
    assert "identity unresolved" in out

    # Consent state, and the level that answered it.
    assert "consented" in out
    assert "denied" in out

    # Oldest-event AGE, which is the column FR-015 asks for.
    assert "Oldest" in out


def test_status_contradicts_its_own_empty_queue_line() -> None:
    """The section must appear *with* "Queue empty", not instead of it.

    This is the assertion the mutant is actually about. `status` reads its queue
    block off the legacy `OfflineQueue`, which `sync migrate` empties, so the
    reassuring sentence is emitted over a contaminated journal. A `status` that
    prints it unaccompanied is the incident's operator experience reproduced.
    """
    _seed_contaminated_store()

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    flat = " ".join(result.output.split())
    assert "Queue empty" in flat, (
        "precondition: the legacy queue really is empty, so the reassuring line "
        "really is printed — without it this test cannot witness the contradiction"
    )
    assert "have not consented to hosted sync" in flat, (
        "`status` printed 'Queue empty -- all events synced' over a journal "
        "holding two never-consenting projects, with nothing contradicting it"
    )
    assert "no stored project identity" in flat
    assert "sync purge" in flat


def test_status_says_so_when_the_journal_is_empty() -> None:
    """An empty journal prints an explicit row, never an absent section.

    Without this, "the journal holds nothing" and "`status` never looked" render
    identically — and the second is what the deleted call site produces.
    """
    journal = _status_journal()
    assert journal.count() == 0

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert "Event journal by project" in result.output
    assert "no events" in result.output.lower()


def test_status_names_the_journal_it_could_not_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A journal `status` cannot open becomes a printed warning, not a gap.

    `status` has no global issues list, so it prints the renderer's warnings
    inline. That loop is a second thing a refactor can drop independently of the
    call site, and dropping it restores the same silence.
    """
    _seed_contaminated_store()

    def _boom() -> object:
        raise PermissionError("journal.db: permission denied")

    monkeypatch.setattr(sync_module, "_open_journal_readonly", _boom)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert "could not be opened" in result.output
    assert "permission denied" in result.output
