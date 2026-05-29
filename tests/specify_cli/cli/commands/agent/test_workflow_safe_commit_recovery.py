"""Workflow commit recovery handling for post-commit safe_commit failures."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

import specify_cli.cli.commands.agent.workflow as workflow
import specify_cli.coordination.transaction as transaction_module
from specify_cli.coordination.transaction import BookkeepingCommitFailed
from specify_cli.git.commit_helpers import SafeCommitRecoveryFailed


def _write_status_artifacts(feature_dir: Path) -> tuple[Path, Path, int, bytes]:
    feature_dir.mkdir(parents=True, exist_ok=True)
    events_path = feature_dir / "status.events.jsonl"
    status_path = feature_dir / "status.json"
    events_path.write_text('{"event_id":"before"}\n', encoding="utf-8")
    status_path.write_text('{"before":true}\n', encoding="utf-8")
    pre_size = events_path.stat().st_size
    pre_status = status_path.read_bytes()
    events_path.write_text(
        events_path.read_text(encoding="utf-8") + '{"event_id":"after"}\n',
        encoding="utf-8",
    )
    status_path.write_text('{"after":true}\n', encoding="utf-8")
    return events_path, status_path, pre_size, pre_status


def _post_commit_recovery_failure(*, worktree_root: Path) -> SafeCommitRecoveryFailed:
    return SafeCommitRecoveryFailed(
        "commit created but staging recovery failed",
        destination_ref="kitty/mission-demo-01ABCDEF",
        worktree_root=worktree_root,
        orphan_stash_ref="stash@{0}",
        commit_sha="abc123",
    )


def test_modern_workflow_does_not_restore_after_post_commit_recovery_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / "demo-01ABCDEF"
    events_path, status_path, pre_size, pre_status = _write_status_artifacts(feature_dir)
    after_events = events_path.read_bytes()
    after_status = status_path.read_bytes()

    class FakeTransaction:
        worktree_root = repo_root

        def __enter__(self) -> FakeTransaction:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def stage_path(self, _path: Path) -> None:
            return None

        def write_artifact(self, path: Path, data: bytes) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        def commit(self, _message: str) -> None:
            recovery = _post_commit_recovery_failure(worktree_root=repo_root)
            raise BookkeepingCommitFailed("wrapped recovery failure") from recovery

    class FakeTransactionFactory:
        @staticmethod
        def acquire(**_kwargs: object) -> FakeTransaction:
            return FakeTransaction()

    monkeypatch.setattr(workflow, "_load_coord_branch_meta", lambda _feature_dir: ("kitty/mission-demo-01ABCDEF", "01ABCDEF000000000000000000", "01ABCDEF"))
    monkeypatch.setattr(transaction_module, "BookkeepingTransaction", FakeTransactionFactory)

    with pytest.raises(typer.Exit):
        workflow._commit_workflow_change(
            repo_root=repo_root,
            feature_dir=feature_dir,
            mission_slug="demo",
            target_branch="main",
            paths=[events_path, status_path],
            message="status: demo",
            operation="planned -> claimed",
            wp_id="WP01",
            pre_emit_event_size=pre_size,
            pre_emit_status_bytes=pre_status,
        )

    assert events_path.read_bytes() == after_events
    assert status_path.read_bytes() == after_status


def test_legacy_workflow_does_not_restore_after_post_commit_recovery_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / "legacy-01ABCDEF"
    events_path, status_path, pre_size, pre_status = _write_status_artifacts(feature_dir)
    after_events = events_path.read_bytes()
    after_status = status_path.read_bytes()

    def fail_after_commit(**_kwargs: object) -> None:
        raise _post_commit_recovery_failure(worktree_root=repo_root)

    monkeypatch.setattr(workflow, "_load_coord_branch_meta", lambda _feature_dir: (None, None, None))
    monkeypatch.setattr(workflow, "safe_commit", fail_after_commit)

    with pytest.raises(typer.Exit):
        workflow._commit_workflow_change(
            repo_root=repo_root,
            feature_dir=feature_dir,
            mission_slug="legacy",
            target_branch="main",
            paths=[events_path, status_path],
            message="status: legacy",
            operation="planned -> claimed",
            wp_id="WP01",
            pre_emit_event_size=pre_size,
            pre_emit_status_bytes=pre_status,
        )

    assert events_path.read_bytes() == after_events
    assert status_path.read_bytes() == after_status
