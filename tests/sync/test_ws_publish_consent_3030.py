"""M1-1 successor: ``_route_event`` performs no direct WebSocket transport (#3030).

This file originally pinned the *consent gate on the opportunistic WebSocket
publish*: ``_route_event`` read ``drain_blocked_reason`` (cwd-derived, M1-1) to
decide whether to hand the wire envelope to a connected client. The per-project
store migration retired that egress path entirely — ``_route_event`` now performs
local durable capture only, and a connected client **never** authorizes egress
there; WP08's runtime publisher owns the admitted WebSocket path through the WP06
transport gate. The recorded judgement above ``_route_event`` in ``emitter.py``
names this file as the pin for both halves of that decision:

* **No consent state opens a publish here.** Granted, refused, absent, and
  unreadable consent all leave ``ws_client.send_event`` untouched. The positive
  publish controls the old file carried (``..._is_still_published``) are premise
  obsolete: there is no opportunistic publish left for a consenting project either,
  so those scenarios now pin "queued for the runtime publisher, not sent inline".
* **Refusing egress is not data loss.** Local capture is the documented
  unconditional outbox (issue #1072), keyed on the *event's own* ``project_uuid``
  — never cwd — into that project's own store (FR-006). C-002 forbids deleting
  rows on refusal, so the durability assertions here are load-bearing in the other
  direction: a "fix" that dropped a non-consenting project's event must fail.

Assertions stay at the client seam — a recorded ``send_event`` call is the egress
attempt, so "never published" means nothing left the process — plus the project
store, the durable artefact that decides later deliverability.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.event_journal.journal import EventJournal
from specify_cli.sync.clock import LamportClock
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.project_identity import ProjectIdentity
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.queue import OfflineQueue

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.unit, pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-0000-0000-0000-00000000000a"
UUID_B = "bbbbbbbb-0000-0000-0000-00000000000b"

_ACTOR = "ws-publish-consent-test"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test project stores; machine-global arming patched on, env var deleted.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is machine-global arming and never a grant, so a
    developer's own export must not decide anything here. ``is_saas_sync_enabled``
    is patched True because a machine with SaaS sync off short-circuits every
    drain classification to ``saas_disabled`` and the per-project question is never
    reached.

    The machine layout authority is published ``project_only`` once (it is a
    machine-wide record shared by every project under this isolated home): live
    payload writes require the project-only layout, and these tests exercise the
    live capture path, not the migration.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    # Arm the emitter directly: with the enable flag deleted (a developer's export
    # must not decide anything here), the canonical ``sync_active()`` gate in
    # ``_emit`` would otherwise read False and short-circuit before local capture.
    # ``is_saas_sync_enabled`` stays patched because the emitter still consults it
    # for the direct-ingress team-slug branch (independent of the arming gate).
    monkeypatch.setattr("specify_cli.sync.emitter.sync_active", lambda: True)
    monkeypatch.setattr("specify_cli.sync.emitter.is_saas_sync_enabled", lambda: True)
    authority = ProjectSyncStore(UUID_A).layout_generation()
    authority.begin_cutover(_ACTOR)
    authority.publish_project_only(_ACTOR, verify_exact=lambda: True)


@pytest.fixture(autouse=True)
def _authenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    """An authenticated session with a resolvable Private Teamspace.

    Under the old implementation these were preconditions of the publish branch.
    They are kept deliberately: with every readiness gate satisfied, the only thing
    stopping an egress attempt is the removal of the direct-transport path itself —
    so ``ws.sent == []`` cannot pass for an unrelated setup reason.
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

    ``send_event`` is a real coroutine, so the recording only happens if the
    emitter actually drives it — the coroutine body is the egress.
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
    """A checkout whose ``.kittify/config.yaml`` declares identity and legacy consent.

    Under UUID-owned consent authority these files are read-only diagnostic
    evidence: they can neither grant nor refuse. They are kept in the scenarios so
    the tests prove exactly that — a committed ``sync.enabled`` value in cwd's
    checkout decides nothing about another project's events.
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

    Caching is the whole point: ``_get_identity`` resolves once per emitter
    lifetime, so under ``SyncRuntime`` the stamped identity stays fixed while cwd
    moves. No queue is attached: capture must go through the transient per-project
    path, which selects the store from the event's own ``project_uuid``.
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
        queue=None,
        ws_client=ws_client,  # type: ignore[arg-type]
        _identity=ProjectIdentity(
            project_uuid=UUID(project_uuid),
            project_slug="acme-payroll",
            node_id="ws-node",
            build_id="06e643fb-d025-48b7-afc2-b46d4925bdfa",
        ),
        _git_resolver=resolver,
    )


def _store_event_ids(project_uuid: str) -> set[str]:
    """The durable journal rows in *project_uuid*'s own store."""
    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        return {event.event_id for event in journal.read_all()}


def _queue_size(project_uuid: str) -> int:
    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        return OfflineQueue(unit, store.layout_generation()).size()


# --------------------------------------------------------------------------- #
# The original M1-1 scenario, end to end through the real emit path             #
# --------------------------------------------------------------------------- #


def test_a_cwd_grant_does_not_publish_another_projects_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Runtime up, identity cached to A, cwd inside a "consenting" B, client connected.

    Project A has no consent record anywhere; project B's own committed config says
    ``sync.enabled: true``. Neither a cwd-derived gate nor the retired direct
    transport may put A's envelope — including ``project_slug``, a client engagement
    name — on the wire.
    """
    ws = _RecordingWsClient()
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == [], (
        "project B's checkout said sync.enabled: true, and something published "
        "project A's envelope over the WebSocket. No emitter path may perform "
        f"direct WebSocket transport: {ws.published_uuids}"
    )
    assert event is not None, (
        "the event must still be emitted and locally durable; withholding the "
        "publish is not the same as dropping the emission"
    )


def test_the_refused_publish_leaves_the_event_locally_durable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refusing egress must not become a second way to lose the operator's data.

    The project-owned store is the durable outbox and the refusal is about
    *shipping*. This is the converse guard that stops "fix it by dropping the
    event" from passing (issue #1072 / C-002 retention).
    """
    ws = _RecordingWsClient()
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == []
    assert _queue_size(UUID_A) == 1, (
        "the envelope must remain in project A's own durable outbox; local capture "
        "is deliberately not consent-gated (the recorded judgement above "
        "_route_event), so refusal of egress may not drop the row"
    )


# --------------------------------------------------------------------------- #
# Consent cannot open the retired direct transport either                       #
# --------------------------------------------------------------------------- #


def test_a_consenting_projects_envelope_is_queued_not_directly_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Premise migrated: the opportunistic publish is retired for *everyone*.

    This test's ancestor was the positive control — a consenting project's envelope
    had to reach the WebSocket. WP02/WP08 removed the direct-transport branch: a
    grant now buys drain eligibility for the runtime publisher, never an inline
    ``send_event``. The strongest surviving assertion is both-sided: nothing is
    sent, and the envelope is durably queued for the admitted path.
    """
    from specify_cli.sync.consent import record_project_opt_in

    ws = _RecordingWsClient()
    record_project_opt_in(UUID_A, actor=_ACTOR)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == [], (
        "a consent grant must not reopen the retired direct WebSocket transport; "
        "egress belongs to the runtime publisher behind the transport gate"
    )
    assert event is not None
    assert event["event_id"] in _store_event_ids(UUID_A), (
        "the consenting project's event must be durably queued in its own store "
        "for the runtime publisher — this gate is not an emission kill switch"
    )


def test_an_explicit_opt_in_captures_from_outside_any_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The daemon's usual case: no readable checkout for the project at all.

    Consent lives in the UUID-owned project store (the retired machine index can no
    longer grant), so an emitter standing nowhere near a checkout must still capture
    into the project's own store — and still must not touch the client.
    """
    from specify_cli.sync.consent import record_project_opt_in

    ws = _RecordingWsClient()
    record_project_opt_in(UUID_A, actor=_ACTOR)
    outside = tmp_path / "not-a-project"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == []
    assert event is not None
    assert event["event_id"] in _store_event_ids(UUID_A)


def test_the_projects_own_explicit_refusal_outranks_an_earlier_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Premise migrated from FR-013: refusal beats grant, on the one live chain.

    The checkout-file refusal this test's ancestor exercised is now diagnostic
    evidence only; the authoritative refusal surface is an explicit opt-out in the
    project's own store, which supersedes the earlier opt-in. Nothing may be sent,
    and — per C-002 — the refusal seals egress eligibility without destroying the
    locally captured row.
    """
    from specify_cli.sync.consent import (
        record_project_opt_in,
        record_project_opt_out,
        resolve_project_consent,
    )

    ws = _RecordingWsClient()
    record_project_opt_in(UUID_A, actor=_ACTOR)
    record_project_opt_out(UUID_A, actor=_ACTOR)
    refusing_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=False)
    monkeypatch.chdir(refusing_a)

    assert resolve_project_consent(UUID_A).granted is False, (
        "an explicit opt-out recorded after an opt-in must refuse"
    )

    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)
    event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == [], (
        "project A explicitly opted out; a refusal outranks the earlier grant, so "
        "nothing may be published"
    )
    assert event is not None
    assert event["event_id"] in _store_event_ids(UUID_A), (
        "refusal governs egress, not local retention (C-002)"
    )


def test_a_consent_read_failure_refuses_the_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-003's rule: inability to determine consent is not consent.

    The emitter swallows exceptions by design so emission never fails; that
    instinct must not convert an unanswerable consent question into egress — and
    must not destroy local durability either.
    """
    from specify_cli.sync.consent import record_project_opt_in

    ws = _RecordingWsClient()
    record_project_opt_in(UUID_A, actor=_ACTOR)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)
    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)

    def _explode(*_args: object, **_kwargs: object) -> frozenset[str]:
        raise RuntimeError("consent index unreadable")

    monkeypatch.setattr("specify_cli.sync.consent.consented_project_uuids", _explode)

    event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

    assert ws.sent == [], "a consent read that raises must refuse the publish"
    assert event is not None
    assert event["event_id"] in _store_event_ids(UUID_A), (
        "an unanswerable consent question blocks egress, not local capture"
    )


# --------------------------------------------------------------------------- #
# Direct pins on the routing seam                                               #
# --------------------------------------------------------------------------- #


def _envelope(
    project_uuid: str | None,
    *,
    blocked: str | None = None,
    event_id: str = "01JTESTTESTTESTTESTTESTTEST",
) -> dict[str, Any]:
    # canonical-event-exempt(exception-flow): legacy WPStatusChanged wire shape (no correlation_id); drives the routing seam
    return {
        "event_id": event_id,
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

    An event with no resolvable ``project_uuid`` has no project-owned outbox to
    select and can never be shown to belong to a consenting project: nothing may
    be sent, and nothing may be stored.
    """
    ws = _RecordingWsClient()
    outside = tmp_path / "not-a-project"
    outside.mkdir()
    monkeypatch.chdir(outside)
    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)

    routed = emitter._route_event(_envelope(None))

    assert routed is False
    assert ws.sent == []


def test_route_event_still_honours_an_upstream_drain_blocked_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The advisory field must keep narrowing, even for a consenting project.

    A ``missing_team`` envelope is retained for the drain to re-evaluate; it must never
    become an inline publish, consent or no consent.
    """
    from specify_cli.sync.consent import record_project_opt_in

    ws = _RecordingWsClient()
    record_project_opt_in(UUID_A, actor=_ACTOR)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)
    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)

    emitter._route_event(_envelope(UUID_A, blocked="missing_team"))

    assert ws.sent == [], "a no_team envelope must never be published opportunistically"


def test_one_long_lived_emitter_routes_each_envelope_to_its_own_projects_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ``SyncRuntime`` shape: one emitter and one client, cwd moved underneath.

    Four routing attempts, two projects, two working directories. Nothing may reach
    the client from anywhere, and each envelope must land in the store of the
    project it *belongs to* — cwd can neither select nor widen the destination.
    """
    from specify_cli.sync.consent import record_project_opt_in

    ws = _RecordingWsClient()
    record_project_opt_in(UUID_A, actor=_ACTOR)  # A consents; B does not
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    refusing_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=False)
    emitter = _emitter(tmp_path, project_uuid=UUID_A, ws_client=ws)

    original = Path(os.getcwd())
    try:
        for cwd in (consenting_a, refusing_b):
            os.chdir(cwd)
            for uuid, tag in ((UUID_A, "a"), (UUID_B, "b")):
                event_id = f"01JTEST{tag.upper()}FROM{cwd.name[-1].upper()}".ljust(26, "0")
                emitter._route_event(_envelope(uuid, event_id=event_id))
    finally:
        os.chdir(original)

    assert ws.published_uuids == [], (
        "no envelope may be published from _route_event, from either working "
        f"directory, for either project: {ws.published_uuids}"
    )
    ids_a = _store_event_ids(UUID_A)
    ids_b = _store_event_ids(UUID_B)
    assert len(ids_a) == 2 and all(id_.startswith("01JTESTA") for id_ in ids_a), (
        f"exactly the two project-A envelopes belong in A's store: {sorted(ids_a)}"
    )
    assert len(ids_b) == 2 and all(id_.startswith("01JTESTB") for id_ in ids_b), (
        f"exactly the two project-B envelopes belong in B's store: {sorted(ids_b)}"
    )
