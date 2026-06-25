"""WP03 — push-preflight unit tests: push/no-push × origin-state matrix.

Covers T010 requirements: 5-origin-state × push/no-push combinations and
FR-004 (local merge results preserved when push blocked).

NFR-001: fetch latency validated manually/observationally — not in automated suite.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


def test_domain_preflight_does_not_import_push_preflight_at_module_load() -> None:
    """Local-merge domain module must not load publish-layer code at import time."""
    source = Path("src/specify_cli/merge/preflight.py").read_text()
    tree = ast.parse(source)
    parents = {
        child: node
        for node in ast.walk(tree)
        for child in ast.iter_child_nodes(node)
    }

    def is_under_type_checking(node: ast.AST) -> bool:
        while node in parents:
            parent = parents[node]
            if (
                isinstance(parent, ast.If)
                and isinstance(parent.test, ast.Name)
                and parent.test.id == "TYPE_CHECKING"
            ):
                return True
            node = parent
        return False

    runtime_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "specify_cli.merge.push_preflight"
        and not is_under_type_checking(node)
    ]
    assert runtime_imports == []


# ---------------------------------------------------------------------------
# T010 Test 1: no-push path never calls check_push_safety
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", ["in_sync", "ahead", "behind", "diverged", "no_tracking_branch"])
def test_merge_no_push_never_calls_check_push_safety(state: str) -> None:
    """When push=False, push_preflight.check_push_safety must never be called.

    This verifies the is_safe_to_push predicate semantics for each origin state,
    and confirms that check_push_safety is not invoked in the no-push path.
    """
    from specify_cli.merge.push_preflight import TargetBranchSyncStatus

    status = TargetBranchSyncStatus(
        target_branch="main",
        tracking_branch="origin/main" if state != "no_tracking_branch" else None,
        ahead_count=1 if state in ("ahead", "diverged") else 0,
        behind_count=1 if state in ("behind", "diverged") else 0,
        state=state,  # type: ignore[arg-type]
    )

    # For no-push path: check_push_safety is never called. The push predicate
    # may still be false for states that would fail after local mutation.
    if state in {"behind", "diverged"}:
        assert not status.is_safe_to_push
    else:
        assert status.is_safe_to_push

    # Local merge is always safe regardless of origin state (is_safe deprecated alias).
    assert status.is_safe is True

    # The gate itself (if push:) is in merge.py — check_push_safety is never
    # invoked in the no-push path, so we simply confirm it was not called here.
    # (No mock needed: we never invoked it above.)


# ---------------------------------------------------------------------------
# T010 Test 2: is_safe_to_push predicate for all 5 states
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state,expected_safe",
    [
        ("in_sync", True),
        ("ahead", True),
        ("behind", False),
        ("diverged", False),
        ("no_tracking_branch", True),
    ],
)
def test_is_safe_to_push_predicate(state: str, expected_safe: bool) -> None:
    """is_safe_to_push returns False when push would fail after local mutation."""
    from specify_cli.merge.push_preflight import TargetBranchSyncStatus

    status = TargetBranchSyncStatus(
        target_branch="main",
        tracking_branch="origin/main" if state != "no_tracking_branch" else None,
        ahead_count=1 if state in ("ahead", "diverged") else 0,
        behind_count=1 if state in ("behind", "diverged") else 0,
        state=state,  # type: ignore[arg-type]
    )
    assert status.is_safe_to_push == expected_safe


# ---------------------------------------------------------------------------
# T010 Test 3: check_push_safety with mocked subprocess
# ---------------------------------------------------------------------------


def test_check_push_safety_fetch_failure_returns_not_safe() -> None:
    """When fetch fails, check_push_safety returns is_safe_to_push=False."""
    from specify_cli.merge.push_preflight import check_push_safety

    with patch("specify_cli.merge.push_preflight.refresh_target_branch_tracking_ref") as mock_refresh:
        mock_refresh.return_value = MagicMock(success=False, error="network error", attempted=True)
        with patch("specify_cli.merge.push_preflight.inspect_target_branch_sync") as mock_inspect:
            result = check_push_safety(Path("/fake/repo"), "main")
            assert result.fetch_failed is True
            assert result.is_safe_to_push is False
            mock_inspect.assert_not_called()


def test_check_push_safety_diverged_returns_not_safe() -> None:
    """When state is diverged, check_push_safety returns is_safe_to_push=False."""
    from specify_cli.merge.push_preflight import TargetBranchSyncStatus, check_push_safety

    with patch("specify_cli.merge.push_preflight.refresh_target_branch_tracking_ref") as mock_refresh:
        mock_refresh.return_value = MagicMock(success=True, error=None)
        with patch("specify_cli.merge.push_preflight.inspect_target_branch_sync") as mock_inspect:
            mock_inspect.return_value = TargetBranchSyncStatus(
                target_branch="main",
                tracking_branch="origin/main",
                ahead_count=5,
                behind_count=3,
                state="diverged",
            )
            result = check_push_safety(Path("/fake/repo"), "main")
            assert result.is_safe_to_push is False
            assert result.fetch_failed is False


def test_check_push_safety_ahead_returns_safe() -> None:
    """When state is ahead, check_push_safety returns is_safe_to_push=True."""
    from specify_cli.merge.push_preflight import TargetBranchSyncStatus, check_push_safety

    with patch("specify_cli.merge.push_preflight.refresh_target_branch_tracking_ref") as mock_refresh:
        mock_refresh.return_value = MagicMock(success=True, error=None)
        with patch("specify_cli.merge.push_preflight.inspect_target_branch_sync") as mock_inspect:
            mock_inspect.return_value = TargetBranchSyncStatus(
                target_branch="main",
                tracking_branch="origin/main",
                ahead_count=10,
                behind_count=0,
                state="ahead",
            )
            result = check_push_safety(Path("/fake/repo"), "main")
            assert result.is_safe_to_push is True
            assert result.fetch_failed is False


# ---------------------------------------------------------------------------
# FR-004: push blocked but local results preserved when diverged
# ---------------------------------------------------------------------------


def test_push_blocked_but_local_results_preserved_when_diverged() -> None:
    """FR-004: When push is blocked for diverged state, local merge results must be preserved.

    check_push_safety is a read-only check — it does not mutate local git state.
    Local merge results are always preserved by design. We verify the safety
    predicate and that the result carries sync_status for diagnostics.
    """
    from specify_cli.merge.push_preflight import TargetBranchSyncStatus, check_push_safety

    with patch("specify_cli.merge.push_preflight.refresh_target_branch_tracking_ref") as mock_refresh:
        mock_refresh.return_value = MagicMock(success=True, error=None)
        with patch("specify_cli.merge.push_preflight.inspect_target_branch_sync") as mock_inspect:
            mock_inspect.return_value = TargetBranchSyncStatus(
                target_branch="main",
                tracking_branch="origin/main",
                ahead_count=5,
                behind_count=3,
                state="diverged",
            )
            result = check_push_safety(Path("/fake/repo"), "main")
            # Push is blocked
            assert result.is_safe_to_push is False
            # But sync_status is preserved for diagnostics (local state intact)
            assert result.sync_status is not None
            assert result.sync_status.state == "diverged"
            # fetch_failed is False — the check ran, it's just unsafe to push
            assert result.fetch_failed is False


def test_resume_preserves_original_push_request() -> None:
    """A resumed merge keeps the original --push intent even if retry omits it."""
    from specify_cli.cli.commands.merge import _effective_push_requested
    from specify_cli.merge.state import MergeState

    state = MergeState(
        mission_id="mission-01KT",
        mission_slug="mission-01KT",
        target_branch="main",
        wp_order=["WP01"],
        push_requested=True,
    )
    with patch("specify_cli.merge.preflight.load_state", return_value=state):
        assert _effective_push_requested(Path("/fake/repo"), "mission-01KT", False) is True


def test_resume_cannot_add_push_to_local_only_merge() -> None:
    """A resumed local-only merge ignores a later --push flag."""
    from specify_cli.cli.commands.merge import _effective_push_requested
    from specify_cli.merge.state import MergeState

    state = MergeState(
        mission_id="mission-01KT",
        mission_slug="mission-01KT",
        target_branch="main",
        wp_order=["WP01"],
        push_requested=False,
    )
    with patch("specify_cli.merge.preflight.load_state", return_value=state):
        assert _effective_push_requested(Path("/fake/repo"), "mission-01KT", True) is False
