"""RED pin: one consenting checkout must not ship a sibling project's events (#3030).

Background. The producer journal is scoped on ``(user_id, team_slug)`` only
(``event_journal/journal.py:_producer_token``) — one DB per producer covering
EVERY project on the machine. ``project_slug`` IS present inside the wire
envelope payload the emitter builds (``sync/emitter.py:2038``), but nothing on
the drain path decodes it to make a delivery decision:
``EventJournal.read_all()`` (``event_journal/journal.py:258``) runs
``SELECT_ALL_SQL`` (``event_journal/models.py:78``), which has no WHERE
clause, and ``_select_undelivered`` (``delivery/dispatcher.py:192-223``) never
looks inside the payload — ``_decode_payload`` (``dispatcher.py:231-245``) is
only reached in the *post* phase, after selection has already happened.

This drives the REAL emit -> capture -> dispatch -> receiver path end to end
(no hand-built journal rows), mirroring
``tests/delivery/test_envelope.py::test_journal_stores_full_envelope_so_dispatch_posts_contract_event``,
with TWO distinct project identities that land in the SAME shared journal —
the shared-journal premise is the point, not an accident, and is asserted
explicitly below before the drain even runs.

Consent is recorded for the FIRST project only, **keyed on its ``project_uuid``**
via ``sync.consent.set_project_consent`` — the same write ``enable_checkout_sync``
performs in production. It is deliberately not a ``[sync.repo_defaults]`` entry:
a repo slug is a mutable git remote, so a grant recorded against it covers every
fresh clone and survives a re-``git init`` (FR-019).

The second project deliberately has NO entry at all — not an explicit opt-out —
because a predicate that reads absence-of-a-decision as consent is the actual
defect this incident turned on (#3031); an explicit opt-out fixture would pass
today's code while the real leak (silence, not refusal) sailed through.

Both emitters share ONE fully open capture gate, so both journal rows carry
``drain_blocked_reason=None`` and consent is the only signal that can separate
their outcomes. That is asserted before the drain runs. Corrected 2026-07-30:
the non-consenting row used to be left machine-gate-blocked, which stamped it
``sync_disabled`` — a *terminal* reason ``selection.py`` excludes on its own — so
this pin passed with the consent clause deleted from ``selectable_event_ids``.

Distinct from, and orthogonal to, the sibling
``tests/delivery/test_dispatch_honours_drain_blocked_3031.py`` (#3031 Defect
5, per-event drain filtering). That file pins that a drain-blocked-reason
predicate must inspect each ``Event`` row rather than gating a whole
process/checkout; it says nothing about *who* consented, because
``drain_blocked_reason`` is a machine-global gate snapshot, not a per-project
decision (see that file's docstring). THIS file pins the orthogonal, genuine
per-project defect: two projects sharing one machine-global journal, where
only ONE of them ever recorded consent. To keep the two files mutually
satisfiable (an earlier revision pinned both against fixtures that stamped
BOTH events with the same ``drain_blocked_reason=saas_disabled``, which made
this file's "must ship" demand and the sibling's "any such row must never
ship" demand directly contradictory — no implementation could satisfy both),
the consenting checkout's capture gate is forced open below so its journal
row is genuinely unblocked (``drain_blocked_reason=None``); only the
non-consenting checkout's row is left machine-gate-blocked. The two files now
key on different, non-overlapping columns: 3031 on
``Event.drain_blocked_reason`` values it constructs directly; this file on
``repo_slug``-keyed consent-record resolution via a real emitter round-trip.
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

if TYPE_CHECKING:
    from specify_cli.sync.emitter import EventEmitter

pytestmark = [pytest.mark.regression, pytest.mark.fast]

# A realistic owner/repo pair — consent keying must not depend on the slug
# looking special (mirrors tests/sync/test_sync_consent_default_deny.py:48).
_CONSENTING_REPO_SLUG = "my-org/engagement-assistant"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """One shared ``SPEC_KITTY_HOME``, mirroring ``test_envelope.py:55-63``.

    A single shared journal across the two "checkouts" simulated below is the
    premise of this test, not an accident.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    reset_journal_cache()
    reset_coalesce_strategy()
    yield
    reset_journal_cache()
    reset_coalesce_strategy()


def _record_consent_for_first_project_only(project_uuid: str) -> None:
    """Record hosted-sync consent for ONE project only, keyed on its ``project_uuid``.

    Uuid-keyed via ``sync.consent.set_project_consent`` — what
    ``enable_checkout_sync`` writes in production. It previously wrote
    ``[sync.repo_defaults."<repo-slug>"]``, which is not a level of the consent chain
    at all: a repo slug is a mutable git remote, so a grant recorded against it
    covers every fresh clone and survives a re-``git init`` (FR-019).

    The second project gets NO entry — absence of a decision, not an explicit
    opt-out, which is the population the incident turned on.
    """
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(project_uuid, True)


def _stub_emitter(
    *, project_slug: str, build_id: str, repo_slug: str | None = None
) -> EventEmitter:
    """A real ``EventEmitter`` with a stubbed identity/git resolver.

    Mirrors ``tests/delivery/test_envelope.py:65-74``'s ``_stub_emitter`` but
    with REAL, distinct project identities (production-shaped project slugs
    and distinct ``project_uuid``s per instance) rather than the envelope
    test's ``None`` placeholders — the point being that two checkouts for two
    different projects on the same machine still resolve to the SAME journal
    file (``team_slug=None``) once SaaS sync is globally disabled.

    ``repo_slug`` is the ONLY field a per-project consent lookup can key on
    (``sync/config.py:get_repository_sync_enabled`` does
    ``repo_defaults.get(repo_slug)``) — a resolver that instead tried to
    match on ``project_slug`` would be the fragile fuzzy correspondence
    #3031 Defect 2 exists to eliminate, so this fixture never invents one.
    Passing ``repo_slug=None`` (the default) reproduces an unresolvable git
    identity — genuinely absent from the consent record, not an explicit
    opt-out.
    """
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    em = EventEmitter()
    em._identity = SimpleNamespace(
        build_id=build_id, project_uuid=uuid4(), project_slug=project_slug
    )
    em._get_git_metadata = lambda: GitMetadata(repo_slug=repo_slug)
    return em


def _open_capture_gate(_team_slug: str | None) -> CaptureGateState:
    """The capture gate for BOTH emitters: fully open. Consent is the only variable.

    Real-world equivalent, and the incident's own state: a machine that IS
    SaaS-enabled, authenticated and team-resolved, with routing default-allow. Both
    checkouts on it are equally ready to ship; the only difference is that one
    project has a consent record and the other has none.

    This is an instance-level override (mirroring the ``_get_git_metadata`` override
    above) rather than a further ``is_saas_sync_enabled`` patch, because every real
    capture gate (``EventEmitter._capture_gate_state``) is machine-global in the
    current implementation — see ``test_dispatch_honours_drain_blocked_3031.py``. The
    per-instance override keeps both events on the SAME producer-scoped journal
    (``get_journal`` is still keyed on ``team_slug=None`` for both, since
    ``is_saas_sync_enabled`` stays patched ``False`` at module scope).

    ``checkout_enabled=True`` so #3030 T006's capture refusal does not fire — the
    rows must exist on disk for a *drain* predicate to be tested at all.

    Corrected 2026-07-30. The non-consenting emitter previously used a second gate
    returning ``saas_enabled=False``, on the reasoning that giving the two rows
    *different* ``drain_blocked_reason`` values kept them "distinguishable". It did
    the opposite: ``classify_drain_blocked_reason`` stamped that row
    ``sync_disabled``, which ``delivery/selection.py`` classifies **terminal**, so
    the row was excluded by the drain-blocked clause and the consent clause never had
    to fire. Mutation testing confirmed this pin still passed with consent stripped
    out of ``selectable_event_ids`` entirely. Identical gates are what make consent
    load-bearing.
    """
    return CaptureGateState(
        saas_enabled=True,
        checkout_enabled=True,
        authenticated=True,
        team_slug="team",
    )


def test_consenting_project_leaks_sibling_project_event_through_shared_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consenting checkout's drain must not also ship a non-consenting sibling's event.

    #3030 (per-project consent) — orthogonal to the rescoped
    ``test_dispatch_honours_drain_blocked_3031.py`` (#3031 Defect 5,
    machine-global drain-blocked-reason filtering). BOTH emitters' capture gates
    are forced open below (``_open_capture_gate``), so both journal rows carry
    ``drain_blocked_reason=None`` and the *only* difference between them is that
    one project's uuid has a consent record and the other's has none.

    That does not collide with the sibling's "any drain-blocked row must never
    ship" demand: neither row here is drain-blocked, so the sibling's rule has
    nothing to say about this population. The two files partition cleanly —
    the sibling owns machine-readiness exclusion, this file owns consent
    exclusion — rather than needing the rows classified differently to coexist.

    Reds today: the dispatcher ships BOTH events. The journal has no project
    scoping at all (only ``user_id``/``team_slug``), and the drain never
    decodes ``project_slug`` from the payload to gate delivery — so once two
    projects share a journal (the common case: no per-project journal
    partitioning exists), a single active sync target drains every project's
    events indiscriminately, exactly as the incident (five non-consenting
    projects' events shipped alongside a consenting one) played out. No
    consent-checking code exists on the drain path at all today, so both
    events ship regardless of ``repo_slug``/consent-record resolution.
    """
    from specify_cli.sync import emitter as emitter_mod

    monkeypatch.setattr(emitter_mod, "is_saas_sync_enabled", lambda: False)

    consenting = _stub_emitter(
        project_slug="engagement-assistant",
        build_id="engagement-build-1",
        repo_slug=_CONSENTING_REPO_SLUG,
    )
    nonconsenting = _stub_emitter(
        project_slug="client-confidential", build_id="confidential-build-1"
    )
    _record_consent_for_first_project_only(str(consenting._identity.project_uuid))

    # BOTH emitters get the same fully open capture gate. #3030 T006 refuses the
    # journal WRITE when the capture gate's checkout_enabled is False, so the
    # non-consenting emitter needs a gate that still captures — otherwise the
    # shared-journal premise below can never hold and this pin would fail on its own
    # setup rather than on the leak.
    #
    # That is not a weakening of the fixture: it is the population this pin exists
    # for. T006 stops *new* non-consenting captures, but the journal on a real
    # machine already holds weeks of rows written before it landed (the incident's own
    # 1,322 are still on disk), plus rows captured while a project was consented and
    # later revoked. Those rows must still be excluded at drain time, which is exactly
    # FR-007/FR-008's job. Capture gating does not retire the drain predicate.
    #
    # The gates are deliberately IDENTICAL. The capture gate is machine-global, while
    # this pin's notion of non-consent is the absent uuid-keyed consent RECORD the
    # drain must resolve — so the two rows must be indistinguishable on every machine
    # signal, leaving consent as the only thing that can separate their outcomes.
    consenting._capture_gate_state = _open_capture_gate
    nonconsenting._capture_gate_state = _open_capture_gate

    consenting_envelope = consenting._emit(
        event_type="ErrorLogged",
        aggregate_id="WP04",
        aggregate_type="WorkPackage",
        payload={"error_type": "runtime", "error_message": "boom", "wp_id": "WP04"},
    )
    nonconsenting_envelope = nonconsenting._emit(
        event_type="ErrorLogged",
        aggregate_id="WP04",
        aggregate_type="WorkPackage",
        payload={"error_type": "runtime", "error_message": "boom", "wp_id": "WP04"},
    )
    assert consenting_envelope is not None, "the consenting project's emit must succeed"
    assert nonconsenting_envelope is not None, (
        "the non-consenting project's emit must ALSO durably capture (FR-017 "
        "capture-first) — the defect is at drain time, not capture time"
    )

    # The shared-journal premise, asserted explicitly before the drain runs:
    # both events landed in the SAME journal file (team_slug=None for both,
    # since is_saas_sync_enabled() is stubbed False for this process).
    journal = get_journal(team_slug=None)
    assert journal.count() == 2, (
        "both projects' events must land in the same producer-scoped journal "
        "for this test to exercise the real cross-project leak"
    )

    # Indistinguishability premise, asserted before the drain runs: the two rows must
    # be IDENTICAL on drain_blocked_reason — both open — so that consent is provably
    # the only thing that can separate their outcomes below.
    #
    # This assertion was inverted on 2026-07-30. It used to require the non-consenting
    # row to carry a NON-null drain_blocked_reason, while claiming in its own message
    # that "consent — not drain_blocked_reason — is the only thing distinguishing the
    # two events". Those two statements contradict each other, and the code was the
    # one telling the truth: the reason it stamped was ``sync_disabled``, which
    # ``delivery/selection.py`` treats as **terminal**, so the row was excluded
    # without consent being consulted at all. Mutation testing confirmed this pin
    # passed with the consent clause deleted from ``selectable_event_ids``. A shared
    # drain_blocked_reason of None is what makes the claim true rather than merely
    # asserted.
    rows_by_id = {event.event_id: event for event in journal.read_all()}
    assert rows_by_id[consenting_envelope["event_id"]].drain_blocked_reason is None, (
        "the consenting row's capture-gate override must have produced an "
        "open (drain_blocked_reason=None) journal row"
    )
    assert rows_by_id[nonconsenting_envelope["event_id"]].drain_blocked_reason is None, (
        "the non-consenting row must ALSO be drain-open. If it carries any "
        "drain_blocked_reason, selection.py's terminal filter excludes it on its own "
        "and this pin stops testing consent — which is exactly how it was fake-green"
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

    received_ids = set(receiver.received_event_ids())
    assert consenting_envelope["event_id"] in received_ids, (
        "the consenting project's event must still ship — this test is not "
        "about breaking a healthy consenting drain"
    )
    assert nonconsenting_envelope["event_id"] not in received_ids, (
        "a project that never consented (no repo_defaults entry at all for "
        f"{_CONSENTING_REPO_SLUG!r}'s sibling) must not have its event "
        "shipped merely because it shares a journal file with a project "
        "that did consent — today it does, because the drain has no notion "
        "of project identity at all"
    )
