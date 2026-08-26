"""#190: ``spec-kitty moments off|on|status`` — the one-line switch.

Covers: the default answer when nothing is configured anywhere, both write
scopes (global ``~/.kittify/config.toml`` vs the per-repo
``<root>/.kittify/config.toml`` override), that ``status`` names WHICH file
decided the effective mode once both exist, the ``--json`` machine form,
and the refusal when ``--repo`` runs outside any Spec Kitty checkout. The
server-side consequence of ``off`` (mcp-serve exits 0 with one line) is
covered by ``tests/zeitgeist_client/test_mcp_stdio.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import tomllib
import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.moments import moments_app

pytestmark = pytest.mark.fast

runner = CliRunner()


@pytest.fixture()
def kittify_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An isolated developer home: ``~/.kittify`` resolves here for the whole
    test, and the process starts OUTSIDE any Spec Kitty checkout so the
    repo-override branch of resolution stays out of the picture until a test
    deliberately walks into one."""
    home = tmp_path / "kittify-home"
    home.mkdir()
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    # SPECIFY_REPO_ROOT is an authoritative override (core/paths Tier 1); a
    # CI/worker value pointing at some real checkout would silently turn
    # every resolution here into "inside a project". Determinism: gone.
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    checkout = tmp_path / "plain-dir"
    checkout.mkdir()
    monkeypatch.chdir(checkout)
    return home


def _checkout_with_kittify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "checkout"
    (root / ".kittify").mkdir(parents=True)
    monkeypatch.chdir(root)
    return root


# --- status ------------------------------------------------------------------


def test_status_defaults_to_mine_from_no_file_at_all(kittify_home: Path) -> None:
    result = runner.invoke(moments_app, ["status"])
    assert result.exit_code == 0
    assert "mine" in result.stdout
    assert "source=default" in result.stdout


def test_status_json_is_plain_machine_json(kittify_home: Path) -> None:
    result = runner.invoke(moments_app, ["status", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["agents"] == "mine"
    assert payload["agents_source"] == "default"
    assert payload["rate_per_minute"] > 0


def test_status_names_the_global_file_that_decided(kittify_home: Path) -> None:
    (kittify_home / "config.toml").write_text('[moments]\nagents = "off"\n')
    result = runner.invoke(moments_app, ["status"])
    assert result.exit_code == 0
    assert "off" in result.stdout
    assert str(kittify_home / "config.toml") in result.stdout


def test_status_reports_a_repo_override_over_the_global_value(kittify_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both files present: repo wins AND status says so — "quiet in THIS
    checkout only" must be visible as exactly that."""
    (kittify_home / "config.toml").write_text('[moments]\nagents = "team"\nkinds = ["WPStatusChanged"]\n')
    root = _checkout_with_kittify(tmp_path, monkeypatch)
    (root / ".kittify" / "config.toml").write_text('[moments]\nagents = "off"\n')

    result = runner.invoke(moments_app, ["status"])
    assert result.exit_code == 0
    assert "off" in result.stdout
    assert str(root / ".kittify" / "config.toml") in result.stdout
    assert "kinds: WPStatusChanged" in result.stdout  # unoverridden keys still come through


# --- off / on ----------------------------------------------------------------


def test_off_writes_the_global_config_and_reports_effective_mode(kittify_home: Path) -> None:
    result = runner.invoke(moments_app, ["off"])
    assert result.exit_code == 0
    assert "off" in result.stdout
    with (kittify_home / "config.toml").open("rb") as fh:
        stored = tomllib.load(fh)
    assert stored == {"moments": {"agents": "off"}}
    assert "effective: off" in result.stdout.replace("**", "")


def test_on_restores_the_documented_default_after_an_off(kittify_home: Path) -> None:
    runner.invoke(moments_app, ["off"])
    result = runner.invoke(moments_app, ["on"])
    assert result.exit_code == 0
    with (kittify_home / "config.toml").open("rb") as fh:
        stored = tomllib.load(fh)
    assert stored["moments"]["agents"] == "mine"
    assert "effective: mine" in result.stdout.replace("**", "")


def test_on_reports_honestly_when_a_repo_override_still_decides(kittify_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``on`` written globally cannot beat a repo override saying off — the
    command re-reads and prints the truth instead of the intent."""
    (kittify_home / "config.toml").write_text('[moments]\nagents = "mine"\n')
    root = _checkout_with_kittify(tmp_path, monkeypatch)
    (root / ".kittify" / "config.toml").write_text('[moments]\nagents = "off"\n')

    result = runner.invoke(moments_app, ["on"])
    assert result.exit_code == 0
    assert "effective: off" in result.stdout.replace("**", "")


def test_off_with_repo_scope_writes_the_checkout_override(kittify_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _checkout_with_kittify(tmp_path, monkeypatch)
    result = runner.invoke(moments_app, ["off", "--repo"])
    assert result.exit_code == 0
    override = root / ".kittify" / "config.toml"
    assert override.exists()
    with override.open("rb") as fh:
        assert tomllib.load(fh)["moments"]["agents"] == "off"
    assert not (kittify_home / "config.toml").exists(), "global scope stayed untouched"


def test_repo_scope_outside_any_checkout_refuses(kittify_home: Path) -> None:
    result = runner.invoke(moments_app, ["off", "--repo"])
    assert result.exit_code == 1
    assert "--repo needs a Spec Kitty checkout" in result.stdout


def test_off_preserves_unrelated_keys_in_an_existing_config(kittify_home: Path) -> None:
    (kittify_home / "config.toml").write_text('[moments]\nkinds = ["MissionCreated"]\n[other]\nkeep = "yes"\n')
    result = runner.invoke(moments_app, ["off"])
    assert result.exit_code == 0
    with (kittify_home / "config.toml").open("rb") as fh:
        document = tomllib.load(fh)
    assert document["moments"] == {"kinds": ["MissionCreated"], "agents": "off"}
    assert document["other"] == {"keep": "yes"}
