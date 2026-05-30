"""Scope: merge done recording unit tests — no real git or subprocesses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
import typer

from specify_cli.cli.commands.merge import (
    BaselineMergeCommitError,
    _assert_baseline_merge_commit_on_target,
    _assert_merged_wps_reached_done,
    _mark_wp_merged_done,
    _record_baseline_merge_commit,
)

pytestmark = pytest.mark.fast


def _write_wp(path: Path, *, review_status: str = "", reviewed_by: str = "", agent: str = "") -> None:
    """Write a minimal WP file. Lane is tracked via event log, not frontmatter."""
    lines = [
        "---",
        'work_package_id: "WP01"',
        'title: "Test WP"',
        "dependencies: []",
        f'review_status: "{review_status}"',
        f'reviewed_by: "{reviewed_by}"',
        f'agent: "{agent}"',
        "---",
        "# WP01",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def test_mark_wp_merged_done_emits_done_transition(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(tasks_dir / "WP01-test.md", review_status="approved", reviewed_by="reviewer-1")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", emit_mock)
    # Lane is event-log-driven; seed it as "approved" via lane_reader
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "approved",
    )

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["to_lane"] == "done"
    assert kwargs["actor"] == "merge"
    assert kwargs["reason"] == "Merged WP01 into main"
    assert kwargs["evidence"]["review"]["reviewer"] == "reviewer-1"


def test_mark_wp_merged_done_approved_without_review_metadata_synthesizes_evidence(tmp_path: Path, monkeypatch) -> None:
    """WPs in approved lane without review_status/reviewed_by should still transition to done."""
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(tasks_dir / "WP01-test.md")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", emit_mock)
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "approved",
    )

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["to_lane"] == "done"
    assert kwargs["actor"] == "merge"
    assert kwargs["evidence"]["review"]["verdict"] == "approved"
    assert kwargs["evidence"]["review"]["reference"] == "lane-approved:WP01"


def test_mark_wp_merged_done_for_review_without_metadata_skips(tmp_path: Path, monkeypatch) -> None:
    """WPs in for_review lane without approval metadata should NOT transition to done."""
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(tasks_dir / "WP01-test.md")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", emit_mock)
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "for_review",
    )

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    emit_mock.assert_not_called()


def test_mark_wp_merged_done_records_approved_before_done_for_legacy_for_review(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(tasks_dir / "WP01-test.md", review_status="approved", reviewed_by="reviewer-1")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", emit_mock)
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "for_review",
    )

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    assert emit_mock.call_count == 2
    first_kwargs = emit_mock.call_args_list[0].kwargs
    second_kwargs = emit_mock.call_args_list[1].kwargs
    assert first_kwargs["to_lane"] == "approved"
    assert second_kwargs["to_lane"] == "done"


@pytest.mark.parametrize("lane_name", ["planned", "claimed", "in_progress"])
def test_mark_wp_merged_done_recovers_reviewed_wps_from_pre_review_lanes(
    tmp_path: Path,
    monkeypatch,
    lane_name: str,
) -> None:
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(tasks_dir / "WP01-test.md", review_status="approved", reviewed_by="reviewer-1")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", emit_mock)
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: lane_name,
    )

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    assert emit_mock.call_count == 2
    assert emit_mock.call_args_list[0].kwargs["to_lane"] == "approved"
    assert emit_mock.call_args_list[1].kwargs["to_lane"] == "done"


def test_mark_wp_merged_done_synthesized_evidence_uses_typed_agent(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """When synthesizing evidence for approved WP, the agent field should come from typed metadata."""
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(tasks_dir / "WP01-test.md", agent="gemini-cli")

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.status.emit.emit_status_transition", emit_mock)
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "approved",
    )

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["evidence"]["review"]["reviewer"] == "gemini-cli"


def test_mark_wp_merged_done_uses_typed_frontmatter(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """Verify _mark_wp_merged_done uses read_wp_frontmatter (typed) not read_frontmatter (raw dict)."""
    import specify_cli.cli.commands.merge as merge_mod

    # The old read_frontmatter import should not exist on the module
    assert not hasattr(merge_mod, "read_frontmatter"), "merge module still imports read_frontmatter; should use read_wp_frontmatter"
    # The new typed import must be present
    assert hasattr(merge_mod, "read_wp_frontmatter"), "merge module must import read_wp_frontmatter"


def test_assert_merged_wps_reached_done_allows_done_snapshot(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    feature_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda *_a, **_kw: "done",
    )

    _assert_merged_wps_reached_done(tmp_path, "021-test", ["WP01", "WP02"])


def test_assert_merged_wps_reached_done_fails_when_wp_not_done(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    feature_dir.mkdir(parents=True)

    lanes = {"WP01": "done", "WP02": "planned"}
    monkeypatch.setattr(
        "specify_cli.status.lane_reader.get_wp_lane",
        lambda _feature_dir, wp_id: lanes[wp_id],
    )

    with pytest.raises(typer.Exit):
        _assert_merged_wps_reached_done(tmp_path, "021-test", ["WP01", "WP02"])


# ---------------------------------------------------------------------------
# baseline_merge_commit invariants (Finding 5): modern lane missions must
# land baseline_merge_commit on the target branch or the merge fails loudly.
# ---------------------------------------------------------------------------


_MODERN_MISSION_ID = "01KTESTMISSIONID00000000000"


def _write_meta(feature_dir: Path, mission_slug: str, **overrides: object) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "created_at": "2026-04-07T00:00:00+00:00",
        "friendly_name": mission_slug.replace("-", " "),
        "mission_id": _MODERN_MISSION_ID,
        "mission_number": None,
        "mission_slug": mission_slug,
        "mission_type": "software-dev",
        "slug": mission_slug,
        "target_branch": "main",
    }
    meta.update(overrides)
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_record_baseline_merge_commit_modern_mission_missing_meta_raises(tmp_path: Path) -> None:
    """A modern lane mission with no meta.json is a HARD failure (Finding 5 (b))."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    feature_dir.mkdir(parents=True)
    # No meta.json on disk.

    with pytest.raises(BaselineMergeCommitError):
        _record_baseline_merge_commit(
            feature_dir,
            "base123",
            mission_id=_MODERN_MISSION_ID,
        )


def test_record_baseline_merge_commit_modern_mission_empty_baseline_raises(tmp_path: Path) -> None:
    """A modern lane mission with an empty captured baseline is a HARD failure."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    _write_meta(feature_dir, "021-test", baseline_merge_commit=None)

    with pytest.raises(BaselineMergeCommitError):
        _record_baseline_merge_commit(
            feature_dir,
            "   ",
            mission_id=_MODERN_MISSION_ID,
        )


def test_record_baseline_merge_commit_modern_mission_invalid_meta_raises(tmp_path: Path) -> None:
    """A modern lane mission with corrupt meta.json is a HARD failure."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text("{not valid json", encoding="utf-8")

    with pytest.raises(BaselineMergeCommitError):
        _record_baseline_merge_commit(
            feature_dir,
            "base123",
            mission_id=_MODERN_MISSION_ID,
        )


def test_record_baseline_merge_commit_legacy_missing_meta_soft_returns_none(tmp_path: Path) -> None:
    """A legacy mission (no mission_id) preserves the soft skip behavior."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    feature_dir.mkdir(parents=True)
    # No meta.json, no mission_id → legacy soft path returns None, no raise.

    result = _record_baseline_merge_commit(feature_dir, "base123", mission_id=None)

    assert result is None


def test_record_baseline_merge_commit_modern_mission_fills_field(tmp_path: Path) -> None:
    """A modern lane mission with valid meta records baseline and returns the path."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    _write_meta(feature_dir, "021-test", baseline_merge_commit=None)

    result = _record_baseline_merge_commit(
        feature_dir,
        "base123",
        mission_id=_MODERN_MISSION_ID,
    )

    assert result == feature_dir / "meta.json"
    data = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert data["baseline_merge_commit"] == "base123"


def test_assert_baseline_on_target_passes_when_committed_meta_matches(tmp_path: Path) -> None:
    """Finding 5 (a)/(c): target meta.json carrying the matching baseline passes."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    _write_meta(feature_dir, "021-test")
    committed_meta = json.dumps({"baseline_merge_commit": "base123"})

    with patch(
        "specify_cli.cli.commands.merge.run_command",
        return_value=(0, committed_meta, ""),
    ):
        # Must not raise.
        _assert_baseline_merge_commit_on_target(
            tmp_path,
            "021-test",
            "main",
            "base123",
            mission_id=_MODERN_MISSION_ID,
        )


def test_assert_baseline_on_target_raises_when_baseline_absent(tmp_path: Path) -> None:
    """Finding 5 (c): target meta.json lacking baseline_merge_commit fails loudly."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    _write_meta(feature_dir, "021-test")
    committed_meta = json.dumps({"mission_slug": "021-test"})  # no baseline_merge_commit

    with patch(
        "specify_cli.cli.commands.merge.run_command",
        return_value=(0, committed_meta, ""),
    ), pytest.raises(BaselineMergeCommitError):
        _assert_baseline_merge_commit_on_target(
            tmp_path,
            "021-test",
            "main",
            "base123",
            mission_id=_MODERN_MISSION_ID,
        )


def test_assert_baseline_on_target_raises_when_baseline_mismatches(tmp_path: Path) -> None:
    """Target meta.json carrying a DIFFERENT baseline fails loudly."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    _write_meta(feature_dir, "021-test")
    committed_meta = json.dumps({"baseline_merge_commit": "other999"})

    with patch(
        "specify_cli.cli.commands.merge.run_command",
        return_value=(0, committed_meta, ""),
    ), pytest.raises(BaselineMergeCommitError):
        _assert_baseline_merge_commit_on_target(
            tmp_path,
            "021-test",
            "main",
            "base123",
            mission_id=_MODERN_MISSION_ID,
        )


def test_assert_baseline_on_target_raises_when_git_show_fails(tmp_path: Path) -> None:
    """A failed `git show <target>:meta.json` (e.g. path absent) fails loudly."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    _write_meta(feature_dir, "021-test")

    with patch(
        "specify_cli.cli.commands.merge.run_command",
        return_value=(128, "", "fatal: path does not exist"),
    ), pytest.raises(BaselineMergeCommitError):
        _assert_baseline_merge_commit_on_target(
            tmp_path,
            "021-test",
            "main",
            "base123",
            mission_id=_MODERN_MISSION_ID,
        )


def test_assert_baseline_on_target_skips_legacy_mission(tmp_path: Path) -> None:
    """Legacy missions (no mission_id) skip the target baseline assertion entirely."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    feature_dir.mkdir(parents=True)

    # run_command would raise if called — assert it is never invoked for legacy.
    def _boom(*_a: Any, **_kw: Any):
        raise AssertionError("run_command must not be called for legacy missions")

    with patch("specify_cli.cli.commands.merge.run_command", side_effect=_boom):
        _assert_baseline_merge_commit_on_target(
            tmp_path,
            "021-test",
            "main",
            "base123",
            mission_id=None,
        )


def test_assert_baseline_on_target_resume_uses_recorded_baseline_not_live_head(
    tmp_path: Path,
) -> None:
    """Resume safety (Finding 5): the invariant compares the COMMITTED target
    baseline against the RECORDED working-meta value, not a freshly re-derived
    target HEAD.

    On ``spec-kitty merge --resume`` a prior run already landed the
    mission/bookkeeping commits, so the live target HEAD (the value
    ``expected_baseline`` is captured from on each invocation) has advanced past
    the original baseline. Comparing the committed value against that advanced
    HEAD would spuriously fail an otherwise-correct resume. Passing
    ``feature_dir`` makes the assertion read the originally-recorded baseline,
    which is stable across resume.
    """
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    # Run 1 recorded the original pre-merge baseline into the working meta and
    # committed the same value to the target branch.
    _write_meta(feature_dir, "021-test", baseline_merge_commit="original_sha_a")
    committed_meta = json.dumps({"baseline_merge_commit": "original_sha_a"})

    with patch(
        "specify_cli.cli.commands.merge.run_command",
        return_value=(0, committed_meta, ""),
    ):
        # expected_baseline is the RE-DERIVED, now-advanced target HEAD on
        # resume; it must be ignored in favor of the recorded value.
        _assert_baseline_merge_commit_on_target(
            tmp_path,
            "021-test",
            "main",
            "advanced_sha_b_from_live_head",
            feature_dir=feature_dir,
            mission_id=_MODERN_MISSION_ID,
        )


def test_assert_baseline_on_target_raises_when_committed_differs_from_recorded(
    tmp_path: Path,
) -> None:
    """A genuine drift (committed target baseline != recorded value) still fails
    loudly even when ``feature_dir`` supplies the recorded baseline."""
    feature_dir = tmp_path / "kitty-specs" / "021-test"
    _write_meta(feature_dir, "021-test", baseline_merge_commit="recorded_sha_a")
    committed_meta = json.dumps({"baseline_merge_commit": "drifted_sha_c"})

    with patch(
        "specify_cli.cli.commands.merge.run_command",
        return_value=(0, committed_meta, ""),
    ), pytest.raises(BaselineMergeCommitError):
        _assert_baseline_merge_commit_on_target(
            tmp_path,
            "021-test",
            "main",
            "recorded_sha_a",
            feature_dir=feature_dir,
            mission_id=_MODERN_MISSION_ID,
        )
