"""FR-026: the daemon publish path is a live egress point with no consent gate (#3030).

Two functions send a full wire envelope off the machine with no per-project consent
check at all. Before this file, ``grep -n "consent"`` returned nothing in
``sync/runtime.py``, nothing in ``sync/events.py`` and nothing in ``sync/daemon.py``.

    sync/runtime.py::SyncRuntime.publish_event
        └── self.ws_client.send_event(event)          ← the network

    sync/events.py::_publish_event_via_sync_daemon
        └── POST http://127.0.0.1:<port>/api/sync/publish
              └── daemon.py::handle_sync_publish
                    └── runtime.publish_event(raw_event)

``_publish_event_via_sync_daemon`` has **twelve** production callers, not the one the
report named: the eleven ``emit_*`` wrappers in ``sync/events.py`` and the
``MissionCreated`` branch of ``_lifecycle_saas_fanout_handler`` in ``sync/__init__.py``.
Every one of them hands over an envelope that ``EventEmitter._emit`` returns
*regardless of consent* — a non-consenting project's event is refused by the journal
capture gate and withheld by ``_route_event``, and then returned to the caller, which
POSTs it to the daemon anyway. The gates on that path were ``is_saas_sync_enabled()``
— machine-global arming, which the spec states is never a grant and which is the
2026-07-27 incident's own mechanism — plus a resolvable repo root, which is *scope*,
not consent.

The confidentiality content is not incidental metadata: ``project_slug`` and the
mission slug are client engagement names in this repository.

Both seams are pinned here, both directions, at the transport: a recorded
``send_event`` call and a recorded POST body are the egress attempts, so "never
published" means the bytes never left. Every refusal test is paired with a positive
control in which the same transport does carry a consenting project's envelope —
without it a gate that simply never publishes, or a fixture where the transport was
unreachable for an unrelated reason, would satisfy every refusal and prove nothing.

The daemon's ``POST /api/sync/publish`` endpoint is covered by the ``publish_event``
seam rather than by a spawned daemon: ``handle_sync_publish`` decodes the payload,
checks the daemon token and calls ``runtime.publish_event`` — that call is its only
egress action, and the gate sits inside it.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.sync import events as events_module
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.layout_generation import LayoutAuthorityError
from specify_cli.sync.project_identity import NIL_PROJECT_UUID
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.runtime import SyncRuntime

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

#: A client engagement name, i.e. the confidentiality content itself. Asserted absent
#: from the raw transport bytes rather than inferred from a boolean return value.
CARVE_OUT = "acme-holdings-carve-out"


@pytest.fixture(autouse=True)
def _isolated_home(canonical_home: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test consent index and queue; machine-global arming neutralised.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is arming and never a grant (``consent.py``
    level 3), so a developer's own export must not decide anything here. Each test
    gets its own ``SPEC_KITTY_HOME`` — the mission's daemon tests share a port band
    and a machine-global store, and a shared home is how one case's grant answers
    another's question.
    """
    del canonical_home  # R1b (#3121): per-test home isolation provided by the canonical SPEC_KITTY_HOME owner
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    # Retained: no autouse restores SPEC_KITTY_SAAS_URL, and these daemon-publish tests need it.
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://app.spec-kitty.ai")
    manager = SimpleNamespace(
        get_current_session=lambda: SimpleNamespace(
            email="account-1",
            teams=[SimpleNamespace(id="teamspace-1", is_private_teamspace=True)],
        )
    )
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: manager)


def _checkout(tmp_path: Path, name: str, *, uuid: str, consents: bool | None) -> Path:
    """A checkout whose ``.kittify/config.yaml`` declares identity and consent.

    ``consents=None`` writes no ``sync`` section — the 2026-07-27 incident's actual
    state for the five leaked projects, and the one FR-002 requires to deny.
    """
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}", "  node_id: 0123456789ab"]
    if consents is not None:
        lines += ["sync:", f"  enabled: {str(consents).lower()}"]
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    try:
        authority.begin_cutover("wp09-daemon-regression")
    except LayoutAuthorityError as exc:
        if "already project-only" not in str(exc):
            raise
    else:
        authority.publish_project_only(
            "wp09-daemon-regression",
            verify_exact=lambda: True,
        )


def _admit_project(project_uuid: str) -> ProjectSyncStore:
    record_project_opt_in(project_uuid, actor="wp09-daemon-regression")
    store = ProjectSyncStore(project_uuid)
    _project_only(store)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://app.spec-kitty.ai', 'account-1', 'teamspace-1', 4, "
            "'admitted', '1', 'private-teamspace:teamspace-1')",
            (project_uuid,),
        )
    return store


def _envelope(project_uuid: str | None, *, slug: str, mission: str) -> dict[str, Any]:
    """A ``MissionCreated`` wire envelope — the shape the reported fan-out relays."""
    # canonical-event-exempt(exception-flow): reproduces the 2026-07-27 incident's legacy fan-out wire shape (no correlation_id)
    event: dict[str, Any] = {
        "event_id": "01JTESTTESTTESTTESTTESTTES" + (project_uuid or "x")[0],
        "event_type": "MissionCreated",
        "aggregate_id": mission,
        "aggregate_type": "Mission",
        "schema_version": "3.0.0",
        "build_id": "06e643fb-d025-48b7-afc2-b46d4925bdfa",
        "payload": {"mission_slug": mission, "mission_number": 3030, "wp_count": 4},
        "node_id": "ws-node",
        "lamport_clock": 7,
        "causation_id": None,
        "timestamp": "2026-07-30T07:00:00+00:00",
        "project_slug": slug,
    }
    if project_uuid is not None:
        event["project_uuid"] = project_uuid
    return event


def _envelope_a() -> dict[str, Any]:
    return _envelope(UUID_A, slug="acme-payroll", mission="payroll-refresh")


def _envelope_b() -> dict[str, Any]:
    """Never-opted-in project B, carrying an engagement name in two places."""
    return _envelope(UUID_B, slug=CARVE_OUT, mission=f"{CARVE_OUT}-disclosure-schedule")


# --------------------------------------------------------------------------- #
# Seam 1 — SyncRuntime.publish_event, the WebSocket egress point               #
# --------------------------------------------------------------------------- #


class _RecordingWsClient:
    """A connected client that records every envelope handed to ``send_event``.

    ``send_event`` is a real coroutine driven on the runtime's own loop, so a
    recording happens only if ``publish_event`` actually completed the send.
    """

    def __init__(self) -> None:
        self.connected = True
        self.sent: list[dict[str, Any]] = []

    async def send_event(self, event: dict[str, Any]) -> bool:
        self.sent.append(event)
        return True

    async def disconnect(self) -> None:
        self.connected = False

    @property
    def published_uuids(self) -> list[str | None]:
        return [event.get("project_uuid") for event in self.sent]

    @property
    def wire_bytes(self) -> str:
        return json.dumps(self.sent, sort_keys=True, default=str)


@pytest.fixture
def runtime_and_client() -> Any:
    """A started runtime with its **own** loop thread and a connected fake client.

    The loop is created and torn down per test on purpose. ``publish_event`` drives
    ``asyncio.run_coroutine_threadsafe`` against ``self._async_loop``, so a loop that
    a sibling test closed turns the send into a caught "WebSocket publish failed" —
    which would make every negative pin below pass for entirely the wrong reason.
    Owning the loop removes the dependence instead of tolerating it.

    ``started=True`` is set directly so no test needs the real ``start()`` path
    (config, auth, auto-start gate); the publish decision under test is independent
    of all of it.
    """
    runtime = SyncRuntime()
    client = _RecordingWsClient()
    runtime._ensure_async_loop()
    runtime.ws_client = client
    runtime.started = True
    try:
        yield runtime, client
    finally:
        loop = runtime._async_loop
        thread = runtime._async_loop_thread
        if loop is not None:
            loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=5.0)
        if loop is not None:
            loop.close()
        runtime._async_loop = None
        runtime._async_loop_thread = None
        runtime.ws_client = None
        runtime.started = False


def test_the_loop_and_client_fixture_can_actually_publish(runtime_and_client: Any) -> None:
    """The harness's own positive control: prove the transport works at all.

    A probe that reports refusal for every case — including the valid one — because
    its fixture was wrong is how this mission previously collected five apparent
    successes that proved nothing. If this test fails, no refusal below means anything.
    """
    runtime, client = runtime_and_client
    _admit_project(UUID_A)

    assert runtime.publish_event(_envelope_a()) is True
    assert client.published_uuids == [UUID_A]


def test_publish_event_withholds_an_unconsented_projects_envelope(
    runtime_and_client: Any,
) -> None:
    """The FR-026 red, in its strongest form: two projects, one transport.

    Project A consents through the uuid-keyed index — the daemon's usual case, since
    it holds no checkout for the project it is publishing for. Project B has no
    consent record anywhere. Only A's envelope may reach the client, and B's
    engagement name must appear nowhere in the bytes the transport received.
    """
    runtime, client = runtime_and_client
    _admit_project(UUID_A)

    published_b = runtime.publish_event(_envelope_b())
    published_a = runtime.publish_event(_envelope_a())

    assert client.published_uuids == [UUID_A], (
        f"the WebSocket publish must be decided from the event's own project_uuid. Project B never opted in anywhere, yet: {client.published_uuids}"
    )
    assert CARVE_OUT not in client.wire_bytes, f"project B's engagement name left the machine inside the published envelope: {client.wire_bytes}"
    assert published_b is False, "a refused publish must report that it did not publish"
    assert published_a is True, "the positive control must still publish; this gate is not a kill switch"


@pytest.mark.parametrize(
    ("label", "event"),
    [
        ("absent key", _envelope(None, slug=CARVE_OUT, mission="m")),
        ("explicit None", {**_envelope(None, slug=CARVE_OUT, mission="m"), "project_uuid": None}),
        ("blank", {**_envelope(None, slug=CARVE_OUT, mission="m"), "project_uuid": "   "}),
        ("nil sentinel", _envelope(NIL_PROJECT_UUID, slug=CARVE_OUT, mission="m")),
        ("not a mapping", "MissionCreated for acme-holdings-carve-out"),
    ],
)
def test_an_unresolvable_project_uuid_denies_the_publish(runtime_and_client: Any, label: str, event: Any) -> None:
    """FR-003's rule at an egress point: cannot determine is never consent.

    NFR-001's second half is that an event whose project cannot be identified can
    never be *shown* to belong to a consenting one, so the nil sentinel and a blank
    string are absence, not a groupable value. Probed as a set rather than as the one
    shape that happens to surface — this mission has now found fail-open in four
    separate places, each first reported as a single shape.
    """
    runtime, client = runtime_and_client

    assert runtime.publish_event(event) is False, label
    assert client.sent == [], f"{label}: an unidentifiable envelope was published"


def test_a_consent_read_that_raises_refuses_the_publish(runtime_and_client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """The ``except`` branch is pinned, not trusted.

    ``publish_event`` is best-effort by contract and swallows failures so emission
    never breaks; that instinct must not convert an unanswerable consent question
    into egress. A guard whose ``except`` quietly starts returning True reports clean
    forever.
    """
    runtime, client = runtime_and_client
    _admit_project(UUID_A)

    def _explode(*_a: object, **_kw: object) -> frozenset[str]:
        raise RuntimeError("consent index unreadable")

    monkeypatch.setattr("specify_cli.sync.project_store.ProjectSyncStore.create_context", _explode)

    assert runtime.publish_event(_envelope_a()) is False
    assert client.sent == []


def test_the_projects_own_committed_refusal_outranks_an_index_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runtime_and_client: Any) -> None:
    """C-003: the decision goes down the one existing chain, not to the index.

    FR-013/FR-019 — a refusal committed in the project's own ``.kittify/config.yaml``
    beats a stale machine-global grant. A second, local copy of the precedence rules
    would take the index's answer and publish.
    """
    runtime, client = runtime_and_client
    _admit_project(UUID_A)
    record_project_opt_out(UUID_A, actor="wp09-daemon-regression")
    monkeypatch.chdir(_checkout(tmp_path, "project-a", uuid=UUID_A, consents=False))

    assert runtime.publish_event(_envelope_a()) is False
    assert client.sent == []


def test_machine_global_arming_never_grants_the_publish(runtime_and_client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """The incident's own mechanism must not authorise anything.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` armed the machine on 2026-07-27 and five
    never-opted-in projects shipped. Arming on, no consent record: refused.
    """
    runtime, client = runtime_and_client
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    assert runtime.publish_event(_envelope_b()) is False
    assert client.sent == []


def test_a_refused_publish_does_not_start_the_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The refusal precedes every side effect of the publish, including ``start()``.

    ``publish_event`` starts the runtime and opens a WebSocket when it is not running
    yet. A non-consenting project's envelope must not be the thing that brings the
    transport up, and putting the gate first is what makes the refusal independent of
    auth, arming and the auto-start gate.
    """
    runtime = SyncRuntime()
    started = MagicMock(name="start")
    monkeypatch.setattr(runtime, "start", started)
    connected = MagicMock(name="_connect_websocket_if_authenticated")
    monkeypatch.setattr(runtime, "_connect_websocket_if_authenticated", connected)

    assert runtime.publish_event(_envelope_b()) is False
    started.assert_not_called()
    connected.assert_not_called()


# --------------------------------------------------------------------------- #
# Seam 2 — events._publish_event_via_sync_daemon, the producer-side relay      #
# --------------------------------------------------------------------------- #


class _RecordingUrlopen:
    """Records every POST body handed to ``urllib.request.urlopen``."""

    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []

    def __call__(self, request: Any, timeout: float | None = None) -> Any:  # noqa: ARG002
        raw = request.data.decode("utf-8") if getattr(request, "data", None) else "{}"
        self.posts.append(json.loads(raw))
        return _FakeResponse()

    @property
    def published_uuids(self) -> list[str | None]:
        return [post.get("event", {}).get("project_uuid") for post in self.posts]

    @property
    def wire_bytes(self) -> str:
        return json.dumps(self.posts, sort_keys=True, default=str)


class _FakeResponse:
    status = 200

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


@pytest.fixture
def relay_egress(monkeypatch: pytest.MonkeyPatch) -> _RecordingUrlopen:
    """A healthy machine-global daemon and a recording loopback transport.

    ``is_saas_sync_enabled`` is forced on because it is the *only* gate this relay
    had, and with it off the per-project question is never reached — every assertion
    below would pass for the wrong reason.
    """
    recorder = _RecordingUrlopen()
    monkeypatch.setattr(events_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        "specify_cli.sync.daemon.get_sync_daemon_status",
        lambda **_kw: SimpleNamespace(healthy=True, url="http://127.0.0.1:9401", token="daemon-token"),
    )
    monkeypatch.setattr("urllib.request.urlopen", recorder)
    return recorder


def test_the_fanout_relay_can_actually_post(tmp_path: Path, relay_egress: _RecordingUrlopen) -> None:
    """The relay harness's positive control — the daemon POST does happen."""
    _admit_project(UUID_A)
    root = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)

    events_module._publish_event_via_sync_daemon(_envelope_a(), root)

    assert relay_egress.published_uuids == [UUID_A]


def test_the_fanout_does_not_relay_another_projects_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relay_egress: _RecordingUrlopen) -> None:
    """The reported scenario: a daemon-scope grant authorising project B's publish.

    ``_lifecycle_saas_fanout_handler`` relays a ``MissionCreated`` through the
    machine-global daemon with ``repo_root`` as its only project-shaped argument —
    and ``repo_root`` is scope, not consent. Here the scope belongs to consenting
    project A while the envelope belongs to never-opted-in project B: the M1-1 shape
    one level up.
    """
    _admit_project(UUID_A)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)

    events_module._publish_event_via_sync_daemon(_envelope_b(), consenting_a)
    events_module._publish_event_via_sync_daemon(_envelope_a(), consenting_a)

    assert relay_egress.published_uuids == [UUID_A], f"project A's scope relayed project B's envelope to the daemon: {relay_egress.published_uuids}"
    assert CARVE_OUT not in relay_egress.wire_bytes, f"project B's engagement name was handed to the daemon: {relay_egress.wire_bytes}"


def test_the_fanout_refuses_an_unidentifiable_envelope(tmp_path: Path, relay_egress: _RecordingUrlopen) -> None:
    """Same FR-003 rule on the relay: no resolvable uuid, no relay."""
    root = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)

    events_module._publish_event_via_sync_daemon(_envelope(None, slug=CARVE_OUT, mission="m"), root)

    assert relay_egress.posts == []


def test_a_consent_read_that_raises_refuses_the_relay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relay_egress: _RecordingUrlopen) -> None:
    """The relay's ``except`` swallows everything; it must not swallow into egress."""
    _admit_project(UUID_A)
    root = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)

    def _explode(*_a: object, **_kw: object) -> frozenset[str]:
        raise RuntimeError("consent index unreadable")

    monkeypatch.setattr("specify_cli.sync.project_store.ProjectSyncStore.create_context", _explode)

    events_module._publish_event_via_sync_daemon(_envelope_a(), root)

    assert relay_egress.posts == []


def test_a_refused_relay_retains_the_event_in_the_local_outbox(tmp_path: Path, relay_egress: _RecordingUrlopen) -> None:
    """The recorded decision: retained-and-ignored, never dropped.

    Every caller of this relay has already written the envelope to the machine-global
    outbox — ``_lifecycle_saas_fanout_handler`` calls ``OfflineQueue().queue_event``
    immediately before it, and the eleven ``emit_*`` wrappers queue via
    ``_route_event``. That write is deliberately not consent-gated (the recorded
    ``queue_event`` judgement above ``emitter._route_event``: it is not egress, and
    gating it would be data loss rather than confidentiality). The FR-026 refusal is
    therefore transmission-only and removes no durability; the residual at-rest
    exposure is C-006's, whose remedy is FR-016/WP08's operator purge.

    This test is the pin that stops the decision being reversed by accident in
    either direction: a "fix" that dropped the row would fail it, and a relay that
    published anyway fails the assertion above it.
    """
    record_project_opt_out(UUID_B, actor="wp09-daemon-regression")
    store = ProjectSyncStore(UUID_B)
    _project_only(store)
    envelope = _envelope_b()
    with store.unit_of_work() as unit:
        queue = OfflineQueue(unit, store.layout_generation())
        queue.queue_event(envelope)

    events_module._publish_event_via_sync_daemon(envelope, tmp_path)

    assert relay_egress.posts == []
    with store.unit_of_work() as unit:
        retained = OfflineQueue(unit, store.layout_generation()).size()
    assert retained == 1, "refusing egress must not become a second way to lose the operator's data"


def test_the_first_refusal_names_its_cause_and_later_ones_stop_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The operator is told which project and what to do, exactly once.

    An armed machine with a healthy daemon silently withholding a project's events is
    a misconfiguration someone has to be told about, and the remedy has to be the real
    one — this mission has already shipped a message that sent operators to ``chmod``
    for a YAML error. The repeat must not warn: the daemon is long-lived and one line
    per event would bury its own log.
    """
    import logging

    from specify_cli.sync import runtime as runtime_module

    runtime_module._reported_publish_refusals.discard(UUID_B)
    record_project_opt_out(UUID_B, actor="wp09-daemon-regression")
    with caplog.at_level(logging.DEBUG, logger=runtime_module.logger.name):
        assert runtime_module.event_project_consents_to_publish(_envelope_b()) is False
        assert runtime_module.event_project_consents_to_publish(_envelope_b()) is False

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1, f"expected exactly one operator-visible refusal per project: {warnings}"
    reported = warnings[0].getMessage()
    assert UUID_B in reported, f"the refusal must name the project it withheld: {reported}"
    assert "sync opt-in" in reported, f"the refusal must name the real remedy, not a guess: {reported}"
    assert "SPEC_KITTY_ENABLE_SAAS_SYNC" in reported, (
        f"the message must say that arming the machine is not consent — that is the misunderstanding the 2026-07-27 incident ran on: {reported}"
    )


def test_the_gate_does_not_mutate_the_envelope_it_refuses(tmp_path: Path, relay_egress: _RecordingUrlopen) -> None:
    """A refused envelope is handed back to its caller unchanged.

    The callers keep using the returned dict (``_request_dashboard_sync``, the
    queue row, the function's own return value), so the gate must be a decision and
    not a rewrite.
    """
    envelope = _envelope_b()
    before = json.dumps(envelope, sort_keys=True)

    events_module._publish_event_via_sync_daemon(envelope, tmp_path)

    assert json.dumps(envelope, sort_keys=True) == before
    assert relay_egress.posts == []
