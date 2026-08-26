"""Z7-C: ``mcp_stdio.py`` — the official-SDK stdio MCP adapter over
``subscription.py``'s shared team-scoped surface.

In-process client/server coverage via ``mcp.shared.memory`` (no subprocess,
no real stdio pipe) — the same official SDK a real MCP client speaks to,
minus the process boundary. Covers: the two-tool surface (``zeitgeist_status``/
``zeitgeist_watch``), explicit ``repo`` argument (no relay_url/token
parameter reaches an MCP client), a bounded read/watch over a real loopback
SSE double, and the not-checked-out fault reported as a tool error rather
than a silently empty/administered result.
"""

from __future__ import annotations

from kernel.clock import now_epoch

from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from specify_cli.zeitgeist_client import credentials, mcp_stdio

pytestmark = [pytest.mark.fast, pytest.mark.asyncio]


@pytest.fixture()
def state_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "spec-kitty-home"))
    return tmp_path / "spec-kitty-home"


def _frame(*, seq: int, frame: dict[str, object], epoch: str = "epoch-1") -> dict[str, object]:
    return {"schema_version": "1.0.0", "epoch": epoch, "seq": seq, "emitted_at": now_epoch(), "frame": frame}


def _presence(session_ref: str = "a" * 12) -> dict[str, object]:
    return {"type": "presence", "presence": {"actor": {"session_ref": session_ref}, "observed_at": now_epoch(), "ttl_s": 30}}


def _checkout(double_url: str, *, repo: str = "github.com/acme/spec-kitty", credential: str = "team-a-cred") -> None:
    credentials.store(repo=repo, relay_url=double_url, token=credential, token_kind="shared_team")


async def test_server_exposes_exactly_the_status_and_watch_tools() -> None:
    server = mcp_stdio.build_server()
    async with create_connected_server_and_client_session(server) as client:
        listed = await client.list_tools()
        names = {t.name for t in listed.tools}
    assert names == {"zeitgeist_status", "zeitgeist_watch"}


async def test_no_tool_input_schema_names_a_relay_url_or_credential_field() -> None:
    server = mcp_stdio.build_server()
    async with create_connected_server_and_client_session(server) as client:
        listed = await client.list_tools()
        for tool in listed.tools:
            props = set((tool.inputSchema or {}).get("properties", {}))
            assert "relay_url" not in props
            assert "token" not in props
            assert "capability_credential" not in props
            assert "runtime_url" not in props
            assert "repo" in props  # the one explicit team-context selector


async def test_status_tool_reports_the_bounded_snapshot(state_root: Path, managed_stream_double) -> None:
    _checkout(managed_stream_double.url)
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence(session_ref="a" * 12)))
    managed_stream_double.close_stream()

    server = mcp_stdio.build_server()
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("zeitgeist_status", {"repo": "github.com/acme/spec-kitty", "timeout_s": 2.0})
    assert not result.isError
    assert result.structuredContent is not None
    assert result.structuredContent["repo"] == "github.com/acme/spec-kitty"
    assert len(result.structuredContent["presence"]) == 1
    assert result.structuredContent["presence"][0]["session_ref"] == "a" * 12


async def test_watch_tool_reports_bounded_frames(state_root: Path, managed_stream_double) -> None:
    _checkout(managed_stream_double.url)
    managed_stream_double.push_frame(_frame(seq=1, frame=_presence()))
    managed_stream_double.close_stream()

    server = mcp_stdio.build_server()
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("zeitgeist_watch", {"repo": "github.com/acme/spec-kitty", "timeout_s": 2.0})
    assert not result.isError
    assert result.structuredContent["repo"] == "github.com/acme/spec-kitty"
    frames = result.structuredContent["frames"]
    assert len(frames) == 1
    assert frames[0]["frame_type"] == "presence"


async def test_status_tool_reports_a_tool_error_when_not_checked_out(state_root: Path) -> None:
    server = mcp_stdio.build_server()
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("zeitgeist_status", {"repo": "never-checked-out"})
    assert result.isError
    text = " ".join(c.text for c in result.content if hasattr(c, "text"))
    assert "never-checked-out" in text


async def test_watch_tool_reports_a_tool_error_when_not_checked_out(state_root: Path) -> None:
    server = mcp_stdio.build_server()
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("zeitgeist_watch", {"repo": "never-checked-out"})
    assert result.isError


async def test_watch_tool_honors_max_frames(state_root: Path, managed_stream_double) -> None:
    _checkout(managed_stream_double.url)
    for n in range(1, 6):
        managed_stream_double.push_frame(_frame(seq=n, frame=_presence(session_ref=f"{n:012d}")))
    managed_stream_double.close_stream()

    server = mcp_stdio.build_server()
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("zeitgeist_watch", {"repo": "github.com/acme/spec-kitty", "timeout_s": 2.0, "max_frames": 2})
    assert len(result.structuredContent["frames"]) == 2
