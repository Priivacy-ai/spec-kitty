"""Unit tests for the WP06 (#2058) ``tasks_parsing_validation`` seam.

Covers the issue-matrix approval-blocker logic, the latest review-cycle verdict
extraction, the self-review fallback guard, and — critically — each of the
behaviour-preserving sub-split validators that compose
``_validate_ready_for_review`` (NFR-001). The sub-validators are exercised
directly with injected collaborators so their branches are tested in isolation,
not only through the broad command-level integration tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.agent.tasks_parsing_validation import (
    _VALID_VERDICTS,
    _apply_review_status_flags,
    _check_branch_currency,
    _check_implementation_commit_present,
    _check_kitty_specs_contamination,
    _check_uncommitted_worktree_changes,
    _check_worktree_health,
    _get_latest_review_cycle_verdict,
    _issue_matrix_approval_blocker,
    _self_review_fallback_option_error,
    _validate_research_artifacts,
    _validate_worktree_state,
)
from specify_cli.status.models import Lane, StatusEvent

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_issue_matrix(
    feature_dir: Path,
    verdict: str,
    evidence_ref: str = "tests/test_demo.py",
    issue: str = "#1582",
) -> None:
    (feature_dir / "issue-matrix.md").write_text(
        "\n".join(
            [
                "| issue | verdict | evidence_ref |",
                "| --- | --- | --- |",
                f"| {issue} | {verdict} | {evidence_ref} |",
            ]
        ),
        encoding="utf-8",
    )


def _write_review_cycle(wp_dir: Path, cycle_n: int, verdict: str) -> Path:
    wp_dir.mkdir(parents=True, exist_ok=True)
    artifact = wp_dir / f"review-cycle-{cycle_n}.md"
    artifact.write_text(
        f"---\n"
        f"cycle_number: {cycle_n}\n"
        f"verdict: {verdict}\n"
        f"wp_id: WP01\n"
        f"---\n\nReview body.\n",
        encoding="utf-8",
    )
    return artifact


def _make_subproc(returncode: int = 0, stdout: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


@dataclass
class _FakeWorkspace:
    """Minimal stand-in: the validator only reads these two attributes."""

    resolution_kind: str
    worktree_path: Path


# ---------------------------------------------------------------------------
# Self-review fallback guard
# ---------------------------------------------------------------------------


def test_self_review_fallback_guard_full_matrix() -> None:
    assert _self_review_fallback_option_error(
        enabled=False, target_lane="approved", force=False,
        intended_reviewer="codex", failure_reason=None,
    ) == "--intended-reviewer/--reviewer-failure-reason require --self-review-fallback."

    assert _self_review_fallback_option_error(
        enabled=False, target_lane="approved", force=False,
        intended_reviewer=None, failure_reason=None,
    ) is None

    assert _self_review_fallback_option_error(
        enabled=True, target_lane="for_review", force=True,
        intended_reviewer="codex", failure_reason="exit 1",
    ) == "--self-review-fallback is only valid when approving or marking done."

    assert _self_review_fallback_option_error(
        enabled=True, target_lane="approved", force=False,
        intended_reviewer="codex", failure_reason="exit 1",
    ) == "--self-review-fallback requires --force so force_count records the independence override."

    assert _self_review_fallback_option_error(
        enabled=True, target_lane="approved", force=True,
        intended_reviewer=" ", failure_reason="exit 1",
    ) == "--self-review-fallback requires --intended-reviewer <agent>."

    assert _self_review_fallback_option_error(
        enabled=True, target_lane="approved", force=True,
        intended_reviewer="codex", failure_reason=" ",
    ) == "--self-review-fallback requires --reviewer-failure-reason <reason>."

    assert _self_review_fallback_option_error(
        enabled=True, target_lane="done", force=True,
        intended_reviewer="codex", failure_reason="exit 1",
    ) is None


# ---------------------------------------------------------------------------
# Issue-matrix approval blocker
# ---------------------------------------------------------------------------


def test_issue_matrix_approval_blocker_requires_resolved_verdicts(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("Fix Priivacy-ai/spec-kitty issue #1582.\n", encoding="utf-8")

    blocker = _issue_matrix_approval_blocker(feature_dir)
    assert blocker is not None
    assert "issue-matrix.md is required" in blocker
    assert "#1582" in blocker

    _write_issue_matrix(feature_dir, "unknown")
    blocker = _issue_matrix_approval_blocker(feature_dir)
    assert blocker is not None
    assert "Unknown: #1582" in blocker

    _write_issue_matrix(feature_dir, "fixed", issue="#1111")
    blocker = _issue_matrix_approval_blocker(feature_dir)
    assert blocker is not None
    assert "Missing rows: #1582" in blocker

    _write_issue_matrix(feature_dir, "fixed")
    assert _issue_matrix_approval_blocker(feature_dir) is None


def test_issue_matrix_in_mission_passes_approved_blocks_done(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("Fix Priivacy-ai/spec-kitty issue #1582.\n", encoding="utf-8")
    _write_issue_matrix(feature_dir, "in-mission", evidence_ref="WP14 (this mission)")

    assert _issue_matrix_approval_blocker(feature_dir, target_lane=Lane.APPROVED) is None
    assert _issue_matrix_approval_blocker(feature_dir) is None

    blocker = _issue_matrix_approval_blocker(feature_dir, target_lane=Lane.DONE)
    assert blocker is not None
    assert "in-mission" in blocker
    assert "#1582" in blocker

    _write_issue_matrix(feature_dir, "fixed", evidence_ref="commit abc123")
    assert _issue_matrix_approval_blocker(feature_dir, target_lane=Lane.DONE) is None


def test_issue_matrix_approval_blocker_no_spec_returns_none(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "demo"
    feature_dir.mkdir(parents=True)
    # No spec.md at all → no referenced issues → nothing to block.
    assert _issue_matrix_approval_blocker(feature_dir) is None


def test_issue_matrix_approval_uses_primary_verdicts_when_coord_copy_stale(tmp_path: Path) -> None:
    coord_dir = tmp_path / "coord" / "kitty-specs" / "demo"
    primary_dir = tmp_path / "primary" / "kitty-specs" / "demo"
    coord_dir.mkdir(parents=True)
    primary_dir.mkdir(parents=True)
    spec_text = "Fix Priivacy-ai/spec-kitty issue #1582.\n"
    (coord_dir / "spec.md").write_text(spec_text, encoding="utf-8")
    (primary_dir / "spec.md").write_text(spec_text, encoding="utf-8")
    _write_issue_matrix(coord_dir, "unknown")
    _write_issue_matrix(primary_dir, "fixed")

    assert _issue_matrix_approval_blocker(coord_dir, primary_feature_dir=primary_dir) is None
    stale_blocker = _issue_matrix_approval_blocker(coord_dir)
    assert stale_blocker is not None
    assert "Unknown: #1582" in stale_blocker


# ---------------------------------------------------------------------------
# Review-cycle verdict extraction + status flags
# ---------------------------------------------------------------------------


def test_valid_verdicts_constant() -> None:
    assert set(_VALID_VERDICTS) == {
        "approved",
        "approved_after_orchestrator_fix",
        "arbiter_override",
        "rejected",
    }


def test_get_latest_review_cycle_verdict_no_artifacts(tmp_path: Path) -> None:
    assert _get_latest_review_cycle_verdict(tmp_path) == (None, None)


def test_get_latest_review_cycle_verdict_picks_highest(tmp_path: Path) -> None:
    _write_review_cycle(tmp_path, 1, "rejected")
    cycle2 = _write_review_cycle(tmp_path, 2, "approved")
    verdict, artifact = _get_latest_review_cycle_verdict(tmp_path)
    assert verdict == "approved"
    assert artifact == cycle2


def test_get_latest_review_cycle_verdict_unknown_warns(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    _write_review_cycle(tmp_path, 1, "super_approved")
    with caplog.at_level("WARNING"):
        verdict, _ = _get_latest_review_cycle_verdict(tmp_path)
    assert verdict == "super_approved"
    assert any("unrecognized verdict" in r.message for r in caplog.records)


def test_get_latest_review_cycle_verdict_missing_frontmatter(tmp_path: Path) -> None:
    artifact = tmp_path / "review-cycle-1.md"
    artifact.write_text("no frontmatter here\n", encoding="utf-8")
    assert _get_latest_review_cycle_verdict(tmp_path) == (None, artifact)


def test_apply_review_status_flags_stale_and_stalled(tmp_path: Path) -> None:
    # Approved WP whose latest review-cycle verdict is rejected → stale flag.
    wp_dir = tmp_path / "WP01"
    _write_review_cycle(wp_dir, 1, "rejected")
    approved_wp: dict[str, object] = {"id": "WP01", "lane": Lane.APPROVED, "file": "WP01.md"}

    # In-review WP with an old event → stalled flag.
    in_review_wp: dict[str, object] = {"id": "WP02", "lane": Lane.IN_REVIEW}
    old_event = StatusEvent(
        event_id="01HXYZ",
        mission_slug="demo",
        wp_id="WP02",
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.IN_REVIEW,
        at="2000-01-01T00:00:00+00:00",
        actor="claude",
        force=False,
        execution_mode="worktree",
    )

    stale, stalled = _apply_review_status_flags(
        [approved_wp, in_review_wp],
        tasks_dir=tmp_path,
        events=[old_event],
        stall_threshold_minutes=30,
    )

    assert stale and stale[0]["wp_id"] == "WP01"
    assert approved_wp["_stale_verdict"] is True
    assert stalled and stalled[0]["wp_id"] == "WP02"
    assert "STALLED" in str(in_review_wp["_stall_label"])


# ---------------------------------------------------------------------------
# Sub-split validator: _validate_research_artifacts
# ---------------------------------------------------------------------------


def test_validate_research_artifacts_clean_returns_none(tmp_path: Path) -> None:
    console = MagicMock()
    with patch("subprocess.run", return_value=_make_subproc(0, "")):
        result = _validate_research_artifacts(
            main_repo_root=tmp_path,
            feature_dir=tmp_path / "kitty-specs" / "demo",
            mission_slug="demo",
            wp_id="WP01",
            mission_type="research",
            target_lane="for_review",
            console=console,
        )
    assert result is None


def test_validate_research_artifacts_blocks_research_commit_format(tmp_path: Path) -> None:
    console = MagicMock()
    porcelain = " M kitty-specs/demo/data-model.md\n"
    with (
        patch("subprocess.run", return_value=_make_subproc(0, porcelain)),
        patch(
            "specify_cli.review.dirty_classifier.classify_dirty_paths",
            return_value=(["kitty-specs/demo/data-model.md"], []),
        ),
    ):
        guidance = _validate_research_artifacts(
            main_repo_root=tmp_path,
            feature_dir=tmp_path / "kitty-specs" / "demo",
            mission_slug="demo",
            wp_id="WP01",
            mission_type="research",
            target_lane="for_review",
            console=console,
        )
    assert guidance is not None
    text = "\n".join(guidance)
    assert "Blocking: 1 uncommitted file(s) owned by WP01" in text
    assert 'research(WP01)' in text
    assert "move-task WP01 --to for_review" in text


def test_validate_research_artifacts_benign_only_passes_with_note(tmp_path: Path) -> None:
    console = MagicMock()
    porcelain = " M kitty-specs/demo/other-wp.md\n"
    with (
        patch("subprocess.run", return_value=_make_subproc(0, porcelain)),
        patch(
            "specify_cli.review.dirty_classifier.classify_dirty_paths",
            return_value=([], ["kitty-specs/demo/other-wp.md"]),
        ),
    ):
        result = _validate_research_artifacts(
            main_repo_root=tmp_path,
            feature_dir=tmp_path / "kitty-specs" / "demo",
            mission_slug="demo",
            wp_id="WP01",
            mission_type="software-dev",
            target_lane="for_review",
            console=console,
        )
    assert result is None
    console.print.assert_called_once()
    assert "not owned by WP01" in console.print.call_args.args[0]


# ---------------------------------------------------------------------------
# Sub-split validator: _check_worktree_health
# ---------------------------------------------------------------------------


def test_check_worktree_health_husk_blocks(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()  # no .git marker → husk
    guidance = _check_worktree_health(worktree, "WP01", "for_review")
    assert guidance is not None
    assert guidance  # populated husk message


def test_check_worktree_health_detached_head(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: ../fake\n", encoding="utf-8")
    with (
        patch(
            "specify_cli.workspace.context.verify_workspace_toplevel",
            return_value=None,
        ),
        patch("specify_cli.core.git_ops.get_current_branch", return_value=None),
    ):
        guidance = _check_worktree_health(worktree, "WP01", "approved")
    assert guidance is not None
    assert guidance[0] == "Detached HEAD detected in worktree!"
    assert "move-task WP01 --to approved" in "\n".join(guidance)


def test_check_worktree_health_in_progress_merge(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: ../fake\n", encoding="utf-8")

    def _fake_run(cmd: list[str], **_kw: object) -> MagicMock:
        # MERGE_HEAD verify → success (rc 0); others → fail.
        if cmd[-1] == "MERGE_HEAD":
            return _make_subproc(0, "")
        return _make_subproc(1, "")

    with (
        patch(
            "specify_cli.workspace.context.verify_workspace_toplevel",
            return_value=None,
        ),
        patch("specify_cli.core.git_ops.get_current_branch", return_value="lane-a"),
        patch("subprocess.run", side_effect=_fake_run),
    ):
        guidance = _check_worktree_health(worktree, "WP01", "for_review")
    assert guidance is not None
    assert guidance[0] == "In-progress git operation detected in worktree!"
    assert "merge" in "\n".join(guidance)


def test_check_worktree_health_clean_returns_none(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: ../fake\n", encoding="utf-8")
    with (
        patch(
            "specify_cli.workspace.context.verify_workspace_toplevel",
            return_value=None,
        ),
        patch("specify_cli.core.git_ops.get_current_branch", return_value="lane-a"),
        patch("subprocess.run", return_value=_make_subproc(1, "")),
    ):
        assert _check_worktree_health(worktree, "WP01", "for_review") is None


# ---------------------------------------------------------------------------
# Sub-split validator: _check_branch_currency
# ---------------------------------------------------------------------------


def test_check_branch_currency_behind_blocks(tmp_path: Path) -> None:
    with patch("subprocess.run", return_value=_make_subproc(0, "3\n")):
        guidance = _check_branch_currency(
            worktree_path=tmp_path,
            check_branch="main",
            mission_slug="demo",
            wp_id="WP01",
            target_lane="for_review",
            behind_commits_touch_only_planning_artifacts=lambda *_a: False,
        )
    assert guidance is not None
    assert "behind main by 3 commit(s)" in "\n".join(guidance)


def test_check_branch_currency_behind_but_planning_only_passes(tmp_path: Path) -> None:
    with patch("subprocess.run", return_value=_make_subproc(0, "3\n")):
        result = _check_branch_currency(
            worktree_path=tmp_path,
            check_branch="main",
            mission_slug="demo",
            wp_id="WP01",
            target_lane="for_review",
            behind_commits_touch_only_planning_artifacts=lambda *_a: True,
        )
    assert result is None


def test_check_branch_currency_up_to_date_passes(tmp_path: Path) -> None:
    with patch("subprocess.run", return_value=_make_subproc(0, "0\n")):
        result = _check_branch_currency(
            worktree_path=tmp_path,
            check_branch="main",
            mission_slug="demo",
            wp_id="WP01",
            target_lane="for_review",
            behind_commits_touch_only_planning_artifacts=lambda *_a: False,
        )
    assert result is None


# ---------------------------------------------------------------------------
# Sub-split validator: _check_uncommitted_worktree_changes
# ---------------------------------------------------------------------------


def test_check_uncommitted_worktree_changes_staged_only(tmp_path: Path) -> None:
    with patch("subprocess.run", return_value=_make_subproc(0, "M  src/foo.py\n")):
        guidance = _check_uncommitted_worktree_changes(
            worktree_path=tmp_path,
            wp_id="WP01",
            target_lane="for_review",
            filter_runtime_state_paths=lambda s: s,
        )
    assert guidance is not None
    assert guidance[0] == "Staged but uncommitted changes in worktree!"


def test_check_uncommitted_worktree_changes_staged_and_unstaged(tmp_path: Path) -> None:
    with patch("subprocess.run", return_value=_make_subproc(0, "MM src/foo.py\n")):
        guidance = _check_uncommitted_worktree_changes(
            worktree_path=tmp_path,
            wp_id="WP01",
            target_lane="for_review",
            filter_runtime_state_paths=lambda s: s,
        )
    assert guidance is not None
    assert guidance[0] == "Staged and unstaged changes in worktree!"


def test_check_uncommitted_worktree_changes_untracked(tmp_path: Path) -> None:
    with patch("subprocess.run", return_value=_make_subproc(0, "?? new.py\n")):
        guidance = _check_uncommitted_worktree_changes(
            worktree_path=tmp_path,
            wp_id="WP01",
            target_lane="for_review",
            filter_runtime_state_paths=lambda s: s,
        )
    assert guidance is not None
    assert guidance[0] == "Uncommitted implementation changes in worktree!"


def test_check_uncommitted_worktree_changes_filtered_clean(tmp_path: Path) -> None:
    # filter strips everything (runtime-state only) → no block.
    with patch("subprocess.run", return_value=_make_subproc(0, " M .spec-kitty/lock\n")):
        result = _check_uncommitted_worktree_changes(
            worktree_path=tmp_path,
            wp_id="WP01",
            target_lane="for_review",
            filter_runtime_state_paths=lambda _s: "",
        )
    assert result is None


# ---------------------------------------------------------------------------
# Sub-split validator: _check_implementation_commit_present
# ---------------------------------------------------------------------------


def test_check_implementation_commit_present_missing_blocks(tmp_path: Path) -> None:
    with patch(
        "specify_cli.cli.commands.agent.tasks_parsing_validation.lane_has_commit_beyond_base",
        return_value=False,
    ):
        guidance = _check_implementation_commit_present(
            worktree_path=tmp_path,
            check_branch="main",
            wp_id="WP01",
            target_lane="for_review",
        )
    assert guidance is not None
    assert guidance[0] == "No implementation commits on lane branch!"


def test_check_implementation_commit_present_ok(tmp_path: Path) -> None:
    with patch(
        "specify_cli.cli.commands.agent.tasks_parsing_validation.lane_has_commit_beyond_base",
        return_value=True,
    ):
        assert _check_implementation_commit_present(
            worktree_path=tmp_path,
            check_branch="main",
            wp_id="WP01",
            target_lane="for_review",
        ) is None


# ---------------------------------------------------------------------------
# Sub-split validator: _check_kitty_specs_contamination
# ---------------------------------------------------------------------------


def test_check_kitty_specs_contamination_blocks_with_planning_branch(tmp_path: Path) -> None:
    with patch(
        "specify_cli.mission_metadata.load_meta",
        return_value={"planning_base_branch": "kitty/plan"},
    ):
        guidance = _check_kitty_specs_contamination(
            worktree_path=tmp_path,
            check_branch="main",
            feature_dir=tmp_path,
            wp_id="WP01",
            target_lane="for_review",
            list_wp_branch_specs_changes_for_guard=lambda **_k: ["kitty-specs/demo/spec.md"],
        )
    assert guidance is not None
    text = "\n".join(guidance)
    assert "Committed kitty-specs files on this lane branch:" in text
    assert "Planning artifacts must live on: kitty/plan" in text
    assert "git show kitty/plan:kitty-specs/demo/spec.md" in text


def test_check_kitty_specs_contamination_unknown_planning_branch(tmp_path: Path) -> None:
    with patch("specify_cli.mission_metadata.load_meta", return_value=None):
        guidance = _check_kitty_specs_contamination(
            worktree_path=tmp_path,
            check_branch="main",
            feature_dir=tmp_path,
            wp_id="WP01",
            target_lane="for_review",
            list_wp_branch_specs_changes_for_guard=lambda **_k: ["kitty-specs/demo/spec.md"],
        )
    assert guidance is not None
    assert "planning branch unknown" in "\n".join(guidance)


def test_check_kitty_specs_contamination_clean_returns_none(tmp_path: Path) -> None:
    result = _check_kitty_specs_contamination(
        worktree_path=tmp_path,
        check_branch="main",
        feature_dir=tmp_path,
        wp_id="WP01",
        target_lane="for_review",
        list_wp_branch_specs_changes_for_guard=lambda **_k: [],
    )
    assert result is None


# ---------------------------------------------------------------------------
# Orchestrator: _validate_worktree_state composition
# ---------------------------------------------------------------------------


def test_validate_worktree_state_repo_root_short_circuits(tmp_path: Path) -> None:
    ws = _FakeWorkspace(resolution_kind="repo_root", worktree_path=tmp_path)
    result = _validate_worktree_state(
        repo_root=tmp_path,
        main_repo_root=tmp_path,
        feature_dir=tmp_path,
        mission_slug="demo",
        wp_id="WP01",
        target_lane="for_review",
        resolve_workspace_for_wp=lambda *_a: ws,
        get_feature_target_branch=lambda *_a: "main",
        review_currency_check_branch=lambda **_k: "main",
        behind_commits_touch_only_planning_artifacts=lambda *_a: False,
        filter_runtime_state_paths=lambda s: s,
        list_wp_branch_specs_changes_for_guard=lambda **_k: [],
    )
    assert result == (True, [])


def test_validate_worktree_state_missing_worktree_falls_through(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    ws = _FakeWorkspace(resolution_kind="lane_workspace", worktree_path=missing)
    result = _validate_worktree_state(
        repo_root=tmp_path,
        main_repo_root=tmp_path,
        feature_dir=tmp_path,
        mission_slug="demo",
        wp_id="WP01",
        target_lane="for_review",
        resolve_workspace_for_wp=lambda *_a: ws,
        get_feature_target_branch=lambda *_a: "main",
        review_currency_check_branch=lambda **_k: "main",
        behind_commits_touch_only_planning_artifacts=lambda *_a: False,
        filter_runtime_state_paths=lambda s: s,
        list_wp_branch_specs_changes_for_guard=lambda **_k: [],
    )
    assert result is None
