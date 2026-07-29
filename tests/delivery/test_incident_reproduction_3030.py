"""T001/SC-001: the 2026-07-27 incident, reproduced at its own shape (#3030).

SC-001 is the mission's primary success criterion and it names a specific
fixture: *six* projects, **one** consented, the other **five carrying no consent
record at all** — then "delivers events from exactly the consented project".

Why this exists alongside ``test_dispatch_project_consent_3030.py``, which pins
the same class with two projects: that file proves the leak *exists*. This one
proves the *incident* is closed, and the difference is not cosmetic.

- **Five silent projects, not one.** The incident's five client repos were never
  opted in, so none had a record. A predicate that special-cases a single
  unknown project, or that resolves "the other one" by elimination against the
  consented slug, passes a two-project fixture and leaks four projects here.
- **A per-project count, not a boolean.** The incident shipped 1,322 events from
  five projects alongside 7,811 from the intended one. Asserting "the sibling's
  one event did not ship" cannot distinguish "filtered correctly" from "dropped
  the tail of a batch". This file groups delivered events *by project* and
  requires every non-consenting group to be empty and the consenting group to be
  whole.
- **An explicit opt-out and an identity-less event are included.** The incident
  population was not homogeneous, and NFR-001 is a subset invariant precisely
  because identity-less events collapse to ``{None}`` and would satisfy a
  cardinality check while leaking.

RED until WP06 lands the filtered read (FR-007/FR-008). It is red *for the right
reason*: the drain has no notion of project identity, so it ships the whole
journal. Landing a failing reproduction for an accepted P0 is the charter's
red-main discipline (standing order 9), not an oversight.

Note on why capture gating (T006) does not already satisfy this: T006 stops
*new* non-consenting captures, but a real machine's journal already holds weeks
of rows written before it landed — the incident's own 1,322 are still on disk —
plus rows captured while a project was consented and later revoked. Those rows
are seeded here through a capture gate that writes but leaves the row
machine-blocked, which is exactly that population. The drain predicate is what
must exclude them.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import StubReceiver
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal import (
    CaptureGateState,
    get_journal,
    reset_coalesce_strategy,
    reset_journal_cache,
)
from specify_cli.sync.project_identity import resolve_event_project_uuid

if TYPE_CHECKING:
    from specify_cli.sync.emitter import EventEmitter

pytestmark = [pytest.mark.regression, pytest.mark.fast]

#: The one project the operator actually opted in — the incident's 7,811 events.
CONSENTED_REPO = "my-org/engagement-assistant"

#: The five that were never opted in — the incident's 1,322 leaked events. None
#: of these gets a consent record: absence of a decision, not a refusal, is what
#: the incident turned on.
SILENT_REPOS = (
    "client-a/confidential-audit",
    "client-b/merger-diligence",
    "client-c/payroll-migration",
    "client-d/security-review",
    "client-e/board-reporting",
)

#: One project that explicitly opted OUT. Distinct from silence and must also
#: never ship.
OPTED_OUT_REPO = "client-f/explicitly-declined"

EVENTS_PER_PROJECT = 3


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """One shared runtime home — the machine-global journal is the premise."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    reset_journal_cache()
    reset_coalesce_strategy()
    yield
    reset_journal_cache()
    reset_coalesce_strategy()


def _write_consent(home: Path) -> None:
    """Consent for the ONE project; an explicit opt-out for one other.

    The five silent repos are deliberately absent from this file entirely.
    """
    lines = [f'[sync.repo_defaults."{CONSENTED_REPO}"]', "enabled = true", ""]
    lines += [f'[sync.repo_defaults."{OPTED_OUT_REPO}"]', "enabled = false", ""]
    (home / "config.toml").write_text("\n".join(lines), encoding="utf-8")


def _captured_but_machine_blocked(_team_slug: str | None) -> CaptureGateState:
    """Write the row, leave it machine-gate-blocked (pre-T006 history)."""
    return CaptureGateState(
        saas_enabled=False, checkout_enabled=True, authenticated=False, team_slug=None
    )


def _open_gate(_team_slug: str | None) -> CaptureGateState:
    """A genuinely deliverable row for the consented project."""
    return CaptureGateState(
        saas_enabled=True, checkout_enabled=True, authenticated=True, team_slug="team"
    )


def _emitter(
    *, project_slug: str, repo_slug: str | None, open_gate: bool
) -> EventEmitter:
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    em = EventEmitter()
    em._identity = SimpleNamespace(
        build_id=f"build-{project_slug}", project_uuid=uuid4(), project_slug=project_slug
    )
    em._get_git_metadata = lambda: GitMetadata(repo_slug=repo_slug)
    em._capture_gate_state = _open_gate if open_gate else _captured_but_machine_blocked
    return em


def _emit_batch(em: EventEmitter, *, n: int = EVENTS_PER_PROJECT) -> list[str]:
    ids: list[str] = []
    for i in range(n):
        envelope = em._emit(
            event_type="ErrorLogged",
            aggregate_id=f"WP{i:02d}",
            aggregate_type="WorkPackage",
            payload={"error_type": "runtime", "error_message": "boom", "wp_id": f"WP{i:02d}"},
        )
        assert envelope is not None
        ids.append(envelope["event_id"])
    return ids


def test_sc001_only_the_consented_project_is_delivered(tmp_path: Path) -> None:
    """SC-001: six projects, one consented — only that project's events ship."""
    _write_consent(tmp_path)

    consented = _emitter(
        project_slug="engagement-assistant", repo_slug=CONSENTED_REPO, open_gate=True
    )
    consented_ids = set(_emit_batch(consented))

    silent_ids: dict[str, set[str]] = {}
    for repo in SILENT_REPOS:
        em = _emitter(
            project_slug=repo.split("/")[1], repo_slug=repo, open_gate=False
        )
        silent_ids[repo] = set(_emit_batch(em))

    opted_out = _emitter(
        project_slug="explicitly-declined", repo_slug=OPTED_OUT_REPO, open_gate=False
    )
    opted_out_ids = set(_emit_batch(opted_out))

    # An identity-less capture: NFR-001 is a subset invariant because these
    # collapse to {None} and would satisfy a cardinality check while leaking.
    identityless = _emitter(project_slug=None, repo_slug=None, open_gate=False)
    identityless._identity = SimpleNamespace(
        build_id="build-anon", project_uuid=None, project_slug=None
    )
    identityless_ids = set(_emit_batch(identityless, n=1))

    journal = get_journal(team_slug=None)

    # Premise: every project shares ONE journal file. Asserted before draining,
    # so a fixture that accidentally isolated them cannot fake a pass.
    all_seeded = (
        consented_ids
        | set().union(*silent_ids.values())
        | opted_out_ids
        | identityless_ids
    )
    stored = {e.event_id for e in journal.read_all()}
    assert all_seeded <= stored, (
        "every project's events must land in the same producer-scoped journal "
        "for this to reproduce the incident's shared-store premise"
    )

    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = registry.register(
        url="https://hosted.example.com",
        team_slug="team",
        user_email="operator@example.com",
    )
    receiver = StubReceiver()

    dispatch(journal=journal, ledger=ledger, receiver=receiver, target=target)
    delivered = set(receiver.received_event_ids())

    # The consenting project must be whole — a filter that starves the drain is
    # not a fix (NFR-002).
    assert consented_ids <= delivered, (
        "every event of the ONE consented project must ship; a predicate that "
        "delivers only part of it has starved the drain"
    )

    # Each non-consenting project reported separately: a per-project count, so a
    # failure names exactly which projects leaked and how much, the way the
    # incident was measured.
    leaked = {
        repo: sorted(ids & delivered)
        for repo, ids in (
            *silent_ids.items(),
            (OPTED_OUT_REPO, opted_out_ids),
            ("<identity-less>", identityless_ids),
        )
        if ids & delivered
    }
    assert not leaked, (
        "SC-001: only the consented project may be delivered. These projects "
        f"never consented yet had events shipped: {leaked}. Five of them carry "
        "no consent record at all — absence of a decision is not consent."
    )


def test_delivered_identities_are_a_subset_of_consented(tmp_path: Path) -> None:
    """NFR-001 stated as the subset invariant, over the same population.

    Separate from the count assertion above because the invariant is about
    *identity*: ``delivered ⊆ consented`` **and** ``None ∉ delivered``. A
    cardinality check cannot express the second half.
    """
    _write_consent(tmp_path)

    consented = _emitter(
        project_slug="engagement-assistant", repo_slug=CONSENTED_REPO, open_gate=True
    )
    consented_uuid = str(consented._identity.project_uuid)
    _emit_batch(consented)

    for repo in SILENT_REPOS:
        _emit_batch(
            _emitter(project_slug=repo.split("/")[1], repo_slug=repo, open_gate=False)
        )

    journal = get_journal(team_slug=None)
    ledger = SqliteDeliveryLedger(":memory:")
    registry = SqliteDeliveryTargetRegistry(":memory:")
    target = registry.register(
        url="https://hosted.example.com",
        team_slug="team",
        user_email="operator@example.com",
    )
    receiver = StubReceiver()

    dispatch(journal=journal, ledger=ledger, receiver=receiver, target=target)

    delivered_ids = set(receiver.received_event_ids())
    rows = {e.event_id: e for e in journal.read_all()}
    delivered_uuids = {
        resolve_event_project_uuid(_decode(rows[eid])) for eid in delivered_ids
    }

    assert None not in delivered_uuids, (
        "NFR-001: an event whose project identity does not resolve must never "
        "be delivered — it cannot be shown to belong to a consenting project"
    )
    assert delivered_uuids <= {consented_uuid}, (
        f"NFR-001: delivered identities {delivered_uuids - {consented_uuid}} are "
        "not a subset of the consented set"
    )


def _decode(event) -> dict:
    import json

    try:
        decoded = json.loads(event.payload)
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}
