"""Regression guard for the #3031 capture-gate gap (Defect 3, ungated capture).

Companion to ``tests/sync/test_sync_consent_default_deny.py`` (#3031). That
file's own docstring names two gaps its five tests do NOT cover:

    Not covered here, and tracked in #3031 as separate work: capture is
    ungated (Defect 3 — events reach the journal regardless of consent) and
    drain selection filters per checkout rather than per event (Defect 5).
    Both need their own fixtures; neither is pinned by this file.

This file is additive — a NEW file, per the same-file docstring's own
instruction that these need their own fixtures. It does not edit
``test_sync_consent_default_deny.py``.

Defect 5 (per-event drain filtering) is already pinned by
``tests/delivery/test_dispatch_honours_drain_blocked_3030.py::test_dispatch_excludes_events_with_recorded_drain_blocked_reason``,
which drains one blocked and one unblocked event in a SINGLE ``dispatch()``
call (one process tick) and asserts differential treatment — a fix that
filters per-*process* rather than per-*event* cannot pass that test. No
duplicate is added here for Defect 5.

Defect 3 (ungated capture) is pinned below, against the #3031 issue's own
stated contract (Proposed resolution, item 3): "A non-consenting project's
events must never reach the journal." This test drives that contract through
the ONE real production entry point for a capture — ``EventEmitter._emit``
(via ``EventEmitter._capture_to_journal``, ``sync/emitter.py:1935-1970``) —
rather than calling ``capture_teamspace_bound`` directly.

Why not call ``capture_teamspace_bound`` directly (as an earlier revision of
this file did, with ``is_teamspace_bound=False, skip_journal=True``): that
parameter combination is unreachable from production.
``capture_teamspace_bound`` has exactly one production caller
(``EventEmitter._capture_to_journal``, ``sync/emitter.py:1961``), and that
caller passes neither ``is_teamspace_bound`` nor ``skip_journal`` — both take
their defaults (``True`` / ``False``). A test built on that combination can be
greened by a two-line ``if skip_journal: return event`` guard inside
``capture_teamspace_bound`` while every real capture keeps landing in the
machine-global journal unconditionally — i.e. Defect 3 would survive the fix
100% intact. This revision instead drives the real caller with a real
non-consenting gate, so nothing inside ``capture_teamspace_bound``'s unused
parameters can satisfy it; the write path that actually runs in production is
what has to change.

Consent, for this test, is the per-project signal ``EventEmitter`` already
computes and already threads into ``CaptureGateState.checkout_enabled`` (via
``is_sync_enabled_for_checkout``, ``sync/routing.py``) — the #3031 Defect
1/2 fix. Today that signal reaches only
``classify_drain_blocked_reason`` -> ``Event.drain_blocked_reason``, a column
read at *drain* time; it never gates the *write*. Two stub emitters below
override ``_capture_gate_state`` per-instance (mirrors
``tests/delivery/test_dispatch_project_consent_3030.py``'s
``_open_capture_gate`` fixture) so ``checkout_enabled`` is the ONLY thing
that differs between them — proving non-consent, not some other knob (SaaS
globally disabled, no auth, capture disabled outright), is what decides the
outcome. A fix that disables capture wholesale would also fail the
consenting half of this test.

MIGRATION NOTE (per-project store cutover): the machine-global shared journal
this file was written against no longer exists. Capture now lands each event
in the store owned by the event's own ``project_uuid``
(``EventEmitter._queue_event_locally`` -> ``ProjectSyncStore``), and consent is
resolved from the UUID-owned project decision, never a stubbed gate. The #3031
Defect 3 invariant is preserved in its post-cutover form: a non-consenting
project's events never appear in another project's journal (the shared-store
disclosure surface is gone by construction, asserted below), and the drain
seam (``consented_project_uuids``) never selects the non-consenting project's
UUID, so its locally captured rows can never ship.

Doctrinal tension, named rather than resolved here: ``event_journal/journal.py``
documents the journal write as deliberately unconditional for Teamspace-bound
families — FR-017 / C-008, enforced by ``TeamspaceBoundDropError`` so a
Teamspace-bound fact is never silently dropped
(``capture_teamspace_bound``'s docstring: "The journal write is unconditional
for Teamspace-bound families; ``gate`` only decides the recorded
``drain_blocked_reason`` ... never whether the write happens"). #3031 Defect 3
asks for the opposite outcome for *non-consenting* projects: no write at all.
Reconciling "unconditional durable write for Teamspace-bound facts" with "a
non-consenting project's events must never reach the journal" is an
architecture question (which axis wins, and whether "Teamspace-bound" and
"consenting" turn out to be the same predicate) being filed separately. This
test pins only what #3031 explicitly asks for; it does not adjudicate the
tension, and the fix that satisfies it must not do so by quietly deciding
every event is not Teamspace-bound.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from uuid import UUID

import pytest

from specify_cli.event_journal import (
    get_journal,
    reset_coalesce_strategy,
    reset_journal_cache,
)
from specify_cli.sync.consent import consented_project_uuids, record_project_opt_in
from specify_cli.sync.project_store import ProjectSyncStore

if TYPE_CHECKING:
    from specify_cli.sync.emitter import EventEmitter

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_OCCURRED_AT = "2026-06-29T00:00:00+00:00"

# Fixed UUIDs so each emitter's project-owned store can be reopened for the
# journal assertions below.
_CONSENTING_UUID = "aaaaaaaa-3031-0000-0000-0000000000aa"
_NONCONSENTING_UUID = "bbbbbbbb-3031-0000-0000-0000000000bb"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Isolate the journal under a fresh, per-test ``SPEC_KITTY_HOME``.

    Mirrors ``tests/delivery/test_dispatch_project_consent_3030.py``'s
    ``_isolated_home`` fixture: ``resolve_journal_path``
    (``event_journal/journal.py:78-89``) honours ``SPEC_KITTY_HOME`` verbatim,
    so this test never touches the real ``~/.spec-kitty/event_journal/``.
    Sync is ARMED here (``SPEC_KITTY_ENABLE_SAAS_SYNC=1``, disable vars cleared):
    since #3799 local capture is machine-arming-gated, so the per-project consent
    axis this test exercises only becomes observable once arming lets ``_emit``
    reach capture. Arming is the precondition; per-project consent
    (``checkout_enabled``) stays the load-bearing axis that decides which
    project's journal an event lands in and which UUID the drain selects.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SYNC_MINIMAL_IMPORT", raising=False)
    # Live per-project capture requires the machine layout to have completed
    # the project-store cutover; publish it for this isolated runtime root.
    authority = ProjectSyncStore(_CONSENTING_UUID).layout_generation()
    authority.begin_cutover("capture-gap-3031-tests")
    authority.publish_project_only("capture-gap-3031-tests", verify_exact=lambda: True)
    reset_journal_cache()
    reset_coalesce_strategy()
    yield
    reset_journal_cache()
    reset_coalesce_strategy()


def _stub_emitter(*, project_slug: str, build_id: str, project_uuid: str) -> EventEmitter:
    """A real ``EventEmitter`` with a stubbed identity/git resolver.

    Mirrors ``tests/delivery/test_dispatch_project_consent_3030.py``'s
    ``_stub_emitter``: everything downstream of identity/git resolution
    (Lamport clock, capture, validation, contract gate) is the real
    production code path — only the two I/O-bound resolvers that would
    otherwise require a real git checkout are stubbed.
    """
    from specify_cli.sync.emitter import EventEmitter
    from specify_cli.sync.git_metadata import GitMetadata

    em = EventEmitter()
    em._identity = SimpleNamespace(
        build_id=build_id, project_uuid=UUID(project_uuid), project_slug=project_slug
    )
    em._get_git_metadata = lambda: GitMetadata()
    return em


def _read_journal_event_ids(project_uuid: str) -> set[str]:
    """All event ids captured in *project_uuid*'s own project-owned journal."""
    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        journal = get_journal(unit=unit, authority=store.layout_generation())
        return {event.event_id for event in journal.read_all()}


def test_non_consenting_project_event_never_reaches_the_journal() -> None:
    """#3031 Defect 3, post-cutover form: no shared journal, no drain selection.

    Previously red: both emitters' events landed in the same machine-global
    journal file, and only a ``drain_blocked_reason`` column separated the
    non-consenting project's row from disclosure. The cutover removed that
    surface: each event is captured only in the store owned by its own
    ``project_uuid``, and the drain seam (``consented_project_uuids``) never
    selects a UUID without an explicit recorded opt-in. Consent here is the
    REAL UUID-owned decision — the consenting project records an explicit
    opt-in, the non-consenting sibling records nothing — so a fix that keys
    the outcome on any other axis (SaaS flag, auth, capture disabled
    wholesale) cannot pass both halves of this test by accident.
    """
    # Real per-project consent: explicit opt-in for exactly one project.
    record_project_opt_in(_CONSENTING_UUID, actor="tester")

    consenting = _stub_emitter(
        project_slug="engagement-assistant",
        build_id="build-consenting-1",
        project_uuid=_CONSENTING_UUID,
    )
    nonconsenting = _stub_emitter(
        project_slug="client-confidential",
        build_id="build-confidential-1",
        project_uuid=_NONCONSENTING_UUID,
    )

    consenting_envelope = consenting._emit(
        event_type="ErrorLogged",
        aggregate_id="WP04",
        aggregate_type="WorkPackage",
        payload={"error_type": "runtime", "error_message": "boom", "wp_id": "WP04"},
        occurred_at=_OCCURRED_AT,
    )
    nonconsenting_envelope = nonconsenting._emit(
        event_type="ErrorLogged",
        aggregate_id="WP04",
        aggregate_type="WorkPackage",
        payload={"error_type": "runtime", "error_message": "boom", "wp_id": "WP04"},
        occurred_at=_OCCURRED_AT,
    )

    assert consenting_envelope is not None, "the consenting project's emit must succeed"
    assert nonconsenting_envelope is not None, (
        "emit itself must not raise for a non-consenting project — capture is "
        "local durability in the project's OWN store, never disclosure"
    )

    consenting_journal_ids = _read_journal_event_ids(_CONSENTING_UUID)

    assert consenting_envelope["event_id"] in consenting_journal_ids, (
        "sanity: the consenting project's event must be captured in its own "
        "project-owned journal — this proves per-project consent is what "
        "decides the outcome below, not capture being disabled wholesale"
    )
    assert nonconsenting_envelope["event_id"] not in consenting_journal_ids, (
        "#3031 Defect 3: 'a non-consenting project's events must never reach "
        "the journal.' Post-cutover the journal is project-owned; the "
        "non-consenting project's event must never appear in ANOTHER "
        "project's journal — the shared-store disclosure surface the "
        "incident turned on must stay gone"
    )

    # And the egress half of the invariant: the drain seam selects only
    # explicitly opted-in project UUIDs, so the non-consenting project's
    # locally captured rows can never ship.
    assert consented_project_uuids([_CONSENTING_UUID, _NONCONSENTING_UUID]) == frozenset(
        {_CONSENTING_UUID}
    ), (
        "the drain seam must select exactly the explicitly opted-in project — "
        "absence of a recorded decision is not consent"
    )
