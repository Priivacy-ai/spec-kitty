"""Legacy review warning coverage for 1.x workflows."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.commands.agent import workflow
from tests.specify_cli.test_review_warnings import create_wp_file


def test_workflow_review_warns_dependents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Review workflow should warn when dependents are in progress."""
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    feature_slug = "011-test"
    tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"
    tasks_dir.mkdir(parents=True)

    create_wp_file(tasks_dir / "WP01-base.md", "WP01", [], lane="for_review")
    create_wp_file(tasks_dir / "WP02-dep.md", "WP02", ["WP01"], lane="doing")

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)

    workflow.review(wp_id="WP01", feature=feature_slug, agent="test-reviewer")
    output = capsys.readouterr().out

    assert "Dependency Alert" in output
    assert "WP02" in output
