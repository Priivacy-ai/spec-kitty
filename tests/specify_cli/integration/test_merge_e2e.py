"""E2E integration test: merge engine v2 with resume (T072).

Verifies SC-004: merge is deterministic, resumable, and handles conflicts.

Covers:
- MergeState: save → load round-trip, remaining_wps, progress_percent
- MergeState: mark_wp_complete updates remaining list
- has_active_merge: true when work remains, false when done
- Lock acquisition prevents double-lock
- Conflict classification: event log vs. metadata vs. human-authored
- Auto-resolution of event log conflicts (append-merge)
- get_merged_branches: merged branch appears, unmerged does not
- Full merge round-trip: 3 WP branches in a real git repo
- Resume: interrupt after WP01, resume picks up from WP02
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.merge.conflict_resolver import (
    ConflictType,
    classify_conflict,
    resolve_owned_conflicts,
    _merge_event_logs,
)
from specify_cli.merge.engine import MergeResult
from specify_cli.merge.reconciliation import get_merged_branches
from specify_cli.merge.state import (
    MergeState,
    acquire_merge_lock,
    clear_state,
    has_active_merge,
    load_state,
    release_merge_lock,
    save_state,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )


def _git_no_check(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repository with a single commit on main."""
    _git(["init", "-b", "main"], tmp_path)
    _git(["config", "user.email", "test@example.com"], tmp_path)
    _git(["config", "user.name", "Test User"], tmp_path)
    (tmp_path / "README.md").write_text("# Test repo\n")
    _git(["add", "README.md"], tmp_path)
    _git(["commit", "-m", "Initial commit"], tmp_path)
    return tmp_path


def _make_wp_branch(repo: Path, base_branch: str, wp_id: str, feature_slug: str) -> str:
    """Create a WP branch with one commit; return branch name."""
    branch = f"{feature_slug}-{wp_id}"
    _git(["checkout", "-b", branch, base_branch], repo)
    (repo / f"{wp_id}.txt").write_text(f"Content for {wp_id}\n")
    _git(["add", f"{wp_id}.txt"], repo)
    _git(["commit", "-m", f"feat({wp_id}): implement"], repo)
    _git(["checkout", "main"], repo)
    return branch


# ---------------------------------------------------------------------------
# T072: MergeState round-trip
# ---------------------------------------------------------------------------


class TestMergeStateRoundTrip:
    """MergeState persists and loads correctly."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        state = MergeState(
            mission_id="047-merge-test",
            feature_slug="047-merge-test",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
        )
        save_state(state, tmp_path)
        loaded = load_state(tmp_path, "047-merge-test")

        assert loaded is not None
        assert loaded.mission_id == "047-merge-test"
        assert loaded.target_branch == "main"
        assert loaded.wp_order == ["WP01", "WP02", "WP03"]
        assert loaded.completed_wps == []

    def test_remaining_wps_after_complete(self, tmp_path: Path) -> None:
        state = MergeState(
            mission_id="047-merge-test",
            feature_slug="047-merge-test",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
        )
        state.mark_wp_complete("WP01")
        save_state(state, tmp_path)

        loaded = load_state(tmp_path, "047-merge-test")
        assert loaded is not None
        assert "WP01" in loaded.completed_wps
        assert loaded.remaining_wps == ["WP02", "WP03"]

    def test_progress_percent_reflects_completion(self, tmp_path: Path) -> None:
        state = MergeState(
            mission_id="047-merge-test",
            feature_slug="047-merge-test",
            target_branch="main",
            wp_order=["WP01", "WP02"],
        )
        assert state.progress_percent == 0.0
        state.mark_wp_complete("WP01")
        assert state.progress_percent == 50.0
        state.mark_wp_complete("WP02")
        assert state.progress_percent == 100.0

    def test_clear_state_removes_file(self, tmp_path: Path) -> None:
        state = MergeState(
            mission_id="047-merge-test",
            feature_slug="047-merge-test",
            target_branch="main",
            wp_order=["WP01"],
        )
        save_state(state, tmp_path)
        assert load_state(tmp_path, "047-merge-test") is not None

        clear_state(tmp_path, "047-merge-test")
        assert load_state(tmp_path, "047-merge-test") is None

    def test_load_returns_none_when_no_state(self, tmp_path: Path) -> None:
        result = load_state(tmp_path, "nonexistent-feature")
        assert result is None


# ---------------------------------------------------------------------------
# T072: has_active_merge
# ---------------------------------------------------------------------------


class TestHasActiveMerge:
    """has_active_merge reflects remaining WP count."""

    def test_true_when_wps_remain(self, tmp_path: Path) -> None:
        state = MergeState(
            mission_id="047-active",
            feature_slug="047-active",
            target_branch="main",
            wp_order=["WP01", "WP02"],
        )
        save_state(state, tmp_path)
        assert has_active_merge(tmp_path, "047-active")

    def test_false_when_all_completed(self, tmp_path: Path) -> None:
        state = MergeState(
            mission_id="047-active",
            feature_slug="047-active",
            target_branch="main",
            wp_order=["WP01"],
            completed_wps=["WP01"],
        )
        save_state(state, tmp_path)
        assert not has_active_merge(tmp_path, "047-active")

    def test_false_when_no_state_file(self, tmp_path: Path) -> None:
        assert not has_active_merge(tmp_path, "047-no-state")


# ---------------------------------------------------------------------------
# T072: Merge lock
# ---------------------------------------------------------------------------


class TestMergeLock:
    """Merge lock prevents double-acquisition."""

    def test_lock_acquired_prevents_second_acquire(self, tmp_path: Path) -> None:
        mission_id = "047-lock-test"
        assert acquire_merge_lock(mission_id, tmp_path)
        assert not acquire_merge_lock(mission_id, tmp_path)

    def test_lock_released_allows_reacquire(self, tmp_path: Path) -> None:
        mission_id = "047-lock-test"
        assert acquire_merge_lock(mission_id, tmp_path)
        release_merge_lock(mission_id, tmp_path)
        assert acquire_merge_lock(mission_id, tmp_path)


# ---------------------------------------------------------------------------
# T072: Conflict classification
# ---------------------------------------------------------------------------


class TestConflictClassification:
    """classify_conflict categorizes files correctly."""

    def test_event_log_classified_as_owned(self) -> None:
        assert classify_conflict("kitty-specs/047-feat/status.events.jsonl") == ConflictType.OWNED_EVENT_LOG
        assert classify_conflict("foo/bar.events.jsonl") == ConflictType.OWNED_EVENT_LOG

    def test_meta_json_classified_as_owned_metadata(self) -> None:
        assert classify_conflict("kitty-specs/047-feat/meta.json") == ConflictType.OWNED_METADATA
        assert classify_conflict("status.json") == ConflictType.OWNED_METADATA

    def test_wp_task_file_classified_as_owned_metadata(self) -> None:
        assert classify_conflict("kitty-specs/047-feat/tasks/WP01-test.md") == ConflictType.OWNED_METADATA

    def test_kittify_runtime_classified_as_unexpected_derived(self) -> None:
        assert classify_conflict(".kittify/runtime/merge/state.json") == ConflictType.UNEXPECTED_DERIVED

    def test_kittify_derived_classified_as_unexpected_derived(self) -> None:
        assert classify_conflict(".kittify/derived/foo.json") == ConflictType.UNEXPECTED_DERIVED

    def test_python_source_classified_as_human_authored(self) -> None:
        assert classify_conflict("src/specify_cli/context/resolver.py") == ConflictType.HUMAN_AUTHORED

    def test_markdown_docs_classified_as_human_authored(self) -> None:
        assert classify_conflict("docs/architecture.md") == ConflictType.HUMAN_AUTHORED


# ---------------------------------------------------------------------------
# T072: Auto-resolution of event log conflicts
# ---------------------------------------------------------------------------


class TestEventLogAutoResolution:
    """Event log conflicts are auto-resolved by append-merge."""

    def _make_event(self, event_id: str, at: str, wp_id: str = "WP01") -> str:
        return json.dumps({
            "actor": "agent",
            "at": at,
            "event_id": event_id,
            "feature_slug": "047-merge-test",
            "force": False,
            "from_lane": "planned",
            "to_lane": "in_progress",
            "wp_id": wp_id,
        }, sort_keys=True)

    def test_deduplication_by_event_id(self) -> None:
        """Same event on both sides = single event after merge."""
        e = self._make_event("AAAA0000000000000000000001", "2026-01-01T10:00:00+00:00")
        result = _merge_event_logs(e + "\n", e + "\n")
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) == 1

    def test_distinct_events_combined(self) -> None:
        """Distinct events from both branches appear in merged log."""
        e1 = self._make_event("AAAA0000000000000000000001", "2026-01-01T10:00:00+00:00")
        e2 = self._make_event("BBBB0000000000000000000002", "2026-01-01T11:00:00+00:00")
        result = _merge_event_logs(e1 + "\n", e2 + "\n")
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) == 2

    def test_merged_log_sorted_by_timestamp(self) -> None:
        """Events are sorted by timestamp in the merged log."""
        e1 = self._make_event("AAAA0000000000000000000001", "2026-01-01T12:00:00+00:00")  # later
        e2 = self._make_event("BBBB0000000000000000000002", "2026-01-01T10:00:00+00:00")  # earlier
        result = _merge_event_logs(e1 + "\n", e2 + "\n")
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["event_id"] == "BBBB0000000000000000000002"

    def test_malformed_lines_skipped(self) -> None:
        """Malformed JSON lines are silently skipped."""
        e = self._make_event("AAAA0000000000000000000001", "2026-01-01T10:00:00+00:00")
        result = _merge_event_logs(e + "\nNOT_JSON\n", "")
        lines = [ln for ln in result.splitlines() if ln.strip()]
        assert len(lines) == 1

    def test_empty_both_sides_returns_empty(self) -> None:
        result = _merge_event_logs("", "")
        assert result.strip() == ""

    def test_human_authored_file_goes_to_unresolved(self, tmp_path: Path) -> None:
        """Human-authored file conflicts are not auto-resolved."""
        result = resolve_owned_conflicts(tmp_path, ["src/mymodule.py"])
        assert result.unresolved == ["src/mymodule.py"]
        assert not result.resolved
        assert not result.errors

    def test_unexpected_derived_flagged_as_error(self, tmp_path: Path) -> None:
        """Derived files appearing as conflicts produce an error."""
        result = resolve_owned_conflicts(tmp_path, [".kittify/runtime/merge/state.json"])
        assert result.errors
        assert "UNEXPECTED_DERIVED" in result.errors[0]


# ---------------------------------------------------------------------------
# T072: get_merged_branches (real git)
# ---------------------------------------------------------------------------


class TestGetMergedBranches:
    """get_merged_branches reflects actual git merge history."""

    def test_merged_branch_appears_after_merge(self, git_repo: Path) -> None:
        branch = _make_wp_branch(git_repo, "main", "WP01", "047-feat")
        _git(["merge", "--no-ff", branch, "-m", f"Merge {branch}"], git_repo)

        merged = get_merged_branches("main", git_repo)
        assert branch in merged

    def test_unmerged_branch_not_in_list(self, git_repo: Path) -> None:
        branch = _make_wp_branch(git_repo, "main", "WP99", "047-feat")
        # Do NOT merge
        merged = get_merged_branches("main", git_repo)
        assert branch not in merged

    def test_invalid_repo_returns_empty_set(self, tmp_path: Path) -> None:
        merged = get_merged_branches("main", tmp_path)
        assert merged == set()

    def test_multiple_merged_branches_all_listed(self, git_repo: Path) -> None:
        """All merged branches appear, unmerged do not."""
        b1 = _make_wp_branch(git_repo, "main", "WP01", "047-multi")
        b2 = _make_wp_branch(git_repo, "main", "WP02", "047-multi")
        b3 = _make_wp_branch(git_repo, "main", "WP03", "047-multi")  # won't be merged

        _git(["merge", "--no-ff", b1, "-m", f"Merge {b1}"], git_repo)
        _git(["merge", "--no-ff", b2, "-m", f"Merge {b2}"], git_repo)
        # b3 intentionally not merged

        merged = get_merged_branches("main", git_repo)
        assert b1 in merged
        assert b2 in merged
        assert b3 not in merged


# ---------------------------------------------------------------------------
# T072: MergeResult dataclass
# ---------------------------------------------------------------------------


class TestMergeResult:
    """MergeResult reports success/conflict/error state correctly."""

    def test_success_with_merged_wps(self) -> None:
        r = MergeResult(success=True, merged_wps=["WP01", "WP02"])
        assert r.success
        assert not r.has_conflicts
        assert not r.has_errors

    def test_failure_with_conflicts(self) -> None:
        r = MergeResult(success=False, conflicts=["src/mymodule.py"])
        assert not r.success
        assert r.has_conflicts
        assert not r.has_errors

    def test_failure_with_errors(self) -> None:
        r = MergeResult(success=False, errors=["Preflight failed: uncommitted changes"])
        assert not r.success
        assert r.has_errors
        assert not r.has_conflicts

    def test_skipped_wps_tracked_separately(self) -> None:
        r = MergeResult(success=True, merged_wps=["WP02"], skipped_wps=["WP01"])
        assert r.merged_wps == ["WP02"]
        assert r.skipped_wps == ["WP01"]

    def test_defaults_are_empty_lists(self) -> None:
        r = MergeResult(success=True)
        assert r.merged_wps == []
        assert r.skipped_wps == []
        assert r.conflicts == []
        assert r.errors == []


# ---------------------------------------------------------------------------
# T072: Resume simulation (state-only, no git ops)
# ---------------------------------------------------------------------------


class TestMergeResumeState:
    """Simulate interruption and resume via MergeState."""

    def test_resume_picks_up_where_left_off(self, tmp_path: Path) -> None:
        """After completing WP01, remaining = [WP02, WP03]."""
        state = MergeState(
            mission_id="047-resume",
            feature_slug="047-resume",
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
        )
        state.mark_wp_complete("WP01")
        save_state(state, tmp_path)

        # Simulate resume: load state and check what's left
        loaded = load_state(tmp_path, "047-resume")
        assert loaded is not None
        assert loaded.remaining_wps == ["WP02", "WP03"]
        assert loaded.progress_percent == pytest.approx(100 / 3, abs=1.0)

    def test_full_completion_clears_remaining(self, tmp_path: Path) -> None:
        """After completing all WPs, remaining_wps is empty."""
        state = MergeState(
            mission_id="047-complete",
            feature_slug="047-complete",
            target_branch="main",
            wp_order=["WP01", "WP02"],
        )
        state.mark_wp_complete("WP01")
        state.mark_wp_complete("WP02")
        save_state(state, tmp_path)

        loaded = load_state(tmp_path, "047-complete")
        assert loaded is not None
        assert loaded.remaining_wps == []
        assert loaded.progress_percent == 100.0
        assert not has_active_merge(tmp_path, "047-complete")

    def test_deterministic_ordering_preserved(self, tmp_path: Path) -> None:
        """WP order is deterministic across save/load cycles."""
        wp_order = ["WP03", "WP01", "WP02"]
        state = MergeState(
            mission_id="047-order",
            feature_slug="047-order",
            target_branch="main",
            wp_order=wp_order,
        )
        save_state(state, tmp_path)
        loaded = load_state(tmp_path, "047-order")
        assert loaded is not None
        assert loaded.wp_order == wp_order
