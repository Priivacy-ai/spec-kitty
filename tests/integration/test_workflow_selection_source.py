"""Integration tests for selection source output in workflow implement (WP07).

Verifies that the `workflow implement` auto-detect path prints a selection
source message for ALL resolve_next_change_wp outcomes:
  - change_stack (ready change WP selected)
  - normal_backlog (no change stack items)
  - blocked (change stack blocks progression → exit 1 with blocker info)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import workflow
from specify_cli.frontmatter import write_frontmatter

runner = CliRunner()


# ============================================================================
# Helpers
# ============================================================================


def _write_wp_file(
    tasks_dir: Path,
    wp_id: str,
    lane: str = "planned",
    change_stack: bool = False,
    stack_rank: int = 0,
    dependencies: list[str] | None = None,
) -> Path:
    """Create a WP file with minimal frontmatter."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    frontmatter: dict = {
        "work_package_id": wp_id,
        "subtasks": ["T001"],
        "title": f"{wp_id} Test Task",
        "phase": "Phase 0",
        "lane": lane,
        "assignee": "",
        "agent": "",
        "shell_pid": "",
        "dependencies": dependencies or [],
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
    if change_stack:
        frontmatter["change_stack"] = True
        frontmatter["stack_rank"] = stack_rank

    slug = wp_id.lower().replace("wp", "task")
    wp_path = tasks_dir / f"{wp_id}-{slug}.md"
    body = f"# {wp_id}\n\n## Activity Log\n- 2026-01-01T00:00:00Z – system – lane={lane} – Prompt created.\n"
    write_frontmatter(wp_path, frontmatter, body)
    return wp_path


def _write_tasks_md(feature_dir: Path, wp_id: str) -> None:
    """Write a minimal tasks.md with one WP entry."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    content = f"## {wp_id} Test\n\n- [x] T001 Placeholder task\n"
    (feature_dir / "tasks.md").write_text(content, encoding="utf-8")


@pytest.fixture()
def workflow_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal repo root for workflow selection tests."""
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out",
        lambda repo_root, feature_slug: (repo_root, "main"),
    )
    return repo_root


# ============================================================================
# Ready change-stack WP → selection source printed
# ============================================================================


class TestChangeStackSelectionSource:
    """Verify selection source message when change-stack WP is auto-selected."""

    def test_change_stack_source_printed(self, workflow_repo: Path) -> None:
        """Auto-detect with ready change WP should print change stack source."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")
        _write_wp_file(
            tasks_dir, "WP09", lane="planned", change_stack=True, stack_rank=1
        )
        _write_tasks_md(feature_dir, "WP09")

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0
        assert "Selected from change stack" in result.output
        assert "stack-first priority" in result.output

    def test_change_stack_selects_correct_wp(self, workflow_repo: Path) -> None:
        """Auto-detect should select the change WP, not the normal WP."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")
        _write_wp_file(
            tasks_dir, "WP09", lane="planned", change_stack=True, stack_rank=1
        )
        _write_tasks_md(feature_dir, "WP09")

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0
        # The prompt file should be for WP09, not WP01
        prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP09.md"
        assert prompt_file.exists(), "Expected prompt file for WP09 (change stack)"


# ============================================================================
# Normal backlog fallback → selection source printed
# ============================================================================


class TestNormalBacklogSelectionSource:
    """Verify selection source message when normal backlog is used."""

    def test_normal_backlog_source_printed(self, workflow_repo: Path) -> None:
        """Auto-detect with no change WPs should print normal backlog source."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0
        assert "Selected from normal backlog" in result.output
        assert "no change stack items" in result.output

    def test_normal_backlog_selects_first_planned(self, workflow_repo: Path) -> None:
        """Auto-detect normal backlog should select the first planned WP."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="done")
        _write_wp_file(tasks_dir, "WP02", lane="planned")
        _write_tasks_md(feature_dir, "WP02")

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0
        prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP02.md"
        assert prompt_file.exists(), "Expected prompt file for WP02 (first planned)"


# ============================================================================
# Blocked stack → error output with blocker info
# ============================================================================


class TestBlockedStackOutput:
    """Verify blocked stack produces error output with blocker details."""

    def test_blocked_stack_exits_with_error(self, workflow_repo: Path) -> None:
        """Auto-detect with blocked change stack should exit 1."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")
        _write_wp_file(tasks_dir, "WP03", lane="doing")
        _write_wp_file(
            tasks_dir,
            "WP09",
            lane="planned",
            change_stack=True,
            stack_rank=1,
            dependencies=["WP03"],
        )

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 1
        assert "Change stack has pending work packages" in result.output

    def test_blocked_stack_shows_blockers(self, workflow_repo: Path) -> None:
        """Blocked output should include dependency blocker details."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")
        _write_wp_file(tasks_dir, "WP03", lane="doing")
        _write_wp_file(
            tasks_dir,
            "WP09",
            lane="planned",
            change_stack=True,
            stack_rank=1,
            dependencies=["WP03"],
        )

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 1
        assert "Blockers:" in result.output
        assert "WP03" in result.output

    def test_blocked_stack_shows_pending_wps(self, workflow_repo: Path) -> None:
        """Blocked output should list pending change WPs."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_wp_file(tasks_dir, "WP03", lane="doing")
        _write_wp_file(
            tasks_dir,
            "WP09",
            lane="planned",
            change_stack=True,
            stack_rank=1,
            dependencies=["WP03"],
        )

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 1
        assert "Pending change WPs:" in result.output
        assert "WP09" in result.output


# ============================================================================
# Explicit WP ID → no selection source (not auto-detected)
# ============================================================================


# ============================================================================
# Cross-stash selection: main change-stack found from feature context (Fix 3)
# ============================================================================


class TestCrossStashSelection:
    """Verify that main change-stack WPs are found when working on a feature.

    This tests Fix 3: _find_first_planned_wp() must check both
    kitty-specs/change-stack/main/ AND the feature-local tasks dir.
    """

    def test_main_stash_wp_selected_from_feature_context(
        self, workflow_repo: Path
    ) -> None:
        """Working on feature, main-stash has planned change WP -> selects it."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        # Feature has a normal planned WP
        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")

        # Main stash has a ready change WP
        main_stash = workflow_repo / "kitty-specs" / "change-stack" / "main"
        _write_wp_file(
            main_stash, "WP01", lane="planned", change_stack=True, stack_rank=1
        )

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0
        # Should select the main-stash change WP, not the feature WP01
        assert "Selected from change stack" in result.output

    def test_main_stash_active_change_wp_blocks_feature(
        self, workflow_repo: Path
    ) -> None:
        """Main-stash has an active (doing) change WP -> blocks progression."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        # Feature has a normal planned WP
        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")

        # Main stash has only an in-progress change WP (none ready)
        main_stash = workflow_repo / "kitty-specs" / "change-stack" / "main"
        _write_wp_file(
            main_stash, "WP01", lane="doing", change_stack=True, stack_rank=1
        )

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 1
        assert "Change stack has pending work packages" in result.output

    def test_empty_main_stash_falls_through_to_feature(
        self, workflow_repo: Path
    ) -> None:
        """Empty main stash -> feature-local WPs selected (regression test)."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        # Feature has a normal planned WP, no main stash at all
        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0
        assert "Selected from normal backlog" in result.output

    def test_main_stash_all_done_falls_through(self, workflow_repo: Path) -> None:
        """Main stash has only done change WPs -> falls through to feature."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")

        # Main stash has only completed change WPs
        main_stash = workflow_repo / "kitty-specs" / "change-stack" / "main"
        _write_wp_file(main_stash, "WP01", lane="done", change_stack=True, stack_rank=1)

        result = runner.invoke(
            workflow.app,
            ["implement", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0
        # Should fall through to feature normal backlog
        assert "Selected from normal backlog" in result.output


# ============================================================================
# Explicit WP ID → no selection source (not auto-detected)
# ============================================================================


class TestExplicitWpNoSelectionSource:
    """Verify no selection source message when WP ID is given explicitly."""

    def test_explicit_wp_no_source_message(self, workflow_repo: Path) -> None:
        """Explicitly providing WP ID should not print selection source."""
        feature_slug = "001-test-feature"
        feature_dir = workflow_repo / "kitty-specs" / feature_slug
        tasks_dir = feature_dir / "tasks"

        _write_tasks_md(feature_dir, "WP01")
        _write_wp_file(tasks_dir, "WP01", lane="planned")

        result = runner.invoke(
            workflow.app,
            ["implement", "WP01", "--feature", feature_slug, "--agent", "test-agent"],
        )

        assert result.exit_code == 0
        assert "Selected from" not in result.output
