"""Tests for ``spec-kitty regen`` (mission #3447, WP02).

RED-first: these fail on the planning base because the command does not exist.
They pin the self-service regeneration behaviour (FR-003/FR-004), the byte-for-
byte fidelity to the committed fixtures (NFR-005), and the single shared version
pin (FR-005).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands import regen as regen_mod
from specify_cli.skills.render_versions import (
    FIXTURE_COMMAND_RENDER_VERSION,
    FIXTURE_SKILL_RENDER_VERSION,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _fixture(tmp_path: Path, name: str, committed: str | None, rendered: str) -> regen_mod._Fixture:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if committed is not None:
        path.write_text(committed, encoding="utf-8")
    return regen_mod._Fixture(path=path, content=rendered, label=name)


# --------------------------------------------------------------------------- #
# _stale_diff
# --------------------------------------------------------------------------- #


def test_stale_diff_is_none_when_committed_matches_render(tmp_path: Path) -> None:
    assert regen_mod._stale_diff(_fixture(tmp_path, "codex/specify.SKILL.md", "same", "same")) is None


def test_stale_diff_returns_unified_diff_when_changed(tmp_path: Path) -> None:
    diff = regen_mod._stale_diff(_fixture(tmp_path, "codex/specify.SKILL.md", "old\n", "new\n"))
    assert diff is not None
    assert "-old" in diff and "+new" in diff


def test_stale_diff_treats_a_missing_fixture_as_stale(tmp_path: Path) -> None:
    missing = regen_mod._Fixture(path=tmp_path / "gone.md", content="x", label="gone")
    assert regen_mod._stale_diff(missing) is not None


# --------------------------------------------------------------------------- #
# check mode
# --------------------------------------------------------------------------- #


def test_check_exits_zero_when_all_fresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fresh = _fixture(tmp_path, "claude/specify.md", "x", "x")
    monkeypatch.setattr(regen_mod, "_all_fixtures", lambda root: [fresh])
    monkeypatch.setattr(regen_mod, "_repo_root", lambda: tmp_path)
    with pytest.raises(typer.Exit) as exc:
        regen_mod.regen(check=True, json_output=False)
    assert exc.value.exit_code == 0
    assert "fresh" in capsys.readouterr().out.lower()


def test_check_exits_one_with_remediation_when_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    stale = _fixture(tmp_path, "claude/specify.md", "old\n", "new\n")
    monkeypatch.setattr(regen_mod, "_all_fixtures", lambda root: [stale])
    monkeypatch.setattr(regen_mod, "_repo_root", lambda: tmp_path)
    with pytest.raises(typer.Exit) as exc:
        regen_mod.regen(check=True, json_output=False)
    assert exc.value.exit_code == 1
    out = capsys.readouterr().out
    assert "Run: spec-kitty regen" in out
    assert "claude/specify.md" in out


def test_check_json_reports_stale_labels_and_remediation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    stale = _fixture(tmp_path, "claude/plan.md", "a\n", "b\n")
    monkeypatch.setattr(regen_mod, "_all_fixtures", lambda root: [stale])
    monkeypatch.setattr(regen_mod, "_repo_root", lambda: tmp_path)
    with pytest.raises(typer.Exit) as exc:
        regen_mod.regen(check=True, json_output=True)
    assert exc.value.exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "stale"
    assert payload["stale"] == ["claude/plan.md"]
    assert payload["remediation"] == "Run: spec-kitty regen"


# --------------------------------------------------------------------------- #
# write mode
# --------------------------------------------------------------------------- #


def test_write_restores_a_stale_fixture_byte_for_byte(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    stale = _fixture(tmp_path, "codex/specify.SKILL.md", "old\n", "new\n")
    monkeypatch.setattr(regen_mod, "_all_fixtures", lambda root: [stale])
    monkeypatch.setattr(regen_mod, "_repo_root", lambda: tmp_path)
    with pytest.raises(typer.Exit) as exc:
        regen_mod.regen(check=False, json_output=False)
    assert exc.value.exit_code == 0
    assert stale.path.read_text(encoding="utf-8") == "new\n"


# --------------------------------------------------------------------------- #
# fidelity + shared pins (the load-bearing guarantees)
# --------------------------------------------------------------------------- #


def test_regen_fails_closed_on_empty_fixture_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty render surface must NOT report fresh — the gate fails closed."""
    monkeypatch.setattr(regen_mod, "_all_fixtures", lambda root: [])
    monkeypatch.setattr(regen_mod, "_repo_root", lambda: tmp_path)
    with pytest.raises(typer.BadParameter):
        regen_mod.regen(check=True, json_output=False)


def test_regen_reproduces_committed_fixtures_byte_for_byte() -> None:
    """NFR-005: on a clean checkout, every rendered fixture equals the committed
    one — i.e. `spec-kitty regen` output is byte-identical to what a
    `PYTEST_UPDATE_SNAPSHOTS=1` pytest run produced."""
    root = regen_mod._repo_root()
    fixtures = regen_mod._all_fixtures(root)
    assert fixtures, "regen produced no fixtures"
    drifted = [f.label for f in fixtures if regen_mod._stale_diff(f) is not None]
    assert not drifted, f"regen output drifted from committed fixtures: {drifted}"


def test_version_pins_come_from_the_single_shared_source() -> None:
    """FR-005: both fixture suites source their render version from the shared
    module, so the tool and the gate can never silently diverge."""
    from tests.specify_cli.regression import test_twelve_agent_parity as parity
    from tests.specify_cli.skills import test_command_renderer as renderer

    assert parity._BASELINE_VERSION == FIXTURE_COMMAND_RENDER_VERSION
    assert renderer._TEST_VERSION == FIXTURE_SKILL_RENDER_VERSION
