"""`sync purge` — the operator's only remediation path (#3030 WP08 / T022).

FR-016 / FR-017 / NFR-006 / C-002. On 2026-07-27 a sync delivered 1,322 events
belonging to five never-opted-in projects; in this product a ``mission_slug`` is a
client engagement name, so the metadata *is* the confidential content. Four stores
hold it — the event journal, the delivery ledger, the body-upload queue and the
per-checkout ``pending_local_commits`` queue — and until this command existed every
store-level purge primitive had zero callers. FR-016's promise was code without an
operator.

These tests therefore drive the **command**, through ``CliRunner``, over real stores
that the command resolves for itself. That is deliberate and it is the WP's own
lesson: WP07 shipped a per-project renderer that ``sync doctor`` never called, fully
unit-tested one layer down, and the operator surface rendered nothing. A test that
stubbed the store resolution or called the helpers directly would re-open that hole.

Two properties are load-bearing and are asserted from the *test's own* reads of the
stores, never from what the command reports about itself:

* **NFR-006 is a differential.** "100% of X, 0% of anything else" is unfalsifiable
  if you only count X — and this mission has already rejected one version of this
  check in which both operands derived from a single read, where 200 randomized
  cases produced zero failures.
* **The dry run's prediction must equal what the real run deletes.** Asserted by
  running both and comparing the dry run's ``in_scope`` against the store rows that
  actually disappear.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.sync import app
from specify_cli.event_journal.journal import EventJournal, reset_journal_cache
from specify_cli.event_journal.models import Event

pytestmark = pytest.mark.fast

runner = CliRunner()

TARGET = "aaaaaaaa-0000-0000-0000-00000000000a"
TARGET_SLUG = "acme-migration"
OTHER = "bbbbbbbb-0000-0000-0000-00000000000b"
OTHER_SLUG = "globex-rollout"
TARGET_ID = "tgt_teamspace"

# Rich folds an over-wide cell; keep the terminal wide enough that assertions can
# pin whole uuids and paths instead of a truncated prefix.
_WIDE_TERMINAL = "240"


# --------------------------------------------------------------------------- #
# Isolation
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Pin every store this command can reach under ``tmp_path``.

    ``SPECIFY_REPO_ROOT`` is not optional here: without it ``locate_project_root``
    walks up from the cwd and finds the *real* spec-kitty checkout, and a
    ``--apply`` test would then delete the developer's own queued local-commit
    frames — gitignored machine-local state with no way back.

    Also resets the process-wide ``TokenManager`` singleton, in BOTH setup and
    teardown: ``sync`` commands unconditionally call ``get_token_manager()``,
    which lazily caches its instance for the lifetime of the worker process,
    so under a ``--dist loadfile`` run a sibling CLI test file that
    authenticates a fake session (or otherwise mutates the singleton) earlier
    in the same worker would otherwise leak into this file's producer-scope
    resolution.

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
    (``65 passed``, per-site suppressed split 24 / 8 / 18 / 50 [this file] /
    30) — a composition that covers leakage among these five files but not
    from an arbitrary sibling CLI file outside them, which no run has placed
    in the same session. So the verdict is scoped to what was actually
    measured — the one discriminating file and the five together — not
    asserted flat for every session composition. Kept anyway: FR-006's
    inventory speaks only to ``tests/sync/``, not this ``tests/cli/`` path,
    so it licenses no conclusion about deletion either way. The width in the
    pinned-width runs above was the WP02 conftest seam's pinned ``240×50``
    surface (``_plain_cli_console_seam``, autouse and unconditional,
    overriding via rich's explicit-size early return): this file's own
    ``COLUMNS=240`` happens to numerically match the seam's pinned width, but
    the seam's explicit ``console.size`` assignment is what was in effect,
    not this file's env var — the seam wins even where the two values happen
    to agree. Reset in both setup and teardown so this file starts clean and
    never poisons whichever file the worker runs next — mirroring the
    existing ``reset_journal_cache()`` isolation below.
    """
    from specify_cli.auth.manager import reset_token_manager

    reset_token_manager()
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    repo = tmp_path / "checkout"
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)
    (repo / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {TARGET}\n  slug: {TARGET_SLUG}\n  node_id: abcdef123456\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo))
    monkeypatch.setenv("COLUMNS", _WIDE_TERMINAL)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    monkeypatch.chdir(repo)
    reset_journal_cache()
    try:
        yield repo
    finally:
        reset_token_manager()


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #


def _live_paths() -> tuple[Path, Path]:
    from specify_cli.delivery.retention import resolve_live_store_paths

    return resolve_live_store_paths()


def _queue_db_path() -> Path:
    from specify_cli.sync.queue import default_queue_db_path

    return default_queue_db_path()


def _event(event_id: str, project_uuid: str | None, index: int, slug: str | None = None) -> Event:
    payload: dict[str, Any] = {"event_id": event_id, "event_type": "mission.updated"}
    if project_uuid is not None:
        payload["project_uuid"] = project_uuid
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=json.dumps(payload).encode("utf-8"),
        occurred_at="2026-07-27T00:00:00+00:00",
        created_at=f"2026-07-27T00:00:{index:02d}+00:00",
        project_uuid=project_uuid,
        project_slug=slug,
    )


def _seed_journal_and_ledger() -> None:
    """The incident's shape, plus the three populations a targeted purge cannot reach."""
    from specify_cli.delivery.ledger import SqliteDeliveryLedger

    journal_path, ledger_path = _live_paths()
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    journal = EventJournal(journal_path)
    for i in range(3):
        journal.append(_event(f"t-{i}", TARGET, i, TARGET_SLUG))
    for i in range(2):
        journal.append(_event(f"o-{i}", OTHER, 10 + i, OTHER_SLUG))
    journal.append(_event("null-1", None, 20))
    journal.append(_event("blank-1", "", 21))
    journal.append(_event("ws-1", "   ", 22))

    ledger = SqliteDeliveryLedger(str(ledger_path))
    try:
        ledger.record_success("t-0", TARGET_ID)
        ledger.record_rejected("t-1", TARGET_ID, error="not consented")
        # t-2 has no ledger row at all: never attempted.
        ledger.record_success("o-0", TARGET_ID)
        ledger.record_rejected("null-1", TARGET_ID, error="no identity")
        # A ledger row whose journal row is already gone — every machine that has
        # run `sync gc` holds some, because gc preserves ledger history by design.
        ledger.record_rejected("ghost-1", TARGET_ID, error="journal row gc'd")
    finally:
        ledger.close()


def _seed_body_queue() -> None:
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue

    path = _queue_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    OfflineBodyUploadQueue(db_path=path)  # ensures the schema exists
    rows = [
        (TARGET, "acme-migration-01K", "spec.md"),
        (TARGET, "acme-migration-01K", "plan.md"),
        (OTHER, "globex-rollout-01K", "spec.md"),
        # The two unattributable forms, and they are unattributable *differently*:
        # ``remove_project_tasks`` returns 0 for a falsy argument and strips a padded
        # one to the same falsy value, so neither is reachable by a project selector.
        # ``project_uuid`` is NOT NULL, so these two strings are the only forms a row
        # can take that name no project.
        ("", "orphan-mission-01K", "spec.md"),
        ("   ", "orphan-mission-01K", "plan.md"),
    ]
    conn = sqlite3.connect(path)
    try:
        for project_uuid, mission_slug, artifact in rows:
            conn.execute(
                """INSERT INTO body_upload_queue
                   (project_uuid, mission_slug, target_branch, mission_type,
                    manifest_version, artifact_path, content_hash, hash_algorithm,
                    content_body, size_bytes, retry_count, next_attempt_at, created_at)
                   VALUES (?, ?, 'main', 'feature', '1', ?, ?, 'sha256', 'body', 4, 0, 0.0, 0.0)""",
                (project_uuid, mission_slug, artifact, f"{project_uuid}-{artifact}"),
            )
        conn.commit()
    finally:
        conn.close()


def _seed_frames(repo: Path) -> None:
    """Two attributed frames, one other project's, and one pre-fix frame with no uuid."""
    frames = [
        {
            "git_hash": "h-target-1",
            "project_uuid": TARGET,
            "changed_files": [f"kitty-specs/{TARGET_SLUG}-01K/spec.md"],
        },
        {
            "git_hash": "h-target-2",
            "project_uuid": TARGET,
            "changed_files": [f"kitty-specs/{TARGET_SLUG}-01K/plan.md"],
        },
        {
            "git_hash": "h-other-1",
            "project_uuid": OTHER,
            "changed_files": [f"kitty-specs/{OTHER_SLUG}-01K/spec.md"],
        },
        # Pre-fix: WP12 added ``project_uuid`` additively, so the frames the
        # incident actually produced carry none.
        {
            "git_hash": "h-prefix-1",
            "changed_files": [f"kitty-specs/{TARGET_SLUG}-legacy-01K/spec.md"],
        },
    ]
    (repo / ".kittify" / "sync-state.json").write_text(
        json.dumps({"last_saas_confirmed_hash": None, "pending_local_commits": frames}),
        encoding="utf-8",
    )


def _seed_all(repo: Path) -> None:
    _seed_journal_and_ledger()
    _seed_body_queue()
    _seed_frames(repo)


# --------------------------------------------------------------------------- #
# The test's OWN reads of the stores — never the command's report
# --------------------------------------------------------------------------- #


def _journal_by_uuid() -> dict[str | None, int]:
    journal_path, _ = _live_paths()
    if not journal_path.exists():
        return {}
    conn = sqlite3.connect(str(journal_path))
    try:
        return {
            (None if row[0] is None else str(row[0])): int(row[1]) for row in conn.execute("SELECT project_uuid, COUNT(*) FROM event_journal GROUP BY project_uuid")
        }
    finally:
        conn.close()


def _journal_ids() -> set[str]:
    journal_path, _ = _live_paths()
    if not journal_path.exists():
        return set()
    conn = sqlite3.connect(str(journal_path))
    try:
        return {str(row[0]) for row in conn.execute("SELECT event_id FROM event_journal")}
    finally:
        conn.close()


def _ledger_ids() -> list[str]:
    _, ledger_path = _live_paths()
    if not ledger_path.exists():
        return []
    conn = sqlite3.connect(str(ledger_path))
    try:
        return [str(row[0]) for row in conn.execute("SELECT event_id FROM delivery_ledger")]
    finally:
        conn.close()


def _body_by_uuid() -> dict[str, int]:
    path = _queue_db_path()
    if not path.exists():
        return {}
    conn = sqlite3.connect(path)
    try:
        return {str(row[0]): int(row[1]) for row in conn.execute("SELECT project_uuid, COUNT(*) FROM body_upload_queue GROUP BY project_uuid")}
    finally:
        conn.close()


def _frames_by_uuid(repo: Path) -> dict[str | None, int]:
    path = repo / ".kittify" / "sync-state.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    census: dict[str | None, int] = {}
    for frame in data.get("pending_local_commits", []):
        raw = frame.get("project_uuid")
        key = None if raw is None else str(raw)
        census[key] = census.get(key, 0) + 1
    return census


def _snapshot(repo: Path) -> dict[str, Any]:
    return {
        "journal": _journal_by_uuid(),
        "journal_ids": _journal_ids(),
        "ledger": sorted(_ledger_ids()),
        "body": _body_by_uuid(),
        "frames": _frames_by_uuid(repo),
    }


def _report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# FR-016 — dry run is the default
# --------------------------------------------------------------------------- #


class TestDryRunIsTheDefault:
    def test_default_invocation_changes_nothing_in_any_of_the_four_stores(self, checkout: Path, tmp_path: Path) -> None:
        """C-002: the safe direction has to be the one an operator gets by default."""
        _seed_all(checkout)
        before = _snapshot(checkout)
        report = tmp_path / "dry.json"

        result = runner.invoke(app, ["purge", "--project", TARGET, "--report", str(report)])

        assert result.exit_code == 0, result.output
        assert _snapshot(checkout) == before, "a dry run mutated a store"
        data = _report(report)
        assert data["dry_run"] is True
        assert data["applied"] is False

    def test_dry_run_reports_per_state_counts_across_all_four_stores(self, checkout: Path, tmp_path: Path) -> None:
        """FR-016: per-state counts, from every store the project has rows in.

        A purge that reported only the journal would attest "100% of X removed"
        while X's verbatim ``spec.md`` text stayed queued in the body store and its
        engagement name stayed in ``sync-state.json``.
        """
        _seed_all(checkout)
        report = tmp_path / "dry.json"

        result = runner.invoke(app, ["purge", "--project", TARGET, "--report", str(report)])

        assert result.exit_code == 0, result.output
        stores = _report(report)["stores"]
        assert stores["event_journal"]["in_scope"] == 3
        assert stores["delivery_ledger"]["in_scope"] == 2
        assert stores["body_upload_queue"]["in_scope"] == 2
        assert stores["local_commit_frames"]["in_scope"] == 3, "two attributed frames plus the pre-fix frame this checkout vouches for"
        # The forensic breakdown the ledger rows themselves will no longer carry.
        states = stores["delivery_ledger"]["states"]
        assert states["success"] == 1
        assert states["rejected"] == 1
        assert stores["delivery_ledger"]["never_attempted"] == 1

        out = result.output
        assert "DRY RUN" in out
        assert "no rows have been deleted" in out.lower()


# --------------------------------------------------------------------------- #
# FR-016 — the prediction is the deletion
# --------------------------------------------------------------------------- #


def test_dry_run_prediction_equals_what_the_real_run_deletes(checkout: Path, tmp_path: Path) -> None:
    """The preview is the operator's record; if it can drift it is worthless.

    Compared three ways: the dry run's prediction, the applied run's own count, and
    the rows that actually disappear as measured by this test.
    """
    _seed_all(checkout)
    dry_report = tmp_path / "dry.json"
    apply_report = tmp_path / "apply.json"

    dry = runner.invoke(app, ["purge", "--project", TARGET, "--report", str(dry_report)])
    assert dry.exit_code == 0, dry.output
    predicted = {name: store["in_scope"] for name, store in _report(dry_report)["stores"].items()}
    # Positive control: a prediction of all zeros would make the equality below
    # true for the wrong reason.
    assert all(predicted[name] > 0 for name in predicted), predicted

    before = _snapshot(checkout)
    applied = runner.invoke(app, ["purge", "--project", TARGET, "--apply", "--report", str(apply_report)])
    assert applied.exit_code == 0, applied.output
    after = _snapshot(checkout)

    observed = {
        "event_journal": before["journal"].get(TARGET, 0) - after["journal"].get(TARGET, 0),
        "delivery_ledger": len(before["ledger"]) - len(after["ledger"]),
        "body_upload_queue": before["body"].get(TARGET, 0) - after["body"].get(TARGET, 0),
        "local_commit_frames": sum(before["frames"].values()) - sum(after["frames"].values()),
    }
    assert observed == predicted, "the dry run predicted counts the real run did not deliver"

    reported = {name: store["removed_observed"] for name, store in _report(apply_report)["stores"].items()}
    assert reported == predicted


# --------------------------------------------------------------------------- #
# NFR-006 — the differential, measured independently
# --------------------------------------------------------------------------- #


def test_no_other_projects_rows_move_in_any_store(checkout: Path, tmp_path: Path) -> None:
    """NFR-006 / SC-006, measured by this test rather than read off the report."""
    _seed_all(checkout)
    before = _snapshot(checkout)
    report = tmp_path / "apply.json"

    result = runner.invoke(app, ["purge", "--project", TARGET, "--apply", "--report", str(report)])

    assert result.exit_code == 0, result.output
    after = _snapshot(checkout)

    # The target is gone from every store.
    assert TARGET not in after["journal"]
    assert TARGET not in after["body"]
    assert TARGET not in after["frames"]
    assert {"t-0", "t-1", "t-2"}.isdisjoint(after["journal_ids"])
    assert {"t-0", "t-1"}.isdisjoint(set(after["ledger"]))

    # Nothing else moved, in any store.
    assert after["journal"].get(OTHER) == before["journal"].get(OTHER) == 2
    assert after["body"].get(OTHER) == before["body"].get(OTHER) == 1
    assert after["frames"].get(OTHER) == before["frames"].get(OTHER) == 1
    assert "o-0" in after["ledger"]
    assert after["journal"].get(None) == before["journal"].get(None) == 1
    assert after["journal"].get("") == before["journal"].get("") == 1
    assert after["journal"].get("   ") == before["journal"].get("   ") == 1

    data = _report(report)
    assert data["others_delta_total"] == 0
    assert data["nfr_006_satisfied"] is True
    assert "0 rows belonging to any other project" in result.output


# --------------------------------------------------------------------------- #
# Report what a targeted purge cannot reach
# --------------------------------------------------------------------------- #


def test_targeted_purge_names_the_populations_it_leaves_behind(checkout: Path, tmp_path: Path) -> None:
    """A residue nobody names is the same defect as a report that overstates.

    Four known-unreachable populations, all real rather than contrived: a NULL
    identity, a non-NULL blank uuid, a whitespace-only uuid (visible in the census,
    selectable by nothing), and a ledger row whose journal row `sync gc` already
    removed.
    """
    _seed_all(checkout)
    report = tmp_path / "dry.json"

    result = runner.invoke(app, ["purge", "--project", TARGET, "--report", str(report)])

    assert result.exit_code == 0, result.output
    not_reached = {row["population"]: row for row in _report(report)["not_reached"]}

    assert not_reached["journal_identity_null"]["count"] == 1
    assert not_reached["journal_identity_null"]["reachable_by"] == "--identity-less"
    assert not_reached["journal_identity_blank"]["count"] == 2, "the '' row and the whitespace-only row: both unreachable by any selector but --all"
    assert not_reached["journal_identity_blank"]["reachable_by"] == "--all"
    assert not_reached["ledger_without_journal_row"]["count"] == 1
    assert not_reached["ledger_without_journal_row"]["reachable_by"] == "--all"
    assert not_reached["body_uploads_identity_blank"]["count"] == 2, "the '' row and the padded row: remove_project_tasks strips its argument"
    # FR-017 completeness: these rows now HAVE a selector. Before
    # ``purge_all_body_uploads`` existed this said "none", and that was the honest
    # report of a store `--all` could not empty.
    assert not_reached["body_uploads_identity_blank"]["reachable_by"] == "--all"

    out = result.output
    assert "Not reached by this purge" in out
    assert "--identity-less" in out
    assert "--all" in out


def test_unparseable_frame_file_is_reported_not_silently_counted_as_empty(checkout: Path, tmp_path: Path) -> None:
    """``load_sync_state`` resets a malformed file to empty and never raises.

    So the purge primitive would report "0 frames" over a file still holding
    engagement names. The command reads the file itself and says so.
    """
    _seed_journal_and_ledger()
    (checkout / ".kittify" / "sync-state.json").write_text("{not json", encoding="utf-8")
    report = tmp_path / "dry.json"

    result = runner.invoke(app, ["purge", "--project", TARGET, "--report", str(report)])

    assert result.exit_code == 0, result.output
    frames = _report(report)["stores"]["local_commit_frames"]
    assert frames["unreadable"] is True
    assert "could not be read" in result.output


# --------------------------------------------------------------------------- #
# FR-017 — --all, its confirmation and its honest scope
# --------------------------------------------------------------------------- #


class TestPurgeAll:
    def test_apply_all_without_the_confirmation_phrase_deletes_nothing(self, checkout: Path) -> None:
        """C-002: the phrase is the operator's explicit act, and it is not a boolean."""
        _seed_all(checkout)
        before = _snapshot(checkout)

        result = runner.invoke(app, ["purge", "--all", "--apply"])

        assert result.exit_code == 1, result.output
        assert _snapshot(checkout) == before, "a refused --all deleted something"
        # The refusal names the phrase, so the operator never has to guess it.
        assert "purge all events" in result.output

    def test_apply_all_with_the_wrong_phrase_deletes_nothing(self, checkout: Path) -> None:
        _seed_all(checkout)
        before = _snapshot(checkout)

        result = runner.invoke(app, ["purge", "--all", "--apply", "--confirm", "yes"])

        assert result.exit_code == 1, result.output
        assert _snapshot(checkout) == before

    def test_confirmed_all_empties_the_machine_global_stores_and_this_checkout(self, checkout: Path, tmp_path: Path) -> None:
        """Including the three populations no targeted selector could reach."""
        _seed_all(checkout)
        report = tmp_path / "all.json"

        result = runner.invoke(
            app,
            [
                "purge",
                "--all",
                "--apply",
                "--confirm",
                "purge all events",
                "--report",
                str(report),
            ],
        )

        assert result.exit_code == 0, result.output
        after = _snapshot(checkout)
        assert after["journal"] == {}
        assert after["ledger"] == []
        assert after["frames"] == {}
        # Including the body store's blank and padded rows. Until
        # ``purge_all_body_uploads`` existed these survived a confirmed ``--all`` and
        # were reported as reachable by nothing — a total purge that left verbatim
        # engagement documents on disk.
        assert after["body"] == {}
        assert _report(report)["stores"]["body_upload_queue"]["left_behind"] == {}

    def test_all_reaches_the_body_rows_no_targeted_selector_could(self, checkout: Path, tmp_path: Path) -> None:
        """FR-017 completeness for the fourth store, from the operator surface.

        ``remove_project_tasks`` strips its argument and returns 0 for a falsy one, so
        the ``''`` and ``'   '`` rows are reachable by no ``--project`` value at all.
        The dry run must count them **in scope** — a total purge that silently
        excluded them would be the false-totality claim this command exists to avoid —
        and the confirmed run must actually remove them.
        """
        _seed_all(checkout)
        assert {key: count for key, count in _body_by_uuid().items() if not key.strip()} == {
            "": 1,
            "   ": 1,
        }, "precondition: the store holds the rows no project selector reaches"
        dry_report = tmp_path / "dry.json"

        dry = runner.invoke(app, ["purge", "--all", "--report", str(dry_report)])

        assert dry.exit_code == 0, dry.output
        assert _report(dry_report)["stores"]["body_upload_queue"]["in_scope"] == 5, "every row, not just the attributable ones"

        applied = runner.invoke(
            app, ["purge", "--all", "--apply", "--confirm", "purge all events"]
        )

        assert applied.exit_code == 0, applied.output
        assert _body_by_uuid() == {}

    def test_the_all_dry_run_predicts_exactly_what_the_confirmed_run_deletes(self, checkout: Path, tmp_path: Path) -> None:
        """FR-017's preview is the operator's record; if it can drift it is worthless.

        Compared against rows that actually disappear, measured by this test's own
        reads — never against what the purge says about itself (NFR-006).
        """
        _seed_all(checkout)
        dry_report = tmp_path / "dry.json"

        dry = runner.invoke(app, ["purge", "--all", "--report", str(dry_report)])
        assert dry.exit_code == 0, dry.output
        predicted = {name: store["in_scope"] for name, store in _report(dry_report)["stores"].items()}
        # Positive control: an all-zero prediction would satisfy the equality below
        # for the wrong reason.
        assert all(count > 0 for count in predicted.values()), predicted

        before = _snapshot(checkout)
        applied = runner.invoke(
            app, ["purge", "--all", "--apply", "--confirm", "purge all events"]
        )
        assert applied.exit_code == 0, applied.output
        after = _snapshot(checkout)

        observed = {
            "event_journal": sum(before["journal"].values()) - sum(after["journal"].values()),
            "delivery_ledger": len(before["ledger"]) - len(after["ledger"]),
            "body_upload_queue": sum(before["body"].values()) - sum(after["body"].values()),
            "local_commit_frames": sum(before["frames"].values()) - sum(after["frames"].values()),
        }
        assert observed == predicted, "the --all dry run predicted counts the real run did not deliver"

    def test_all_names_the_per_checkout_scope_and_claims_nothing_wider(self, checkout: Path) -> None:
        """The operator decision of 2026-07-30, in the operator's own output.

        One call clears only the invoking checkout's frame queue and there is no
        registry that could enumerate the others. "Erased" that silently means
        "erased here" is the same class of defect as a gate reporting success for
        having done nothing.
        """
        _seed_all(checkout)

        result = runner.invoke(app, ["purge", "--all"])

        assert result.exit_code == 0, result.output
        flat = " ".join(result.output.split())
        assert "this checkout only" in flat
        assert str(checkout / ".kittify" / "sync-state.json") in flat
        assert "other checkouts" in flat.lower()
        assert "every checkout" not in flat.lower()

    def test_help_does_not_promise_machine_wide_erasure(self) -> None:
        result = runner.invoke(app, ["purge", "--help"])

        assert result.exit_code == 0, result.output
        flat = " ".join(result.output.split()).lower()
        assert "--all" in flat
        for overclaim in ("everything on this machine", "all checkouts", "machine-wide"):
            assert overclaim not in flat, f"--all is advertised as {overclaim!r}"


def test_applied_run_says_the_two_stores_are_not_one_transaction(
    checkout: Path,
) -> None:
    """The ledger delete commits first; the journal is untouched on failure.

    A report that implied atomicity would leave an operator with no reason to
    re-run after an interruption — and a re-run is exactly what converges.
    """
    _seed_all(checkout)

    result = runner.invoke(app, ["purge", "--project", TARGET, "--apply"])

    assert result.exit_code == 0, result.output
    flat = " ".join(result.output.split()).lower()
    assert "not one transaction" in flat
    assert "re-run" in flat


# --------------------------------------------------------------------------- #
# Selector resolution
# --------------------------------------------------------------------------- #


class TestSelectorResolution:
    def test_a_slug_resolves_to_the_projects_uuid(self, checkout: Path, tmp_path: Path) -> None:
        """FR-016 takes a slug *or* a uuid; an operator knows the engagement name."""
        _seed_all(checkout)
        report = tmp_path / "dry.json"

        result = runner.invoke(app, ["purge", "--project", TARGET_SLUG, "--report", str(report)])

        assert result.exit_code == 0, result.output
        data = _report(report)
        assert data["selector"]["project_uuid"] == TARGET
        assert data["selector"]["matched_slug"] == TARGET_SLUG
        assert data["stores"]["event_journal"]["in_scope"] == 3

    def test_an_unknown_slug_refuses_instead_of_purging_nothing(self, checkout: Path) -> None:
        """ "0 rows removed" is indistinguishable from "wrong selector"."""
        _seed_all(checkout)
        before = _snapshot(checkout)

        result = runner.invoke(app, ["purge", "--project", "no-such-engagement", "--apply"])

        assert result.exit_code == 2, result.output
        assert _snapshot(checkout) == before
        assert "no-such-engagement" in result.output

    def test_a_uuid_spelled_in_the_wrong_case_refuses_and_names_the_stored_spelling(self, checkout: Path) -> None:
        """The journal matches a uuid exactly; the frame store casefolds.

        So an upper-cased selector would purge frames while leaving journal rows,
        and report "0 journal rows in scope" as though the project were clean.
        """
        _seed_all(checkout)
        before = _snapshot(checkout)

        result = runner.invoke(app, ["purge", "--project", TARGET.upper(), "--apply"])

        assert result.exit_code == 2, result.output
        assert _snapshot(checkout) == before
        assert TARGET in result.output

    def test_identity_less_selector_takes_the_null_rows_and_says_what_it_omits(self, checkout: Path, tmp_path: Path) -> None:
        _seed_all(checkout)
        before = _snapshot(checkout)
        report = tmp_path / "il.json"

        result = runner.invoke(app, ["purge", "--identity-less", "--apply", "--report", str(report)])

        assert result.exit_code == 0, result.output
        after = _snapshot(checkout)
        assert None not in after["journal"], "the NULL-identity row survived"
        assert "null-1" not in after["ledger"]
        # Blank and whitespace uuids are NOT this selector's population.
        assert after["journal"].get("") == 1
        assert after["journal"].get("   ") == 1
        # Nothing attributed moved.
        assert after["journal"].get(TARGET) == before["journal"].get(TARGET) == 3
        assert after["journal"].get(OTHER) == before["journal"].get(OTHER) == 2
        assert after["body"] == before["body"], "this selector does not span the body queue"
        assert after["frames"] == before["frames"]

        stores = _report(report)["stores"]
        assert stores["body_upload_queue"]["in_scope"] == 0
        assert stores["local_commit_frames"]["in_scope"] == 0
        assert "--all" in result.output

    @pytest.mark.parametrize(
        ("argv", "expected"),
        [
            ([], "exactly one of"),
            (["--project", TARGET, "--all"], "mutually exclusive"),
            (["--project", TARGET, "--identity-less"], "mutually exclusive"),
            (["--all", "--identity-less"], "mutually exclusive"),
            (["--project", TARGET, "--apply", "--dry-run"], "mutually exclusive"),
        ],
    )
    def test_selector_misuse_is_a_usage_error_that_deletes_nothing(self, checkout: Path, argv: list[str], expected: str) -> None:
        """The expected text is asserted so "no such command" cannot pass as a refusal."""
        _seed_all(checkout)
        before = _snapshot(checkout)

        result = runner.invoke(app, ["purge", *argv])

        assert result.exit_code == 2, result.output
        assert expected in result.output
        assert _snapshot(checkout) == before


# --------------------------------------------------------------------------- #
# C-002 — unreachable from an unattended path
# --------------------------------------------------------------------------- #


def test_the_cli_and_local_commit_agree_on_where_frames_live(tmp_path: Path) -> None:
    """The CLI duplicates ``local_commit._sync_state_path``'s layout to report it.

    Pinned rather than trusted, exactly as ``retention.py`` pins its duplicate of the
    delivery-store layout: a relocation must be a red, not a purge report that names
    a file nobody writes.
    """
    from specify_cli.cli.commands import sync as sync_module
    from specify_cli.sync import local_commit

    assert local_commit._sync_state_path(tmp_path) == tmp_path / sync_module._PURGE_SYNC_STATE_RELPATH


def test_no_unattended_caller_of_the_total_purge_primitives() -> None:
    """The `--all` primitives may be reached from the operator command and nowhere else.

    ``purge_project_events_from_live_stores`` is deliberately excluded: it has one
    live caller, ``sync/routing.py``'s opt-out, which is itself an operator action.
    """
    src = Path(__file__).resolve().parents[3] / "src" / "specify_cli"
    allowed = {
        src / "cli" / "commands" / "sync.py",
        src / "delivery" / "retention.py",
        src / "sync" / "local_commit.py",
    }
    for symbol in (
        "purge_all_events",
        "purge_all_pending_local_commits",
        "purge_identity_less_events",
        "purge_pending_local_commits",
        "purge_project_body_uploads",
    ):
        callers = {path for path in src.rglob("*.py") if f"{symbol}(" in path.read_text(encoding="utf-8")}
        assert callers <= allowed, f"{symbol} gained an unattended caller: {callers - allowed}"
