"""WP04 (#676) — Integration tests: counter advances only on real rejections.

Scenario coverage (from WP04, T022):

1. Set up a mission + WP via the existing rejection-cycle fixtures.
2. Drive the WP to ``for_review``.
3. Re-run ``agent action implement`` 2 times → counter unchanged, no new
   ``review-cycle-N.md`` artifact.
4. Trigger a real rejection event (``move-task --to planned`` with a
   ``--review-feedback-file``) → counter advances by exactly 1, exactly one
   new ``review-cycle-N.md`` artifact at the new N.
5. Re-run ``agent action implement`` once more → counter unchanged.

The integration is end-to-end via the CLI Typer app:
``specify_cli.cli.commands.agent.workflow.app`` for implement, and
``specify_cli.cli.commands.agent.tasks._persist_review_feedback`` for the
canonical rejection event (the same helper invoked by the
``move-task --to planned`` CLI surface).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import workflow
from specify_cli.frontmatter import write_frontmatter
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event


MISSION_SLUG = "001-rejection-only-feature"
WP_SLUG = "WP01-test-task"


# ---------------------------------------------------------------------------
# Helpers (kept in-file for clarity; mirror tests/integration/test_rejection_cycle.py)
# ---------------------------------------------------------------------------


def _make_event(
    *,
    event_id: str,
    wp_id: str = "WP01",
    from_lane: Lane = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
    review_ref: str | None = None,
    mission_slug: str = MISSION_SLUG,
) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug=mission_slug,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at="2026-04-28T12:00:00Z",
        actor="claude",
        force=False,
        execution_mode="worktree",
        review_ref=review_ref,
    )


def _write_cli_wp(wp_path: Path) -> None:
    write_frontmatter(
        wp_path,
        {
            "work_package_id": "WP01",
            "subtasks": ["T001"],
            "title": "Test Task",
            "phase": "Phase 1",
            "lane": "planned",
            "dependencies": [],
            "assignee": "",
            "agent": "claude",
            "shell_pid": "",
            "review_status": "none",
            "review_feedback": "",
            "history": [],
        },
        "# WP01 Prompt\n",
    )


def _count_cycle_artifacts(sub_artifact_dir: Path) -> int:
    if not sub_artifact_dir.exists():
        return 0
    return len(list(sub_artifact_dir.glob("review-cycle-*.md")))


def _list_cycle_artifacts(sub_artifact_dir: Path) -> list[str]:
    if not sub_artifact_dir.exists():
        return []
    return sorted(p.name for p in sub_artifact_dir.glob("review-cycle-*.md"))


# ---------------------------------------------------------------------------
# Fixture: build a minimal mission + WP repo and put the WP into for_review.
# ---------------------------------------------------------------------------


@pytest.fixture()
def for_review_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    """Initialise a git repo with one mission, one WP, currently in ``for_review``.

    Returns ``(repo_root, feature_dir, sub_artifact_dir)``.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    (repo / ".kittify").mkdir()

    feature_dir = repo / "kitty-specs" / MISSION_SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "feature_number": "001",
                "mission_slug": MISSION_SLUG,
                "created_at": "2026-04-28T00:00:00Z",
                "friendly_name": MISSION_SLUG,
                "mission": "software-dev",
                "slug": MISSION_SLUG,
                "target_branch": "main",
                "vcs": "git",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            mission_slug=MISSION_SLUG,
            mission_id=f"mission-{MISSION_SLUG}",
            mission_branch=f"kitty/mission-{MISSION_SLUG}",
            target_branch="main",
            lanes=[
                ExecutionLane(
                    lane_id="lane-a",
                    wp_ids=("WP01",),
                    write_scope=("src/**",),
                    predicted_surfaces=("core",),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
            computed_at="2026-04-28T10:00:00Z",
            computed_from="test",
        ),
    )
    (feature_dir / "tasks.md").write_text(
        "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
    )
    _write_cli_wp(tasks_dir / f"{WP_SLUG}.md")

    # Drive event log: planned -> claimed -> in_progress -> for_review.
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000001",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
        ),
    )
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000002",
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
        ),
    )
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000003",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
        ),
    )

    workspace = repo / ".worktrees" / f"{MISSION_SLUG}-lane-a"
    workspace.mkdir(parents=True)

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed for-review fixture"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    sub_artifact_dir = feature_dir / "tasks" / WP_SLUG

    monkeypatch.chdir(repo)
    return repo, feature_dir, sub_artifact_dir


# ---------------------------------------------------------------------------
# Helper: fire the canonical rejection handler (counter mutation site).
# ---------------------------------------------------------------------------


def _trigger_rejection(repo: Path, body: str) -> Path:
    """Drive the canonical rejection handler exactly once.

    Mirrors what ``spec-kitty agent tasks move-task WP01 --to planned
    --review-feedback-file <path>`` does internally — calls
    ``_persist_review_feedback`` which writes ``review-cycle-N.md`` and
    returns the persisted path.
    """
    from specify_cli.cli.commands.agent.tasks import _persist_review_feedback

    feedback_file = repo / f"feedback_{abs(hash(body))}.md"
    feedback_file.write_text(body, encoding="utf-8")

    persisted, _pointer = _persist_review_feedback(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        task_id="WP01",
        feedback_source=feedback_file,
        reviewer_agent="claude",
    )
    return persisted


# ---------------------------------------------------------------------------
# T022 — End-to-end integration test
# ---------------------------------------------------------------------------


def test_review_cycle_counter_advances_only_on_real_rejection(
    for_review_repo: tuple[Path, Path, Path],
) -> None:
    """Counter advances by exactly 1 per rejection; reruns are no-ops."""
    repo, _feature_dir, sub_artifact_dir = for_review_repo

    # Step 1: WP is in for_review with zero artifacts.
    assert _count_cycle_artifacts(sub_artifact_dir) == 0
    assert _list_cycle_artifacts(sub_artifact_dir) == []

    # Step 2: Re-run `agent action implement WP01` two times against the
    # for_review WP. Each invocation must be a counter no-op.
    runner = CliRunner()
    for attempt in range(2):
        result = runner.invoke(
            workflow.app,
            [
                "implement",
                "WP01",
                "--feature",
                MISSION_SLUG,
                "--agent",
                "claude",
            ],
        )
        # The CLI may exit 0 or 1 depending on workspace plumbing; for the
        # purposes of this test we only care that no review-cycle artifact
        # appeared as a side effect.
        assert _count_cycle_artifacts(sub_artifact_dir) == 0, (
            f"Implement rerun #{attempt + 1} unexpectedly created an artifact: "
            f"{_list_cycle_artifacts(sub_artifact_dir)}\nstdout:\n{result.stdout}"
        )

    # Step 3: Trigger a real rejection event. Counter must advance by 1.
    persisted = _trigger_rejection(repo, "## Cycle 1 issues\n\nFix me.")
    assert persisted.name == "review-cycle-1.md"
    assert persisted.exists()
    assert _count_cycle_artifacts(sub_artifact_dir) == 1
    assert _list_cycle_artifacts(sub_artifact_dir) == ["review-cycle-1.md"]

    # Capture the file's signature so we can prove subsequent reruns do not
    # rewrite it.
    artifact_mtime = persisted.stat().st_mtime_ns
    artifact_size = persisted.stat().st_size

    # Step 4: Re-run `agent action implement WP01` again. Counter unchanged;
    # the existing artifact must not be touched.
    result = runner.invoke(
        workflow.app,
        [
            "implement",
            "WP01",
            "--feature",
            MISSION_SLUG,
            "--agent",
            "claude",
        ],
    )
    assert _count_cycle_artifacts(sub_artifact_dir) == 1, (
        f"Implement rerun after rejection unexpectedly inflated counter; "
        f"artifacts now: {_list_cycle_artifacts(sub_artifact_dir)}\nstdout:\n{result.stdout}"
    )
    assert persisted.stat().st_mtime_ns == artifact_mtime, (
        "Existing review-cycle-1.md must not be rewritten by an implement rerun."
    )
    assert persisted.stat().st_size == artifact_size

    # Bonus: confirm that the canonical artifact-set is exactly {1}.
    assert _list_cycle_artifacts(sub_artifact_dir) == ["review-cycle-1.md"]


def test_two_rejections_produce_two_distinct_artifacts(
    for_review_repo: tuple[Path, Path, Path],
) -> None:
    """A second rejection writes review-cycle-2.md without disturbing review-cycle-1.md."""
    repo, _feature_dir, sub_artifact_dir = for_review_repo

    p1 = _trigger_rejection(repo, "## First rejection issues")
    assert p1.name == "review-cycle-1.md"
    assert _count_cycle_artifacts(sub_artifact_dir) == 1
    p1_mtime = p1.stat().st_mtime_ns

    p2 = _trigger_rejection(repo, "## Second rejection issues")
    assert p2.name == "review-cycle-2.md"
    assert _count_cycle_artifacts(sub_artifact_dir) == 2
    assert _list_cycle_artifacts(sub_artifact_dir) == [
        "review-cycle-1.md",
        "review-cycle-2.md",
    ]
    # First artifact untouched.
    assert p1.stat().st_mtime_ns == p1_mtime
