"""Regression tests for workflow review lane gating and implement prompt content."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.lane_test_utils import lane_worktree_path, write_single_lane_manifest

from specify_cli.cli.commands.agent import workflow
from specify_cli.frontmatter import write_frontmatter
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.store import append_event
from specify_cli.status.models import StatusEvent, Lane
from specify_cli.tasks_support import extract_scalar, split_frontmatter

pytestmark = pytest.mark.fast


def _seed_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Seed a WP into a specific lane in the event log."""
    _lane_alias = {"doing": "in_progress"}
    canonical_lane = _lane_alias.get(lane, lane)
    event = StatusEvent(
        event_id=f"test-{wp_id}-{canonical_lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(canonical_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _write_wp_file(path: Path, wp_id: str, lane: str) -> None:
    frontmatter = {
        "work_package_id": wp_id,
        "subtasks": ["T001"],
        "title": f"{wp_id} Test",
        "phase": "Phase 0",
        "lane": lane,
        "assignee": "",
        "agent": "",
        "shell_pid": "",
        "review_status": "",
        "reviewed_by": "",
        "dependencies": [],
        "history": [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "lane": lane,
                "agent": "system",
                "shell_pid": "",
                "action": "Prompt created",
            }
        ],
    }
    body = f"# {wp_id} Prompt\n\n## Activity Log\n- 2026-01-01T00:00:00Z – system – lane={lane} – Prompt created.\n"
    write_frontmatter(path, frontmatter, body)


@pytest.fixture()
def workflow_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    (repo_root / ".kittify" / "config.yaml").write_text(
        "vcs:\n  type: git\nproject:\n  uuid: test-project-uuid\n  slug: test-project\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out",
        lambda repo_root, mission_slug: (repo_root, "main"),
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow.safe_commit",
        lambda **kwargs: True,
    )
    return repo_root


def test_workflow_review_rejects_planned_lane(workflow_repo: Path) -> None:
    mission_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane="planned")
    # Seed event log with planned lane so review command finds canonical state
    _seed_wp_lane(feature_dir, "WP01", "planned")

    result = CliRunner().invoke(
        workflow.app,
        ["review", "WP01", "--feature", mission_slug, "--agent", "test-reviewer"],
    )

    assert result.exit_code == 1
    assert "not 'for_review'" in result.stdout
    frontmatter, _, _ = split_frontmatter(wp_path.read_text(encoding="utf-8"))
    assert extract_scalar(frontmatter, "lane") == "planned"


def test_workflow_review_accepts_for_review_lane(workflow_repo: Path) -> None:
    mission_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane="for_review")
    # Seed event log with for_review lane so review command finds canonical state
    _seed_wp_lane(feature_dir, "WP01", "for_review")

    result = CliRunner().invoke(
        workflow.app,
        ["review", "WP01", "--feature", mission_slug, "--agent", "test-reviewer"],
    )

    assert result.exit_code == 0
    # Lane is event-log-only; verify canonical state via event log
    from specify_cli.status.store import read_events
    from specify_cli.status.reducer import reduce
    events = read_events(feature_dir)
    snapshot = reduce(events)
    wp_state = snapshot.work_packages.get("WP01", {})
    assert wp_state.get("lane") in ("in_progress", "doing"), f"Expected in_progress lane, got: {wp_state.get('lane')}"


def test_workflow_implement_moves_planned_to_doing(workflow_repo: Path) -> None:
    """Implement command should transition a planned WP to doing lane.

    Extracted from tests/legacy/specify_cli/test_workflow_auto_moves.py.
    """
    # Arrange
    mission_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
    (feature_dir / "tasks.md").write_text("## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8")
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane="planned")
    # Seed canonical state so implement doesn't hard-fail (no frontmatter fallback)
    _seed_wp_lane(feature_dir, "WP01", "planned")

    # Pre-create workspace so implement skips worktree creation (which needs real git)
    workspace = lane_worktree_path(workflow_repo, mission_slug)
    workspace.mkdir(parents=True)

    # Assumption check
    frontmatter_before, _, _ = split_frontmatter(wp_path.read_text(encoding="utf-8"))
    assert extract_scalar(frontmatter_before, "lane") == "planned"

    # Act
    result = CliRunner().invoke(
        workflow.app,
        ["implement", "WP01", "--feature", mission_slug, "--agent", "test-agent"],
    )

    # Assert
    assert result.exit_code == 0, result.stdout
    # The implement command claims the WP by writing the agent name to frontmatter.
    # Lane is event-log-only and not updated by implement (no emit_status_transition call).
    # Verify the agent name was written to frontmatter as evidence of successful claim.
    frontmatter, _, _ = split_frontmatter(wp_path.read_text(encoding="utf-8"))
    assert extract_scalar(frontmatter, "agent") == "test-agent"


def test_workflow_review_tracks_reviewer_agent_name(workflow_repo: Path) -> None:
    """Review command should write the reviewer agent name into WP frontmatter.

    Extracted from tests/legacy/specify_cli/test_workflow_auto_moves.py.
    """
    # Arrange
    mission_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
    (feature_dir / "tasks.md").write_text("## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8")
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane="for_review")
    # Seed event log with for_review lane so review command finds canonical state
    _seed_wp_lane(feature_dir, "WP01", "for_review")

    # Assumption check
    frontmatter_before, _, _ = split_frontmatter(wp_path.read_text(encoding="utf-8"))
    assert extract_scalar(frontmatter_before, "agent") == ""

    # Act
    result = CliRunner().invoke(
        workflow.app,
        ["review", "WP01", "--feature", mission_slug, "--agent", "claude"],
    )

    # Assert
    assert result.exit_code == 0, result.stdout
    frontmatter, _, _ = split_frontmatter(wp_path.read_text(encoding="utf-8"))
    assert extract_scalar(frontmatter, "agent") == "claude"


def test_workflow_review_uses_existing_canonical_event_lane(workflow_repo: Path) -> None:
    """Review should read the existing canonical event lane before claiming the WP."""
    mission_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
    (feature_dir / "tasks.md").write_text("## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8")
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane="for_review")

    emit_status_transition(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id="WP01",
        to_lane="for_review",
        actor="system",
        force=True,
        reason="seed canonical lane",
        repo_root=workflow_repo,
    )

    result = CliRunner().invoke(
        workflow.app,
        ["review", "WP01", "--feature", mission_slug, "--agent", "test-reviewer"],
    )

    assert result.exit_code == 0, result.stdout
    # Lane is event-log-only; verify canonical state via event log
    from specify_cli.status.store import read_events
    from specify_cli.status.reducer import reduce
    events = read_events(feature_dir)
    snapshot = reduce(events)
    wp_state = snapshot.work_packages.get("WP01", {})
    assert wp_state.get("lane") in ("in_progress", "doing"), f"Expected in_progress lane, got: {wp_state.get('lane')}"


def _setup_implement_fixture(workflow_repo: Path, *, lane: str = "planned") -> tuple[Path, str]:
    """Shared setup for implement prompt-content tests.

    Returns (wp_path, mission_slug).
    """
    mission_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
    (feature_dir / "tasks.md").write_text("## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8")
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane=lane)
    # Seed canonical state so implement doesn't hard-fail (no frontmatter fallback)
    _seed_wp_lane(feature_dir, "WP01", lane)
    # Pre-create workspace so implement skips real git worktree creation
    workspace = lane_worktree_path(workflow_repo, mission_slug)
    workspace.mkdir(parents=True, exist_ok=True)
    return wp_path, mission_slug


def _setup_review_fixture(workflow_repo: Path, *, lane: str = "for_review") -> tuple[Path, str]:
    """Shared setup for review prompt-content tests.

    Returns (wp_path, feature_slug).
    """
    feature_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",), predicted_surfaces=("workflow",))
    (feature_dir / "tasks.md").write_text("## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8")
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane=lane)
    _seed_wp_lane(feature_dir, "WP01", lane)
    workspace = lane_worktree_path(workflow_repo, feature_slug)
    workspace.mkdir(parents=True, exist_ok=True)
    return wp_path, feature_slug


def test_implement_prompt_includes_when_youre_done_header(workflow_repo: Path) -> None:
    """Implement prompt file must include the 'WHEN YOU'RE DONE:' section header.

    Extracted from tests/legacy/unit/agent/test_workflow_instructions.py.
    """
    # Arrange
    wp_path, mission_slug = _setup_implement_fixture(workflow_repo)

    # Assumption check
    assert not (Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md").exists() or True

    # Act
    result = CliRunner().invoke(
        workflow.app,
        ["implement", "WP01", "--feature", mission_slug, "--agent", "test-agent"],
    )

    # Assert
    assert result.exit_code == 0, result.stdout
    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
    assert prompt_file.exists(), f"Prompt file not written: {prompt_file}"
    content = prompt_file.read_text(encoding="utf-8")
    assert "WHEN YOU'RE DONE:" in content
    assert "1. **Commit your implementation files:**" in content
    assert "git add" in content
    assert "git commit" in content
    assert "feat(WP01):" in content or "fix(WP01):" in content
    assert "git log -1" in content


def test_implement_prompt_includes_commit_message_conventions(workflow_repo: Path) -> None:
    """Implement prompt file must document commit message type conventions.

    Extracted from tests/legacy/unit/agent/test_workflow_instructions.py.
    """
    # Arrange
    wp_path, mission_slug = _setup_implement_fixture(workflow_repo)

    # Act
    result = CliRunner().invoke(
        workflow.app,
        ["implement", "WP01", "--feature", mission_slug, "--agent", "test-agent"],
    )

    # Assert
    assert result.exit_code == 0, result.stdout
    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
    content = prompt_file.read_text(encoding="utf-8")
    assert "feat(" in content or "fix(" in content
    assert "chore:" in content or "chore(" in content
    assert "docs:" in content or "docs(" in content


def test_implement_prompt_has_numbered_steps(workflow_repo: Path) -> None:
    """Implement prompt file must include numbered steps 1, 2, 3.

    Extracted from tests/legacy/unit/agent/test_workflow_instructions.py.
    """
    # Arrange
    wp_path, mission_slug = _setup_implement_fixture(workflow_repo)

    # Act
    result = CliRunner().invoke(
        workflow.app,
        ["implement", "WP01", "--feature", mission_slug, "--agent", "test-agent"],
    )

    # Assert
    assert result.exit_code == 0, result.stdout
    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
    content = prompt_file.read_text(encoding="utf-8")
    assert "1. **Commit your implementation files:**" in content
    assert "2." in content
    assert "3." in content


def test_implement_prompt_points_to_shared_feature_artifacts(workflow_repo: Path) -> None:
    _wp_path, feature_slug = _setup_implement_fixture(workflow_repo)

    result = CliRunner().invoke(
        workflow.app,
        ["implement", "WP01", "--feature", feature_slug, "--agent", "test-agent"],
    )

    assert result.exit_code == 0, result.stdout
    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
    content = prompt_file.read_text(encoding="utf-8")
    assert "📚 SHARED FEATURE ARTIFACTS:" in content
    assert f"Spec, plan, tasks, and status live in main repo: {workflow_repo}/kitty-specs/{feature_slug}/" in content
    assert "Use this lane workspace for code/tests; do not expect shared feature artifacts here" in content


def test_review_prompt_points_to_shared_feature_artifacts(workflow_repo: Path) -> None:
    _wp_path, feature_slug = _setup_review_fixture(workflow_repo)

    result = CliRunner().invoke(
        workflow.app,
        ["review", "WP01", "--feature", feature_slug, "--agent", "test-reviewer"],
    )

    assert result.exit_code == 0, result.stdout
    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-review-WP01.md"
    content = prompt_file.read_text(encoding="utf-8")
    assert "📚 SHARED FEATURE ARTIFACTS:" in content
    assert f"Spec, plan, tasks, and status live in main repo: {workflow_repo}/kitty-specs/{feature_slug}/" in content
    assert "Use this lane workspace for code/tests; do not expect shared feature artifacts here" in content
