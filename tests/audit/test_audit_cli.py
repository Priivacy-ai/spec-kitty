"""CLI integration tests for `spec-kitty doctor mission-state`.

Uses typer.testing.CliRunner to invoke the command in-process.
Monkeypatches locate_project_root so tests run without a real kitty project.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import specify_cli.cli.commands.doctor as doctor_mod
from specify_cli.cli.commands.doctor import app

runner = CliRunner()


def _make_clean_mission(parent: Path, slug: str = "test-mission") -> Path:
    """Create a minimal valid mission directory under parent."""
    mission_dir = parent / slug
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
                "mission_slug": slug,
                "mission_type": "software-dev",
                "target_branch": "main",
            }
        ),
        encoding="utf-8",
    )
    return mission_dir


def _make_corrupt_mission(parent: Path, slug: str = "corrupt-mission") -> Path:
    """Create a mission directory with a corrupt events file."""
    mission_dir = parent / slug
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_slug": slug, "mission_type": "software-dev"}),
        encoding="utf-8",
    )
    (mission_dir / "status.events.jsonl").write_text(
        "THIS IS NOT VALID JSON {{{\n",
        encoding="utf-8",
    )
    return mission_dir


# ---------------------------------------------------------------------------
# Test 1: --audit flag is required
# ---------------------------------------------------------------------------


def test_cli_requires_audit_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without --audit, command exits 0 and mentions --audit."""
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
    result = runner.invoke(app, ["mission-state"])
    assert result.exit_code == 0
    assert "--audit" in result.output


# ---------------------------------------------------------------------------
# Test 2: --fixture-dir runs the audit
# ---------------------------------------------------------------------------


def test_cli_runs_audit_with_fixture_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--audit --fixture-dir scans the fixture and exits 0 for a clean mission."""
    fixture_root = tmp_path / "fixtures"
    _make_clean_mission(fixture_root)
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)

    result = runner.invoke(app, ["mission-state", "--audit", "--fixture-dir", str(fixture_root)])
    assert result.exit_code == 0, result.output
    combined = (result.output or "") + (result.stderr or "")
    assert "clean" in combined.lower() or "no findings" in combined.lower()


# ---------------------------------------------------------------------------
# Test 3: --json output shape
# ---------------------------------------------------------------------------


def test_cli_json_output_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--json output is valid JSON with missions, shape_counters, repo_summary keys."""
    fixture_root = tmp_path / "fixtures"
    _make_clean_mission(fixture_root)
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)

    result = runner.invoke(
        app,
        ["mission-state", "--audit", "--json", "--fixture-dir", str(fixture_root)],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "missions" in data
    assert "shape_counters" in data
    assert "repo_summary" in data
    assert data["repo_summary"]["total_missions"] >= 1


# ---------------------------------------------------------------------------
# Test 4: --fail-on error exits 0 when clean
# ---------------------------------------------------------------------------


def test_cli_fail_on_error_exit_0_when_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--fail-on error exits 0 when the fixture has no errors."""
    fixture_root = tmp_path / "fixtures"
    _make_clean_mission(fixture_root)
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)

    result = runner.invoke(
        app,
        ["mission-state", "--audit", "--fail-on", "error", "--fixture-dir", str(fixture_root)],
    )
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Test 5: --fail-on error exits 1 when errors present
# ---------------------------------------------------------------------------


def test_cli_fail_on_error_exit_1_when_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--fail-on error exits 1 when the fixture has a CORRUPT_JSONL (error) finding."""
    fixture_root = tmp_path / "fixtures"
    _make_corrupt_mission(fixture_root)
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)

    result = runner.invoke(
        app,
        ["mission-state", "--audit", "--fail-on", "error", "--fixture-dir", str(fixture_root)],
    )
    assert result.exit_code == 1, result.output


# ---------------------------------------------------------------------------
# Test 6: invalid --fail-on exits 2
# ---------------------------------------------------------------------------


def test_cli_invalid_fail_on_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown --fail-on value exits 2 with a helpful error message."""
    fixture_root = tmp_path / "fixtures"
    _make_clean_mission(fixture_root)
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)

    result = runner.invoke(
        app,
        [
            "mission-state",
            "--audit",
            "--fail-on",
            "critical",
            "--fixture-dir",
            str(fixture_root),
        ],
    )
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Test 7: --mission scopes the audit to one mission
# ---------------------------------------------------------------------------


def test_cli_mission_scoping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--mission filters the audit to a single mission slug.

    Uses kitty-specs/ under repo_root since resolve_mission() needs that structure.
    """
    specs_dir = tmp_path / "kitty-specs"
    _make_clean_mission(specs_dir, slug="alpha")
    _make_clean_mission(specs_dir, slug="beta")
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)

    result = runner.invoke(
        app,
        ["mission-state", "--audit", "--json", "--mission", "alpha"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["repo_summary"]["total_missions"] == 1
    assert data["missions"][0]["mission_slug"] == "alpha"


# ---------------------------------------------------------------------------
# Test 8: --json output is deterministic
# ---------------------------------------------------------------------------


def test_cli_json_determinism(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invoking --json twice on the same fixture produces byte-identical output."""
    fixture_root = tmp_path / "fixtures"
    _make_clean_mission(fixture_root)
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)

    args = ["mission-state", "--audit", "--json", "--fixture-dir", str(fixture_root)]
    result1 = runner.invoke(app, args)
    result2 = runner.invoke(app, args)

    assert result1.exit_code == 0
    assert result2.exit_code == 0
    assert result1.output == result2.output
