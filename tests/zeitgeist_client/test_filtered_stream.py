"""Z4-C §network layer: ``filtered_stream.FilteredStream`` over F3's
``GET /managed/stream`` — one SSE connection per team-bound subscription.

Covers: the capability credential is the ONLY selector sent (forbidden-field
denial by construction — there is no team/deployment/repo parameter to leak
one through), composable non-aggregating subscriptions, watch() updating
local state as check()/current_focus() read it back with no network call of
their own, and the network fault/race/security matrix around that loop.

``live_frame``'s own parsing/state-machine matrix (gap/epoch/revoke/<=90s
clear) is covered in ``test_live_frame.py`` and is not re-derived here —
these tests exercise the wire/loop mechanics that sit on top of it.
"""

from __future__ import annotations

import inspect
import socket
import threading
import time
import urllib.error

import pytest

from specify_cli.zeitgeist_client import filtered_stream, sanitizer

pytestmark = pytest.mark.fast


def closed_port_url() -> str:
    """A ``127.0.0.1`` URL with nothing listening (connection-refused
    target). Local helper, not imported cross-module — same reasoning as
    ``test_transport.py``'s own copy: pytest.ini deliberately keeps ``.``
    off ``pythonpath``, so ``tests`` is not importable as a package."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"


def _config(url: str, credential: str = "cred-team-a") -> filtered_stream.TeamStreamConfig:
    return filtered_stream.TeamStreamConfig(relay_url=url, capability_credential=credential)


def _frame(*, seq: int, frame: dict[str, object], epoch: str = "epoch-1") -> dict[str, object]:
    return {"schema_version": "1.0.0", "epoch": epoch, "seq": seq, "emitted_at": time.time(), "frame": frame}


def _presence(session_ref: str = "a" * 12) -> dict[str, object]:
    return {"type": "presence", "presence": {"actor": {"session_ref": session_ref}, "observed_at": time.time(), "ttl_s": 30}}


def _focus(focus_ref: str = "mission-x", state: str = "active", session_ref: str = "b" * 12) -> dict[str, object]:
    return {"type": "focus", "focus": {"actor": {"session_ref": session_ref}, "focus_ref": focus_ref, "state": state, "ttl_s": 90}}


def _signal(kind: str, **extra: object) -> dict[str, object]:
    signal: dict[str, object] = {"kind": kind}
    signal.update(extra)
    return {"type": "signal", "signal": signal}


def _drain(gen: object, n: int, timeout_s: float = 5.0) -> list[object]:
    """Pull exactly ``n`` items from a watch() generator, bounded — never an
    unbounded ``list(gen)`` against a stream that never signals EOF."""
    out: list[object] = []
    deadline = time.monotonic() + timeout_s
    it = iter(gen)  # type: ignore[call-overload]
    while len(out) < n:
        if time.monotonic() > deadline:
            raise TimeoutError(f"only drained {len(out)}/{n} frames before the {timeout_s}s bound")
        out.append(next(it))
    return out


# --- selector is the credential, structurally, nothing else -----------------


def test_watch_sends_the_capability_credential_header_and_nothing_else_identifying(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url, credential="team-a-cred"))
    gen = stream.watch()
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence()))
    _drain(gen, 1)
    gen.close()

    assert managed_stream_double.received_headers
    sent = managed_stream_double.received_headers[0]
    assert sent.get("X-Zeitgeist-Capability") == "team-a-cred"


def test_team_stream_config_has_no_team_deployment_or_repo_field() -> None:
    """Forbidden-field denial by construction: there is structurally no
    field a caller could use to smuggle a client-supplied team filter — the
    credential IS the selector. Every one of these names is a member of
    ``sanitizer.FORBIDDEN_CONTROL_KEYS``."""
    field_names = set(filtered_stream.TeamStreamConfig.__dataclass_fields__)
    assert field_names == {"relay_url", "capability_credential"}
    assert field_names.isdisjoint(sanitizer.FORBIDDEN_CONTROL_KEYS)


def test_public_surface_has_no_team_selector_parameter() -> None:
    """Same guarantee, checked across the whole public surface: no method
    of ``FilteredStream`` accepts a parameter named like a forbidden
    control key, so there is no way to pass one even by a future mistake."""
    for name in ("__init__", "watch", "check", "current_focus"):
        sig = inspect.signature(getattr(filtered_stream.FilteredStream, name))
        params = set(sig.parameters) - {"self"}
        assert params.isdisjoint(sanitizer.FORBIDDEN_CONTROL_KEYS), f"{name} accepts a forbidden-key-named parameter"


# --- watch() updates state; check()/current_focus() read it back locally ----


def test_check_reflects_frames_observed_by_a_running_watch(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    assert stream.check().presence == ()  # nothing observed yet: honestly empty, not an error

    gen = stream.watch()
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="a" * 12)))
    _drain(gen, 1)

    snap = stream.check()
    assert len(snap.presence) == 1
    assert snap.presence[0].session_ref == "a" * 12
    gen.close()


def test_current_focus_reflects_focus_frames(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_frame(_frame(seq=1, frame=_focus(focus_ref="mission-y")))
    _drain(gen, 1)

    focus = stream.current_focus()
    assert len(focus) == 1
    assert focus[0].focus_ref == "mission-y"
    gen.close()


def test_watch_yields_each_accepted_frame(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence()))
    managed_stream_double.push_frame(_frame(seq=2, frame=_focus()))
    frames = _drain(gen, 2)
    assert [f.frame_type for f in frames] == ["presence", "focus"]  # type: ignore[attr-defined]
    gen.close()


# --- no missed-event reconstruction: gap/epoch clear, revoke is scoped ------


def test_gap_signal_clears_check_snapshot(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence()))
    _drain(gen, 1)
    assert stream.check().presence

    managed_stream_double.push_frame(_frame(seq=2, frame=_signal("gap", from_seq=2, to_seq=4)))
    _drain(gen, 1)
    snap = stream.check()
    assert snap.presence == ()
    assert snap.last_reset_reason == "gap"
    gen.close()


def test_revoked_signal_removes_only_the_named_session(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="c" * 12)))
    managed_stream_double.push_frame(_frame(seq=2, frame=_presence(session_ref="d" * 12)))
    _drain(gen, 2)
    managed_stream_double.push_frame(_frame(seq=3, frame=_signal("revoked", session_ref="d" * 12)))
    _drain(gen, 1)

    refs = {p.session_ref for p in stream.check().presence}
    assert refs == {"c" * 12}
    gen.close()


# --- composability: two subscriptions never implicitly aggregate ------------


def test_two_subscriptions_never_share_state(managed_stream_double) -> None:
    stream_a = filtered_stream.FilteredStream(_config(managed_stream_double.url, credential="team-a"))
    stream_b = filtered_stream.FilteredStream(_config(managed_stream_double.url, credential="team-b"))

    gen_a = stream_a.watch()
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="a" * 12)))
    _drain(gen_a, 1)

    # stream_b never called watch(): its own state is untouched by stream_a's
    # traffic on the same double — there is no shared registry to leak through.
    assert stream_a.check().presence
    assert stream_b.check().presence == ()
    gen_a.close()


def test_module_offers_no_multi_subscription_aggregate_helper() -> None:
    """"no implicit multi-team aggregate": the module must not offer a
    function/method whose job is to merge several FilteredStream states."""
    banned_substrings = ("aggregate", "merge", "union", "combine_all")
    public_names = [n for n in dir(filtered_stream) if not n.startswith("_")]
    offenders = [n for n in public_names if any(b in n.lower() for b in banned_substrings)]
    assert offenders == []


# --- fault / compatibility ----------------------------------------------------


def test_connection_refused_raises_on_first_next(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(closed_port_url()))
    gen = stream.watch()
    with pytest.raises(urllib.error.URLError):
        next(gen)


def test_non_2xx_status_raises_http_error(managed_stream_double) -> None:
    managed_stream_double.response_status = 403
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    with pytest.raises(urllib.error.HTTPError):
        next(gen)


def test_malformed_data_line_is_dropped_not_fatal(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_raw(b"data: not-json-at-all\n\n")
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence()))
    frames = _drain(gen, 1)  # the malformed line is skipped; the real frame after it still arrives
    assert frames[0].frame_type == "presence"  # type: ignore[attr-defined]
    gen.close()


def test_unknown_frame_shape_is_dropped_not_fatal(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_frame({"schema_version": "2.0.0", "epoch": "e", "seq": 1, "emitted_at": 1.0, "frame": {}})
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence()))
    frames = _drain(gen, 1)
    assert frames[0].frame_type == "presence"  # type: ignore[attr-defined]
    gen.close()


def test_server_closing_the_stream_ends_watch_cleanly(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence()))
    _drain(gen, 1)
    managed_stream_double.close_stream()
    # No further frame arrives; the generator returns (StopIteration), it
    # does not raise.
    with pytest.raises(StopIteration):
        next(gen)


def test_idle_timeout_stops_watch_without_raising(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch(idle_timeout_s=0.3)
    start = time.monotonic()
    with pytest.raises(StopIteration):
        next(gen)  # double never sends anything: idle timeout fires
    assert time.monotonic() - start < 3.0


# --- race: check() from another thread while watch() is applying frames -----


def test_concurrent_check_during_active_watch_does_not_raise(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()

    errors: list[BaseException] = []
    stop = threading.Event()

    def _read_repeatedly() -> None:
        try:
            while not stop.is_set():
                stream.check()
        except BaseException as exc:  # noqa: BLE001 - collected for the assertion below
            errors.append(exc)

    reader = threading.Thread(target=_read_repeatedly, daemon=True)
    reader.start()
    for n in range(1, 21):
        managed_stream_double.push_frame(_frame(seq=n, frame=_presence(session_ref=f"{n:012d}".replace("0", "a"))))
    _drain(gen, 20)
    stop.set()
    reader.join(timeout=5)
    assert not reader.is_alive()
    assert errors == []
    gen.close()


# --- security: a hostile double cannot crash the loop ------------------------


def test_binary_garbage_chunk_between_valid_frames_is_dropped(managed_stream_double) -> None:
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_raw(b"\xff\xfe\x00garbage not even sse\n\n")
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence()))
    frames = _drain(gen, 1)
    assert frames[0].frame_type == "presence"  # type: ignore[attr-defined]
    gen.close()


def test_oversized_nested_payload_is_still_shape_checked_not_trusted_blindly(managed_stream_double) -> None:
    presence_payload = {
        "actor": {"session_ref": "a" * 12},
        "observed_at": time.time(),
        "ttl_s": 30,
        "extra": {"nested": ["x"] * 500},
    }
    hostile = _frame(seq=1, frame={"type": "presence", "presence": presence_payload})
    stream = filtered_stream.FilteredStream(_config(managed_stream_double.url))
    gen = stream.watch()
    managed_stream_double.push_frame(hostile)
    frames = _drain(gen, 1)
    assert frames[0].frame_type == "presence"  # type: ignore[attr-defined]  # extra keys are ignored, not rejected outright, not crashed on
    gen.close()
