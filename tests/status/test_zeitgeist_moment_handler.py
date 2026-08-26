"""The Zeitgeist moment handler at the status/adapters seam (#8).

Pins the three contracts the issue names:

1. **Handler registered → one offer.** Registering the moment handlers puts
   exactly one handler in each fan-out slot, and one status moment produces
   exactly one ``event.publish`` offer carrying the volatile attrs.
2. **No credentials → no network call.** An unresolvable credential ends the
   broadcast before any client exists, let alone a socket.
3. **Budget exceeded → dropped and logged.** A ``dropped_budget`` outcome is
   logged once and never retried, queued, or raised.

Plus the drop paths around them: unencodable payloads cost zero attempts, and
non-volatile lifecycle types are skipped outright. All tests drive the seam
through the same boundaries production does — the ``adapters.fire_*`` functions,
E3's ``resolve_credentials``, and the typed ``ZeitgeistClient`` — with only the
network itself faked.
"""

from __future__ import annotations

import logging
import re
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
    """Stands in for ``ZeitgeistClient``, recording offers instead of POSTing."""

    outcome: str = "sent"
    offers: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    configs: list[Any] = field(default_factory=list)
    clients_built: int = 0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> OfferRecorder:
        recorder = self

        class FakeZeitgeistClient:
            def __init__(self, config: Any) -> None:
                recorder.clients_built += 1
                recorder.configs.append(config)

            def offer(self, op: str, args: Any) -> Any:
                recorder.offers.append((op, dict(args)))
                return transport_module.OfferResult(
                    outcome=transport_module.OfferOutcome(recorder.outcome),
                    request_id="req-1",
                    elapsed_s=0.01,
                )

        monkeypatch.setattr(transport_module, "ZeitgeistClient", FakeZeitgeistClient)
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


def test_one_offer_per_registered_transition(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition()

    assert len(recorder.offers) == 1
    op, args = recorder.offers[0]
    assert op == "event.publish"
    assert args["kind"] == "WPStatusChanged"
    assert args["ref"] == "demo-mission"
    attrs = args["attrs"]
    assert attrs["event_id"] == _EVENT_ID
    assert attrs["occurred_at"] == "2026-08-25T09:00:00+00:00"
    assert attrs["mission_slug"] == "demo-mission"
    assert attrs["wp_id"] == "WP01"
    assert attrs["from_lane"] == "planned"
    assert attrs["to_lane"] == "claimed"
    assert attrs["actor"] == "robert"
    assert attrs["force"] == "false"
    # Prose stays local (UNBROADCAST_FIELDS): identifiers ride, free text never
    # lives on the team relay.
    assert "reason" not in attrs


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

    # One attempt per moment, each logged once, neither retried nor queued.
    assert len(recorder.offers) == 2
    drops = [m for m in caplog.messages if outcome in m]
    assert len(drops) == 2
    assert all("no retry by design" in m for m in drops)


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
    assert len(recorder.offers) == 1


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

    assert len(recorder.offers) == 1
    op, args = recorder.offers[0]
    assert op == "event.publish"
    assert args["kind"] == "WPStatusChanged"
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

    assert len(recorder.offers) == 1
    _op, args = recorder.offers[0]
    assert args["kind"] == "MissionCreated"
    assert args["ref"] == "demo-mission"
    assert "friendly_name" not in args["attrs"]  # prose stays local
    assert args["attrs"]["mission_type"] == "software-dev"


def test_status_event_occurrence_time_is_preserved_in_the_attrs(monkeypatch: pytest.MonkeyPatch, resolved_credential: list[Path]) -> None:
    """Rule R-T-01: the moment carries the transition's own time, not emission time."""
    recorder = OfferRecorder().install(monkeypatch)

    _fire_transition(metadata=_transition_metadata(occurred_at="2026-08-25T11:22:33+00:00"))

    _op, args = recorder.offers[0]
    assert args["attrs"]["occurred_at"] == "2026-08-25T11:22:33+00:00"
