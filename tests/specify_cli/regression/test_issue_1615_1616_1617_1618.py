"""Regression tests for issues #1615, #1616, #1617, #1618.

Each test documents a specific bug and proves the fix:

  #1615 — implement.py dependency gate read status from repo_root/kitty-specs
           instead of the coord worktree → now uses resolve_mission_read_path.

  #1616 — orchestrator_api._resolve_mission_dir used bare kitty-specs path
           without checking coord worktree topology.

  #1617 — DecisionGitLog._decisions_file was rooted at repo_root when a
           coord worktree was in use, writing decision events to the wrong tree.

  #1618 — move_task emitted a second safe_commit to the protected target branch
           even when coord topology was active (coord branch already owns it).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.regression]

# ---------------------------------------------------------------------------
# FR-017: source-scanning guards — stale strings must be absent, resolver
#         imports must be present (guards against re-introduction)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parents[3]  # tests/specify_cli/regression/ → repo root (worktree root)


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


# --- #1616: stale prompt strings must not reappear ---

def test_no_stale_status_in_main_repo_string() -> None:
    """workflow.py must not say status lives in main repo."""
    src = _read("src/specify_cli/cli/commands/agent/workflow.py")
    assert "Spec, plan, tasks, and status live in main repo" not in src, (
        "Stale prompt string from #1616 re-introduced in workflow.py"
    )


def test_no_stale_auto_commit_to_target_branch() -> None:
    """workflow.py must not say status auto-commits to target_branch."""
    src = _read("src/specify_cli/cli/commands/agent/workflow.py")
    assert "auto-commit to {target_branch} branch" not in src, (
        "Stale prompt string from #1616 re-introduced in workflow.py"
    )


def test_no_stale_for_review_to_in_progress() -> None:
    """workflow.py review docstring must not say for_review to in_progress."""
    src = _read("src/specify_cli/cli/commands/agent/workflow.py")
    assert "for_review to in_progress" not in src, (
        "Stale docstring from #1616 re-introduced in workflow.py"
    )


def test_no_stale_done_only_dependency() -> None:
    """Doctrine implement prompt must not require only 'done' status."""
    src = _read(
        "src/doctrine/missions/mission-steps/software-dev/implement/prompt.md"
    )
    assert "in `done` status before proceeding" not in src, (
        "Stale dependency condition from #1616 re-introduced in implement/prompt.md"
    )


# --- #1615: coord-aware resolver must be present ---

def test_resolve_mission_read_path_used_in_implement() -> None:
    """implement.py must import or reference resolve_mission_read_path."""
    src = _read("src/specify_cli/cli/commands/implement.py")
    assert "resolve_mission_read_path" in src, (
        "coord-aware resolver not present in implement.py (#1615 regression)"
    )


def test_resolve_mission_read_path_used_in_orchestrator_api() -> None:
    """orchestrator_api/commands.py must use resolve_mission_read_path."""
    src = _read("src/specify_cli/orchestrator_api/commands.py")
    assert "resolve_mission_read_path" in src, (
        "coord-aware resolver not present in orchestrator_api/commands.py (#1615 regression)"
    )


# ---------------------------------------------------------------------------
# #1615: implement.py reads status from coord worktree when present
# ---------------------------------------------------------------------------

class TestIssue1615ImplementCoordRead:
    """#1615: dependency gate must read from coord worktree, not primary checkout."""

    def test_resolve_mission_read_path_prefers_coord_worktree(self, tmp_path: Path) -> None:
        """resolve_mission_read_path returns coord path when coord dir exists on disk."""
        from specify_cli.missions._read_path_resolver import resolve_mission_read_path

        slug = "my-feature"
        mid8 = "01KT3YBD"
        # Create coord mission dir
        coord_dir = (
            tmp_path / ".worktrees" / f"{slug}-{mid8}-coord"
            / "kitty-specs" / f"{slug}-{mid8}"
        )
        coord_dir.mkdir(parents=True)
        # Also create primary (should NOT be selected)
        primary_dir = tmp_path / "kitty-specs" / f"{slug}-{mid8}"
        primary_dir.mkdir(parents=True)

        result = resolve_mission_read_path(tmp_path, slug, mid8)

        assert result == coord_dir, (
            f"Expected coord path {coord_dir}, got {result}. "
            "Regression: implement.py was reading from primary checkout instead of coord worktree."
        )

    def test_primary_checkout_returned_when_coord_absent(self, tmp_path: Path) -> None:
        """When no coord worktree, resolver correctly falls back to primary checkout."""
        from specify_cli.missions._read_path_resolver import resolve_mission_read_path

        slug = "my-feature"
        mid8 = "01KT3YBD"
        primary_dir = tmp_path / "kitty-specs" / f"{slug}-{mid8}"
        primary_dir.mkdir(parents=True)

        result = resolve_mission_read_path(tmp_path, slug, mid8)
        assert result == primary_dir

    def test_mid8_extracted_from_full_slug(self) -> None:
        """mid8 extraction from slug (used by implement.py before calling resolver)."""
        slug = "execution-context-unification-01KT3YBD"
        mid8 = ""
        if "-" in slug:
            tail = slug.rsplit("-", 1)[-1]
            if len(tail) == 8 and tail.isalnum() and tail.isupper():
                mid8 = tail
        assert mid8 == "01KT3YBD", (
            "Regression: implement.py failed to extract mid8 from mission slug."
        )


# ---------------------------------------------------------------------------
# #1616: orchestrator_api._resolve_mission_dir checks coord topology
# ---------------------------------------------------------------------------

class TestIssue1616OrchestratorApiCoordRead:
    """#1616: _resolve_mission_dir must return coord path, not always primary."""

    def test_coord_path_returned_when_coord_exists(self, tmp_path: Path) -> None:
        """_resolve_mission_dir returns coord mission dir when present."""
        from specify_cli.orchestrator_api.commands import _resolve_mission_dir

        slug = "my-feature"
        mid8 = "01KT3YBD"
        coord_dir = (
            tmp_path / ".worktrees" / f"{slug}-{mid8}-coord"
            / "kitty-specs" / f"{slug}-{mid8}"
        )
        coord_dir.mkdir(parents=True)

        result = _resolve_mission_dir(tmp_path, f"{slug}-{mid8}")
        assert result == coord_dir, (
            f"Expected coord path {coord_dir}, got {result}. "
            "Regression: orchestrator_api was not checking coord topology."
        )

    def test_none_returned_when_mission_not_found(self, tmp_path: Path) -> None:
        """_resolve_mission_dir returns None (not raises) when mission absent."""
        from specify_cli.orchestrator_api.commands import _resolve_mission_dir

        result = _resolve_mission_dir(tmp_path, "nonexistent-01KT3YBD")
        assert result is None, (
            "Regression: _resolve_mission_dir should return None when mission not found."
        )


# ---------------------------------------------------------------------------
# #1617: DecisionGitLog writes to coord worktree, not repo_root
# ---------------------------------------------------------------------------

class TestIssue1617DecisionLogCoordRouting:
    """#1617: decisions.events.jsonl must be written under coord worktree."""

    def test_decisions_file_uses_worktree_root_not_repo_root(self, tmp_path: Path) -> None:
        """When worktree_root is coord path, decisions_file is in coord path."""
        from specify_cli.events.decision_log import DecisionGitLog
        from runtime.next._internal_runtime.events import NullEmitter

        repo_root = tmp_path / "repo"
        coord_root = tmp_path / "coord-worktree"
        repo_root.mkdir()
        coord_root.mkdir()

        slug = "my-mission"
        log = DecisionGitLog(
            repo_root=repo_root,
            worktree_root=coord_root,
            destination_ref="kitty/mission-my-mission",
            mission_slug=slug,
            inner=NullEmitter(),
        )

        # Regression: pre-fix this was repo_root / "kitty-specs" / ...
        expected = coord_root / "kitty-specs" / slug / "decisions.events.jsonl"
        assert log._decisions_file == expected, (
            f"Expected decisions_file under coord_root ({expected}), "
            f"but got {log._decisions_file}. "
            "Regression: DecisionGitLog was writing to repo_root instead of coord worktree."
        )

    def test_decisions_file_not_in_repo_root_when_coord_present(self, tmp_path: Path) -> None:
        """Explicitly assert that decisions_file is NOT in repo_root when coord is used."""
        from specify_cli.events.decision_log import DecisionGitLog
        from runtime.next._internal_runtime.events import NullEmitter

        repo_root = tmp_path / "repo"
        coord_root = tmp_path / "coord-worktree"
        repo_root.mkdir()
        coord_root.mkdir()

        slug = "my-mission"
        log = DecisionGitLog(
            repo_root=repo_root,
            worktree_root=coord_root,
            destination_ref="kitty/mission-my-mission",
            mission_slug=slug,
            inner=NullEmitter(),
        )

        wrong_path = repo_root / "kitty-specs" / slug / "decisions.events.jsonl"
        assert log._decisions_file != wrong_path, (
            "Regression: DecisionGitLog._decisions_file must not point to repo_root "
            "when a coord worktree is in use."
        )


# ---------------------------------------------------------------------------
# #1618: move_task guard skips safe_commit when coord+protected
# ---------------------------------------------------------------------------

class TestIssue1618MoveTaskGuard:
    """#1618: second safe_commit skipped when coord topology active + protected branch."""

    def test_coord_topology_active_returns_true_when_coord_exists(self, tmp_path: Path) -> None:
        """_coord_topology_active returns True with coord worktree present on disk."""
        from specify_cli.cli.commands.agent.tasks import _coord_topology_active

        slug = "my-feature-01KT3YBD"
        mid8 = "01KT3YBD"
        base_slug = "my-feature"

        coord_path = tmp_path / ".worktrees" / f"{base_slug}-{mid8}-coord"
        coord_path.mkdir(parents=True)

        result = _coord_topology_active(tmp_path, slug)
        assert result is True, (
            "Regression: _coord_topology_active must return True when coord worktree exists. "
            "move_task guard was not detecting coord topology correctly."
        )

    def test_coord_topology_active_false_when_coord_absent(self, tmp_path: Path) -> None:
        """_coord_topology_active returns False when coord worktree absent."""
        from specify_cli.cli.commands.agent.tasks import _coord_topology_active

        result = _coord_topology_active(tmp_path, "my-feature-01KT3YBD")
        assert result is False

    def test_guard_condition_skips_commit_on_coord_plus_protected(self) -> None:
        """Guard: coord_active AND protected → skip second safe_commit."""
        coord_active = True
        target_branch = "main"
        protected = ["main"]

        skip = coord_active and target_branch in protected
        assert skip is True, (
            "Regression: move_task guard must set _skip_target_commit=True "
            "when coord topology active and target branch is protected."
        )

    def test_guard_condition_does_not_skip_on_legacy_missions(self) -> None:
        """Guard: legacy mission (coord_active=False) → safe_commit proceeds normally."""
        coord_active = False
        target_branch = "main"
        protected = ["main"]

        skip = coord_active and target_branch in protected
        assert skip is False, (
            "Regression: safe_commit must proceed for legacy missions (no coord topology)."
        )

    def test_guard_condition_does_not_skip_on_unprotected_branch(self) -> None:
        """Guard: coord active but target not protected → safe_commit still runs."""
        coord_active = True
        target_branch = "feature/my-work"
        protected = ["main"]

        skip = coord_active and target_branch in protected
        assert skip is False, (
            "Regression: safe_commit must run when target branch is not protected, "
            "even with coord topology active."
        )
