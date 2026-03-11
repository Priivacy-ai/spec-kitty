from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from specify_cli.cli.commands.merge import _mark_wp_merged_done


def _write_wp(path: Path, *, lane: str, review_status: str, reviewed_by: str) -> None:
    path.write_text(
        "---\n"
        'work_package_id: "WP01"\n'
        f'lane: "{lane}"\n'
        f'review_status: "{review_status}"\n'
        f'reviewed_by: "{reviewed_by}"\n'
        "---\n"
        "# WP01\n",
        encoding="utf-8",
    )


def test_mark_wp_merged_done_emits_done_transition(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(
        tasks_dir / "WP01-test.md",
        lane="approved",
        review_status="approved",
        reviewed_by="reviewer-1",
    )

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.cli.commands.merge.emit_status_transition", emit_mock)

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["to_lane"] == "done"
    assert kwargs["actor"] == "merge"
    assert kwargs["reason"] == "Merged WP01 into main"
    assert kwargs["evidence"]["review"]["reviewer"] == "reviewer-1"


def test_mark_wp_merged_done_approved_without_review_metadata_synthesizes_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    """WPs in approved lane without review_status/reviewed_by should still transition to done."""
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(
        tasks_dir / "WP01-test.md",
        lane="approved",
        review_status="",
        reviewed_by="",
    )

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.cli.commands.merge.emit_status_transition", emit_mock)

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    assert kwargs["to_lane"] == "done"
    assert kwargs["actor"] == "merge"
    assert kwargs["evidence"]["review"]["verdict"] == "approved"
    assert kwargs["evidence"]["review"]["reference"] == "lane-approved:WP01"


def test_mark_wp_merged_done_for_review_without_metadata_skips(
    tmp_path: Path, monkeypatch
) -> None:
    """WPs in for_review lane without approval metadata should NOT transition to done."""
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "021-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    _write_wp(
        tasks_dir / "WP01-test.md",
        lane="for_review",
        review_status="",
        reviewed_by="",
    )

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.cli.commands.merge.emit_status_transition", emit_mock)

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
    _write_wp(
        tasks_dir / "WP01-test.md",
        lane="for_review",
        review_status="approved",
        reviewed_by="reviewer-1",
    )

    emit_mock = Mock()
    monkeypatch.setattr("specify_cli.cli.commands.merge.emit_status_transition", emit_mock)

    _mark_wp_merged_done(repo_root, "021-test", "WP01", "main")

    assert emit_mock.call_count == 2
    first_call = emit_mock.call_args_list[0].kwargs
    second_call = emit_mock.call_args_list[1].kwargs
    assert first_call["to_lane"] == "approved"
    assert second_call["to_lane"] == "done"
