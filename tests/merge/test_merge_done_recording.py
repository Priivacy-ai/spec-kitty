"""Scope: merge done recording unit tests — no real git or subprocesses."""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from specify_cli.cli.commands.merge import _mark_wp_merged_done

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
    first_call = emit_mock.call_args_list[0].kwargs
    second_call = emit_mock.call_args_list[1].kwargs
    assert first_call["to_lane"] == "approved"
    assert second_call["to_lane"] == "done"


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
