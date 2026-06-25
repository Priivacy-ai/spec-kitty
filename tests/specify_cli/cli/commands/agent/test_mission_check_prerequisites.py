"""Direct unit tests for the check-prerequisites seam (#2056 WP05, T019).

Exercises the relocated helpers in
``specify_cli.cli.commands.agent.mission_check_prerequisites`` directly: the
paths-only payload shaper, the JSON / human result emitters, the detection-error
emitter, and the two ``meta.json`` readers' silent-degrade contracts. The
end-to-end command stays pinned by ``test_agent_feature.py``,
``test_check_prerequisites_surface_agreement.py`` and the WP01 golden harness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.cli.commands.agent import mission_check_prerequisites as seam

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# _paths_only_payload
# ---------------------------------------------------------------------------


def test_paths_only_payload_aliases_legacy_keys() -> None:
    validation = {
        "paths": {
            "feature_dir": "/repo/kitty-specs/001-demo",
            "spec_file": "/repo/kitty-specs/001-demo/spec.md",
            "plan_file": "/repo/kitty-specs/001-demo/plan.md",
            "tasks_file": "/repo/kitty-specs/001-demo/tasks.md",
        },
        "artifact_files": {"x": 1},
        "artifact_dirs": {"y": 2},
        "available_docs": ["a"],
    }
    out = seam._paths_only_payload(validation)
    assert out["FEATURE_DIR"] == "/repo/kitty-specs/001-demo"
    assert out["SPEC_FILE"] == "/repo/kitty-specs/001-demo/spec.md"
    assert out["IMPL_PLAN"] == "/repo/kitty-specs/001-demo/plan.md"
    assert out["TASKS"] == "/repo/kitty-specs/001-demo/tasks.md"
    assert out["SPECS_DIR"] == "/repo/kitty-specs"
    assert out["artifact_files"] == {"x": 1}


def test_paths_only_payload_empty_feature_dir() -> None:
    out = seam._paths_only_payload({"paths": {}})
    assert out["SPECS_DIR"] == ""


# ---------------------------------------------------------------------------
# _emit_check_prerequisites_result
# ---------------------------------------------------------------------------


def test_emit_result_json_injects_branch_contract(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    seam._emit_check_prerequisites_result(
        validation_result={"valid": True, "errors": [], "warnings": [], "paths": {}},
        feature_dir=tmp_path / "001-demo",
        json_output=True,
        paths_only=False,
        target_branch="main",
        current_branch="main",
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["target_branch"] == "main"
    assert "branch_context" in payload


def test_emit_result_human_pass(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    seam._emit_check_prerequisites_result(
        validation_result={"valid": True, "errors": [], "warnings": [], "paths": {}},
        feature_dir=tmp_path / "001-demo",
        json_output=False,
        paths_only=False,
        target_branch="main",
        current_branch="main",
    )
    assert "Prerequisites check passed" in capsys.readouterr().out


def test_emit_result_human_failure_lists_errors(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    seam._emit_check_prerequisites_result(
        validation_result={"valid": False, "errors": ["missing spec"], "warnings": ["stale tasks"], "paths": {}},
        feature_dir=tmp_path / "001-demo",
        json_output=False,
        paths_only=False,
        target_branch="main",
        current_branch="main",
    )
    out = capsys.readouterr().out
    assert "Prerequisites check failed" in out
    assert "missing spec" in out
    assert "stale tasks" in out


# ---------------------------------------------------------------------------
# _emit_check_prerequisites_detection_error
# ---------------------------------------------------------------------------


def test_emit_detection_error_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr(
        seam,
        "_build_setup_plan_detection_error",
        lambda *a, **k: {"error": "boom", "available_missions": ["001-demo"]},
    )
    seam._emit_check_prerequisites_detection_error(
        repo_root=tmp_path,
        detection_error=ValueError("ctx"),
        feature=None,
        json_output=True,
        paths_only=False,
        include_tasks=True,
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "boom"


def test_emit_detection_error_human(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr(
        seam,
        "_build_setup_plan_detection_error",
        lambda *a, **k: {"error": "boom", "available_missions": ["001-demo"], "example_command": "spec-kitty ..."},
    )
    seam._emit_check_prerequisites_detection_error(
        repo_root=tmp_path,
        detection_error=ValueError("ctx"),
        feature=None,
        json_output=False,
        paths_only=True,
        include_tasks=False,
    )
    out = capsys.readouterr().out
    assert "boom" in out
    assert "001-demo" in out


# ---------------------------------------------------------------------------
# meta readers — silent-degrade contracts
# ---------------------------------------------------------------------------


def test_read_meta_for_pr_bound_empty_when_missing(tmp_path: Path) -> None:
    assert seam._read_meta_for_pr_bound(tmp_path / "001-demo") == {}


def test_read_meta_for_pr_bound_reads_existing(tmp_path: Path) -> None:
    fd = tmp_path / "001-demo"
    fd.mkdir()
    (fd / "meta.json").write_text(json.dumps({"mission_id": "01ABC", "pr_bound": False}))
    out: dict[str, Any] = seam._read_meta_for_pr_bound(fd)
    assert out["mission_id"] == "01ABC"


def test_read_meta_for_emission_none_when_missing(tmp_path: Path) -> None:
    assert seam._read_meta_for_emission(tmp_path / "001-demo") is None


def test_read_meta_for_emission_reads_existing(tmp_path: Path) -> None:
    fd = tmp_path / "001-demo"
    fd.mkdir()
    (fd / "meta.json").write_text(json.dumps({"mission_id": "01ABC"}))
    out = seam._read_meta_for_emission(fd)
    assert out is not None
    assert out["mission_id"] == "01ABC"
