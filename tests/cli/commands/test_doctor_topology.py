"""CLI tests for ``spec-kitty doctor topology`` (T014 / FR-003).

The audit reports each mission's STORED topology without re-inferring: a backfilled
mission shows its value, an un-backfilled mission shows ``null``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import doctor as doctor_mod
from specify_cli.cli.commands.doctor import app

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()


def _write_meta(feature_dir: Path, meta: dict[str, Any]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "kitty-specs").mkdir()
    (tmp_path / ".kittify").mkdir()
    monkeypatch.setattr(doctor_mod, "locate_project_root", lambda: tmp_path)
    return tmp_path


def test_reports_stored_and_null(repo: Path) -> None:
    """A backfilled mission shows its value; an un-backfilled one shows null."""
    _write_meta(repo / "kitty-specs" / "mission-done", {"topology": "coord", "flattened": False})
    _write_meta(repo / "kitty-specs" / "mission-pending", {"coordination_branch": "kitty/x"})

    result = runner.invoke(app, ["topology", "--json"])

    assert result.exit_code == 0
    rows = {r["slug"]: r for r in json.loads(result.stdout)["missions"]}
    assert rows["mission-done"]["topology"] == "coord"
    assert rows["mission-done"]["flattened"] is False
    assert rows["mission-pending"]["topology"] is None


def test_does_not_re_infer(repo: Path) -> None:
    """The audit reads the stored value; it must NOT derive a missing one."""
    feature_dir = repo / "kitty-specs" / "mission-noinfer"
    _write_meta(feature_dir, {"coordination_branch": "kitty/x"})

    runner.invoke(app, ["topology", "--json"])

    # No write happened — the audit is read-only.
    persisted = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert "topology" not in persisted


def test_mission_scoping(repo: Path) -> None:
    _write_meta(repo / "kitty-specs" / "mission-a", {"topology": "lanes"})
    _write_meta(repo / "kitty-specs" / "mission-b", {"topology": "coord"})

    result = runner.invoke(app, ["topology", "--json", "--mission", "mission-a"])

    assert result.exit_code == 0
    missions = json.loads(result.stdout)["missions"]
    assert len(missions) == 1
    assert missions[0]["slug"] == "mission-a"
    assert missions[0]["topology"] == "lanes"


def test_corrupt_meta_reports_null(repo: Path) -> None:
    feature_dir = repo / "kitty-specs" / "mission-corrupt"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text("{ not json", encoding="utf-8")

    result = runner.invoke(app, ["topology", "--json"])

    assert result.exit_code == 0
    row = json.loads(result.stdout)["missions"][0]
    assert row["topology"] is None
    assert "corrupt json" in (row["error"] or "")


def test_human_output(repo: Path) -> None:
    _write_meta(repo / "kitty-specs" / "mission-h", {"topology": "single_branch"})

    result = runner.invoke(app, ["topology"])

    assert result.exit_code == 0
    assert "Mission Topology Audit" in result.stdout
    assert "single_branch" in result.stdout
