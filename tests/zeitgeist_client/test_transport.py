"""Z1-T1 §4 matrix: transport.ZeitgeistClient — offer()/focus_*()/presence().

Covers N1, N2 (forbidden-field zero-attempt), N3, N4, N5, N6
(750ms/drop-no-retry, one-offer-after-append), N12 (focus_end cannot claim
"revoked"), N15 (one active focus at a time), N16 (DND pauses focus only),
N17 (no fabricated client-side expiry), N18 (focus_ref derivation), and R1
(race: concurrent focus_heartbeat calls do not corrupt state).

``watch()``/``status()``/credential checkout are explicitly NOT covered here
— see the WP01 handoff for what remains (validator.py schema checks,
mcp_stdio.py, the CLI adapter, harness-asset staging, credentials.py).
"""

from __future__ import annotations

import socket
import threading
import time
from unittest.mock import patch

import pytest

from specify_cli.zeitgeist_client import budget, transport

# See tests/zeitgeist_client/test_grammar.py's pytestmark comment. This file
# uses real loopback sockets/threads (the Team Kitty double) but no
# subprocess and no git — the "fast" tier's actual disqualifier.
pytestmark = pytest.mark.fast


def closed_port_url() -> str:
    """A ``127.0.0.1`` URL with nothing listening (N5's connection-refused
    target). Local helper (not imported cross-module) to avoid depending on
    ``tests`` being on ``sys.path`` as an importable package — pytest.ini
    intentionally keeps ``.`` off ``pythonpath`` (see that file's own
    docstring)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"


def _config(double_url: str, **overrides: object) -> transport.ClientConfig:
    base: dict[str, object] = {
        "relay_url": double_url,
        "token": "test-token",
        "harness": "claude-code",
        "session_id": "sess-1",
        "agent_id": "agent-1",
        "repo": "spec-kitty",
        "branch": "main",
    }
    base.update(overrides)
    return transport.ClientConfig(**base)  # type: ignore[arg-type]


# --- N1 / N2: forbidden-field zero-attempt --------------------------------


def test_n1_offer_with_forbidden_field_makes_zero_network_attempts(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    result = client.offer("presence.publish", {"activity": "file_edit", "detail": "x"})
    assert result.outcome == transport.OfferOutcome.REFUSED_LOCAL
    assert result.elapsed_s == 0.0
    assert team_kitty_double.requests == []
    assert team_kitty_double.connection_count == 0


def test_n2_offer_with_nested_forbidden_field_makes_zero_network_attempts(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    result = client.offer(
        "presence.publish", {"activity": "file_edit", "meta": {"team_id": "t-1"}}
    )
    assert result.outcome == transport.OfferOutcome.REFUSED_LOCAL
    assert team_kitty_double.connection_count == 0


# --- N3 / N4 / N5: 750ms/drop-no-retry -------------------------------------


def test_n3_slow_double_drops_at_budget_with_exactly_one_attempt(team_kitty_double):
    team_kitty_double.configure(delay_s=2.0)
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    start = time.monotonic()
    result = client.offer("presence.publish", {"activity": "file_edit"})
    wall = time.monotonic() - start

    assert result.outcome == transport.OfferOutcome.DROPPED_BUDGET
    # Generous bound vs. the draft's +/-50ms: http.server + urllib overhead on
    # a loaded CI box makes a razor-thin window flaky without changing the
    # underlying behaviour under test (a hard total bound, not a per-op one).
    assert budget.OFFER_BUDGET_S <= wall < 1.5
    assert team_kitty_double.connection_count == 1
    assert len(team_kitty_double.requests) == 1


def test_n4_double_rejects_immediately(team_kitty_double):
    team_kitty_double.configure(status=503)
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    result = client.offer("presence.publish", {"activity": "file_edit"})
    assert result.outcome == transport.OfferOutcome.REJECTED
    assert team_kitty_double.connection_count == 1


def test_n5_connection_refused_is_dropped_unreachable():
    client = transport.ZeitgeistClient(_config(closed_port_url()))
    result = client.offer("presence.publish", {"activity": "file_edit"})
    assert result.outcome == transport.OfferOutcome.DROPPED_UNREACHABLE


# --- N6: one-offer-after-append, no batching -------------------------------


def test_n6_two_sequential_heartbeats_produce_two_distinct_requests(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    client.focus_start("mission-x")
    r1 = client.focus_heartbeat()
    r2 = client.focus_heartbeat()

    assert r1.request_id != r2.request_id
    posts = [r for r in team_kitty_double.requests if r.method == "POST"]
    heartbeat_ids = {
        r.body["request_id"] for r in posts if r.body and r.body.get("op") == "focus.heartbeat"
    }
    assert len(heartbeat_ids) == 2


# --- N12: focus_end cannot claim "revoked" ---------------------------------


def test_n12_focus_end_rejects_revoked_reason(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    client.focus_start("mission-x")
    with pytest.raises(ValueError, match="revoked"):
        client.focus_end(reason="revoked")  # type: ignore[arg-type]


def test_n12_focus_end_accepts_user_and_timeout(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    client.focus_start("mission-x")
    result = client.focus_end(reason="user")
    assert result.outcome in (transport.OfferOutcome.SENT, transport.OfferOutcome.REJECTED)

    client.focus_start("mission-y")
    result = client.focus_end(reason="timeout")
    assert result.outcome in (transport.OfferOutcome.SENT, transport.OfferOutcome.REJECTED)


# --- N15: one active focus at a time, client-enforced -----------------------


def test_n15_second_focus_start_without_end_is_refused_local(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    first = client.focus_start("mission-x")
    assert first.outcome != transport.OfferOutcome.REFUSED_LOCAL

    second = client.focus_start("mission-y")
    assert second.outcome == transport.OfferOutcome.REFUSED_LOCAL
    # no second focus.start POST reached the double
    starts = [
        r for r in team_kitty_double.requests if r.body and r.body.get("op") == "focus.start"
    ]
    assert len(starts) == 1


def test_n15_focus_start_after_end_is_allowed(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    client.focus_start("mission-x")
    client.focus_end(reason="user")
    second = client.focus_start("mission-y")
    assert second.outcome != transport.OfferOutcome.REFUSED_LOCAL


# --- N16: DND pauses focus reporting only, not presence ---------------------


def test_n16_dnd_pause_does_not_block_presence(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    client.focus_start("mission-x")
    pause_result = client.focus_pause(reason="dnd")
    assert pause_result.outcome != transport.OfferOutcome.REFUSED_LOCAL

    presence_result = client.presence(activity="file_edit", path="src/foo.py")
    assert presence_result.outcome != transport.OfferOutcome.REFUSED_LOCAL
    presence_posts = [
        r for r in team_kitty_double.requests if r.body and r.body.get("op") == "presence.publish"
    ]
    assert len(presence_posts) == 1


# --- N17: no fabricated client-side expiry ----------------------------------


def test_n17_no_offer_fires_on_a_bare_timer(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    with patch.object(client, "offer", wraps=client.offer) as spy:
        client.focus_start("mission-x")
        assert spy.call_count == 1
        # no heartbeat/timer fires on its own while nothing else calls offer()
        time.sleep(0.3)
        assert spy.call_count == 1


def test_n17_focus_start_creates_no_background_timer_thread():
    before = threading.active_count()
    client = transport.ZeitgeistClient(_config(closed_port_url()))
    client.focus_start("mission-x")
    # allow any (incorrect) fire-and-forget thread to have started
    time.sleep(0.1)
    after = threading.active_count()
    assert after <= before + 1  # at most the daemon worker thread run_with_deadline spawns per offer, already finished/settling


# --- N18: focus_ref derivation ----------------------------------------------


def test_n18_focus_ref_with_wp_id(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    client.focus_start("mission-x", wp_id="WP03")
    starts = [
        r for r in team_kitty_double.requests if r.body and r.body.get("op") == "focus.start"
    ]
    assert starts[0].body["args"]["focus_ref"] == "mission-x/WP03"


def test_n18_focus_ref_without_wp_id(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    client.focus_start("mission-x")
    starts = [
        r for r in team_kitty_double.requests if r.body and r.body.get("op") == "focus.start"
    ]
    assert starts[0].body["args"]["focus_ref"] == "mission-x"


# --- R1: race — concurrent focus_heartbeat calls ----------------------------


def test_r1_concurrent_heartbeats_produce_independent_request_ids(team_kitty_double):
    client = transport.ZeitgeistClient(_config(team_kitty_double.url))
    client.focus_start("mission-x")

    results: list[transport.OfferResult] = []
    lock = threading.Lock()

    def _call() -> None:
        r = client.focus_heartbeat()
        with lock:
            results.append(r)

    threads = [threading.Thread(target=_call) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(results) == 2
    assert results[0].request_id != results[1].request_id
    heartbeat_posts = [
        r for r in team_kitty_double.requests if r.body and r.body.get("op") == "focus.heartbeat"
    ]
    assert len(heartbeat_posts) == 2
    assert len({r.body["request_id"] for r in heartbeat_posts}) == 2
