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
are seeded here through a capture gate that is fully OPEN, which is exactly that
population. The drain predicate is what must exclude them.

Every project on this fixture's machine shares ONE fully open capture gate, so
every seeded row is drain-open and per-project consent is the only signal that
can exclude anything. That is asserted, not assumed, before each drain. It is
also a correction: the non-consenting emitters previously used a gate reporting
``saas_enabled=False``, whose rows got stamped ``sync_disabled`` — a *terminal*
``drain_blocked_reason``. ``selection.py`` excluded them on that clause alone, so
both pins in this file passed with the consent clause deleted from
``selectable_event_ids`` (proved by mutation, 2026-07-30). ``tasks.md`` records
that terminal filter as covering ZERO incident rows; the pins were resting on it.
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


def _record_consent(*, granted: str, refused: str | None = None) -> None:
    """Record consent **uuid-keyed**, for the one project that opted in.

    Keyed on ``project_uuid``, not on a repo slug. A repo-slug-keyed
    ``[sync.repo_defaults]`` record is not a level of the consent chain (FR-019: it
    is keyed on a mutable git remote, so a fresh clone or re-``git init`` would
    inherit a grant nobody gave), and ``sync.consent.set_project_consent`` is what
    ``enable_checkout_sync`` writes in production anyway — so this fixture now
    records consent the same way the product does.

    *refused* gets an explicit ``False``, which is a genuinely different population
    from the five silent repos: those get no record at all, because absence of a
    decision is what the incident turned on and it must deny on its own.
    """
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(granted, True)
    if refused is not None:
        set_project_consent(refused, False)


def _drain_open_gate(_team_slug: str | None) -> CaptureGateState:
    """Every project's capture gate: fully open. Consent is the ONLY difference.

    One gate for all six projects, deliberately. This is the incident's actual
    machine state, and the fixture must reproduce it or the pins below measure
    nothing. On 2026-07-27 the machine was armed (``SPEC_KITTY_ENABLE_SAAS_SYNC``
    exported), authenticated, team-resolved, and routing was default-allow for the
    five client repos — so their journal rows carried ``drain_blocked_reason=None``.
    Nothing about machine *readiness* distinguished them from the consented
    project's rows. The only difference was that nobody had ever opted them in.

    The non-consenting emitters previously used a second gate returning
    ``saas_enabled=False``, which made ``classify_drain_blocked_reason`` stamp their
    rows ``sync_disabled`` — a reason ``delivery/selection.py`` classifies
    **terminal**. Those rows were therefore excluded by the drain-blocked filter
    alone and the consent clause never had to fire: three of this mission's four
    acceptance pins still passed with consent stripped out of
    ``selectable_event_ids`` entirely (verified by mutation). ``tasks.md`` says of
    that terminal filter, "Covers ZERO incident rows — never treat as containment";
    the fixture was resting on exactly it.

    ``checkout_enabled=True`` so #3030 T006's capture refusal does not fire — the
    rows must exist on disk for a *drain* predicate to be tested at all.
    """
    return CaptureGateState(
        saas_enabled=True, checkout_enabled=True, authenticated=True, team_slug="team"
    )


def _emitter(*, project_slug: str | None, repo_slug: str | None) -> EventEmitter:
    """An emitter for one project, with a fully open capture gate.

    No ``open_gate`` switch any more: every project on this fixture's machine is
    equally drain-open, so consent is the only variable the pins can be reading.
    """
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    em = EventEmitter()
    em._identity = SimpleNamespace(
        build_id=f"build-{project_slug}", project_uuid=uuid4(), project_slug=project_slug
    )
    em._get_git_metadata = lambda: GitMetadata(repo_slug=repo_slug)
    em._capture_gate_state = _drain_open_gate
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
    consented = _emitter(
        project_slug="engagement-assistant", repo_slug=CONSENTED_REPO
    )
    opted_out = _emitter(
        project_slug="explicitly-declined", repo_slug=OPTED_OUT_REPO
    )
    # Consent is recorded uuid-keyed, so it can only be written once the emitters
    # exist and their project identities are known.
    _record_consent(
        granted=str(consented._identity.project_uuid),
        refused=str(opted_out._identity.project_uuid),
    )

    consented_ids = set(_emit_batch(consented))

    silent_ids: dict[str, set[str]] = {}
    for repo in SILENT_REPOS:
        em = _emitter(project_slug=repo.split("/")[1], repo_slug=repo)
        silent_ids[repo] = set(_emit_batch(em))

    opted_out_ids = set(_emit_batch(opted_out))

    # An identity-less capture: NFR-001 is a subset invariant because these
    # collapse to {None} and would satisfy a cardinality check while leaking.
    identityless = _emitter(project_slug=None, repo_slug=None)
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

    # Second premise, and the one that makes this file's pins load-bearing: EVERY
    # seeded row is drain-open. If any non-consenting row carried a terminal
    # drain_blocked_reason, selection.py would exclude it on the drain-blocked
    # clause alone and the leak assertion below would pass with consent stripped out
    # of the predicate entirely — which is exactly how this file was fake-green.
    # Asserted, not assumed, so a future fixture edit cannot quietly restore that.
    blocked = {
        e.event_id: e.drain_blocked_reason
        for e in journal.read_all()
        if e.event_id in all_seeded and e.drain_blocked_reason is not None
    }
    assert not blocked, (
        "every seeded row must be drain-OPEN so that per-project consent is the "
        f"only thing that can exclude it; these rows are gate-blocked: {blocked}. "
        "A blocked row is excluded by the terminal drain_blocked_reason filter, "
        "which tasks.md records as covering ZERO incident rows"
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
    consented = _emitter(
        project_slug="engagement-assistant", repo_slug=CONSENTED_REPO
    )
    consented_uuid = str(consented._identity.project_uuid)
    _record_consent(granted=consented_uuid)
    _emit_batch(consented)

    for repo in SILENT_REPOS:
        _emit_batch(_emitter(project_slug=repo.split("/")[1], repo_slug=repo))

    journal = get_journal(team_slug=None)

    # Same drain-open premise as SC-001: without it the subset invariant is
    # satisfiable by the terminal drain-blocked filter alone.
    assert all(e.drain_blocked_reason is None for e in journal.read_all()), (
        "every seeded row must be drain-open so consent is the only exclusion"
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
