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
    credentials.store(repo="github.com/acme/spec-kitty", relay_url=managed_stream_double.url, token="team-a-cred", token_kind="shared_team")
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="a" * 12)))
    managed_stream_double.close_stream()

    result = runner.invoke(app, ["status", "github.com/acme/spec-kitty", "--timeout", "2.0", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repo"] == "github.com/acme/spec-kitty"
    assert payload["presence"][0]["session_ref"] == "a" * 12
    assert managed_stream_double.received_headers[0].get("X-Zeitgeist-Capability") == "team-a-cred"


def test_watch_end_to_end_over_a_real_loopback_double(state_root: Path, managed_stream_double) -> None:
    credentials.store(repo="github.com/acme/spec-kitty", relay_url=managed_stream_double.url, token="team-a-cred", token_kind="shared_team")
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="b" * 12)))
    managed_stream_double.close_stream()

    result = runner.invoke(app, ["watch", "github.com/acme/spec-kitty", "--timeout", "2.0", "--json"])
    assert result.exit_code == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    frame = json.loads(lines[0])
    assert frame["frame_type"] == "presence"
    assert frame["payload"]["actor"]["session_ref"] == "b" * 12


# --- spec-kitty#137: no repo argument derives the key from the checkout -----


def _checkout_with_origin(bare: Path, dest: Path, origin: str) -> Path:
    """A minimal checkout whose origin claims ``origin`` (same shape as
    test_resolution.py's helper; fixtures are not shared across top-level
    test directories)."""
    import subprocess

    bare.mkdir(parents=True)
    subprocess.run(["git", "init", "--bare", "-q"], cwd=bare, check=True, capture_output=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(dest)], check=True, capture_output=True)
    subprocess.run(["git", "remote", "set-url", "origin", origin], cwd=dest, check=True, capture_output=True)
    return dest


def test_status_with_no_repo_argument_reads_the_checkout_own_credential(
    state_root: Path, managed_stream_double, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The #137 acceptance probe, end to end: the bridge auto-mints under
    ``github.com/acme/widget`` (resolution.store_key of the checkout's
    origin); ``status`` run inside that checkout with NO repo argument must
    find exactly that entry — and a stale pre-#132 bare-name entry in the
    same store file must be neither matched nor served."""
    checkout = _checkout_with_origin(
        tmp_path / "server" / "acme" / "widget.git",
        tmp_path / "work" / "acme" / "widget",
        "https://github.com/acme/widget.git",
    )
    credentials.store(repo="github.com/acme/widget", relay_url=managed_stream_double.url, token="team-a-cred", token_kind="shared_team")
    # A leftover live-shaped bearer from before #132, still on disk.
    with credentials.credentials_path().open("a") as fh:
        fh.write('\n["widget"]\nrelay_url = "http://stale.invalid"\ntoken = "stale-bearer"\n')
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="c" * 12)))
    managed_stream_double.close_stream()

    monkeypatch.chdir(checkout)
    result = runner.invoke(app, ["status", "--timeout", "2.0", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repo"] == "github.com/acme/widget"
    assert payload["presence"][0]["session_ref"] == "c" * 12
    assert managed_stream_double.received_headers[0].get("X-Zeitgeist-Capability") == "team-a-cred"
