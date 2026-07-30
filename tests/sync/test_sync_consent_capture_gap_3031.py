"""P0 red-main pin for the #3031 capture-gate gap (Defect 3, ungated capture).

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
from uuid import uuid4

import pytest

from specify_cli.event_journal import (
    CaptureGateState,
    get_journal,
    reset_coalesce_strategy,
    reset_journal_cache,
)

if TYPE_CHECKING:
    from specify_cli.sync.emitter import EventEmitter

pytestmark = [pytest.mark.regression, pytest.mark.fast]

_OCCURRED_AT = "2026-06-29T00:00:00+00:00"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Isolate the journal under a fresh, per-test ``SPEC_KITTY_HOME``.

    Mirrors ``tests/delivery/test_dispatch_project_consent_3030.py``'s
    ``_isolated_home`` fixture: ``resolve_journal_path``
    (``event_journal/journal.py:78-89``) honours ``SPEC_KITTY_HOME`` verbatim,
    so this test never touches the real ``~/.spec-kitty/event_journal/``.
    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is cleared so the SaaS-enabled axis stays
    off regardless of the invoking shell's environment — this test's only
    load-bearing axis is per-project consent (``checkout_enabled``), not the
    global rollout flag.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    reset_journal_cache()
    reset_coalesce_strategy()
    yield
    reset_journal_cache()
    reset_coalesce_strategy()


def _stub_emitter(*, project_slug: str, build_id: str) -> EventEmitter:
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
        build_id=build_id, project_uuid=uuid4(), project_slug=project_slug
    )
    em._get_git_metadata = lambda: GitMetadata()
    return em


def _consenting_gate(_team_slug: str | None, **_kwargs: object) -> CaptureGateState:
    """The per-project consent signal open (``checkout_enabled=True``)."""
    return CaptureGateState(
        saas_enabled=False, checkout_enabled=True, authenticated=False, team_slug=None
    )


def _non_consenting_gate(_team_slug: str | None, **_kwargs: object) -> CaptureGateState:
    """The per-project consent signal closed — the #3031 incident shape.

    ``saas_enabled`` and ``authenticated`` are held identical to
    ``_consenting_gate`` above; ``checkout_enabled`` is the ONLY field that
    differs, so a fix that keys capture on the wrong axis (e.g. SaaS-enabled,
    or auth) rather than per-project consent cannot pass this test by
    accident.
    """
    return CaptureGateState(
        saas_enabled=False, checkout_enabled=False, authenticated=False, team_slug=None
    )


def test_non_consenting_project_event_never_reaches_the_journal() -> None:
    """#3031 Defect 3: a non-consenting project's events must never reach the journal.

    Reds today: both emitters' events land in the same machine-global
    journal file. ``EventEmitter._capture_to_journal`` calls
    ``capture_teamspace_bound`` unconditionally (``sync/emitter.py:1961``),
    and ``capture_teamspace_bound`` itself only ever uses ``gate`` to compute
    the *recorded* ``drain_blocked_reason`` column (``classify_drain_blocked_reason``,
    ``event_journal/journal.py:400``) before an unconditional
    ``journal.append(event)`` (``event_journal/journal.py:402``) — the write
    itself never consults ``gate.checkout_enabled``. So today the
    non-consenting project's event is captured exactly like its consenting
    sibling's, differing only in the ``drain_blocked_reason`` value stamped
    on the row already sitting in the journal.
    """
    consenting = _stub_emitter(project_slug="engagement-assistant", build_id="build-consenting-1")
    consenting._capture_gate_state = _consenting_gate
    nonconsenting = _stub_emitter(project_slug="client-confidential", build_id="build-confidential-1")
    nonconsenting._capture_gate_state = _non_consenting_gate

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
        "emit itself must not raise for a non-consenting project — the gap is "
        "at capture time, not at emission"
    )

    # Both emitters have SaaS globally disabled (is_saas_sync_enabled() is
    # False), so both resolve team_slug=None and therefore share the SAME
    # producer-scoped journal file — the incident's shared-store premise,
    # asserted by construction rather than by inspecting internals.
    journal = get_journal(team_slug=None)

    assert journal.read_by_id(consenting_envelope["event_id"]) is not None, (
        "sanity: the consenting project's event must be captured — this "
        "proves checkout_enabled is what decides the outcome below, not "
        "capture being disabled wholesale"
    )
    assert journal.read_by_id(nonconsenting_envelope["event_id"]) is None, (
        "#3031 Defect 3: 'a non-consenting project's events must never reach "
        "the journal.' The non-consenting emitter's CaptureGateState "
        "(checkout_enabled=False) must gate the journal WRITE itself, not "
        "merely the drain_blocked_reason recorded on a row that gets written "
        "regardless"
    )
