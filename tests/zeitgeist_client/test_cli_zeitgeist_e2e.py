"""Z7-C: one true end-to-end run of ``spec-kitty zeitgeist status`` — CLI
invocation through ``subscription.py`` through ``FilteredStream`` to a real
loopback SSE double. The unit-level CLI paths (help text, error handling,
``--json`` framing) are covered with mocked ``subscription`` calls in
``tests/cli/commands/test_zeitgeist_command.py``; this file is the one place
that proves the whole wire-up actually works end to end, not just each
layer in isolation.
"""

from __future__ import annotations

import json
import time
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
    return {"schema_version": "1.0.0", "epoch": epoch, "seq": seq, "emitted_at": time.time(), "frame": frame}


def _presence(session_ref: str = "a" * 12) -> dict[str, object]:
    return {"type": "presence", "presence": {"actor": {"session_ref": session_ref}, "observed_at": time.time(), "ttl_s": 30}}


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
