"""A name the report prints must be a name `sync purge` accepts (#3030 WP07, SC-004).

Measured against a seeded store before the fix:

    ! 2 project(s) in the journal have not consented to hosted sync: acme/app, beta/svc.
      Their events are retained locally and never delivered;
      `spec-kitty sync purge --project <slug>` removes them.

    $ spec-kitty sync purge --project acme/app
    Error: No project matches slug "acme/app". Slugs this machine has a record of:
           acme-app, beta-svc, engagement-assistant.

`_project_store_label` and `_per_project_store_issues` lead with ``repo_slug``;
`_purge_resolve_project` built its candidate map from ``project_slug`` only. So the
operator running the incident's own remediation was handed a name the very next
command refused — with SC-004's promise being *zero hand-written SQLite queries* to
answer "whose data is in here?".

The defect survived three reviews because both ends *documented* it as correct:
``status_report.unresolved_candidate_name`` asserted "``repo_slug`` leads because
``sync purge --project`` and the consent records are keyed on it", and
``test_doctor_prefers_the_repo_slug_label_…`` repeated the premise in its docstring.
Neither was true — consent is keyed on ``project_uuid``, and purge was keyed on
``project_slug`` — so a passing test defended the wrong behaviour. Both texts are
corrected; this file is what replaces them, because a comment cannot red.

**The invariant lives here, in neither function's internals.** The label chain and
the selector map are free to change independently as long as their composition
holds, so these tests take whatever the report *actually renders* and feed it to the
command the report *actually recommends*. Both halves are driven through
``CliRunner`` for the reason this WP already learned the hard way: a helper-level
check passes while the command never reaches it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_module
from specify_cli.cli.commands.sync import app
from specify_cli.event_journal.journal import EventJournal, resolve_journal_path
from specify_cli.event_journal.models import Event

pytestmark = pytest.mark.fast

runner = CliRunner()

#: (uuid, project_slug, repo_slug, event_count, consent)
SILENT = ("aaaaaaaa-0000-0000-0000-00000000000a", "acme-app", "acme/app", 3, None)
REFUSED = ("bbbbbbbb-0000-0000-0000-00000000000b", "beta-svc", "beta/svc", 2, False)
CONSENTED = (
    "cccccccc-0000-0000-0000-00000000000c",
    "engagement-assistant",
    "my-org/engagement-assistant",
    5,
    True,
)
SEEDED = (SILENT, REFUSED, CONSENTED)

_WIDE_TERMINAL = "240"


@pytest.fixture(autouse=True)
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One tmp home and one tmp checkout, shared by both commands under test.

    ``SPECIFY_REPO_ROOT`` is not optional: without it ``locate_project_root`` walks
    up from the cwd to the real spec-kitty checkout and a purge would reach the
    developer's own gitignored frame queue.
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    repo = tmp_path / "checkout"
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)
    (repo / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {CONSENTED[0]}\n  slug: {CONSENTED[1]}\n  node_id: abcdef123456\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo))
    monkeypatch.setenv("COLUMNS", _WIDE_TERMINAL)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    monkeypatch.setattr(
        sync_module, "_check_server_connection", lambda _url: ("[dim]Disabled[/dim]", "")
    )
    from specify_cli.cli.commands._auth_recovery import RecoveryOutcome

    monkeypatch.setattr(
        sync_module,
        "handle_unauthenticated_with_teamspace",
        lambda **_: RecoveryOutcome.NO_TEAMSPACE,
    )
    monkeypatch.setattr("specify_cli.sync.daemon.scan_sync_daemons", lambda: None)
    monkeypatch.chdir(repo)
    from specify_cli.event_journal.journal import reset_journal_cache

    reset_journal_cache()
    return repo


def _report_journal_path() -> Path:
    """The journal `doctor` reads."""
    scope = sync_module._current_event_sync_scope()
    return resolve_journal_path(user_id=scope.user_id, team_slug=scope.team_slug)


def _purge_journal_path() -> Path:
    """The journal `purge` acts on."""
    from specify_cli.delivery.retention import resolve_live_store_paths

    return resolve_live_store_paths()[0]


def _seed() -> EventJournal:
    """The incident's shape, with BOTH name columns recorded on every row.

    Rows carrying a repo slug *and* a project slug are the population the defect
    needed: with only one name recorded there is nothing for the two surfaces to
    disagree about.
    """
    from specify_cli.sync.consent import set_project_consent

    # `doctor` and `purge` resolve their journal through different helpers. If those
    # ever diverge, this file would be reporting on one store and purging another —
    # a purge over an empty twin reports "0 removed", which is indistinguishable
    # from "nothing to remove".
    assert _report_journal_path() == _purge_journal_path(), (
        "precondition: the report surface and the purge act on ONE journal"
    )

    journal = EventJournal(_report_journal_path())
    for uuid, project_slug, repo_slug, count, consent in SEEDED:
        if consent is not None:
            set_project_consent(uuid, consent)
        for index in range(count):
            journal.append(
                Event(
                    event_id=f"evt-{project_slug}-{index}",
                    event_type="WorkPackageApproved",
                    payload=json.dumps({"project_uuid": uuid}).encode(),
                    occurred_at=f"2026-07-01T00:00:{index:02d}+00:00",
                    created_at=f"2026-07-01T00:00:{index:02d}+00:00",
                    project_uuid=uuid,
                    project_slug=project_slug,
                    repo_slug=repo_slug,
                )
            )
    return journal


def _named_refusals(output: str) -> list[str]:
    """The exact name list from the report's "have not consented" sentence.

    Reads the sentence's own payload rather than grepping the whole report, so the
    test constrains *which* names the operator is handed. Rich wraps at the console
    width, so whitespace is normalised before slicing.
    """
    flat = " ".join(output.split())
    marker = "have not consented to hosted sync: "
    if marker not in flat:
        return []
    tail = flat.split(marker, 1)[1]
    return [name.strip() for name in tail.split(".", 1)[0].split(",") if name.strip()]


def _purge_dry_run(selector: str, tmp_path: Path) -> tuple[int, str, dict[str, Any] | None]:
    """Ask `sync purge` to resolve *selector*, without deleting anything.

    Returns ``(exit_code, output, report)``; ``report`` is ``None`` when the run
    refused before writing one.
    """
    destination = tmp_path / f"purge-{abs(hash(selector))}.json"
    result = runner.invoke(
        app, ["purge", "--project", selector, "--report", str(destination)]
    )
    payload = None
    if destination.exists() and destination.stat().st_size:
        payload = json.loads(destination.read_text(encoding="utf-8"))
    return result.exit_code, result.output, payload


# --------------------------------------------------------------------------- #
# The invariant
# --------------------------------------------------------------------------- #


def test_every_name_doctor_recommends_purging_is_a_name_purge_accepts(
    tmp_path: Path,
) -> None:
    """The operator's own copy-paste path, end to end.

    Red before the fix, with the exact transcript in this module's docstring:
    `doctor` named ``acme/app`` and ``beta/svc`` in the same sentence as
    ``spec-kitty sync purge --project <slug>``, and both were refused with
    ``No project matches slug``.
    """
    _seed()

    doctor = runner.invoke(app, ["doctor"])
    assert doctor.exit_code == 0, doctor.output

    recommended = _named_refusals(doctor.output)
    assert recommended == [SILENT[2], REFUSED[2]], (
        "precondition: the report must actually name the two non-consenting "
        f"projects by their repo slug, not {recommended} — without that this test "
        "has nothing to feed the resolver and would pass vacuously"
    )
    assert "sync purge --project" in " ".join(doctor.output.split()), (
        "precondition: the sentence must actually recommend the command whose "
        "acceptance of these names is what is under test"
    )

    expected = {SILENT[2]: SILENT, REFUSED[2]: REFUSED}
    for name in recommended:
        uuid, _project_slug, _repo_slug, count, _consent = expected[name]
        exit_code, output, report = _purge_dry_run(name, tmp_path)

        assert exit_code == 0, (
            f"`doctor` told the operator to run `sync purge --project {name}` and "
            f"the command refused it:\n{output}"
        )
        assert report is not None, f"no purge report was written for {name!r}"
        assert report["selector"]["project_uuid"] == uuid, (
            f"{name!r} resolved to the wrong project — a purge under a recommended "
            "name must reach the project that name was printed for"
        )
        assert report["stores"]["event_journal"]["in_scope"] == count, (
            f"{name!r} resolved but selected {report['stores']['event_journal']['in_scope']} "
            f"rows where the report attributed {count} to it"
        )


def test_every_label_the_table_renders_is_a_purge_selector(tmp_path: Path) -> None:
    """The same invariant over the table, which the refusal sentence does not cover.

    The sentence names only projects known to have refused. The table names *every*
    project in the journal, including consenting ones, and an operator reads a name
    off it just as readily. Driving the composition — the report's own label into
    the command's own resolver — is what keeps the two ends free to change
    independently without silently drifting apart again.
    """
    from specify_cli.delivery.status_report import build_per_project_store_report

    journal = _seed()
    report = build_per_project_store_report(journal)
    rendered = [
        (sync_module._project_store_label(row), row.project_uuid, row.event_count)
        for row in report.rows
        if not row.is_unresolved_identity
    ]
    assert len(rendered) == len(SEEDED), (
        f"precondition: the report must render one row per seeded project, got {rendered}"
    )

    for label, uuid, count in rendered:
        exit_code, output, purge_report = _purge_dry_run(label, tmp_path)

        assert exit_code == 0, (
            f"the table renders {label!r} as this project's name and `sync purge` "
            f"will not accept it:\n{output}"
        )
        assert purge_report is not None
        assert purge_report["selector"]["project_uuid"] == uuid
        assert purge_report["stores"]["event_journal"]["in_scope"] == count


def test_the_probe_distinguishes_a_good_selector_from_a_bad_one(tmp_path: Path) -> None:
    """The control, because a probe that answers the same way for every case is mute.

    This mission has already been misled once by a diagnostic that returned the
    same answer for all five inputs *including the valid one*. The two tests above
    assert "resolves"; this one proves the same harness reports "refused" when the
    name genuinely is not in the store — so their green is a discrimination and not
    a constant.
    """
    _seed()

    good_code, _good_output, good_report = _purge_dry_run(SILENT[2], tmp_path)
    bad_code, bad_output, bad_report = _purge_dry_run("acme/no-such-repo", tmp_path)

    assert good_code == 0 and good_report is not None
    assert bad_code == 2, (
        "an unknown name must be refused — '0 rows removed' is indistinguishable "
        "from 'wrong selector', and the purge report is the only record left"
    )
    assert bad_report is None
    assert "acme/no-such-repo" in bad_output
    # The refusal must list names the operator can actually use, and both columns
    # are now selectors, so both belong in the list.
    flat = " ".join(bad_output.split())
    assert SILENT[2] in flat and SILENT[1] in flat, (
        "the refusal enumerates what this machine has a record of; after repo slugs "
        f"became selectors it must list them too, got: {flat}"
    )


def test_the_invoking_checkouts_repo_slug_is_a_selector_too(
    checkout: Path, tmp_path: Path
) -> None:
    """The resolver's second candidate site, pinned because the first one hid it.

    Found by reading the pre-fix mutant's **per-site bind split** rather than its
    colour: ``journal_projection`` blanked 51 repo slugs while ``checkout_identity``
    blanked **zero**. The resolver offers names from two sources — the journal's
    identity projection and the invoking checkout's ``config.yaml`` — and every
    other test in this file seeds the journal, so the checkout half of the same
    change was carried by nothing at all. A single aggregate count would have read
    as healthy coverage.

    The case is not hypothetical: it is the one the resolver's docstring already
    names for uuids. A project whose journal rows are gone — purged, migrated, or
    never written — can still hold payloads in the body-upload queue, and its
    checkout is then the only place either of its names survives.
    """
    stranded = "eeeeeeee-0000-0000-0000-00000000000e"
    (checkout / ".kittify" / "config.yaml").write_text(
        "project:\n"
        f"  uuid: {stranded}\n"
        "  slug: stranded-engagement\n"
        "  repo_slug: stranded/engagement\n"
        "  node_id: abcdef123456\n",
        encoding="utf-8",
    )
    _seed()  # a populated journal that holds NOTHING for this project

    exit_code, output, report = _purge_dry_run("stranded/engagement", tmp_path)

    assert exit_code == 0, (
        "a checkout that declares a repo slug must be purgeable by it; its rows may "
        f"survive only in a store the journal projection cannot name:\n{output}"
    )
    assert report is not None
    assert report["selector"]["project_uuid"] == stranded
    # The other seeded projects must not be swept in by a selector that matched none
    # of their names — a resolver that fell through to "everything" would also pass
    # the assertions above.
    assert report["stores"]["event_journal"]["in_scope"] == 0


def test_two_projects_sharing_a_repo_slug_refuse_rather_than_span_both(
    tmp_path: Path,
) -> None:
    """The cost of accepting ``repo_slug``, paid by the existing ambiguity refusal.

    Two projects can share a repo slug — the same repository cloned under two
    project identities is the ordinary case, and a repo slug can equally collide
    with another project's project slug. The candidate map is keyed by name to a
    *set* of uuids, so a colliding name takes the same refusal a colliding project
    slug always did. Purging both would destroy a consenting project's history
    while remediating a different one.
    """
    _seed()
    twin = "dddddddd-0000-0000-0000-00000000000d"
    journal = EventJournal(_report_journal_path())
    journal.append(
        Event(
            event_id="evt-twin-0",
            event_type="WorkPackageApproved",
            payload=b"{}",
            occurred_at="2026-07-02T00:00:00+00:00",
            created_at="2026-07-02T00:00:00+00:00",
            project_uuid=twin,
            project_slug="acme-app-fork",
            repo_slug=SILENT[2],  # the SAME repo slug as SILENT
        )
    )

    exit_code, output, report = _purge_dry_run(SILENT[2], tmp_path)

    assert exit_code == 2, (
        "an ambiguous name must refuse; a purge that spans two projects deletes a "
        f"bystander's history:\n{output}"
    )
    assert report is None
    flat = " ".join(output.split())
    assert SILENT[0] in flat and twin in flat, (
        "the refusal must name both uuids so the operator can pass the one they "
        f"mean, got: {flat}"
    )
    # The unambiguous name for the same project still works, which is the whole
    # reason the refusal is acceptable rather than a dead end.
    good_code, _good_output, good_report = _purge_dry_run(SILENT[1], tmp_path)
    assert good_code == 0
    assert good_report is not None
    assert good_report["selector"]["project_uuid"] == SILENT[0]
