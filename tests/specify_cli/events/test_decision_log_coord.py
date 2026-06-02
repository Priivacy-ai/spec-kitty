"""Unit tests for WP03: DecisionGitLog coord-aware worktree routing.

T017: DecisionGitLog._decisions_file rooted under worktree_root (not repo_root).
T018: _wrap_with_decision_git_log passes coord worktree path when it exists.
T019: _wrap_with_decision_git_log falls back to repo_root when coord absent.
T020: DecisionGitLog.safe_commit uses worktree_root as worktree_root arg.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.events.decision_log import DecisionGitLog
from runtime.next._internal_runtime.events import NullEmitter

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_log(
    repo_root: Path,
    worktree_root: Path,
    *,
    mission_slug: str = "my-mission",
    destination_ref: str = "kitty/mission-my-mission",
    inner: Any | None = None,
) -> DecisionGitLog:
    return DecisionGitLog(
        repo_root=repo_root,
        worktree_root=worktree_root,
        destination_ref=destination_ref,
        mission_slug=mission_slug,
        inner=inner or NullEmitter(),
    )


# ---------------------------------------------------------------------------
# T017: _decisions_file is rooted under worktree_root
# ---------------------------------------------------------------------------

class TestDecisionsFileLocation:
    """Verify decisions.events.jsonl is written under worktree_root (T017)."""

    def test_decisions_file_under_worktree_root(self, tmp_path: Path) -> None:
        """When worktree_root != repo_root, decisions_file uses worktree_root."""
        repo_root = tmp_path / "repo"
        worktree_root = tmp_path / "coord-worktree"
        repo_root.mkdir()
        worktree_root.mkdir()
        slug = "my-mission"

        log = _make_log(repo_root, worktree_root, mission_slug=slug)

        expected = worktree_root / "kitty-specs" / slug / "decisions.events.jsonl"
        assert log._decisions_file == expected

    def test_decisions_file_not_under_repo_root_when_coord_present(self, tmp_path: Path) -> None:
        """decisions_file must NOT point into repo_root when coord worktree is set."""
        repo_root = tmp_path / "repo"
        worktree_root = tmp_path / "coord-worktree"
        repo_root.mkdir()
        worktree_root.mkdir()
        slug = "my-mission"

        log = _make_log(repo_root, worktree_root, mission_slug=slug)

        wrong_path = repo_root / "kitty-specs" / slug / "decisions.events.jsonl"
        assert log._decisions_file != wrong_path

    def test_decisions_file_repo_root_when_no_coord(self, tmp_path: Path) -> None:
        """When worktree_root == repo_root (legacy/no coord), file is in repo_root."""
        slug = "legacy-mission"
        log = _make_log(tmp_path, tmp_path, mission_slug=slug)

        expected = tmp_path / "kitty-specs" / slug / "decisions.events.jsonl"
        assert log._decisions_file == expected


# ---------------------------------------------------------------------------
# T018: _wrap_with_decision_git_log coord routing
# ---------------------------------------------------------------------------

class TestWrapWithDecisionGitLogCoordRouting:
    """_wrap_with_decision_git_log selects worktree_root based on coord existence (T018, T019)."""

    def test_coord_worktree_used_when_exists(self, tmp_path: Path) -> None:
        """When coord worktree directory exists, it becomes worktree_root (T018)."""
        from runtime.next.runtime_bridge import _wrap_with_decision_git_log
        from runtime.next._internal_runtime.events import NullEmitter

        slug = "my-feature-01KT3YBD"
        mid8 = "01KT3YBD"
        base_slug = "my-feature"

        # Create coord worktree directory on disk
        coord_path = tmp_path / ".worktrees" / f"{base_slug}-{mid8}-coord"
        coord_path.mkdir(parents=True)

        inner = NullEmitter()

        captured: dict[str, Any] = {}

        def _fake_decision_git_log(
            repo_root: Path,
            worktree_root: Path,
            destination_ref: str,
            mission_slug: str,
            *,
            inner: Any,
            mission_id: str = "",
        ) -> Any:
            captured["worktree_root"] = worktree_root
            return inner  # return inner unchanged for simplicity

        with (
            patch(
                "specify_cli.events.decision_log.DecisionGitLog",
                side_effect=_fake_decision_git_log,
            ),
            patch(
                "runtime.next.runtime_bridge._resolve_coordination_branch",
                return_value="kitty/mission-my-feature-01KT3YBD",
            ),
            patch(
                "runtime.next.runtime_bridge._resolve_mission_ulid",
                return_value="01KT3YBDABCDEFGHIJKLMNOP",
            ),
        ):
            _wrap_with_decision_git_log(inner, slug, tmp_path)

        assert "worktree_root" in captured
        assert captured["worktree_root"] == coord_path

    def test_repo_root_used_when_coord_absent(self, tmp_path: Path) -> None:
        """When coord worktree does not exist, repo_root becomes worktree_root (T019)."""
        from runtime.next.runtime_bridge import _wrap_with_decision_git_log
        from runtime.next._internal_runtime.events import NullEmitter

        slug = "my-feature-01KT3YBD"
        inner = NullEmitter()

        captured: dict[str, Any] = {}

        def _fake_decision_git_log(
            repo_root: Path,
            worktree_root: Path,
            destination_ref: str,
            mission_slug: str,
            *,
            inner: Any,
            mission_id: str = "",
        ) -> Any:
            captured["worktree_root"] = worktree_root
            return inner

        with (
            patch(
                "specify_cli.events.decision_log.DecisionGitLog",
                side_effect=_fake_decision_git_log,
            ),
            patch(
                "runtime.next.runtime_bridge._resolve_coordination_branch",
                return_value="kitty/mission-my-feature-01KT3YBD",
            ),
            patch(
                "runtime.next.runtime_bridge._resolve_mission_ulid",
                return_value="01KT3YBDABCDEFGHIJKLMNOP",
            ),
        ):
            _wrap_with_decision_git_log(inner, slug, tmp_path)

        assert "worktree_root" in captured
        assert captured["worktree_root"] == tmp_path


# ---------------------------------------------------------------------------
# T020: safe_commit called with correct worktree_root
# ---------------------------------------------------------------------------

class TestDecisionGitLogSafeCommitWorktreeRoot:
    """DecisionGitLog passes worktree_root (not repo_root) to safe_commit (T020)."""

    def test_safe_commit_uses_worktree_root(self, tmp_path: Path) -> None:
        """safe_commit is called with worktree_root matching what was passed in."""
        from spec_kitty_events.mission_next import (
            DecisionInputAnsweredPayload,
            DecisionInputRequestedPayload,
            RuntimeActorIdentity,
        )

        repo_root = tmp_path / "repo"
        worktree_root = tmp_path / "coord-worktree"
        repo_root.mkdir()
        worktree_root.mkdir()

        # Pre-create decisions directory
        decisions_dir = worktree_root / "kitty-specs" / "my-mission"
        decisions_dir.mkdir(parents=True)

        log = _make_log(repo_root, worktree_root)

        actor = RuntimeActorIdentity(actor_id="test-agent", actor_type="llm")
        req_payload = DecisionInputRequestedPayload(
            run_id="run-001",
            decision_id="dec-001",
            step_id="implement",
            question="Should I proceed?",
            actor=actor,
        )
        ans_payload = DecisionInputAnsweredPayload(
            run_id="run-001",
            decision_id="dec-001",
            answer="yes",
            actor=actor,
        )

        safe_commit_calls: list[dict[str, Any]] = []

        def _mock_safe_commit(**kwargs: Any) -> bool:
            safe_commit_calls.append(kwargs)
            return True

        with patch("specify_cli.events.decision_log.safe_commit", side_effect=_mock_safe_commit):
            log.emit_decision_input_requested(req_payload)
            log.emit_decision_input_answered(ans_payload)

        # Exactly one safe_commit call (for the answered event)
        assert len(safe_commit_calls) == 1
        call = safe_commit_calls[0]
        assert call["worktree_root"] == worktree_root
        assert call["repo_root"] == repo_root

    def test_safe_commit_not_called_for_request_only(self, tmp_path: Path) -> None:
        """safe_commit is NOT called for DecisionInputRequested (only for Answered)."""
        from spec_kitty_events.mission_next import (
            DecisionInputRequestedPayload,
            RuntimeActorIdentity,
        )

        decisions_dir = tmp_path / "kitty-specs" / "my-mission"
        decisions_dir.mkdir(parents=True)

        log = _make_log(tmp_path, tmp_path)

        actor = RuntimeActorIdentity(actor_id="test-agent", actor_type="llm")
        req_payload = DecisionInputRequestedPayload(
            run_id="run-001",
            decision_id="dec-001",
            step_id="implement",
            question="Should I proceed?",
            actor=actor,
        )

        safe_commit_calls: list[Any] = []

        with patch("specify_cli.events.decision_log.safe_commit", side_effect=lambda **kw: safe_commit_calls.append(kw) or True):
            log.emit_decision_input_requested(req_payload)

        assert len(safe_commit_calls) == 0
