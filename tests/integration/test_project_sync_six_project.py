"""T050 / FR-019 / SC-006: the core-owned six-project omission proof.

Six deterministic local projects A-F exist on one machine. Only project A is
admitted (per-project opt-in **and** an admitted target row). The real
capture->dispatch path is driven through ``_run_dispatch_batches`` with the real
``_HttpReceiver`` transport whose poster — the exact network boundary — records
the EXACT bytes of every request. The proof is byte-level omission:

* every identifier of project A appears in the transmitted bytes, and
* no marker, UUID, slug, or event id of projects B-F appears in ANY transmitted
  byte sequence (URLs, headers, raw gzip request bodies, decompressed bodies,
  and any WebSocket frame).

Core owns **omission only** (FR-019): this test never simulates a server-side
refusal for B-F. SaaS-owned evidence (bypass/legacy refusal, zero server side
effects) is produced and owned by the SaaS repository — referenced by the WP11
manifest, never regenerated here.

The B-F denial matrix covers every core-owned way a project can be non-admitted
without any server involvement:

========  =================================  ==========================
project   consent record                     target admission row
========  =================================  ==========================
A         granted                            admitted
B         none (absence is denial, #3030)    none
C         none                               admitted (no consent)
D         explicitly opted out               none
E         granted                            none (no admission)
F         granted then revoked               admitted (revoked consent)
========  =================================  ==========================
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from specify_cli.cli.commands import sync as sync_module
from specify_cli.delivery.dispatcher import DispatchSummary, dispatch
from specify_cli.delivery.receivers import _HttpReceiver
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.client import WebSocketClient
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

pytestmark = [pytest.mark.integration, pytest.mark.fast]

_EVENTS_PER_PROJECT = 3


@dataclass(frozen=True)
class _Project:
    """One deterministic row of the six-project contract matrix."""

    letter: str
    uuid: str
    #: "granted" | "absent" | "opted_out" | "revoked"
    consent: str
    #: whether an admitted ``project_target_admissions`` row exists
    admitted: bool

    @property
    def slug(self) -> str:
        return f"six-proj-{self.letter}-slug"

    @property
    def secret(self) -> str:
        """A payload marker that exists nowhere but this project's events."""
        return f"SECRET-{self.letter.upper()}-{self.uuid}"

    @property
    def event_ids(self) -> tuple[str, ...]:
        return tuple(f"evt-{self.letter}-{index}" for index in range(_EVENTS_PER_PROJECT))

    @property
    def markers(self) -> tuple[str, ...]:
        """Every identifier whose bytes must be traceable on (A) / absent from (B-F) the wire."""
        return (self.uuid, self.slug, self.secret, *self.event_ids)


PROJECT_A = _Project("a", "aaaaaaaa-0000-0000-0000-00000000000a", consent="granted", admitted=True)
PROJECT_B = _Project("b", "bbbbbbbb-0000-0000-0000-00000000000b", consent="absent", admitted=False)
PROJECT_C = _Project("c", "cccccccc-0000-0000-0000-00000000000c", consent="absent", admitted=True)
PROJECT_D = _Project("d", "dddddddd-0000-0000-0000-00000000000d", consent="opted_out", admitted=False)
PROJECT_E = _Project("e", "eeeeeeee-0000-0000-0000-00000000000e", consent="granted", admitted=False)
PROJECT_F = _Project("f", "ffffffff-0000-0000-0000-00000000000f", consent="revoked", admitted=True)

ALL_PROJECTS = (PROJECT_A, PROJECT_B, PROJECT_C, PROJECT_D, PROJECT_E, PROJECT_F)
DENIED_PROJECTS = (PROJECT_B, PROJECT_C, PROJECT_D, PROJECT_E, PROJECT_F)

_ACTOR = "six-project-proof"


class _FakeResponse:
    """Minimal ``HttpResponse`` for the recording poster (never a real socket)."""

    def __init__(self, status_code: int, body: Mapping[str, Any]) -> None:
        self._status_code = status_code
        self._body = body

    @property
    def status_code(self) -> int:
        return self._status_code

    def json(self) -> Any:
        return self._body


@dataclass
class _RecordingPoster:
    """The exact network boundary: records every POST's URL, headers, and raw bytes.

    Sitting at ``_HttpReceiver._poster`` — the physical sink named by the WP09
    adapter contract for ``direct_dispatcher``/``final_exit_sync`` — means the
    recorded ``data`` IS the byte sequence the CLI would put on the wire, gzip
    framing included, not a reconstruction of it.
    """

    posts: list[tuple[str, bytes, dict[str, str]]] = field(default_factory=list)

    def __call__(self, url: str, *, data: bytes, headers: Mapping[str, str], timeout: float) -> _FakeResponse:
        del timeout
        self.posts.append((url, bytes(data), dict(headers)))
        body = json.loads(gzip.decompress(data).decode("utf-8"))
        results = [{"event_id": event["event_id"], "status": "success"} for event in body["events"]]
        return _FakeResponse(200, {"results": results})

    def transmitted_blobs(self) -> list[bytes]:
        """Every byte sequence that left the CLI, raw and decoded forms alike."""
        blobs: list[bytes] = []
        for url, data, headers in self.posts:
            blobs.append(url.encode("utf-8"))
            blobs.append(json.dumps(headers, sort_keys=True).encode("utf-8"))
            blobs.append(data)
            blobs.append(gzip.decompress(data))
        return blobs


class _RecordingHttpReceiver(_HttpReceiver):
    """The REAL HTTP receiver (build -> gzip -> POST -> map) over a recording poster."""

    def __init__(self, poster: _RecordingPoster) -> None:
        self._poster = poster

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__six-project-proof__/api/v1/events/batch/"


def _event(event_id: str, project: _Project, *, ordinal: int) -> Event:
    created_at = f"2026-08-01T00:00:{ordinal:02d}+00:00"
    payload = {
        "event_id": event_id,
        "project_slug": project.slug,
        "marker": project.secret,
    }
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=json.dumps(payload).encode("utf-8"),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=project.uuid,
    )


def _insert_admitted_row(store: ProjectSyncStore, project: _Project) -> None:
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
            "'admitted', '1', 'private-teamspace:team')",
            (project.uuid,),
        )


def _materialize_project(project: _Project) -> ProjectSyncStore:
    """Create one matrix row exactly: layout, journal rows, consent, admission."""
    store = ProjectSyncStore(project.uuid)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover(_ACTOR)
        authority.publish_project_only(_ACTOR, verify_exact=lambda: True)
    # Consent BEFORE capture: rows are epoch-stamped at append time, and only
    # rows in an eligible consent epoch are ever selectable (WP03). A granted
    # project's live captures happen under its granted epoch; capturing first
    # would park A's rows in a pre-consent epoch and starve the drain — the
    # exact fail-closed behavior the revoked/opted-out rows below rely on.
    if project.consent == "granted":
        record_project_opt_in(project.uuid, actor=_ACTOR)
    elif project.consent == "opted_out":
        record_project_opt_out(project.uuid, actor=_ACTOR)
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, authority)
        for index, event_id in enumerate(project.event_ids):
            journal.append(_event(event_id, project, ordinal=index))
    if project.consent == "revoked":
        record_project_opt_in(project.uuid, actor=_ACTOR)
        record_project_opt_out(project.uuid, actor=_ACTOR)
    if project.admitted:
        _insert_admitted_row(store, project)
    return store


@pytest.fixture
def websocket_frames(monkeypatch: pytest.MonkeyPatch) -> list[bytes]:
    """Record any WebSocket wire frame so "everything transmitted" includes them.

    The capture->dispatch drain is HTTP-only, so this list must stay empty — but
    recording (rather than asserting emptiness by construction) means a future
    change that routed a frame through the WebSocket sink would still be caught
    by the byte-absence assertion below.
    """
    frames: list[bytes] = []
    original_send_wire = WebSocketClient._send_wire

    async def _recording_send_wire(self: WebSocketClient, wire: dict[str, Any]) -> None:
        frames.append(json.dumps(wire, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        await original_send_wire(self, wire)

    monkeypatch.setattr(WebSocketClient, "_send_wire", _recording_send_wire)
    return frames


@pytest.fixture
def six_projects(canonical_home: None, monkeypatch: pytest.MonkeyPatch) -> dict[str, ProjectSyncStore]:
    del canonical_home  # the ONE SPEC_KITTY_HOME owner (R1a #3121) pins the home
    # The WP06 transport lease binds egress eligibility only while the machine
    # kill switch is armed (arming is NOT consent — #3030; the per-project rows
    # built above still decide what ships).
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    return {project.uuid: _materialize_project(project) for project in ALL_PROJECTS}


def _drain(store: ProjectSyncStore, receiver: _RecordingHttpReceiver) -> DispatchSummary:
    """Run the real CLI drain loop for one project's resolved target."""
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    runtime = SimpleNamespace(store=store, context=store.create_context())
    return sync_module._run_dispatch_batches(runtime, receiver, target)


def test_six_project_run_transmits_only_admitted_project_a_bytes(
    six_projects: dict[str, ProjectSyncStore],
    websocket_frames: list[bytes],
) -> None:
    """FR-019 / SC-006 core half: only A's bytes ever leave the CLI."""
    poster = _RecordingPoster()
    receiver = _RecordingHttpReceiver(poster)

    # Projects with a resolvable target row are drained through the REAL loop.
    summary_a = _drain(six_projects[PROJECT_A.uuid], receiver)
    summary_c = _drain(six_projects[PROJECT_C.uuid], receiver)
    summary_f = _drain(six_projects[PROJECT_F.uuid], receiver)

    # Projects without an admitted row resolve NO delivery target: the CLI has
    # nothing to dispatch, and a None-target dispatch is a receiver-free no-op.
    for project in (PROJECT_B, PROJECT_D, PROJECT_E):
        store = six_projects[project.uuid]
        with store.unit_of_work() as unit:
            resolved = ProjectDeliveryTargetRegistry(store).get_current(unit)
        assert resolved is None, f"project {project.letter} must have no resolvable delivery target"
        assert dispatch(receiver=receiver, target=None) == DispatchSummary.empty()

    # The admitted project actually shipped — the instrument records something,
    # so the absence assertions below are measurements, not vacuous truths.
    assert summary_a.delivered == _EVENTS_PER_PROJECT
    assert summary_a.selected == _EVENTS_PER_PROJECT
    assert len(poster.posts) == 1, "A's three events fit one batch; nothing else may POST"

    # Consent-denied projects select nothing even with an admitted target row.
    assert summary_c.selected == 0 and summary_c.recorded == 0
    assert summary_f.selected == 0 and summary_f.recorded == 0

    transmitted = poster.transmitted_blobs() + websocket_frames
    assert transmitted, "no bytes were captured — the transport was not exercised"

    body = json.loads(gzip.decompress(poster.posts[0][1]).decode("utf-8"))
    wire_event_ids = tuple(event["event_id"] for event in body["events"])
    assert wire_event_ids == PROJECT_A.event_ids

    # Project A's identifiers appear in the exact transmitted bytes.
    decompressed = gzip.decompress(poster.posts[0][1])
    for marker in PROJECT_A.markers:
        assert marker.encode("utf-8") in decompressed, f"admitted marker {marker!r} missing from the wire"

    # THE property: every B-F marker is byte-absent from EVERYTHING transmitted.
    for project in DENIED_PROJECTS:
        for marker in project.markers:
            needle = marker.encode("utf-8")
            for blob in transmitted:
                assert needle not in blob, (
                    f"project {project.letter} marker {marker!r} appeared in transmitted "
                    "bytes; a non-admitted project reached the wire (FR-019 omission "
                    "proof violated)"
                )

    # Core owns omission only: no server-side refusal was simulated anywhere —
    # the recording poster answered success for every batch it ever saw, so a
    # denied project could only have been kept off the wire by the CLI itself.
    assert websocket_frames == []
