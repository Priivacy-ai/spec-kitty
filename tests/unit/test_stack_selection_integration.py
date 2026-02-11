"""Unit tests for stack-first implement selection integration (WP07).

Tests the selection matrix: ready change WP, blocked stack, normal fallback.
"""

from __future__ import annotations

from pathlib import Path


from specify_cli.core.change_stack import (
    StackSelectionResult,
    resolve_next_change_wp,
)


# ============================================================================
# Helpers
# ============================================================================


def _create_wp_file(
    tasks_dir: Path,
    wp_id: str,
    lane: str = "planned",
    change_stack: bool = False,
    dependencies: list[str] | None = None,
    stack_rank: int = 0,
) -> None:
    """Create a WP file with minimal frontmatter."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    deps_yaml = ""
    if dependencies:
        deps_yaml = "\ndependencies:\n" + "\n".join(f'  - "{d}"' for d in dependencies)
    change_yaml = f"\nchange_stack: true\nstack_rank: {stack_rank}" if change_stack else ""
    slug = wp_id.lower().replace("wp", "task")
    content = (
        f"---\n"
        f'work_package_id: "{wp_id}"\n'
        f'title: "Task for {wp_id}"\n'
        f'lane: "{lane}"{deps_yaml}{change_yaml}\n'
        f"---\n\n# {wp_id}\n"
    )
    (tasks_dir / f"{wp_id}-{slug}.md").write_text(content, encoding="utf-8")


# ============================================================================
# Ready change WP selection
# ============================================================================


class TestReadyChangeWpSelection:
    """Verify ready change-stack WPs are selected before normal backlog."""

    def test_ready_change_wp_selected_over_normal(self, tmp_path: Path) -> None:
        """A ready change WP should be selected before a normal planned WP."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="planned")
        _create_wp_file(tasks_dir, "WP09", lane="planned", change_stack=True, stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "change_stack"
        assert result.next_wp_id == "WP09"

    def test_higher_priority_change_wp_selected(self, tmp_path: Path) -> None:
        """Among ready change WPs, lower stack_rank is selected first."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP09", lane="planned", change_stack=True, stack_rank=2)
        _create_wp_file(tasks_dir, "WP10", lane="planned", change_stack=True, stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "change_stack"
        assert result.next_wp_id == "WP10"

    def test_change_wp_with_satisfied_deps(self, tmp_path: Path) -> None:
        """Change WP whose deps are done should be selected."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="done")
        _create_wp_file(tasks_dir, "WP09", lane="planned", change_stack=True,
                       dependencies=["WP01"], stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "change_stack"
        assert result.next_wp_id == "WP09"


# ============================================================================
# Blocked stack stop behavior
# ============================================================================


class TestBlockedStackStop:
    """Verify normal progression is blocked when change stack has pending items."""

    def test_blocked_when_change_wp_has_unsatisfied_deps(self, tmp_path: Path) -> None:
        """Should block when change WP exists but deps aren't done."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="planned")
        _create_wp_file(tasks_dir, "WP03", lane="doing")
        _create_wp_file(tasks_dir, "WP09", lane="planned", change_stack=True,
                       dependencies=["WP03"], stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "blocked"
        assert result.normal_progression_blocked is True
        assert result.next_wp_id is None

    def test_blockers_list_populated(self, tmp_path: Path) -> None:
        """Blocker details should include blocking dep info."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP03", lane="doing")
        _create_wp_file(tasks_dir, "WP09", lane="planned", change_stack=True,
                       dependencies=["WP03"], stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert len(result.blockers) >= 1
        assert any("WP03" in b for b in result.blockers)

    def test_pending_change_wps_reported(self, tmp_path: Path) -> None:
        """Pending change WPs should be listed in the result."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP03", lane="doing")
        _create_wp_file(tasks_dir, "WP09", lane="planned", change_stack=True,
                       dependencies=["WP03"], stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert "WP09" in result.pending_change_wps

    def test_active_change_wp_blocks_normal(self, tmp_path: Path) -> None:
        """A change WP in doing/for_review should block normal progression."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="planned")
        _create_wp_file(tasks_dir, "WP09", lane="doing", change_stack=True, stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "blocked"
        assert result.normal_progression_blocked is True


# ============================================================================
# Normal fallback when stack empty
# ============================================================================


class TestNormalFallback:
    """Verify normal backlog selection when change stack is empty or complete."""

    def test_no_change_wps_selects_normal(self, tmp_path: Path) -> None:
        """Without change WPs, normal backlog should be used."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="planned")
        _create_wp_file(tasks_dir, "WP02", lane="done")

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "normal_backlog"
        assert result.next_wp_id == "WP01"

    def test_all_change_wps_done_selects_normal(self, tmp_path: Path) -> None:
        """When all change WPs are done, normal backlog should be used."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="planned")
        _create_wp_file(tasks_dir, "WP09", lane="done", change_stack=True, stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "normal_backlog"
        assert result.next_wp_id == "WP01"

    def test_empty_tasks_dir_returns_normal(self, tmp_path: Path) -> None:
        """Empty tasks dir should return normal_backlog with no WP."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "normal_backlog"
        assert result.next_wp_id is None

    def test_no_planned_wps_at_all(self, tmp_path: Path) -> None:
        """When everything is done, return normal with None."""
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="done")
        _create_wp_file(tasks_dir, "WP02", lane="done")

        result = resolve_next_change_wp(tasks_dir, "test-feature")

        assert result.selected_source == "normal_backlog"
        assert result.next_wp_id is None

    def test_nonexistent_tasks_dir(self, tmp_path: Path) -> None:
        """Nonexistent tasks dir should return normal_backlog."""
        result = resolve_next_change_wp(tmp_path / "nonexistent", "test-feature")

        assert result.selected_source == "normal_backlog"


# ============================================================================
# StackSelectionResult serialization
# ============================================================================


class TestStackSelectionResult:
    """Test StackSelectionResult dataclass behavior."""

    def test_default_values(self) -> None:
        result = StackSelectionResult(selected_source="normal_backlog")
        assert result.next_wp_id is None
        assert result.normal_progression_blocked is False
        assert result.blockers == []
        assert result.pending_change_wps == []

    def test_blocked_state(self) -> None:
        result = StackSelectionResult(
            selected_source="blocked",
            normal_progression_blocked=True,
            blockers=["WP09 blocked by: WP03"],
            pending_change_wps=["WP09"],
        )
        assert result.selected_source == "blocked"
        assert result.normal_progression_blocked is True
        assert len(result.blockers) == 1
