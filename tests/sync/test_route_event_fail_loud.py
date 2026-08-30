"""Fail-loud regression for the ``_route_event`` bool-discard residual (#3517).

``EventEmitter._emit`` used to *discard* the boolean ``_route_event`` returns and
``return event`` unconditionally, so an event that never durably landed in a
project-owned outbox was still handed back truthy. The 11 ``if event is not
None:`` publish gates in ``sync/events.py`` then fed that non-durable envelope to
``_publish_event_via_sync_daemon`` — a silent-drop: shipped to the daemon with
nothing on disk behind it (fail-loud / silent-drop, epics #3410 / #3549).

The fix binds ``_emit`` to the residual bool ONLY (not the bounded-retry redesign,
which stays with #3549): when ``_route_event`` reports the event did NOT durably
land, ``_emit`` must (1) make the failure legible on an existing operator surface
and (2) stop returning the envelope as publication-eligible — i.e. ``return None``
so every publish gate skips it. The success path (routing True) is untouched.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from specify_cli.sync import emitter as emitter_mod
from specify_cli.sync.emitter import EventEmitter

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


class _RecordingConsole:
    """Stand-in for the module stderr console that records warnings verbatim."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str = "", *args: object, **kwargs: object) -> None:
        self.messages.append(str(message))


def _identity_with_project() -> SimpleNamespace:
    """An identity carrying a resolvable ``project_uuid``.

    A truthy ``project_uuid`` is exactly what steers ``_emit`` past the
    intentional "queued locally only" arm and into the ``_route_event`` call
    whose returned bool the fix must consume.
    """
    return SimpleNamespace(
        project_uuid=uuid4(),
        project_slug="fail-loud-slug",
        build_id="build-1",
        node_id="node-1",
    )


def test_non_durable_route_is_not_publication_eligible_and_is_legible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routing that does NOT durably land yields ``None`` + an operator signal.

    RED on the bool-discard code: ``_emit`` returned the envelope truthy even
    though ``_route_event`` reported ``False`` (non-durable), making it
    publication-eligible at the ``events.py`` gates with nothing durably queued.
    GREEN after the fix: the envelope is dropped from publication (``None``) and
    the drop is made legible on the existing stderr warning surface.
    """
    # Arm sync so ``_emit`` reaches the real ``_route_event`` seam. The old
    # ``SYNC_DISABLE=1`` (pre-#3799 "local-only, no network") now disarms the
    # whole emit — ``_route_event`` is local-only, so arming reaches it without
    # network egress.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    console = _RecordingConsole()
    monkeypatch.setattr(emitter_mod, "_console", console)

    emitter = EventEmitter()
    monkeypatch.setattr(emitter, "_get_identity", _identity_with_project)
    # The event reaches routing, but routing reports it did NOT durably land.
    monkeypatch.setattr(emitter, "_route_event", lambda _event: False)

    result = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    # Durability semantics: a non-durable event is NOT publication-eligible.
    # ``None`` is exactly what the 11 ``if event is not None`` publish gates skip.
    assert result is None
    # Fail-loud: the silent drop is now legible on an operator-visible surface.
    assert console.messages, "a non-durable routing drop must emit a legible signal"
    assert any("durab" in m.lower() or "publication" in m.lower() for m in console.messages)


def test_durable_route_still_returns_the_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The success path is untouched: routing ``True`` still returns the event.

    Guards against over-correcting the fix into dropping durable events too.
    """
    # Arm sync so ``_emit`` reaches the real ``_route_event`` seam. The old
    # ``SYNC_DISABLE=1`` (pre-#3799 "local-only, no network") now disarms the
    # whole emit — ``_route_event`` is local-only, so arming reaches it without
    # network egress.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    console = _RecordingConsole()
    monkeypatch.setattr(emitter_mod, "_console", console)

    emitter = EventEmitter()
    monkeypatch.setattr(emitter, "_get_identity", _identity_with_project)
    monkeypatch.setattr(emitter, "_route_event", lambda _event: True)

    result = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert result is not None
    assert result["aggregate_id"] == "WP01"


def test_queue_full_nonexception_false_is_not_publication_eligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The benign queue-full arm (queue REFUSES without raising) is fail-loud too.

    ``_queue_event_locally`` returns ``False`` when the project outbox refuses the
    event (e.g. ``size() >= max_queue_size``) — a non-exception ``False``, distinct
    from the SQLite-locked / disk-full *exception* arm the sibling tests cover
    (adversarial review finding 2b). It flows through the real ``_route_event``,
    so it must also drop the event from publication and warn.
    """
    # Arm sync so ``_emit`` reaches the real ``_route_event`` seam. The old
    # ``SYNC_DISABLE=1`` (pre-#3799 "local-only, no network") now disarms the
    # whole emit — ``_route_event`` is local-only, so arming reaches it without
    # network egress.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE", raising=False)
    console = _RecordingConsole()
    monkeypatch.setattr(emitter_mod, "_console", console)

    emitter = EventEmitter()
    monkeypatch.setattr(emitter, "_get_identity", _identity_with_project)
    # The outbox REFUSES the event (returns False) without raising — the real
    # ``_route_event`` observes that and must report the event non-durable.
    monkeypatch.setattr(emitter, "_queue_event_locally", lambda _event: False)

    result = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert result is None
    assert any(
        "durab" in m.lower() or "publication" in m.lower() for m in console.messages
    )


def test_route_event_reports_false_without_a_resolvable_outbox() -> None:
    """The durability contract the fix binds to: no project outbox → ``False``.

    ``_route_event`` returns ``True`` iff the event durably landed in a
    project-owned outbox. With no attached queue and no resolvable
    ``project_uuid`` on the event, there is no outbox to land in, so it must
    report ``False`` (never a swallowed truthy).
    """
    emitter = EventEmitter(queue=None)

    landed = emitter._route_event({"event_id": "evt-no-project"})

    assert landed is False
