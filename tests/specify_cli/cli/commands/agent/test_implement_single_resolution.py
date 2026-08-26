"""FR-008/#1832 (C-IC05): ``agent action implement`` single resolution path.

These tests pin the single-resolution invariant for the implement create/verify
seam: the workspace is resolved exactly once by the caller, and the post-create
verification *consumes* that already-resolved context instead of re-running a
second resolution authority that could report "no workspace could be resolved"
on a verified read-path.

The behavior under test lives in
``workflow._ensure_workspace_materialized`` — the seam extracted from the
implement command's create block (C14). Topology-true fixtures use a full
26-char ULID ``mission_id`` in the slug, a real ``.worktrees/`` lane path with a
``.git`` marker, and a real ``lanes.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import typer

pytestmark = [pytest.mark.fast]

from specify_cli.cli.commands.agent import workflow
from specify_cli.cli.commands.agent.workflow import _ensure_workspace_materialized
from specify_cli.workspace.context import ResolvedWorkspace

# Full 26-char ULID mission_id (topology-true; NFR-002).
MISSION_ID = "01KV8NPCSINGLERES0LUTI0N00"
MID8 = MISSION_ID[:8].lower()
MISSION_SLUG = f"read-path-single-resolution-{MISSION_ID.lower()}"


def _build_real_lane_topology(tmp_path: Path, *, materialize_git: bool) -> ResolvedWorkspace:
    """Create a topology-true lane workspace and its lanes.json.

    Returns a ResolvedWorkspace whose ``worktree_path`` points at a real
    ``.worktrees/<slug>-<mid8>-lane-a`` directory. When *materialize_git* is
    True the lane carries a ``.git`` marker (a usable worktree); otherwise the
    path is absent (creation pending).
    """
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)

    # Real lanes.json (the resolution path consumes it).
    lanes_path = feature_dir / "lanes.json"
    lanes_path.write_text(
        json.dumps(
            {
                "version": 1,
                "feature_slug": MISSION_SLUG,
                "target_branch": "feat/read-path-error-fidelity",
                "lanes": [
                    {
                        "lane_id": "lane-a",
                        "wp_ids": ["WP05"],
                        "depth": 0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    worktree_path = repo_root / ".worktrees" / f"{MISSION_SLUG}-{MID8}-lane-a"
    if materialize_git:
        worktree_path.mkdir(parents=True)
        # git worktrees carry a .git FILE pointing at the gitdir.
        (worktree_path / ".git").write_text("gitdir: /real/gitdir\n", encoding="utf-8")

    return ResolvedWorkspace(
        mission_slug=MISSION_SLUG,
        wp_id="WP05",
        execution_mode="code_change",
        mode_source="lanes.json",
        resolution_kind="lane_workspace",
        workspace_name=worktree_path.name,
        worktree_path=worktree_path,
        branch_name=f"kitty/mission-{MISSION_SLUG}-{MID8}-lane-a",
        lane_id="lane-a",
        lane_wp_ids=["WP05"],
        context=None,
    )


def test_already_materialized_workspace_is_consumed_without_re_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A verified (already-existing) workspace is consumed; no re-resolution.

    Guards the single-resolution invariant: the helper must NOT call
    ``resolve_workspace_for_wp`` (a second authority).

    #3281/C-006 rationale: the ORIGINAL invariant ("no re-resolution when
    exists") is unchanged by this WP -- ``create_workspace`` (the second
    resolution authority / full ``top_level_implement``) still never runs on
    an exists=True workspace. What changed is that a SEPARATE, dedicated,
    idempotent self-heal callable now always runs on that path (see T008/T009
    below) -- this test asserts it runs and is harmless (ancestry-correct ==
    a true no-op resume), not that it is skipped.
    """
    resolve_calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        workflow,
        "resolve_workspace_for_wp",
        lambda *a, **k: resolve_calls.append((a, k)),
    )

    workspace = _build_real_lane_topology(tmp_path, materialize_git=True)

    def _create() -> None:  # pragma: no cover - must not be called
        raise AssertionError("create must not run when the workspace already exists")

    self_heal_calls: list[bool] = []

    def _self_heal() -> None:
        self_heal_calls.append(True)

    _ensure_workspace_materialized(workspace, "WP05", _create, _self_heal)

    assert workspace.exists  # same resolved contract, consumed not rebuilt
    assert resolve_calls == [], "single resolution path must not re-resolve"
    assert self_heal_calls == [True], (
        "an exists=True retry must re-enter self-heal (#3281 FR-005), "
        "not silently no-op"
    )


def test_create_then_consume_resolved_context_no_no_workspace_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create materializes the resolved path; the same contract reports exists.

    This is the #1832 captured behavior: after a successful claim+create on a
    verified read-path, implement MUST NOT raise "no workspace could be
    resolved". The fix is that the already-resolved workspace is re-stat'd via
    ``.exists`` — NOT re-resolved through a second authority.
    """
    re_resolution_calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        workflow,
        "resolve_workspace_for_wp",
        lambda *a, **k: re_resolution_calls.append((a, k)),
    )
    # Creation is only permitted from the main repo (not a worktree). The test
    # suite itself runs inside a lane worktree, so model the main-repo caller.
    monkeypatch.setattr(workflow, "is_worktree_context", lambda _cwd: False)

    workspace = _build_real_lane_topology(tmp_path, materialize_git=False)
    assert not workspace.exists  # path not yet on disk

    def _create() -> None:
        # top_level_implement materializes the worktree at the ALREADY-RESOLVED
        # path. It does not change the resolved identity.
        workspace.worktree_path.mkdir(parents=True)
        (workspace.worktree_path / ".git").write_text(
            "gitdir: /real/gitdir\n", encoding="utf-8"
        )

    def _self_heal() -> None:  # pragma: no cover - must not be called
        raise AssertionError("self-heal is only for the exists=True (reuse) path")

    _ensure_workspace_materialized(workspace, "WP05", _create, _self_heal)

    assert workspace.exists, "the materialized resolved workspace must report exists"
    assert re_resolution_calls == [], (
        "post-create verification must consume the resolved context, "
        "not re-resolve via a second authority"
    )


def test_husk_workspace_is_blocked_not_recreated(tmp_path: Path) -> None:
    """A husk (path present, no .git) is absent-but-blocked (#1833)."""
    workspace = _build_real_lane_topology(tmp_path, materialize_git=False)
    # Materialize the directory WITHOUT a .git marker => husk.
    workspace.worktree_path.mkdir(parents=True)

    assert workspace.is_husk

    def _create() -> None:  # pragma: no cover - must not be called
        raise AssertionError("husk must not be silently recreated")

    def _self_heal() -> None:  # pragma: no cover - must not be called
        raise AssertionError("husk is refused before the exists/self-heal branch")

    with pytest.raises(typer.Exit):
        _ensure_workspace_materialized(workspace, "WP05", _create, _self_heal)


def test_unmaterialized_after_create_raises_structured_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If create does not materialize the path, a structured error fires.

    The error must come from the post-create verification (not the worktree
    guard), so model a main-repo caller.
    """
    monkeypatch.setattr(workflow, "is_worktree_context", lambda _cwd: False)
    create_ran: list[bool] = []
    workspace = _build_real_lane_topology(tmp_path, materialize_git=False)

    def _create() -> None:
        # Buggy creator: does nothing — path stays absent.
        create_ran.append(True)

    def _self_heal() -> None:  # pragma: no cover - must not be called
        raise AssertionError("self-heal is only for the exists=True (reuse) path")

    with pytest.raises(typer.Exit):
        _ensure_workspace_materialized(workspace, "WP05", _create, _self_heal)

    assert create_ran == [True], "create must run before the materialization check"


def test_stale_exists_workspace_reenters_self_heal_not_create(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T008 (#3281/C-006 RED-first): a stale-but-existing lane worktree.

    One missing the recorded planning SHA (or an approved dependency tip
    merged after this worktree was created) — must re-enter the idempotent
    reuse-path self-heal on retry, NOT silently no-op. This reproduces the
    #3281 retry-short-circuit defect directly through the pre-existing
    ``ensure_workspace_materialized`` entry point: before the fix, the bare
    ``if workspace.exists: return`` never even looked at staleness, so
    ``reenter_self_heal`` was never invoked at all.

    Reconciles (#1832/#1833, C-006): the "no re-resolution when exists"
    invariant is preserved exactly — ``create_workspace`` (the SECOND
    resolution authority) still never runs — while the NEW, narrower
    invariant this WP adds is "no re-resolution when exists, AND the
    dedicated idempotent self-heal always re-enters to bring a stale
    worktree's ancestry up to date."
    """
    def _must_not_resolve(*_a: object, **_k: object) -> None:
        raise AssertionError("must not re-resolve")

    monkeypatch.setattr(workflow, "resolve_workspace_for_wp", _must_not_resolve)

    # A leftover worktree: exists on disk (a prior WP in the lane, or an
    # earlier interrupted attempt) but its allocator-level ancestry is stale
    # -- modeled here by a self-heal spy standing in for the real
    # ``reenter_lane_self_heal`` (unit-tested separately against real git in
    # tests/lanes/test_worktree_allocator_atomicity.py and
    # tests/specify_cli/cli/commands/agent/test_claim_ancestry_gate.py).
    workspace = _build_real_lane_topology(tmp_path, materialize_git=True)

    def _create() -> None:  # pragma: no cover - must not be called
        raise AssertionError(
            "create must not run when the workspace already exists (#1832)"
        )

    self_heal_calls: list[bool] = []

    def _self_heal() -> None:
        # Models the reuse-path merges (_merge_recorded_planning_commit +
        # _merge_dependency_lane_tips) running -- the observable effect T008
        # requires, without needing a real git repo at this unit-test layer.
        self_heal_calls.append(True)

    _ensure_workspace_materialized(workspace, "WP05", _create, _self_heal)

    assert self_heal_calls == [True], (
        "a retry over an existing (possibly stale) lane worktree must "
        "re-enter self-heal — the #3281 retry-short-circuit defect"
    )
