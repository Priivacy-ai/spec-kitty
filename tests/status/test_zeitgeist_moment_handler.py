"""The Zeitgeist moment handler at the status/adapters seam (#8).

Pins the three contracts the issue names:

1. **Handler registered → one moment + its liveness frames.** Registering the
   moment handlers puts exactly one handler in each fan-out slot, and one
   status moment produces one ``event.publish`` offer carrying the volatile
   attrs plus (#186) the presence/focus frames that give the relay's live
   panel its liveness state.
2. **No credentials → no network call.** An unresolvable credential ends the
   broadcast before any client exists, let alone a socket.
3. **Budget exceeded → dropped and logged.** A ``dropped_budget`` outcome is
   logged once and never retried, queued, or raised.

Plus the drop paths around them: unencodable payloads cost zero attempts, and
non-volatile lifecycle types are skipped outright. All tests drive the seam
through the same boundaries production does — the ``adapters.fire_*`` functions,
E3's ``resolve_credentials``, and the typed ``ZeitgeistClient`` — with only the
network itself faked (and checkout identity pinned so no test ever shells out
to git).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from specify_cli.status import adapters
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.lifecycle_events import emit_mission_created_local
from specify_cli.status.models import Lane, TransitionRequest
from specify_cli.status import zeitgeist_bridge as bridge
from specify_cli.status.wp_status_metadata import WPStatusChangeMetadata
from specify_cli.zeitgeist_client import resolution as resolution_module
from specify_cli.zeitgeist_client import transport as transport_module
from specify_cli.zeitgeist_client.credentials import StoredCredential
from tests.status.conftest import seed_wp_to_planned as _seed_planned

pytestmark = pytest.mark.fast

_EVENT_ID = "01JME2E2E2E2E2E2E2E2E2E2E2"


@pytest.fixture(autouse=True)
def _zeitgeist_only_registry() -> None:
    """Run every test with the Zeitgeist handlers as the sole wiring.

    Isolates these tests from the sync package's own fan-out handlers and from
    whatever a previous test left registered; restored afterwards so the
    next test sees the production wiring again.
    """
    adapters.reset_handlers()
    adapters.ensure_zeitgeist_moment_handlers()
    yield
    adapters.reset_handlers()
    adapters.ensure_zeitgeist_moment_handlers()


def _credential() -> StoredCredential:
    return StoredCredential(
        relay_url="http://127.0.0.1:9",
        token="relay-token",
        token_issued_at="2026-08-25T00:00:00+00:00",
        token_kind="presence",
        capability_credential="capability-jwt",
    )


@dataclass
class OfferRecorder:
    """Stands in for ``ZeitgeistClient``, recording offers instead of POSTing.

    ``install`` also pins ``ClientConfig.for_repository`` to a fixed identity,
    so the #186 liveness frames exercise the same code path as production
    (a config built from "git truth") without any test ever shelling out to
    git or depending on the host checkout's branch.
    """

    outcome: str = "sent"
    offers: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    configs: list[Any] = field(default_factory=list)
    clients_built: int = 0

    def summaries(self) -> list[tuple[str, str | None]]:
        """(op, event-kind) per offer — the whole "the right frames" contract.

        Only the moment and presence frames carry a ``kind``; focus args name
        their ref instead, so they report ``None``.
        """
        return [(op, args.get("kind")) for op, args in self.offers]

    def moment_offers(self) -> list[tuple[str, dict[str, Any]]]:
        return [(op, args) for op, args in self.offers if op == "event.publish"]

    def install(self, monkeypatch: pytest.MonkeyPatch) -> OfferRecorder:
        recorder = self

        class FakeZeitgeistClient:
            def __init__(self, config: Any) -> None:
                recorder.clients_built += 1
                recorder.configs.append(config)
                self._config = config

            def offer(self, op: str, args: Any) -> Any:
                recorder.offers.append((op, dict(args)))
                return transport_module.OfferResult(
                    outcome=transport_module.OfferOutcome(recorder.outcome),
                    request_id="req-1",
                    elapsed_s=0.01,
                )

            def presence(self, activity: str, path: str | None = None) -> Any:
                config = self._config
                args: dict[str, Any] = {"session_id": config.session_id}
                if config.repo:
                    args["repo"] = config.repo
                if config.branch:
                    args["branch"] = config.branch
                args["kind"] = activity
                if path is not None:
                    args["path"] = path
                return self.offer("presence.publish", args)

            def focus_start(self, mission_slug: str, wp_id: str | None = None) -> Any:
                config = self._config
                focus_ref = mission_slug if wp_id is None else f"{mission_slug}.{wp_id}"
                return self.offer(
                    "focus.start",
                    {
                        "session_id": config.session_id,
                        **({"repo": config.repo} if config.repo else {}),
                        **({"branch": config.branch} if config.branch else {}),
                        "focus_ref": focus_ref,
                        "ttl_s": transport_module.FOCUS_TTL_S,
                    },
                )

        def fake_for_repository(cls: type, cwd: str, **kwargs: Any) -> Any:
            return transport_module.ClientConfig(
                relay_url=kwargs["relay_url"],
                token=kwargs["token"],
                harness=kwargs["harness"],
                session_id=kwargs["session_id"],
                agent_id=kwargs.get("agent_id"),
                repo="demo-repo",
                branch="main",
                capability_credential=kwargs.get("capability_credential"),
            )

        monkeypatch.setattr(transport_module, "ZeitgeistClient", FakeZeitgeistClient)
        monkeypatch.setattr(transport_module.ClientConfig, "for_repository", classmethod(fake_for_repository))
        return recorder


@pytest.fixture
def resolved_credential(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Resolve every credential request to a stored relay credential."""
    seen: list[Path] = []

    def fake_resolve(cwd: Path, **kwargs: Any) -> StoredCredential:
        seen.append(cwd)
        return _credential()

    monkeypatch.setattr(resolution_module, "resolve_credentials", fake_resolve)
    return seen


@pytest.fixture(autouse=True)
def no_focus_capability(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every test to "no focus-kind lease available".

    Focus emission is opt-in per test via :func:`focus_capability`: the
    default here keeps each test's expected frame sequence to moment +
    presence and guarantees no test ever touches the real resolution path
    (which would read the ambient credential store).
    """
    monkeypatch.setattr(resolution_module, "resolve_focus_capability", lambda *a, **k: None)


@pytest.fixture
def focus_capability(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Resolve every focus-capability request to a minted ``focus`` JWT,
    recording the cwd each request came from."""
    seen: list[str] = []

    def fake_resolve(cwd: Path, **kwargs: Any) -> str | None:
        seen.append(str(cwd))
        return "focus-jwt"

    monkeypatch.setattr(resolution_module, "resolve_focus_capability", fake_resolve)
    return seen


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_ensure_registers_exactly_one_zeitgeist_handler_per_slot() -> None:
    adapters.reset_handlers()
    try:
        adapters.ensure_zeitgeist_moment_handlers()
        adapters.ensure_zeitgeist_moment_handlers()  # idempotent
        assert [h.__qualname__ for h in adapters._saas_handlers] == ["saas_moment_handler"]
        assert [h.__qualname__ for h in adapters._lifecycle_saas_handlers] == ["lifecycle_moment_handler"]
        assert [h.__qualname__ for h in adapters._resolved_binding_handlers] == ["resolved_binding_moment_handler"]
    finally:
        adapters.ensure_zeitgeist_moment_handlers()


def test_session_id_matches_the_relay_schema_pattern() -> None:
    # managed_control.schema.json EventArgs.session_id:
    # [A-Za-z0-9][A-Za-z0-9._:-]{0,127}
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", bridge._SESSION_ID)


# ---------------------------------------------------------------------------
# The wire contract: what the real client would put on the socket
# ---------------------------------------------------------------------------

# Pinned from EXPERIMENTAL-zeitgeist's managed_control.schema.json
# $defs/EventArgs: required [session_id, kind, attrs], additionalProperties
# false, the patterns and bounds below. If zeitgeist widens or narrows this,
# this pin is what forces a deliberate re-check.
_EVENT_ARGS_REQUIRED = {"session_id", "kind", "attrs"}
_EVENT_ARGS_ALLOWED = {"session_id", "kind", "ref", "attrs"}


def _assert_event_args(args: dict[str, Any]) -> None:
    assert set(args) <= _EVENT_ARGS_ALLOWED, f"keys outside EventArgs: {sorted(args)}"
    assert set(args) >= _EVENT_ARGS_REQUIRED, f"missing required: {sorted(_EVENT_ARGS_REQUIRED - set(args))}"
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", args["session_id"])
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,63}", args["kind"])
    assert len(args.get("ref", "").encode()) <= 240
    assert len(args["attrs"]) <= 16
    for key, value in args["attrs"].items():
        assert len(key.encode()) <= 64, key
        assert len(value.encode()) <= 240, key


def _pin_checkout_identity(monkeypatch: pytest.MonkeyPatch, *, capability: str) -> None:
    """Pin ``for_repository`` so the real-client wire test never shells to git."""

    def fake_for_repository(cls: type, cwd: str, **kwargs: Any) -> Any:
        return transport_module.ClientConfig(
            relay_url=kwargs["relay_url"],
            token=kwargs["token"],
            harness=kwargs["harness"],
            session_id=kwargs["session_id"],
            agent_id=kwargs.get("agent_id"),
            repo="demo-repo",
            branch="main",
            capability_credential=capability,
        )

    monkeypatch.setattr(transport_module.ClientConfig, "for_repository", classmethod(fake_for_repository))


def test_wire_envelopes_satisfy_the_relay_schema(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
    focus_capability: list[str],
) -> None:
    """Drive the REAL ZeitgeistClient with a stubbed HTTP layer and validate every
    outgoing envelope — moment, presence, focus — against the relay's own
    schema contracts.

    The faked-client tests above prove orchestration; this one proves the wire.
    It fails if offer_args ever omits session_id again (the relay answers 422 to
    an envelope missing it — every frame silently rejected).
    """
    captured: list[Any] = []

    class _FakeResponse:
        status = 202

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def read(self) -> bytes:
            return b"{}"

    def fake_open_bounded(req: Any, timeout: float) -> _FakeResponse:
        captured.append(req)
        return _FakeResponse()

    monkeypatch.setattr(transport_module.budget, "open_bounded", fake_open_bounded)
    _pin_checkout_identity(monkeypatch, capability="capability-jwt")

    _fire_transition()

    # One transition → three envelopes: the moment first, then liveness.
    assert [json.loads(req.data.decode())["op"] for req in captured] == [
        "event.publish",
        "presence.publish",
        "focus.start",
    ]

    moment_req = captured[0]
    body = json.loads(moment_req.data.decode())
    assert body["schema_version"] == "1.0.0"
    _assert_event_args(body["args"])
    args = body["args"]
    assert args["kind"] == "WPStatusChanged"
    assert args["ref"] == "demo-mission"
    assert args["attrs"]["wp_id"] == "WP01"
    assert moment_req.get_header("Authorization") == "Bearer relay-token"
    assert moment_req.get_header("X-zeitgeist-capability") == "capability-jwt"

    # PresencePublish (managed_presence.schema.json): session_id required,
    # additionalProperties false, kind in its closed enum. The presence frame
    # rides the stored presence-kind credential, same as the moment.
    presence_args = json.loads(captured[1].data.decode())["args"]
    assert set(presence_args) <= {"session_id", "repo", "branch", "kind", "path", "host", "harness", "agent_id", "ts"}
    assert presence_args["kind"] == "command"
    assert presence_args["repo"] == "demo-repo"
    assert presence_args["branch"] == "main"

    # FocusArgs (managed_control.schema.json): required [session_id, repo,
    # focus_ref, ttl_s], ident-grammar ref, ttl within the ≤90s bound — and
    # the FOCUS lease on the capability gate, not the presence one.
    focus_body = json.loads(captured[2].data.decode())
    focus_args = focus_body["args"]
    assert set(focus_args) == {"session_id", "repo", "branch", "focus_ref", "ttl_s"}
    assert focus_args["focus_ref"] == "demo-mission.WP01"
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,63}", focus_args["focus_ref"])
    assert focus_args["ttl_s"] == 90
    assert captured[2].get_header("X-zeitgeist-capability") == "focus-jwt"


def test_import_tail_honours_the_minimal_import_gate() -> None:
    """SPEC_KITTY_SYNC_MINIMAL_IMPORT means 'register no transport at import' —
    the Zeitgeist tail is bound by the same gate the sync package obeys."""
    script = "from specify_cli.status import adapters\nprint(len([h for h in adapters._saas_handlers if h.__module__.endswith('zeitgeist_bridge')]))\n"
    gated_env = dict(os.environ)
    gated_env["SPEC_KITTY_SYNC_MINIMAL_IMPORT"] = "1"
    ungated_env = {k: v for k, v in os.environ.items() if k != "SPEC_KITTY_SYNC_MINIMAL_IMPORT"}

    gated = subprocess.run([sys.executable, "-c", script], env=gated_env, text=True, capture_output=True, timeout=120)
    ungated = subprocess.run([sys.executable, "-c", script], env=ungated_env, text=True, capture_output=True, timeout=120)

    assert gated.returncode == 0, gated.stderr
    assert gated.stdout.strip() == "0"
    assert ungated.returncode == 0, ungated.stderr
    assert ungated.stdout.strip() == "1"


def test_review_only_done_transition_still_broadcasts(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    """A done moment whose evidence carries no repos must not die in payload
    validation: local journals treat repos as optional, the canonical model
    requires one — normalised exactly as the sync emitter always did."""
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition(
        to_lane="done",
        metadata=_transition_metadata(evidence={"review": {"reviewer": "rob", "verdict": "approved", "reference": "pr-1"}}),
    )

    # The review-only done transition still broadcasts its moment (plus the
    # #186 presence frame; focus stays off via the autouse fixture).
    assert [op for op, _args in recorder.moment_offers()] == ["event.publish"]
    _op, args = recorder.offers[0]
    assert args["kind"] == "WPStatusChanged"
    assert args["attrs"]["to_lane"] == "done"
    assert "evidence" not in args["attrs"]  # unbroadcast, whatever its shape


# ---------------------------------------------------------------------------
# Slot 1: WP lane transitions -> WPStatusChanged
# ---------------------------------------------------------------------------


def _transition_metadata(**overrides: Any) -> WPStatusChangeMetadata:
    fields: dict[str, Any] = {
        "causation_id": _EVENT_ID,
        "force": False,
        "execution_mode": "worktree",
        "occurred_at": "2026-08-25T09:00:00+00:00",
    }
    fields.update(overrides)
    return WPStatusChangeMetadata(**fields)


def _fire_transition(**overrides: Any) -> None:
    kwargs: dict[str, Any] = {
        "wp_id": "WP01",
        "from_lane": "planned",
        "to_lane": "claimed",
        "actor": "robert",
        "mission_slug": "demo-mission",
        "mission_id": None,
        "metadata": _transition_metadata(),
        "ensure_daemon": False,
    }
    kwargs.update(overrides)
    adapters.fire_saas_fanout(**kwargs)


def test_transition_broadcasts_one_moment_plus_its_liveness_frames(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition()

    # One moment, then its liveness frames (#186): presence always, focus for
    # a WP-carrying broadcast — but only when the focus lease resolves (the
    # autouse fixture keeps it off here).
    assert recorder.summaries() == [
        ("event.publish", "WPStatusChanged"),
        ("presence.publish", "command"),
    ]
    _op, args = recorder.moment_offers()[0]
    assert args["ref"] == "demo-mission"
    attrs = args["attrs"]
    assert attrs["event_id"] == _EVENT_ID
    assert attrs["occurred_at"] == "2026-08-25T09:00:00+00:00"
    assert attrs["mission_slug"] == "demo-mission"
    assert attrs["wp_id"] == "WP01"
    assert attrs["from_lane"] == "planned"
    assert attrs["to_lane"] == "claimed"
    assert attrs["actor"] == "robert"
    # HIC amendment 2026-08-26 (planning decisions/HIC-EPHEMERAL-TEAM-STATUS):
    # ``force`` is an enumeration about the transition, so it rides; the
    # free-text ``reason`` stays local (UNBROADCAST_FIELDS). Identifiers and
    # transition facts ride; prose never does.
    assert attrs["force"] == "false"
    assert "reason" not in attrs


def test_forced_rollback_transition_broadcasts_force_true(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    """A forced backward transition carries ``force="true"`` on the wire.

    The amendment moves ``force`` onto the relay with every other transition
    fact — only its reason text stays local. Re-introducing a bridge-side
    strip of ``force`` fails this test: the codec's attrs go out unfiltered.
    """
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition(
        from_lane="approved",
        to_lane="planned",
        metadata=_transition_metadata(force=True, reason="found a defect after approval"),
    )

    _op, args = recorder.moment_offers()[0]
    assert args["kind"] == "WPStatusChanged"
    assert args["attrs"]["force"] == "true"
    assert "reason" not in args["attrs"]


def test_reason_and_evidence_never_reach_the_wire(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    """The rule that survives the amendment: prose and evidence stay local.

    Both fields are dropped by spec-kitty-events' ``UNBROADCAST_FIELDS``, which
    is now the single owner of the wire vocabulary — this bridge adds no
    filtering of its own, so removing either field there turns this red
    immediately (the keys would reappear in the offered attrs).
    """
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition(metadata=_transition_metadata(force=True, reason="found a defect after approval"))
    _fire_transition(
        to_lane="done",
        metadata=_transition_metadata(
            force=False,
            reason="closing out",
            evidence={
                "repos": [{"repo": "demo", "branch": "main", "commit": "abc1234"}],
                "review": {"reviewer": "rob", "verdict": "approved", "reference": "pr-1"},
            },
        ),
    )

    moments = recorder.moment_offers()
    assert [op for op, _args in moments] == ["event.publish", "event.publish"]
    for _op, args in moments:
        leaked = sorted(key for key in args["attrs"] if key.split(".")[0] in {"reason", "evidence"})
        assert leaked == []


def test_structured_actor_rides_as_its_single_label(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition(actor={"role": "implementer", "profile": "rob", "tool": "claude", "model": None})

    _op, args = recorder.offers[0]
    assert args["attrs"]["actor"] == "rob"


def test_client_config_carries_the_stored_relay_credential(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition()

    config = recorder.configs[0]
    assert config.relay_url == "http://127.0.0.1:9"
    assert config.token == "relay-token"
    assert config.capability_credential == "capability-jwt"


def test_unencodable_payload_drops_before_any_attempt(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path], caplog: pytest.LogCaptureFixture) -> None:
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition(wp_id="WP01" + "x" * 300)  # over the 240-byte attr bound

    assert recorder.offers == []
    assert recorder.clients_built == 0
    assert resolved_credential == []  # codec failure costs zero lookups too
    assert "not broadcast" in caplog.text


def test_malformed_payload_is_logged_and_dropped(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path], caplog: pytest.LogCaptureFixture) -> None:
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition(actor=None)  # StatusTransitionPayload.actor is required

    assert recorder.offers == []
    assert "WPStatusChanged not broadcast" in caplog.text


def test_handler_never_raises_even_when_resolution_explodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    OfferRecorder().install(monkeypatch)

    def exploding_resolve(cwd: Path, **kwargs: Any) -> StoredCredential:
        raise RuntimeError("boom")

    monkeypatch.setattr(resolution_module, "resolve_credentials", exploding_resolve)

    _fire_transition()  # must not raise into the fan-out


# ---------------------------------------------------------------------------
# No credentials / not-a-moment -> nothing leaves the process
# ---------------------------------------------------------------------------


def test_no_credentials_means_no_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = OfferRecorder().install(monkeypatch)
    monkeypatch.setattr(resolution_module, "resolve_credentials", lambda *a, **k: None)

    _fire_transition()

    assert recorder.clients_built == 0
    assert recorder.offers == []


def test_non_volatile_lifecycle_types_broadcast_nothing(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    recorder = OfferRecorder().install(monkeypatch)

    adapters.fire_lifecycle_saas_fanout(
        envelope={"event_type": "SpecifyStarted", "payload": {}},
        log_path=None,
    )

    assert recorder.offers == []
    assert resolved_credential == []  # not even a credential lookup


def test_resolved_binding_slot_is_wired_but_broadcasts_nothing_yet(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    recorder = OfferRecorder().install(monkeypatch)
    caplog.set_level(logging.DEBUG, logger=bridge.__name__)

    adapters.fire_resolved_binding_fanout(
        wp_id="WP01",
        mission_slug="demo-mission",
        actor="robert",
        causation_id=_EVENT_ID,
        occurred_at="2026-08-25T09:00:00+00:00",
        role="implementer",
        agent_profile=None,
        agent_profile_version=None,
        model="claude",
        provider=None,
    )

    assert recorder.offers == []
    assert "not a volatile-family moment" in caplog.text


# ---------------------------------------------------------------------------
# Liveness frames (#186): presence beside every moment, focus beside a WP
# ---------------------------------------------------------------------------


def test_focus_frame_names_mission_dot_wp_when_the_lease_resolves(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
    focus_capability: list[str],
) -> None:
    """E2E-MVP 1.2: a WP transition puts ``<mission>.<WP>`` on the live panel.

    The focus frame is a separate offer on a separate lease: zeitgeist grants
    the focus.* ops only to the ``focus`` credential kind, so its client
    config must carry the focus JWT on the capability gate while the moment
    and presence frames ride the stored presence-kind one.
    """
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition()

    assert recorder.summaries() == [
        ("event.publish", "WPStatusChanged"),
        ("presence.publish", "command"),
        ("focus.start", None),
    ]
    _op, args = recorder.offers[2]
    assert args["focus_ref"] == "demo-mission.WP01"
    assert args["ttl_s"] == transport_module.FOCUS_TTL_S
    assert focus_capability == [str(Path.cwd())]
    # Lease split across the two capability gates.
    assert [config.capability_credential for config in recorder.configs] == [
        "capability-jwt",
        "capability-jwt",
        "focus-jwt",
    ]


def test_presence_rides_the_stored_presence_kind_lease(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
) -> None:
    """``presence.publish`` needs no second mint: the presence kind grants it
    alongside ``event.publish``, so the presence frame reuses the stored
    credential exactly as the moment did."""
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition()

    assert recorder.summaries() == [
        ("event.publish", "WPStatusChanged"),
        ("presence.publish", "command"),
    ]
    _op, args = recorder.offers[1]
    assert args["kind"] == "command"
    assert args["repo"] == "demo-repo"
    assert args["branch"] == "main"
    assert recorder.configs[0].capability_credential == recorder.configs[1].capability_credential == "capability-jwt"


def test_unresolvable_focus_lease_skips_only_focus(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A missing/denied focus mint costs the focus frame alone — never the
    moment, never presence, and never a raised error into the fan-out."""
    recorder = OfferRecorder().install(monkeypatch)
    caplog.set_level(logging.DEBUG, logger=bridge.__name__)

    _fire_transition()

    assert recorder.summaries() == [
        ("event.publish", "WPStatusChanged"),
        ("presence.publish", "command"),
    ]
    assert "no focus-kind capability" in caplog.text


def test_overlong_focus_ref_is_filtered_before_any_attempt(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """managed_control.schema.json caps focus_ref at 64 ident chars; a longer
    ``<mission>.<WP>`` is a guaranteed 422, so it is filtered locally — the
    resolver is never even asked, let alone the relay."""
    recorder = OfferRecorder().install(monkeypatch)

    def must_not_be_asked(cwd: Any, **kwargs: Any) -> str | None:
        raise AssertionError("focus resolver consulted for a ref that cannot go out")

    monkeypatch.setattr(resolution_module, "resolve_focus_capability", must_not_be_asked)
    caplog.set_level(logging.DEBUG, logger=bridge.__name__)

    _fire_transition(mission_slug="m" * 70)

    assert recorder.summaries() == [
        ("event.publish", "WPStatusChanged"),
        ("presence.publish", "command"),
    ]
    assert "does not fit the relay's focus_ref grammar" in caplog.text


def test_unidentifiable_checkout_drops_liveness_but_not_the_moment(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
) -> None:
    """Presence/focus are bound to git truth (Z6-C); where git cannot answer,
    liveness goes silent while the moment still goes out."""
    from specify_cli.zeitgeist_client import repo_identity

    def raising_for_repository(cls: type, cwd: str, **kwargs: Any) -> Any:
        raise repo_identity.RepoIdentityError("no canonical identity")

    recorder = OfferRecorder().install(monkeypatch)
    monkeypatch.setattr(transport_module.ClientConfig, "for_repository", classmethod(raising_for_repository))

    _fire_transition()

    assert recorder.moment_offers() != []
    assert [op for op, _args in recorder.offers if op != "event.publish"] == []


def test_liveness_failure_never_raises_into_the_fanout(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The fan-out slot stays non-raising whatever liveness does — canonical
    persistence and the moment broadcast are unaffected."""

    def exploding_identity(cls: type, cwd: str, **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    recorder = OfferRecorder().install(monkeypatch)
    monkeypatch.setattr(transport_module.ClientConfig, "for_repository", classmethod(exploding_identity))
    caplog.set_level(logging.WARNING, logger=bridge.__name__)

    _fire_transition()  # must not raise

    assert recorder.moment_offers() != []
    assert "presence/focus refresh failed" in caplog.text


def test_mission_creation_publishes_no_focus_even_with_a_lease(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    resolved_credential: list[Path],
    focus_capability: list[str],
) -> None:
    """Mission creation refreshes presence only: there is no WP to name, so
    no focus frame exists even when a focus lease is in hand."""
    recorder = OfferRecorder().install(monkeypatch)
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"

    emit_mission_created_local(
        feature_dir,
        mission_slug="demo-mission",
        mission_id=_EVENT_ID,
        mission_number=1,
        mission_type="software-dev",
        target_branch="main",
        wp_count=2,
        friendly_name="Demo",
        purpose_tldr="tldr",
        purpose_context="context",
    )

    assert recorder.summaries() == [
        ("event.publish", "MissionCreated"),
        ("presence.publish", "command"),
    ]
    assert focus_capability == []  # never consulted without a WP


# ---------------------------------------------------------------------------
# Budget / rejection outcomes: one attempt per moment, logged, no retry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "outcome",
    ["dropped_budget", "rejected", "dropped_unreachable"],
)
def test_non_sent_outcome_is_dropped_and_logged_once(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
    caplog: pytest.LogCaptureFixture,
    outcome: str,
) -> None:
    recorder = OfferRecorder(outcome=outcome).install(monkeypatch)
    caplog.set_level(logging.WARNING, logger=bridge.__name__)

    _fire_transition()
    _fire_transition()

    # One attempt per frame, neither retried nor queued; every drop names the
    # outcome and the no-retry contract, content-exact.
    assert (
        recorder.summaries()
        == [
            ("event.publish", "WPStatusChanged"),
            ("presence.publish", "command"),
        ]
        * 2
    )
    moment_drop = f"Zeitgeist moment WPStatusChanged dropped ({outcome}) after 10 ms; no retry by design"
    presence_drop = f"Zeitgeist presence dropped ({outcome}) after 10 ms; no retry by design"
    assert [m for m in caplog.messages if "dropped" in m] == [moment_drop, presence_drop] * 2


def test_budget_drop_does_not_block_canonical_persistence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The fan-out contract: a hanging/expired relay never touches local truth."""
    recorder = OfferRecorder(outcome="dropped_budget").install(monkeypatch)
    monkeypatch.setattr(resolution_module, "resolve_credentials", lambda *a, **k: _credential())
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)
    _seed_planned(feature_dir, "WP01")

    event = emit_status_transition(
        TransitionRequest(
            feature_dir=feature_dir,
            mission_slug="demo-mission",
            wp_id="WP01",
            to_lane="claimed",
            actor="robert",
        )
    )

    assert event.to_lane is Lane.CLAIMED
    assert recorder.summaries() == [
        ("event.publish", "WPStatusChanged"),
        ("presence.publish", "command"),
    ]


# ---------------------------------------------------------------------------
# Credential-resolution cwd selection
# ---------------------------------------------------------------------------


def test_lifecycle_slot_resolves_credentials_from_the_log_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, resolved_credential: list[Path]) -> None:
    OfferRecorder().install(monkeypatch)
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"

    adapters.fire_lifecycle_saas_fanout(
        envelope={
            "event_type": "MissionClosed",
            "payload": {"mission_slug": "demo-mission", "mission_number": 1, "mission_type": "software-dev"},
        },
        log_path=feature_dir / "status.events.jsonl",
    )

    assert resolved_credential == [feature_dir]


def test_transition_slot_resolves_credentials_from_repo_root_when_given(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, resolved_credential: list[Path]) -> None:
    """Mirrors the lifecycle slot: a caller-supplied checkout root wins over cwd (#125)."""
    OfferRecorder().install(monkeypatch)
    repo_root = tmp_path / "some-other-checkout"

    _fire_transition(repo_root=repo_root)

    assert resolved_credential == [repo_root]


def test_transition_slot_falls_back_to_cwd_when_no_repo_root_given(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    """A caller that omits ``repo_root`` (older wiring, direct calls) keeps the old behaviour."""
    OfferRecorder().install(monkeypatch)

    _fire_transition()

    assert resolved_credential == [Path.cwd()]


# ---------------------------------------------------------------------------
# End-to-end through the producers (real emit path, faked network only)
# ---------------------------------------------------------------------------


def test_lane_transition_via_emit_status_transition_offers_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    resolved_credential: list[Path],
) -> None:
    recorder = OfferRecorder().install(monkeypatch)
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    feature_dir.mkdir(parents=True)
    _seed_planned(feature_dir, "WP01")

    emit_status_transition(
        TransitionRequest(
            feature_dir=feature_dir,
            mission_slug="demo-mission",
            wp_id="WP01",
            to_lane="claimed",
            actor="robert",
        )
    )

    assert recorder.summaries() == [
        ("event.publish", "WPStatusChanged"),
        ("presence.publish", "command"),
    ]
    _op, args = recorder.moment_offers()[0]
    assert args["attrs"]["actor"] == "robert"


def test_mission_creation_via_local_emitter_offers_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    resolved_credential: list[Path],
) -> None:
    recorder = OfferRecorder(outcome="sent").install(monkeypatch)
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"

    emit_mission_created_local(
        feature_dir,
        mission_slug="demo-mission",
        mission_id=_EVENT_ID,
        mission_number=1,
        mission_type="software-dev",
        target_branch="main",
        wp_count=2,
        friendly_name="Demo",
        purpose_tldr="tldr",
        purpose_context="context",
    )

    assert recorder.summaries() == [
        ("event.publish", "MissionCreated"),
        ("presence.publish", "command"),
    ]
    _op, args = recorder.moment_offers()[0]
    assert args["ref"] == "demo-mission"
    assert "friendly_name" not in args["attrs"]  # prose stays local
    assert args["attrs"]["mission_type"] == "software-dev"


def test_mission_created_moment_carries_the_payload_actor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    resolved_credential: list[Path],
) -> None:
    """The WHO a mission-level moment renders with is the payload's ``actor``.

    The local emitter resolves it (#75); the bridge must project it verbatim —
    never fabricate one and never drop it.
    """
    recorder = OfferRecorder(outcome="sent").install(monkeypatch)
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"

    emit_mission_created_local(
        feature_dir,
        mission_slug="demo-mission",
        mission_id=_EVENT_ID,
        mission_number=1,
        mission_type="software-dev",
        target_branch="main",
        wp_count=2,
        friendly_name="Demo",
        purpose_tldr="tldr",
        purpose_context="context",
        actor="robert@example.com",
    )

    # Mission creation carries presence (E2E-MVP 1.1: "presence shows you on
    # EXPERIMENTAL-demo-repo") but no focus — there is no WP to name.
    assert recorder.summaries() == [
        ("event.publish", "MissionCreated"),
        ("presence.publish", "command"),
    ]
    _op, args = recorder.moment_offers()[0]
    assert args["attrs"]["actor"] == "robert@example.com"


def test_status_event_occurrence_time_is_preserved_in_the_attrs(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    """Rule R-T-01: the moment carries the transition's own time, not emission time."""
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition(metadata=_transition_metadata(occurred_at="2026-08-25T11:22:33+00:00"))

    _op, args = recorder.offers[0]
    assert args["attrs"]["occurred_at"] == "2026-08-25T11:22:33+00:00"


def test_throttled_outcome_is_recorded_at_debug_without_a_second_warning(
    monkeypatch: pytest.MonkeyPatch,
    resolved_credential: list[Path],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """#180: a throttled moment is lost loudly, not silently — the client
    prints the one-line stderr notice itself (proven against the real
    ``offer()`` in ``tests/zeitgeist_client/test_transport.py``), so this
    bridge records only the structured detail, at debug level, instead of
    logging the loss a second time (the other drop outcomes keep their
    warning). The recorder throttles every offer it sees, so the moment's
    unconditional presence frame (#186) is throttled too — same discipline,
    same debug-only record, still no warning."""
    recorder = OfferRecorder(outcome="throttled").install(monkeypatch)
    caplog.set_level(logging.DEBUG, logger=bridge.__name__)

    _fire_transition()

    assert recorder.summaries() == [
        ("event.publish", "WPStatusChanged"),
        ("presence.publish", "command"),
    ]
    # Nothing at warning level or above — the loss was already noticed on
    # stderr by the client; only the structured debug record remains.
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
    assert sum("throttled" in r.getMessage() for r in caplog.records) == 2
