"""O1-C: ``spec-kitty zeitgeist operability`` — the thin CLI adapter over
``zeitgeist_client.operability``'s payload-free signals and local drills.

Mirrors ``test_zeitgeist_command.py``'s own patterns: no
``--relay-url``/``--token`` option on any subcommand (the credential comes
solely from ``credentials.py``'s existing store, same as ``status``/
``watch``), ``--json`` emits the dataclass verbatim via the canonical
console seam, and the drill commands never touch a real relay or a real
controlling terminal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.zeitgeist import app
from specify_cli.zeitgeist_client import credentials, outbox_approval

pytestmark = pytest.mark.fast

runner = CliRunner()


@pytest.fixture()
def state_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "spec-kitty-home"))
    return tmp_path / "spec-kitty-home"


# --- no runtime URL/credential option on any operability subcommand ---------


@pytest.mark.parametrize(
    "args",
    [
        ["operability", "report", "--help"],
        ["operability", "drill-timeout", "--help"],
        ["operability", "drill-rotation", "--help"],
        ["operability", "drill-rollback", "--help"],
    ],
)
def test_operability_subcommand_has_no_relay_url_or_credential_option(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    for forbidden in ("--relay-url", "--token", "--credential", "--runtime-url"):
        assert forbidden not in result.stdout


def test_operability_group_is_registered() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "operability" in result.stdout


# --- report -------------------------------------------------------------


def test_operability_report_json_offline_reports_honest_staleness(state_root: Path) -> None:
    result = runner.invoke(app, ["operability", "report", "spec-kitty", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repo"] == "spec-kitty"
    assert payload["credential_checked_out"] is False
    assert payload["offer"] is None
    assert payload["lease"]["active"] is False
    assert payload["lease"]["ttl_s"] == 90


def test_operability_report_human_readable_mentions_every_signal(state_root: Path) -> None:
    result = runner.invoke(app, ["operability", "report", "spec-kitty"])
    assert result.exit_code == 0
    for label in ("lease", "revoke", "mcp", "repair"):
        assert label in result.stdout


def test_operability_report_reflects_a_stored_checkout(state_root: Path) -> None:
    credentials.store(repo="spec-kitty", relay_url="http://127.0.0.1:9", token="tok", token_kind="shared_team")
    result = runner.invoke(app, ["operability", "report", "spec-kitty", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["credential_checked_out"] is True
    assert "tok" not in result.stdout  # never echoes the credential value


# --- drill-timeout --------------------------------------------------------


def test_operability_drill_timeout_json_passes_without_a_repo_argument(state_root: Path) -> None:
    result = runner.invoke(app, ["operability", "drill-timeout", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["outcome"] == "pass"
    assert payload["drop"]["dropped"] is True


# --- drill-rotation --------------------------------------------------------


def test_operability_drill_rotation_json_reports_not_checked_out(state_root: Path) -> None:
    result = runner.invoke(app, ["operability", "drill-rotation", "spec-kitty", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["outcome"] == "pass"
    assert payload["checked_out"] is False


# --- drill-rollback ---------------------------------------------------------


def test_operability_drill_rollback_json_blocks_before_a_human_gesture(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom():
        raise AssertionError("CLI drill-rollback must never open the controlling terminal")

    monkeypatch.setattr(outbox_approval, "_controlling_tty", _boom)
    result = runner.invoke(app, ["operability", "drill-rollback", "spec-kitty", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["outcome"] == "pass"
    assert payload["blocked_reason"] == "not_yet_approved"
