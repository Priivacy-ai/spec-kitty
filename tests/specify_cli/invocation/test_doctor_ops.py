"""Tests for spec-kitty doctor ops orphan detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.doctor.ops import list_orphan_ops
from specify_cli.invocation.writer import EVENTS_DIR

pytestmark = [pytest.mark.unit]

runner = CliRunner()


def _write_op(path: Path, *, completed: bool) -> None:
    events = [
        {
            "event": "started",
            "invocation_id": path.stem,
            "profile_id": "implementer-fixture",
            "action": "implement",
            "started_at": "2026-06-05T00:00:00+00:00",
        }
    ]
    if completed:
        events.append(
            {
                "event": "completed",
                "invocation_id": path.stem,
                "profile_id": "implementer-fixture",
                "action": "",
                "completed_at": "2026-06-05T00:01:00+00:00",
            }
        )
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")


def test_list_orphan_ops_ignores_missing_dir(tmp_path: Path) -> None:
    assert list_orphan_ops(tmp_path) == []


def test_list_orphan_ops_returns_started_only_files(tmp_path: Path) -> None:
    ops_dir = tmp_path / EVENTS_DIR
    ops_dir.mkdir()
    orphan = ops_dir / "01KTBE0RQY9XKTV0PE49PJDMRM.jsonl"
    closed = ops_dir / "01KTBE0RQY9XKTV0PE49PJDMRN.jsonl"
    _write_op(orphan, completed=False)
    _write_op(closed, completed=True)
    for name in ("ops-index.jsonl", "lifecycle.jsonl", "propagation-errors.jsonl"):
        (ops_dir / name).write_text("{}\n", encoding="utf-8")

    assert list_orphan_ops(tmp_path) == [orphan]


def test_doctor_ops_json_reports_orphan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".kittify").mkdir()
    ops_dir = tmp_path / EVENTS_DIR
    ops_dir.mkdir()
    orphan = ops_dir / "01KTBE0RQY9XKTV0PE49PJDMRM.jsonl"
    _write_op(orphan, completed=False)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli_app, ["doctor", "ops", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.output) == [{"path": f"{EVENTS_DIR}/{orphan.name}"}]
