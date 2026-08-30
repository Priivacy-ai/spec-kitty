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
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.sync import app
from specify_cli.event_journal.journal import EventJournal, reset_journal_cache
from specify_cli.event_journal.models import Event
from specify_cli.sync.project_store import ProjectSyncStore
from tests._support.ansi import strip_ansi

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

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
    from specify_cli.sync.project_store import ProjectSyncStore
    import specify_cli.sync.routing as routing

    target_store = ProjectSyncStore(TARGET)
    authority = target_store.layout_generation()
    authority.begin_cutover("purge-cli")
    authority.publish_project_only("purge-cli", verify_exact=lambda: True)
    for project_uuid in (TARGET, OTHER):
        with ProjectSyncStore(project_uuid).unit_of_work():
            pass
    monkeypatch.setattr(
        routing,
        "resolve_checkout_sync_routing_readonly",
        lambda: type(
            "Routing",
            (),
            {
                "project_uuid": target_store.project_uuid,
                "project_slug": TARGET_SLUG,
                "repo_slug": None,
                "build_id": None,
            },
        )(),
    )
    reset_journal_cache()
    try:
        yield repo
    finally:
        reset_token_manager()


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #


def _stores() -> tuple[Any, Any]:
    from specify_cli.sync.project_store import ProjectSyncStore

    return ProjectSyncStore(TARGET), ProjectSyncStore(OTHER)


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
    """Seed two physically isolated project stores plus a target ledger ghost."""
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.sync.consent import record_project_opt_in

    target_store, other_store = _stores()
    for project_uuid in (TARGET, OTHER):
        record_project_opt_in(project_uuid, actor="purge-cli-test")
    with target_store.unit_of_work() as unit:
        journal = EventJournal(unit, target_store.layout_generation())
        for i in range(3):
            journal.append(_event(f"t-{i}", TARGET, i, TARGET_SLUG))
        ledger = SqliteDeliveryLedger(unit, target_store.layout_generation())
        ledger.record_success("t-0", TARGET_ID)
        ledger.record_rejected("t-1", TARGET_ID, error="not consented")
        # t-2 has no result: never attempted.
    with other_store.unit_of_work() as unit:
        journal = EventJournal(unit, other_store.layout_generation())
        for i in range(2):
            journal.append(_event(f"o-{i}", OTHER, 10 + i, OTHER_SLUG))
        ledger = SqliteDeliveryLedger(unit, other_store.layout_generation())
        ledger.record_success("o-0", TARGET_ID)


def _seed_body_queue() -> None:
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue
    from specify_cli.sync.namespace import NamespaceRef

    target_store, other_store = _stores()
    for store, project_uuid, mission_slug, artifacts in (
        (target_store, TARGET, "acme-migration-01K", ("spec.md", "plan.md")),
        (other_store, OTHER, "globex-rollout-01K", ("spec.md",)),
    ):
        with store.unit_of_work() as unit:
            queue = OfflineBodyUploadQueue(unit, store.layout_generation())
            for artifact in artifacts:
                queue.enqueue(
                    NamespaceRef(project_uuid, mission_slug, "main", "software-dev", "1"),
                    artifact,
                    f"{project_uuid}-{artifact}",
                    "body",
                    4,
                )


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
    result: dict[str | None, int] = {}
    for store in _stores():
        with store.unit_of_work() as unit:
            count = EventJournal(unit, store.layout_generation()).count()
            if count:
                result[str(store.project_uuid.storage_token)] = count
    return result


def _journal_ids() -> set[str]:
    result: set[str] = set()
    for store in _stores():
        with store.unit_of_work() as unit:
            result.update(event.event_id for event in EventJournal(unit, store.layout_generation()).read_all())
    return result


def _ledger_ids() -> list[str]:
    from specify_cli.delivery.ledger import SqliteDeliveryLedger

    result: list[str] = []
    for store in _stores():
        with store.unit_of_work() as unit:
            result.extend(
                row.event_id
                for row in SqliteDeliveryLedger(
                    unit,
                    store.layout_generation(),
                ).rows()
            )
    return result


def _body_by_uuid() -> dict[str, int]:
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue

    result: dict[str, int] = {}
    for store in _stores():
        with store.unit_of_work() as unit:
            result.update(
                OfflineBodyUploadQueue(
                    unit,
                    store.layout_generation(),
                ).count_by_project()
            )
    return result


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
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- #
# FR-016 — dry run is the default
# --------------------------------------------------------------------------- #


class TestDryRunIsTheDefault:
    def test_default_invocation_changes_nothing_in_any_of_the_four_stores(
        self,
        checkout: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """C-002: the safe direction has to be the one an operator gets by default."""
        _seed_all(checkout)
        before = _snapshot(checkout)
        report = tmp_path / "dry.json"
        from specify_cli.identity import project as identity_module
        from specify_cli.sync import queue as queue_module

        original_load = identity_module.load_identity
        original_get_max_queue_size = queue_module.get_max_queue_size
        identity_reads = 0
        max_queue_reads = 0

        def load_with_lock_probe(path: Path) -> Any:
            nonlocal identity_reads
            identity_reads += 1
            # Filesystem identity resolution must happen before purge owns the
            # active store write transaction.
            with ProjectSyncStore(TARGET).unit_of_work(lock_timeout_seconds=0):
                pass
            return original_load(path)

        def max_queue_size_with_lock_probe() -> int:
            nonlocal max_queue_reads
            max_queue_reads += 1
            with ProjectSyncStore(TARGET).unit_of_work(lock_timeout_seconds=0):
                pass
            return cast(int, cast(Any, original_get_max_queue_size)())

        monkeypatch.setattr(identity_module, "load_identity", load_with_lock_probe)
        monkeypatch.setattr(queue_module, "get_max_queue_size", max_queue_size_with_lock_probe)

        result = runner.invoke(app, ["purge", "--project", TARGET, "--report", str(report)])

        assert result.exit_code == 0, result.output
        assert _snapshot(checkout) == before, "a dry run mutated a store"
        data = _report(report)
        assert data["dry_run"] is True
        assert data["applied"] is False
        assert identity_reads == 1
        assert max_queue_reads == 1

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
        assert "ledger rows would be deleted" in out.lower()
        assert "ledger rows are deleted" not in out.lower()


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
    # Project stores cannot contain unbound identity rows; the old global
    # journal fixture fabricated them. Their absence is part of the authority
    # invariant, not a missing purge population.
    assert not any(key is None or not str(key).strip() for key in after["journal"])

    data = _report(report)
    assert data["others_delta_total"] == 0
    assert data["nfr_006_satisfied"] is True
    assert "0 rows belonging to any other project" in result.output


# --------------------------------------------------------------------------- #
# Report what a targeted purge cannot reach
# --------------------------------------------------------------------------- #


def test_targeted_purge_names_the_populations_it_leaves_behind(checkout: Path, tmp_path: Path) -> None:
    """The report never invents unbound live rows or claims another store."""
    _seed_all(checkout)
    report = tmp_path / "dry.json"

    result = runner.invoke(app, ["purge", "--project", TARGET, "--report", str(report)])

    assert result.exit_code == 0, result.output
    not_reached = {row["population"]: row for row in _report(report)["not_reached"]}

    assert "journal_identity_null" not in not_reached
    assert "journal_identity_blank" not in not_reached
    assert "body_uploads_identity_blank" not in not_reached
    assert _snapshot(checkout)["journal"].get(OTHER) == 2

    out = result.output
    assert "identity_null" not in out
    assert "identity_blank" not in out


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


def test_unparseable_frame_file_refuses_apply_before_any_store_changes(checkout: Path) -> None:
    """Every destructive boundary is preflighted before the shared UoW mutates."""
    _seed_all(checkout)
    frame_path = checkout / ".kittify" / "sync-state.json"
    frame_path.write_bytes(b"{not json")
    journal_before = _journal_by_uuid()
    ledger_before = sorted(_ledger_ids())
    body_before = _body_by_uuid()
    frame_before = frame_path.read_bytes()

    result = runner.invoke(app, ["purge", "--project", TARGET, "--apply"])

    assert result.exit_code == 2, result.output
    assert "refusing before any project-store or frame deletion" in result.output
    assert _journal_by_uuid() == journal_before
    assert sorted(_ledger_ids()) == ledger_before
    assert _body_by_uuid() == body_before
    assert frame_path.read_bytes() == frame_before


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
        """Confirmed --all empties only the active project and this checkout."""
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
        assert after["journal"] == {OTHER: 2}
        assert set(after["ledger"]) == {"o-0"}
        assert after["frames"] == {}
        # Including the body store's blank and padded rows. Until
        # ``purge_all_body_uploads`` existed these survived a confirmed ``--all`` and
        # were reported as reachable by nothing — a total purge that left verbatim
        # engagement documents on disk.
        assert after["body"] == {OTHER: 1}
        assert _report(report)["stores"]["body_upload_queue"]["left_behind"] == {}

    def test_all_reaches_the_body_rows_no_targeted_selector_could(self, checkout: Path, tmp_path: Path) -> None:
        """The active-project body purge cannot cross-open another store."""
        _seed_all(checkout)
        assert _body_by_uuid() == {TARGET: 2, OTHER: 1}
        dry_report = tmp_path / "dry.json"

        dry = runner.invoke(app, ["purge", "--all", "--report", str(dry_report)])

        assert dry.exit_code == 0, dry.output
        assert _report(dry_report)["stores"]["body_upload_queue"]["in_scope"] == 2

        applied = runner.invoke(app, ["purge", "--all", "--apply", "--confirm", "purge all events"])

        assert applied.exit_code == 0, applied.output
        assert _body_by_uuid() == {OTHER: 1}

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
        applied = runner.invoke(app, ["purge", "--all", "--apply", "--confirm", "purge all events"])
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
        # Rich force-enables terminal styling under CI (``GITHUB_ACTIONS`` is
        # always set) even though CliRunner captures to a non-TTY buffer, and
        # its option highlighter emits the leading ``--`` as a separately
        # styled span from the rest of the flag name. A raw substring check
        # on the coloured output then misses ``--all`` even though it is
        # exposed in the plain text the user actually reads — strip the SGR
        # codes first so the assertion pins the contract, not the renderer.
        flat = " ".join(strip_ansi(result.output).split()).lower()
        assert "--all" in flat
        for overclaim in ("everything on this machine", "all checkouts", "machine-wide"):
            assert overclaim not in flat, f"--all is advertised as {overclaim!r}"


def test_applied_run_says_the_two_stores_are_not_one_transaction(
    checkout: Path,
) -> None:
    """The report states the local transaction and frame-file boundary."""
    _seed_all(checkout)

    result = runner.invoke(app, ["purge", "--project", TARGET, "--apply"])

    assert result.exit_code == 0, result.output
    flat = " ".join(result.output.split()).lower()
    assert "one local database transaction" in flat
    assert "checkout-local frames are a separate file boundary" in flat
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
        assert after == before, "canonical project stores contain no identity-less live rows"

        stores = _report(report)["stores"]
        assert stores["body_upload_queue"]["in_scope"] == 0
        assert stores["local_commit_frames"]["in_scope"] == 0
        assert "Nothing matched" in result.output
        assert "no rows matched or were removed" in result.output.lower()
        assert "rows have been deleted" not in result.output.lower()

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
        # WP06 relocated the journal/ledger + body executors (which invoke the
        # total-purge primitives) out of the ``purge`` shell into this seam
        # module. It is reached only by the operator ``purge`` command, so the
        # primitives keep their operator-attended-only reachability.
        src / "sync" / "sync_purge_exec.py",
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
