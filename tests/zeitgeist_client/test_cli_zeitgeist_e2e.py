"""Z7-C: one true end-to-end run of ``spec-kitty zeitgeist status`` — CLI
invocation through ``subscription.py`` through ``FilteredStream`` to a real
loopback SSE double. The unit-level CLI paths (help text, error handling,
``--json`` framing) are covered with mocked ``subscription`` calls in
``tests/cli/commands/test_zeitgeist_command.py``; this file is the one place
that proves the whole wire-up actually works end to end, not just each
layer in isolation.
"""

from __future__ import annotations

from kernel.clock import now_epoch

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.zeitgeist import app
from specify_cli.zeitgeist_client import credentials

pytestmark = pytest.mark.fast

runner = CliRunner()


@pytest.fixture()
def state_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "spec-kitty-home"))
    return tmp_path / "spec-kitty-home"


def _frame(*, seq: int, frame: dict[str, object], epoch: str = "epoch-1") -> dict[str, object]:
    return {"schema_version": "1.0.0", "epoch": epoch, "seq": seq, "emitted_at": now_epoch(), "frame": frame}


def _presence(session_ref: str = "a" * 12) -> dict[str, object]:
    return {"type": "presence", "presence": {"actor": {"session_ref": session_ref}, "observed_at": now_epoch(), "ttl_s": 30}}


def test_status_end_to_end_over_a_real_loopback_double(state_root: Path, managed_stream_double) -> None:
    credentials.store(repo="spec-kitty", relay_url=managed_stream_double.url, token="team-a-cred", token_kind="shared_team")
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="a" * 12)))
    managed_stream_double.close_stream()

    result = runner.invoke(app, ["status", "spec-kitty", "--timeout", "2.0", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repo"] == "spec-kitty"
    assert payload["presence"][0]["session_ref"] == "a" * 12
    assert managed_stream_double.received_headers[0].get("X-Zeitgeist-Capability") == "team-a-cred"


def test_watch_end_to_end_over_a_real_loopback_double(state_root: Path, managed_stream_double) -> None:
    credentials.store(repo="spec-kitty", relay_url=managed_stream_double.url, token="team-a-cred", token_kind="shared_team")
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="b" * 12)))
    managed_stream_double.close_stream()

    result = runner.invoke(app, ["watch", "spec-kitty", "--timeout", "2.0", "--json"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    frame = json.loads(lines[0])
    assert frame["frame_type"] == "presence"
    assert frame["payload"]["actor"]["session_ref"] == "b" * 12


def _event(session_ref: str = "c" * 12) -> dict[str, object]:
    return {
        "type": "event",
        "event": {
            "observed_at": now_epoch(),
            "kind": "mission.status.changed",
            "actor": {"session_ref": session_ref, "user": "lynn"},
            "ref": "034-demo/WP01",
            "attrs": {"wp_id": "WP01", "to_lane": "for_review"},
        },
    }


def test_watch_end_to_end_delivers_a_status_moment_event_frame(state_root: Path, managed_stream_double) -> None:
    """The demo path's step 1: a teammate moves a WP, and `spec-kitty
    zeitgeist watch` shows it within a second. Before #10 the client dropped
    the relay's `event` frame unread, so the moment never reached Bob."""
    credentials.store(repo="spec-kitty", relay_url=managed_stream_double.url, token="team-a-cred", token_kind="shared_team")
    managed_stream_double.push_frame(_frame(seq=1, frame=_event()))
    managed_stream_double.close_stream()

    result = runner.invoke(app, ["watch", "spec-kitty", "--timeout", "2.0", "--json"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1  # golden-count: cardinality-is-contract (one pushed moment -> one delivered frame)
    frame = json.loads(lines[0])
    assert frame["frame_type"] == "event"
    assert frame["payload"]["kind"] == "mission.status.changed"
    assert frame["payload"]["attrs"] == {"wp_id": "WP01", "to_lane": "for_review"}
