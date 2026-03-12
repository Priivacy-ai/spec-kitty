"""Banner visibility tests for CLI invocations."""

from __future__ import annotations

import importlib
import pytest
import typer

from specify_cli.cli import helpers

cli_module = importlib.import_module("specify_cli.__init__")

_AGENT_ENV_MARKERS = ("CLAUDECODE", "CLAUDE_CODE", "CODEX", "OPENCODE", "CURSOR_TRACE_ID")


@pytest.fixture(autouse=False)
def _clean_agent_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all agent runtime env markers so banner logic is not suppressed."""
    for key in _AGENT_ENV_MARKERS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("SPEC_KITTY_NO_BANNER", raising=False)


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["init"], True),
        (["--version"], True),
        (["-v"], True),
        (["merge", "--feature", "001-test"], False),
        (["research"], False),
        (["agent", "feature", "check-prerequisites", "--json"], False),
    ],
)
@pytest.mark.usefixtures("_clean_agent_env")
def test_banner_scope_is_limited_to_init_and_version(argv: list[str], expected: bool) -> None:
    """ASCII art should be limited to init and version invocations."""
    assert helpers._should_render_banner_for_invocation(argv) is expected


def test_banner_can_be_explicitly_disabled_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_NO_BANNER", "true")
    assert helpers._should_render_banner_for_invocation(["init"]) is False


@pytest.mark.parametrize(
    "marker",
    ["CLAUDECODE", "CLAUDE_CODE", "CODEX", "OPENCODE", "CURSOR_TRACE_ID"],
)
def test_banner_is_suppressed_for_agent_runtime_markers(
    monkeypatch: pytest.MonkeyPatch,
    marker: str,
) -> None:
    monkeypatch.setenv(marker, "1")
    assert helpers._should_render_banner_for_invocation(["init"]) is False


def test_version_callback_renders_banner(monkeypatch: pytest.MonkeyPatch) -> None:
    """--version should still render the banner before printing version text."""
    calls: list[bool] = []

    def _fake_show_banner(*, force: bool = False) -> None:
        calls.append(force)

    monkeypatch.setattr(cli_module, "show_banner", _fake_show_banner)

    with pytest.raises(typer.Exit):
        cli_module.version_callback(True)

    assert calls == [True]
