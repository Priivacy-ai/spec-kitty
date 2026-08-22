"""Z8-C: ``spec-kitty zeitgeist outbox`` — the thin Typer shell over
``outbox_approval.py``'s bundled inspect/approve/reject/revoke surface.

Covers: ``list``/``show`` render the redacted preview vs. exact content
correctly, ``approve``/``reject``/``revoke`` have no ``--yes``/``--force``/
``--non-interactive`` bypass option (the CLI-layer half of the hard trust
requirement — see ``test_outbox_approval_human_gesture.py`` for the
module-layer half), a non-interactive CLI invocation (no controlling
terminal reachable through the monkeypatched seam) fails closed with a
non-zero exit code, and a scripted correct human gesture end-to-end
approves an item through the real CLI command dispatch.
"""

from __future__ import annotations

import inspect

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.zeitgeist import app
from specify_cli.zeitgeist_client import outbox_approval

pytestmark = pytest.mark.fast

runner = CliRunner()


@pytest.fixture()
def state_root(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "spec-kitty-home"))
    return tmp_path / "spec-kitty-home"


class FakeTTY:
    def __init__(self, response: str) -> None:
        self.response = response
        self.written: list[str] = []

    def write(self, text: str) -> int:
        self.written.append(text)
        return len(text)

    def flush(self) -> None:
        pass

    def readline(self) -> str:
        return self.response + "\n"

    def close(self) -> None:
        pass


# --- no bypass flag on any decision command ----------------------------------


@pytest.mark.parametrize("verb", ["approve", "reject", "revoke"])
def test_decision_commands_have_no_bypass_option(verb: str) -> None:
    result = runner.invoke(app, ["outbox", verb, "--help"])
    assert result.exit_code == 0
    for forbidden in ("--yes", "-y", "--force", "--non-interactive", "--no-confirm", "--assume-yes", "--auto"):
        assert forbidden not in result.stdout


# --- list / show --------------------------------------------------------------


def test_outbox_list_reports_no_pending_items_when_empty(state_root) -> None:
    result = runner.invoke(app, ["outbox", "list"])
    assert result.exit_code == 0
    assert "no pending" in result.stdout.lower()


def test_outbox_list_shows_a_redacted_preview_not_exact_content(state_root) -> None:
    long_content = "SECRET-PROSE-" + ("x" * 200)
    outbox_approval.submit(repo="spec-kitty", audience="team-a", content=long_content)
    result = runner.invoke(app, ["outbox", "list"])
    assert result.exit_code == 0
    assert long_content not in result.stdout
    assert "SECRET-PROSE-" in result.stdout  # the redacted prefix is still visible


def test_outbox_show_discloses_exact_content(state_root) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="the exact verbatim message")
    result = runner.invoke(app, ["outbox", "show", item.item_id])
    assert result.exit_code == 0
    assert "the exact verbatim message" in result.stdout


def test_outbox_show_unknown_id_exits_non_zero(state_root) -> None:
    result = runner.invoke(app, ["outbox", "show", "0" * 64])
    assert result.exit_code != 0


# --- approve/reject/revoke: fail closed with no controlling terminal --------


def test_outbox_approve_with_no_controlling_terminal_fails_closed(state_root, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="ship it")
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: None)

    result = runner.invoke(app, ["outbox", "approve", item.item_id])
    assert result.exit_code != 0
    assert outbox_approval.show(item.item_id).status == "pending"


def test_outbox_approve_with_the_correct_gesture_succeeds_end_to_end(state_root, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="ship it")
    tty = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)

    result = runner.invoke(app, ["outbox", "approve", item.item_id, "--actor", "robert"])
    assert result.exit_code == 0
    assert outbox_approval.show(item.item_id).status == "approved"


def test_outbox_reject_with_the_correct_gesture_succeeds_end_to_end(state_root, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="do not send")
    tty = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)

    result = runner.invoke(app, ["outbox", "reject", item.item_id, "--actor", "robert"])
    assert result.exit_code == 0
    assert outbox_approval.show(item.item_id).status == "rejected"


def test_outbox_revoke_after_approve_succeeds_end_to_end(state_root, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="go ahead, for now")
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: FakeTTY(item.item_id[:8]))
    runner.invoke(app, ["outbox", "approve", item.item_id, "--actor", "robert"])

    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: FakeTTY(item.item_id[:8]))
    result = runner.invoke(app, ["outbox", "revoke", item.item_id, "--actor", "robert"])
    assert result.exit_code == 0
    assert outbox_approval.show(item.item_id).status == "revoked"


def test_outbox_revoke_on_a_pending_item_fails_closed(state_root, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="not decided yet")
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: FakeTTY(item.item_id[:8]))

    result = runner.invoke(app, ["outbox", "revoke", item.item_id, "--actor", "robert"])
    assert result.exit_code != 0


# --- outbox command group is registered but never via MCP -------------------


def test_outbox_is_not_the_hidden_mcp_serve_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "outbox" in result.stdout


def test_no_outbox_cli_command_signature_accepts_a_bypass_kwarg() -> None:
    from specify_cli.cli.commands import zeitgeist as zeitgeist_module

    for name in ("outbox_approve", "outbox_reject", "outbox_revoke"):
        fn = getattr(zeitgeist_module, name)
        params = set(inspect.signature(fn).parameters)
        forbidden = {"force", "yes", "assume_yes", "no_confirm", "auto", "non_interactive"}
        assert not (params & forbidden)
