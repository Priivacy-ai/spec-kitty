"""Regression/acceptance coverage for upstream issue #1589 (facet 1).

Replicates the real failure: a circular WP dependency aborts ``finalize-tasks``
before canonical status is bootstrapped, so the documented loop command
``move-task`` raises "no canonical status, run finalize-tasks" — a hint that
loops forever because finalize keeps aborting on the same cycle.

This is an end-to-end acceptance test that drives the actual ``move-task`` CLI
against a cyclic, status-uninitialized mission and asserts the operator-visible
output names the dependency cycle as the root cause. It fails on the unfixed
production message (generic "run finalize-tasks") and passes after the fix.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app

pytestmark = [pytest.mark.regression, pytest.mark.git_repo]

runner = CliRunner()


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "issue1589@example.invalid")
    _git(repo, "config", "user.name", "Issue 1589")
    # Work on a non-protected mission branch so move-task reaches the
    # canonical-status check (the protected-branch guard fires earlier on main).
    _git(repo, "checkout", "-q", "-b", "mission/demo-1589")
    (repo / ".kittify").mkdir()


def _wp(wp_id: str, deps: list[str]) -> str:
    dep_block = "dependencies: []\n" if not deps else (
        "dependencies:\n" + "".join(f"- {d}\n" for d in deps)
    )
    return (
        "---\n"
        f"work_package_id: {wp_id}\n"
        f"title: {wp_id}\n"
        "execution_mode: code_change\n"
        "agent: testbot\n"
        f"{dep_block}"
        "owned_files:\n"
        f"  - src/{wp_id.lower()}/**\n"
        f"authoritative_surface: src/{wp_id.lower()}/\n"
        "---\n"
        f"# {wp_id}\n\n## Activity Log\n"
    )


def _seed_cyclic_mission(repo: Path) -> str:
    mission_slug = "demo-1589"
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": mission_slug,
                "mission": "software-dev",
                "target_branch": "mission/demo-1589",
                "friendly_name": "Issue 1589 cyclic mission",
                "created_at": "2026-06-01T00:00:00+00:00",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text(
        "# Spec\n\n## Functional Requirements\n\n- **FR-001**: First requirement.\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP09\n- [ ] T001 (WP09)\n\n## WP10\n- [ ] T002 (WP10)\n",
        encoding="utf-8",
    )
    # The cycle: WP09 -> WP10 -> WP09.
    (tasks_dir / "WP09-a.md").write_text(_wp("WP09", ["WP10"]), encoding="utf-8")
    (tasks_dir / "WP10-b.md").write_text(_wp("WP10", ["WP09"]), encoding="utf-8")
    # NOTE: no status.events.jsonl — canonical status is uninitialized, exactly
    # as it is left when finalize-tasks aborts on the cycle.
    return mission_slug


def test_move_task_names_dependency_cycle_when_status_uninitialized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    mission_slug = _seed_cyclic_mission(repo)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed cyclic mission")
    monkeypatch.chdir(repo)

    result = runner.invoke(
        tasks_app,
        ["move-task", "WP10", "--to", "for_review", "--mission", mission_slug],
    )

    # The transition cannot proceed (status uninitialized).
    assert result.exit_code != 0
    out = result.output.lower()
    # ACCEPTANCE: the operator must be told the real root cause — the dependency
    # cycle — not just "run finalize-tasks" (which loops). This is what fails on
    # the unfixed production code.
    assert "circular" in out or "cycle" in out, (
        f"expected the cycle to be named as the root cause; got:\n{result.output}"
    )
    assert "WP09" in result.output and "WP10" in result.output
