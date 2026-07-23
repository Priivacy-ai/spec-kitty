"""Tests for ``spec-kitty sync import-history`` — WP-Y1 (#2262).

WP-Y1 is the command surface + mission selection + the fail-closed TeamSpace
audit gate. It reuses ``migration.mission_state`` helpers rather than
re-deriving them; envelope synthesis and the §3.6b pre-sync log re-drain land
in later slices, so ``--apply`` is an honest non-zero stub here (it must never
claim a materialize it cannot perform).

These tests drive the CLI wrapper only. The selection/audit authority stays in
``migration.mission_state`` and is monkeypatched at its seams, so the suite
needs no on-disk repo, no dossier, and no TeamSpace credentials.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_command
from specify_cli.cli.commands.sync import app

pytestmark = pytest.mark.fast

runner = CliRunner()


# ── seam helpers ─────────────────────────────────────────────────────────────


def _patch_checkout(monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    """Point the command's active-checkout resolver at a fixed repo root."""
    monkeypatch.setattr(
        sync_command,
        "_require_active_checkout",
        lambda: SimpleNamespace(repo_root=repo_root),
    )


def _patch_selection(
    monkeypatch: pytest.MonkeyPatch,
    *,
    mission_dirs: list[Path],
    blockers: list[dict[str, object]],
) -> None:
    """Stub the two migration seams the command reuses.

    Patched on the source module so the command's local
    ``from specify_cli.migration.mission_state import ...`` binds to the stubs.
    """
    import specify_cli.migration.mission_state as mission_state

    monkeypatch.setattr(
        mission_state,
        "_select_mission_dirs",
        lambda repo_root, *, scan_root, mission: list(mission_dirs),
    )
    monkeypatch.setattr(
        mission_state,
        "_teamspace_audit_blockers",
        lambda repo_root, *, scan_root, mission_dirs: list(blockers),
    )


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ── wiring ───────────────────────────────────────────────────────────────────


def test_command_is_wired_with_its_flags():
    """``import-history --help`` renders and advertises its three flags."""
    result = runner.invoke(app, ["import-history", "--help"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.output)
    assert "--apply" in plain
    assert "--dry-run" in plain
    assert "--mission" in plain


def test_apply_and_dry_run_are_mutually_exclusive():
    """Both flags at once is a usage error (exit 2), caught before any I/O."""
    result = runner.invoke(app, ["import-history", "--apply", "--dry-run"])
    assert result.exit_code == 2
    assert "mutually exclusive" in _strip_ansi(result.output)


# ── stage 1: selection ───────────────────────────────────────────────────────


def test_no_missions_found_exits_zero(tmp_path, monkeypatch):
    _patch_checkout(monkeypatch, tmp_path)
    _patch_selection(monkeypatch, mission_dirs=[], blockers=[])
    result = runner.invoke(app, ["import-history"])
    assert result.exit_code == 0
    assert "No missions found" in _strip_ansi(result.output)


def test_selection_repair_error_exits_one(tmp_path, monkeypatch):
    """A ``MissionStateRepairError`` from selection fails closed (exit 1)."""
    import specify_cli.migration.mission_state as mission_state

    _patch_checkout(monkeypatch, tmp_path)

    def _boom(repo_root, *, scan_root, mission):
        raise mission_state.MissionStateRepairError("selector could not resolve mission handle")

    monkeypatch.setattr(mission_state, "_select_mission_dirs", _boom)
    result = runner.invoke(app, ["import-history", "--mission", "does-not-resolve"])
    assert result.exit_code == 1
    assert "selector could not resolve mission handle" in _strip_ansi(result.output)


# ── stage 2: fail-closed audit gate ──────────────────────────────────────────


def test_clean_missions_are_previewed_on_dry_run(tmp_path, monkeypatch):
    dirs = [tmp_path / "demo-mission-01AAAA", tmp_path / "demo-mission-01BBBB"]
    _patch_checkout(monkeypatch, tmp_path)
    _patch_selection(monkeypatch, mission_dirs=dirs, blockers=[])

    result = runner.invoke(app, ["import-history"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.output)
    # The dry-run now previews the synthesized plan, not just the selection.
    assert "2 mission(s)" in plain
    assert "demo-mission-01AAAA" in plain
    assert "demo-mission-01BBBB" in plain
    # A MissionCreated is synthesized per mission even with nothing on disk.
    assert "MissionCreated" in plain
    # Dry-run resolves the synthetic offline identity and uploads nothing.
    assert "synthetic offline id" in plain
    assert "nothing uploaded" in plain


def test_audit_blockers_block_import_and_name_the_finding(tmp_path, monkeypatch):
    dirs = [tmp_path / "demo-mission-01CCCC"]
    blockers = [
        {
            "mission_slug": "demo-mission-01CCCC",
            "artifact_path": "spec.md",
            "message": "spec.md failed dossier schema validation",
            "finding_code": "SCHEMA_INVALID",
        }
    ]
    _patch_checkout(monkeypatch, tmp_path)
    _patch_selection(monkeypatch, mission_dirs=dirs, blockers=blockers)

    result = runner.invoke(app, ["import-history"])
    assert result.exit_code == 1
    plain = _strip_ansi(result.output)
    assert "Import blocked" in plain
    # The blocker is named (mission + message), not dumped as a raw dict.
    assert "demo-mission-01CCCC" in plain
    assert "spec.md failed dossier schema validation" in plain
    assert "{'mission_slug'" not in plain


# ── --apply is an honest stub until the synthesizer lands ────────────────────


def test_apply_is_an_honest_nonzero_stub(tmp_path, monkeypatch):
    """``--apply`` on a clean selection must not fake a materialize (exit 3)."""
    dirs = [tmp_path / "demo-mission-01DDDD"]
    _patch_checkout(monkeypatch, tmp_path)
    _patch_selection(monkeypatch, mission_dirs=dirs, blockers=[])

    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 3
    assert "not available yet" in _strip_ansi(result.output)


def test_apply_short_circuits_before_any_work(monkeypatch):
    """Until WP-Y5 wires the upload, ``--apply`` is a pure honest stub: it does
    no checkout resolution / selection / scan, so it can have no side effects.
    (The audit-gate-on-apply returns with the real upload path.)"""

    def _forbidden_checkout():
        raise AssertionError("the --apply stub must not resolve a checkout")

    monkeypatch.setattr(sync_command, "_require_active_checkout", _forbidden_checkout)
    result = runner.invoke(app, ["import-history", "--apply"])
    assert result.exit_code == 3
    assert "not available yet" in _strip_ansi(result.output)
