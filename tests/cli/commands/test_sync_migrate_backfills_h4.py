"""H4: the two backfills must have a production caller, not just tests.

`backfill_journal_identity` and `backfill_uuid_consent_index` were referenced only
from `tests/`. No CLI command, no schema hook, no daemon path ran either, so on a
real machine:

1. every pre-mission journal row keeps ``project_uuid IS NULL``, and
   ``delivery/selection.py`` makes NULL permanently unselectable — so the
   operator's OWN CONSENTED project's history (7,811 events in the incident) never
   ships again; and
2. a user whose only consent record is path-keyed (``checkout_overrides[path]``)
   gets no uuid record, so the drain's level-2 lookup cannot see their consent.

Both fail CLOSED. The symptom is a consenting project silently not delivering, not
a non-consenting project shipping — a data-availability defect wearing a security
fix's clothes, which reads to an operator as "sync is broken", not "sync is safe".

These tests drive the COMMAND. A test that calls the backfill directly proves the
function works, which was never in doubt and is already covered elsewhere; it says
nothing about whether anything invokes it.
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

CONSENTED = "aaaaaaaa-0000-0000-0000-00000000000a"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    monkeypatch.setenv("COLUMNS", "220")
    from specify_cli.event_journal.journal import reset_journal_cache

    reset_journal_cache()


def _journal() -> EventJournal:
    """The journal `sync migrate` itself resolves, at the same producer scope."""
    scope = sync_module._current_event_sync_scope()
    return EventJournal(
        resolve_journal_path(user_id=scope.user_id, team_slug=scope.team_slug)
    )


def _seed_pre_mission_row(journal: EventJournal, event_id: str = "evt-legacy") -> None:
    """A row written before the identity columns existed.

    The uuid IS recoverable — it is in the stored envelope, which is what makes
    stranding it a defect rather than a limitation. Only the COLUMN is NULL.
    """
    journal.append(
        Event(
            event_id=event_id,
            event_type="WorkPackageApproved",
            payload=json.dumps(
                {
                    "event_id": event_id,
                    "namespace": {
                        "project_uuid": CONSENTED,
                        "project_slug": "engagement-assistant",
                    },
                    "repo_slug": "my-org/engagement-assistant",
                }
            ).encode("utf-8"),
            occurred_at="2026-06-01T00:00:00+00:00",
            created_at="2026-06-01T00:00:00+00:00",
            project_uuid=None,
            project_slug=None,
            repo_slug=None,
        )
    )


def test_sync_migrate_backfills_identity_onto_pre_mission_rows() -> None:
    """H4(1): `sync migrate` must converge identity columns, not just import rows.

    Red before the fix: the row stayed ``project_uuid IS NULL`` after the command,
    so `delivery/selection.py` could never select it — the operator's own
    consented history, permanently undeliverable, with nothing anywhere running the
    backfill that would recover it.
    """
    journal = _journal()
    _seed_pre_mission_row(journal)

    # Preconditions and assertions are both stated about THIS ROW, by id, rather
    # than about an aggregate count. `count_missing_identity() == 0` is satisfiable
    # by a journal holding a different population than the one the test seeded — it
    # says how many rows are NULL, never which. The row-identity form cannot pass
    # for a reason the test did not name, and it additionally pins that the
    # recovered values are the ones from THIS row's envelope rather than any
    # plausible-looking uuid. The aggregate is still asserted, last, as a
    # whole-journal cross-check.
    before = journal.read_by_id("evt-legacy")
    assert before is not None, "precondition: the row was seeded"
    assert before.project_uuid is None, "precondition: its identity column is NULL"
    assert before.project_slug is None
    assert before.repo_slug is None

    result = runner.invoke(app, ["migrate"])
    assert result.exit_code == 0, result.output

    after = journal.read_by_id("evt-legacy")
    assert after is not None, "the row must survive the migration (C-002)"
    assert after.project_uuid == CONSENTED, (
        "`sync migrate` must project the stored envelope's identity into the "
        "columns — otherwise a consenting project's own history stays "
        "permanently unselectable"
    )
    assert after.project_slug == "engagement-assistant"
    assert after.repo_slug == "my-org/engagement-assistant"
    # The payload is never rewritten to achieve this (FR-001 / IC-02).
    assert after.payload == before.payload
    assert journal.count_missing_identity() == 0


def test_sync_migrate_reports_what_the_identity_backfill_recovered() -> None:
    """An operator must be able to see it happened, not infer it from behaviour."""
    _seed_pre_mission_row(_journal())

    result = runner.invoke(app, ["migrate"])

    assert result.exit_code == 0, result.output
    out = " ".join(result.output.split())
    assert "identity" in out.lower()
    assert "1" in out


def test_sync_migrate_identity_backfill_is_idempotent() -> None:
    """The convergence contract: a second run is a no-op, not a rewrite."""
    journal = _journal()
    _seed_pre_mission_row(journal)

    first = runner.invoke(app, ["migrate"])
    assert first.exit_code == 0, first.output
    stored = journal.read_by_id("evt-legacy")
    assert stored is not None

    second = runner.invoke(app, ["migrate"])
    assert second.exit_code == 0, second.output

    again = journal.read_by_id("evt-legacy")
    assert again is not None
    # Bytes never rewritten (FR-001/IC-02), identity unchanged, nothing re-counted.
    assert again.payload == stored.payload
    assert again.project_uuid == stored.project_uuid
    assert journal.count_missing_identity() == 0
    assert "recovered 0" in " ".join(second.output.split())


def test_sync_migrate_leaves_a_genuinely_unresolvable_row_null() -> None:
    """Fail-closed is preserved: an unrecoverable row must NOT be invented into one.

    The backfill's value is recovering identity that is already stored. A row whose
    envelope carries none must stay NULL — unselectable — rather than being
    assigned a uuid so it can ship.
    """
    journal = _journal()
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

    result = runner.invoke(app, ["migrate"])

    assert result.exit_code == 0, result.output
    row = journal.read_by_id("evt-opaque")
    assert row is not None, "an unreadable payload must not cost the row (C-002)"
    assert row.project_uuid is None, (
        "identity must only ever be RECOVERED from the stored envelope, never "
        "invented — inventing one here would make the row deliverable"
    )
    assert journal.count_missing_identity() == 1


# --- H4(2): the uuid consent index, behind an explicit opt-in ----------------
#
# This backfill WRITES machine-global consent records, and the uuid index is
# consulted at level 2 — ABOVE the repo default at level 3. So migrating a
# path-keyed record can CHANGE the effective answer: a project currently denied by
# a repo default becomes granted once its path record lands in the index. On a P0
# confidentiality mission a migration must never silently flip delivery on, so the
# write is opt-in and reports its per-project deltas. The identity backfill above
# needs no flag because it cannot grant anything — selection still requires a
# consent record.


def _write_path_keyed_consent(checkout: Path, *, enabled: bool = True) -> None:
    """Record consent the old way: path-keyed, with no uuid record anywhere."""
    from specify_cli.sync.config import SyncConfig

    SyncConfig().set_checkout_sync_enabled(checkout, enabled)


def _declare_project_uuid(checkout: Path, project_uuid: str) -> None:
    checkout.mkdir(parents=True, exist_ok=True)
    (checkout / ".kittify").mkdir(parents=True, exist_ok=True)
    (checkout / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {project_uuid}\n", encoding="utf-8"
    )


def test_plain_migrate_never_writes_the_consent_index(tmp_path: Path) -> None:
    """The default must not touch consent records — that is the whole opt-in point."""
    from specify_cli.sync.config import SyncConfig

    checkout = tmp_path / "checkout"
    _declare_project_uuid(checkout, CONSENTED)
    _write_path_keyed_consent(checkout)
    assert SyncConfig().get_all_project_consent() == {}

    result = runner.invoke(app, ["migrate"])

    assert result.exit_code == 0, result.output
    assert SyncConfig().get_all_project_consent() == {}, (
        "a migration that silently rewrote consent records would be exactly the "
        "kind of invisible consent change this mission exists to stop"
    )


def test_migrate_with_the_flag_maps_path_keyed_consent_onto_the_uuid_index(
    tmp_path: Path,
) -> None:
    """H4(2): red before the fix — nothing ran the backfill, so the flag's work
    never happened and an existing user's consent stayed invisible to the drain's
    level-2 lookup.
    """
    from specify_cli.sync.config import SyncConfig

    checkout = tmp_path / "checkout"
    _declare_project_uuid(checkout, CONSENTED)
    _write_path_keyed_consent(checkout)

    result = runner.invoke(app, ["migrate", "--backfill-consent-index"])

    assert result.exit_code == 0, result.output
    assert SyncConfig().get_all_project_consent() == {CONSENTED: True}
    out = " ".join(result.output.split())
    assert "consent index" in out.lower()
    # The delta is named, so the operator sees WHICH project changed.
    assert CONSENTED in out


def test_the_consent_backfill_reports_records_it_could_not_resolve(
    tmp_path: Path,
) -> None:
    """The deferred WP07 contract bullet: `unresolved`-consent rows must render.

    A path record whose checkout no longer declares a uuid keeps its entry and is
    marked unresolved — the operator's decision is not lost, but the uuid-keyed
    predicate cannot see it. US2 scenario 3 promises this is surfaced; before the
    backfill was wired, no such row could exist to surface.
    """
    gone = tmp_path / "deleted-checkout"
    gone.mkdir(parents=True, exist_ok=True)
    _write_path_keyed_consent(gone)  # no .kittify/config.yaml -> unresolvable

    result = runner.invoke(app, ["migrate", "--backfill-consent-index"])

    assert result.exit_code == 0, result.output
    out = " ".join(result.output.split())
    assert "unresolved" in out.lower()
    assert str(gone) in out or gone.name in out


def test_the_consent_backfill_is_idempotent(tmp_path: Path) -> None:
    """A converged index reports zero mapped on the second run."""
    checkout = tmp_path / "checkout"
    _declare_project_uuid(checkout, CONSENTED)
    _write_path_keyed_consent(checkout)

    first = runner.invoke(app, ["migrate", "--backfill-consent-index"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["migrate", "--backfill-consent-index"])
    assert second.exit_code == 0, second.output
    assert "mapped 0" in " ".join(second.output.split())


def test_an_opted_out_path_record_maps_as_a_refusal(tmp_path: Path) -> None:
    """The flag must carry a refusal across as faithfully as a grant.

    Mapping only the grants would turn an explicit opt-out into an absent record,
    which the resolver reads as "absent" — a weaker denial than the operator chose,
    and one a later repo default could override.
    """
    from specify_cli.sync.config import SyncConfig

    checkout = tmp_path / "refused"
    _declare_project_uuid(checkout, CONSENTED)
    _write_path_keyed_consent(checkout, enabled=False)

    result = runner.invoke(app, ["migrate", "--backfill-consent-index"])

    assert result.exit_code == 0, result.output
    assert SyncConfig().get_all_project_consent() == {CONSENTED: False}
