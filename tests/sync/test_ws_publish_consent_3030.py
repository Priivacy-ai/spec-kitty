"""M1-1: the opportunistic WebSocket publish is a live egress path (#3030).

M1 fixed the capture gate and recorded an exclusion for
``_classify_drain_blocked_reason``, on the premise that *"nothing reads this value
to decide whether anything ships"*. **That premise was false.** ``_route_event``
reads exactly that value to decide whether to publish::

    if event.get("drain_blocked_reason") is not None:
        return queued
    ...
    if authenticated and self.ws_client is not None and self.ws_client.connected:
        ... self.ws_client.send_event(event)

and ``drain_blocked_reason`` came from ``_classify_drain_blocked_reason``, whose
``is_sync_enabled_for_checkout()`` call takes **no argument** — i.e. ``Path.cwd()``.
A cwd grant therefore yielded ``None``, which opened a WebSocket publish of the full
wire envelope to the hosted server.

Not dormant: ``SyncRuntime`` — the long-lived singleton where cwd and the cached
``_get_identity()`` diverge — injects a live connected client into the emitter.

The confirmed scenario, pinned by ``test_a_cwd_grant_does_not_publish_another_...``
below: runtime up, identity cached to project A which has no consent record, an
agent session ``cd``s into project B which consents, emit for A. The capture gate
correctly refuses the journal row (M1) — and then execution continues straight past
``_validate_event`` and the contract gate into ``_route_event``, which publishes A's
envelope. A refused capture is not a refused emission.

Assertions are made at the **client seam**: a recorded ``send_event`` call is the
egress attempt, so "never published" means nothing left the process — the same
standard as the body-upload drain's ``egress.posts == []``. Both directions are
pinned, so neither a cwd-derived implementation nor a blanket-deny one passes.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.sync.clock import LamportClock
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.project_identity import ProjectIdentity
from specify_cli.sync.queue import OfflineQueue

pytestmark = [pytest.mark.unit, pytest.mark.fast]

UUID_A = "aaaaaaaa-0000-0000-0000-00000000000a"
UUID_B = "bbbbbbbb-0000-0000-0000-00000000000b"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test consent index; machine-global arming patched on, env var deleted.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is machine-global arming and never a grant
    (``consent.py`` level 3), so a developer's own export must not decide anything
    here. ``is_saas_sync_enabled`` is patched True because a machine with SaaS sync
    off short-circuits to ``sync_disabled`` and the per-project question is never
    reached.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr("specify_cli.sync.emitter.is_saas_sync_enabled", lambda: True)


@pytest.fixture(autouse=True)
def _usable_event_loop():
    """Give ``_route_event`` a real, non-running loop to drive the client with.

    ``_route_event`` reaches for ``asyncio.get_event_loop()``. That is process-global
    state: a sibling test that closed or unset the loop makes it raise "There is no
    current event loop in thread 'MainThread'", which ``_route_event`` catches and
    turns into "send failed; event remains queued". The negative pins would then pass
    for entirely the wrong reason and the positive controls would fail only when the
    file runs alongside others — order-dependent both ways. Owning the loop here
    removes the dependence instead of tolerating it.
    """
    import asyncio

    previous: asyncio.AbstractEventLoop | None
    try:
        previous = asyncio.get_event_loop()
    except RuntimeError:
        previous = None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        asyncio.set_event_loop(previous)
        loop.close()


@pytest.fixture(autouse=True)
def _authenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    """An authenticated session with a resolvable private workspace.

    Both are preconditions of the publish branch, not the subject: without them
    ``_route_event`` never reaches the client and every assertion below would pass
    for the wrong reason.
    """
    team = MagicMock()
    team.id = "private-team-id"
    team.slug = "private-team-id"
    session = MagicMock()
    session.default_team_id = "private-team-id"
    session.teams = [team]
    session.email = "ops@example.com"
    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = session
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
    monkeypatch.setattr(
        "specify_cli.sync._team.resolve_private_team_id_for_ingress",
        lambda *_a, **_kw: "private-team-id",
    )


class _RecordingWsClient:
    """A connected client that records every envelope handed to ``send_event``.

    ``send_event`` is a real coroutine, so the recording only happens if
    ``_route_event`` actually drives it — the coroutine body is the egress.
    """

    def __init__(self) -> None:
        self.connected = True
        self.sent: list[dict[str, Any]] = []

    async def send_event(self, event: dict[str, Any]) -> bool:
        self.sent.append(event)
        return True

    @property
    def published_uuids(self) -> list[str | None]:
        return [event.get("project_uuid") for event in self.sent]


def _checkout(tmp_path: Path, name: str, *, uuid: str, consents: bool | None) -> Path:
    """A checkout whose ``.kittify/config.yaml`` declares identity and consent.

    ``consents=None`` writes no ``sync`` section — the 2026-07-27 incident's actual
    state, and the one FR-002 requires to deny.
    """
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}", "  node_id: 0123456789ab"]
    if consents is not None:
        lines += ["sync:", f"  enabled: {str(consents).lower()}"]
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _emitter(
    tmp_path: Path, *, project_uuid: str, ws_client: _RecordingWsClient
) -> EventEmitter:
    """A long-lived emitter with identity **cached** to *project_uuid*.

    Caching is the whole point: ``_get_identity`` resolves once per emitter lifetime,
    so under ``SyncRuntime`` the stamped identity stays fixed while cwd moves.
    """
    from uuid import UUID

    from specify_cli.sync.git_metadata import GitMetadata, GitMetadataResolver

    resolver = MagicMock(spec=GitMetadataResolver)
    resolver.resolve.return_value = GitMetadata(
        git_branch="main", head_commit_sha="a" * 40, repo_slug="acme/payroll"
    )
    resolver.repo_root = Path("/nonexistent/ws-consent-fixture")

    return EventEmitter(
        clock=LamportClock(
            value=0, node_id="ws-node", _storage_path=tmp_path / "clock.json"
        ),
        config=MagicMock(),
        queue=OfflineQueue(db_path=tmp_path / "queue.db"),
        ws_client=ws_client,  # type: ignore[arg-type]
        _identity=ProjectIdentity(
            project_uuid=UUID(project_uuid),
            project_slug="acme-payroll",
            node_id="ws-node",
            build_id="06e643fb-d025-48b7-afc2-b46d4925bdfa",
        ),
        _git_resolver=resolver,
    )


# --------------------------------------------------------------------------- #
# The red: the confirmed M1-1 scenario, end to end through the real emit path   #
# --------------------------------------------------------------------------- #


def test_a_cwd_grant_does_not_publish_another_projects_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Runtime up, identity cached to A, cwd inside consenting B, client connected.

    Project A has no consent record anywhere; project B's own committed config says
    ``sync.enabled: true``. A cwd-derived ``drain_blocked_reason`` reads B's grant,
    yields ``None``, and ``_route_event`` publishes A's full envelope — including
    ``project_slug``, which is a client engagement name.
    """
    ws = _RecordingWsClient()
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == [], (
        "project B's grant published project A's envelope over the WebSocket. The "
        "publish decision must be resolved from the event's own project_uuid, not "
        f"from the working directory: {ws.published_uuids}"
    )
    assert event is not None, (
        "the event must still be emitted and locally durable; withholding the "
        "opportunistic publish is not the same as dropping the emission"
    )


def test_the_refused_publish_leaves_the_event_locally_durable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refusing egress must not become a second way to lose the operator's data.

    The local queue is the durable outbox and the refusal is about *shipping*. This
    is the converse guard that stops "fix it by dropping the event" from passing.
    """
    ws = _RecordingWsClient()
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == []
    assert emitter.queue.size() == 1, (
        "the envelope must remain in the durable outbox; see the module-level "
        "reasoning recorded for the at-rest exposure this leaves"
    )


# --------------------------------------------------------------------------- #
# The converse: a blanket-deny implementation must not pass                      #
# --------------------------------------------------------------------------- #


def test_a_consenting_projects_envelope_is_still_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive control, and the reason every assertion above is load-bearing.

    Without it a gate that simply never publishes — or a fixture where the publish
    branch is unreachable for an unrelated reason — would satisfy the refusals while
    proving nothing.
    """
    from specify_cli.sync.consent import set_project_consent

    ws = _RecordingWsClient()
    set_project_consent(UUID_A, True)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.published_uuids == [UUID_A], (
        "a consenting project's event must still reach the WebSocket; this gate is "
        "not a publish kill switch"
    )


def test_an_index_grant_publishes_from_outside_any_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The daemon's usual case: no readable checkout for the project at all.

    Consent then comes from the uuid-keyed index, the level that exists precisely
    because a drain sees only a ``project_uuid``. A gate that reached for the
    checkout and gave up would strand every honest daemon publish.
    """
    from specify_cli.sync.consent import set_project_consent

    ws = _RecordingWsClient()
    set_project_consent(UUID_A, True)
    outside = tmp_path / "not-a-project"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.published_uuids == [UUID_A]


# --------------------------------------------------------------------------- #
# The one chain, not a second one (C-003)                                       #
# --------------------------------------------------------------------------- #


def test_the_projects_own_committed_refusal_outranks_an_index_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-013: a refusal in the project's own config beats a stale index grant.

    Proves the publish decision goes down ``sync/consent.py``'s chain rather than
    taking a shortcut to the index — which is what a second, local copy of the
    precedence rules would do.
    """
    from specify_cli.sync.consent import set_project_consent

    ws = _RecordingWsClient()
    set_project_consent(UUID_A, True)
    refusing_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=False)
    monkeypatch.chdir(refusing_a)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == [], (
        "project A's own .kittify/config.yaml says sync.enabled: false; a refusal "
        "outranks the index grant (FR-013), so nothing may be published"
    )


def test_a_consent_read_failure_refuses_the_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-003's rule: inability to determine consent is not consent.

    ``_route_event`` swallows exceptions by design so emission never fails; that
    instinct must not convert an unanswerable consent question into egress.
    """
    from specify_cli.sync.consent import set_project_consent

    ws = _RecordingWsClient()
    set_project_consent(UUID_A, True)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)
    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)

    def _explode(*_args: object, **_kwargs: object) -> frozenset[str]:
        raise RuntimeError("consent index unreadable")

    monkeypatch.setattr("specify_cli.sync.consent.consented_project_uuids", _explode)

    emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == [], "a consent read that raises must refuse the publish"


# --------------------------------------------------------------------------- #
# Direct pins on the routing seam                                               #
# --------------------------------------------------------------------------- #


def _envelope(project_uuid: str | None, *, blocked: str | None = None) -> dict[str, Any]:
    # canonical-event-exempt(exception-flow): legacy WPStatusChanged wire shape (no correlation_id); drives the ws-publish routing seam
    return {
        "event_id": "01JTESTTESTTESTTESTTESTTEST",
        "event_type": "WPStatusChanged",
        "aggregate_id": "WP01",
        "aggregate_type": "WorkPackage",
        "schema_version": "3.0.0",
        "payload": {"wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress"},
        "node_id": "ws-node",
        "lamport_clock": 1,
        "causation_id": None,
        "timestamp": "2026-07-30T07:00:00+00:00",
        "team_slug": "private-team-id",
        "project_uuid": project_uuid,
        "project_slug": "acme-payroll",
        "drain_blocked_reason": blocked,
    }


def test_route_event_refuses_an_envelope_with_no_project_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-001's second half: not identifiable is not consentable.

    ``_emit`` queues such an event without routing it, so production never arrives
    here with a blank uuid — but the seam must refuse it on its own rather than rely
    on a caller's check, because that reliance is what M1-1 was.
    """
    ws = _RecordingWsClient()
    outside = tmp_path / "not-a-project"
    outside.mkdir()
    monkeypatch.chdir(outside)
    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)

    emitter._route_event(_envelope(None))

    assert ws.sent == []


def test_route_event_still_honours_an_upstream_drain_blocked_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The advisory field must keep narrowing, even for a consenting project.

    Consent is now an independent, load-bearing condition of the publish; it does not
    replace the readiness gates (``no_auth`` / ``no_team``) the field carries, which
    exist for ingress safety.
    """
    from specify_cli.sync.consent import set_project_consent

    ws = _RecordingWsClient()
    set_project_consent(UUID_A, True)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)
    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)

    emitter._route_event(_envelope(UUID_A, blocked="no_team"))

    assert ws.sent == [], "a no_team envelope must never be published opportunistically"


def test_one_long_lived_emitter_decides_each_publish_on_its_events_own_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ``SyncRuntime`` shape: one emitter and one client, cwd moved underneath.

    Four routing attempts, two projects, two working directories. Only project A
    consents, so exactly the two A envelopes may be published — from either
    directory, and neither B envelope from either.
    """
    from specify_cli.sync.consent import set_project_consent

    ws = _RecordingWsClient()
    set_project_consent(UUID_A, True)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    refusing_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=False)
    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)

    original = Path(os.getcwd())
    try:
        for cwd in (consenting_a, refusing_b):
            os.chdir(cwd)
            for uuid in (UUID_A, UUID_B):
                emitter._route_event(_envelope(uuid))
    finally:
        os.chdir(original)

    assert ws.published_uuids == [UUID_A, UUID_A], (
        "exactly the two project-A envelopes must be published, from either working "
        f"directory, and neither project-B envelope from either: {ws.published_uuids}"
    )
