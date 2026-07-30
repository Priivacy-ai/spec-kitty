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

Both sides drive the REAL emit -> capture -> dispatch -> receiver path end to end,
mirroring
``tests/delivery/test_envelope.py::test_journal_stores_full_envelope_so_dispatch_posts_contract_event``.
Both events therefore sit in the SAME shared journal — that premise is the point,
not an accident, and is asserted explicitly below before the drain even runs.

A note on how this pin is *not* built, because it was built that way once. An
earlier revision seeded the never-opted-in row directly and stamped it
``saas_disabled`` so that nothing claimed the checkout had consented at capture
time. That removed one overclaim and introduced a worse one: ``saas_disabled`` is
the sole member of ``selection.TERMINAL_DRAIN_BLOCKED_REASONS``, so T003's filter
excluded the row on its own and the pin stopped testing consent at all — green with
the consent predicate reverted entirely. Making both gates identical and open is
the stronger arrangement: neither row is drain-blocked, so consent is the only
signal that can separate their outcomes, and the reviewer's original objection is
answered without handing T003 the decision. The complementary "no row is created in
the first place" property is pinned separately in
:func:`test_a_never_opted_in_project_no_longer_reaches_the_journal_at_all`.

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
row is genuinely unblocked (``drain_blocked_reason=None``); only the residual
row carries ``saas_disabled``. The two files now key on different,
non-overlapping columns: 3031 on ``Event.drain_blocked_reason`` values it
constructs directly; this file on the ABSENCE of a ``repo_slug``-keyed consent
record for a project whose row is on disk regardless.

That separation had a cost this file used to pay wrongly, and the fix is why both
gates are now identical. ``saas_disabled`` is the SOLE member of
``selection.TERMINAL_DRAIN_BLOCKED_REASONS``, so while the two rows carried
*different* drain-blocked reasons, T003's filter excluded the non-consenting one on
its own and the consent clause never had to fire — the pin stayed green with the
consent predicate stripped out entirely. Two independent investigations reached that
same conclusion and it was fixed the same way: make the rows indistinguishable on
every machine signal, so consent is the only thing left that can separate their
outcomes.
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

    ``repo_slug`` is carried for reporting only. Consent is keyed on
    ``project_uuid`` and nothing else (FR-019: a repo slug is a mutable git
    remote, so it cannot speak for a project), and a resolver that instead
    matched on ``project_slug`` would be the fragile fuzzy correspondence
    #3031 Defect 2 exists to eliminate — so this fixture never invents one.

    Passing ``repo_slug=None`` (the default) reproduces an unresolvable git
    identity. It is deliberately NOT what makes the second project
    non-consenting; the absence of a uuid-keyed consent record is. Consent must
    deny for that project even though its row reaches the journal and is
    drain-open.
    """
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    em = EventEmitter()
    em._identity = SimpleNamespace(
        build_id=build_id, project_uuid=uuid4(), project_slug=project_slug
    )
    em._get_git_metadata = lambda: GitMetadata(repo_slug=repo_slug)
    return em


def _open_capture_gate(_team_slug: str | None, **_kwargs: object) -> CaptureGateState:
    """The capture gate for BOTH emitters: fully open. Consent is the only variable.

    Real-world equivalent, and the incident's own state: a machine that IS
    SaaS-enabled, authenticated and team-resolved, with routing default-allow. Both
    checkouts on it are equally ready to ship; the only difference is that one
    project has a consent record and the other has none.

    This is an instance-level override (mirroring the ``_get_git_metadata`` override
    above) rather than a further ``is_saas_sync_enabled`` patch. The per-instance
    override keeps both events on the SAME producer-scoped journal (``get_journal``
    is still keyed on ``team_slug=None`` for both, since ``is_saas_sync_enabled``
    stays patched ``False`` at module scope).

    ``checkout_enabled=True`` so #3030 T006's capture refusal does not fire — the
    rows must exist on disk for a *drain* predicate to be tested at all. Overriding
    the whole method is what makes that possible, and as of #3030 M1 it is also
    *necessary*: ``_capture_gate_state`` now resolves ``checkout_enabled`` from the
    event's own ``project_uuid`` (it used to read ``is_sync_enabled_for_checkout()``
    against cwd, and was machine-global), so the real gate would refuse to write the
    non-consenting project's row at all and this file's premise — two rows on disk,
    both drain-open, separated only by the *drain*'s consent predicate — could not be
    set up. Keeping capture and drain independently testable is the point of the
    override, not a way around the capture gate.

    ``**_kwargs`` absorbs that ``project_uuid=`` keyword. Arity repair only; no
    assertion in this file changed.

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

    Which is precisely why a third row is needed to pin CONSENT. An earlier
    revision of this docstring claimed the two rows established that "consent — not
    drain_blocked_reason — is the only thing distinguishing the two events", and
    that was false: the assertions below establish that they differ on exactly that
    field, and ``saas_disabled`` is on its own a terminal exclusion under T003. The
    open never-opted-in row added below carries the consent claim instead.

    Originally red because the dispatcher shipped BOTH events: the journal has no
    project scoping (only ``user_id``/``team_slug``), and the drain never decoded
    ``project_slug`` from the payload to gate delivery — so once two projects
    shared a journal (the common case: no per-project journal partitioning
    exists), a single active sync target drained every project's events
    indiscriminately, exactly as the incident (five non-consenting projects'
    events shipped alongside a consenting one) played out.

    Still falsifiable today, which is the point of keeping it, and falsifiable by
    the regression that matters: reverting the consent predicate while leaving
    T003's drain-blocked filter intact ships the open never-opted-in row and reds
    this test. Replacing ``selectable_event_ids`` with the wholly unfiltered
    universe reds it too, on the residual row as well.
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
    # The gates are deliberately IDENTICAL. The capture gate is per-project as of
    # #3030 M1 (it was machine-global, reading cwd), while
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

    journal = get_journal(team_slug=None)

    # A THIRD row, and it is what makes this file a consent pin at all. The residual
    # The shared-journal premise, asserted explicitly before the drain runs: both
    # events sit in the SAME journal file (team_slug=None, since
    # is_saas_sync_enabled() is stubbed False for this process).
    assert journal.count() == 2, (
        "every project's event must sit in the same producer-scoped journal "
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
        "a project that never consented (no uuid-keyed consent record at all for "
        f"{_CONSENTING_REPO_SLUG!r}'s sibling) must not have its event shipped "
        "merely because it shares a journal file with a project that did consent. "
        "Both rows are drain-open, so consent is the only thing that can exclude "
        "this one"
    )


def test_a_never_opted_in_project_no_longer_reaches_the_journal_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stronger post-T006 property, which nothing currently pins.

    The test above proves the DRAIN excludes a never-opted-in project's residual
    row. This proves the complementary half: after T006 no such row is created in
    the first place, so the machine-global pool stops growing. Without this, T006's
    capture refusal could be reverted and every existing pin would stay green —
    the drain would keep excluding rows that no longer needed to exist.

    Nothing is stubbed to produce the refusal. The emitter keeps its REAL
    ``_capture_gate_state``, and this project has no consent record anywhere, so
    ``_project_consents_to_capture`` denies and the write never happens.

    That mechanism changed under #3030 M1 and this docstring changed with it: the
    gate used to resolve ``checkout_enabled`` from the working directory via
    ``routing.is_sync_enabled_for_checkout``, so the refusal came from cwd being a
    plain temp dir rather than a checkout (WP01's deny-by-default, FR-003). It now
    resolves from the EVENT'S OWN ``project_uuid``, which is strictly better here —
    the refusal is now caused by the absent consent record this test is about,
    rather than by an incidental property of the working directory. The
    ``monkeypatch.chdir`` below is retained only to keep the test off the developer's
    real checkout; it is no longer what produces the denial.
    """
    from specify_cli.sync import emitter as emitter_mod

    monkeypatch.setattr(emitter_mod, "is_saas_sync_enabled", lambda: False)
    monkeypatch.chdir(tmp_path)
    # Deliberately NO consent record for this project, anywhere.

    nonconsenting = _stub_emitter(
        project_slug="client-confidential", build_id="confidential-build-1"
    )

    envelope = nonconsenting._emit(
        event_type="ErrorLogged",
        aggregate_id="WP04",
        aggregate_type="WorkPackage",
        payload={"error_type": "runtime", "error_message": "boom", "wp_id": "WP04"},
    )
    assert envelope is not None, (
        "emission itself must still succeed — the local command does not fail "
        "because hosted sync was declined"
    )

    journal = get_journal(team_slug=None)
    assert journal.count() == 0, (
        "a project that never opted in must leave NO journal row (T006 / NFR-005 "
        "as amended): capture-first durability applies to consenting projects "
        f"only, yet {journal.count()} row(s) were written"
    )
    assert journal.read_by_id(envelope["event_id"]) is None
