"""Architectural guard for the Typer 0.26 compatibility smoke test."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"


def test_ci_exercises_typer_026_json_error_surface() -> None:
    """CI must install Typer 0.26+ for the JSON error-surface smoke test."""
    data = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    lint_steps = data["jobs"]["lint"]["steps"]
    runs = [str(step.get("run", "")) for step in lint_steps]
    assert any(
        "typer>=0.26" in run and "tests/agent/test_json_group_typer_surface.py" in run
        for run in runs
    ), (
        "ci-quality.yml must exercise tests/agent/test_json_group_typer_surface.py "
        "under Typer >=0.26 so the vendored-click compatibility path is live."
    )
