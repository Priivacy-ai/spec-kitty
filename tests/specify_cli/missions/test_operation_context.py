"""Mission-scoped checkout resolution contracts.

These tests use real Git linked worktrees so caller-owned and managed checkout
classification exercise the production filesystem and Git boundaries.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from specify_cli.missions.operation_context import (
    CheckoutKind,
    MissionSurfaceConflictError,
    resolve_mission_operation_context,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

MISSION_A = "01AAAAAAAAAAAAAAAAAAAAAAAB"
MISSION_B = "01BBBBBBAAAAAAAAAAAAAAAAAC"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True)
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Spec Kitty Tests")
    (root / ".kittify").mkdir()
    (root / ".kittify" / "config.yaml").write_text("project: test\n", encoding="utf-8")
    (root / "README.md").write_text("test repository\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "test: initialize repository")
    return root


def _add_worktree(repo: Path, path: Path, branch: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-q", "-b", branch, str(path))
    return path


def _write_mission(root: Path, slug: str, mission_id: str) -> Path:
    mission_dir = root / "kitty-specs" / slug
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": mission_id, "mission_slug": slug}),
        encoding="utf-8",
    )
    return mission_dir


def test_caller_owned_worktree_is_the_mission_anchor(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    caller = _add_worktree(repo, tmp_path / "caller-owned", "codex/caller")
    _write_mission(caller, "demo-mission", MISSION_A)

    context = resolve_mission_operation_context(repo, "demo-mission", cwd=caller)

    assert context.repository_root == repo.resolve()
    assert context.mission_anchor_root == caller.resolve()
    assert context.checkout_kind is CheckoutKind.CALLER_OWNED
    assert context.mission_id == MISSION_A
    assert context.mission_slug == "demo-mission"


def test_explicit_root_does_not_expand_candidates_through_cwd(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    caller = _add_worktree(repo, tmp_path / "caller-owned", "codex/caller")
    _write_mission(repo, "demo-mission", MISSION_A)
    _write_mission(caller, "demo-mission", MISSION_B)

    context = resolve_mission_operation_context(
        repo,
        "demo-mission",
        cwd=caller,
        explicit_root=True,
    )

    assert context.mission_anchor_root == repo.resolve()
    assert context.checkout_kind is CheckoutKind.EXPLICIT
    assert context.mission_id == MISSION_A


def test_managed_lane_preserves_repository_root_anchor(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    managed = _add_worktree(
        repo,
        repo / ".worktrees" / "demo-01AAAAAA-lane-a",
        "kitty/mission-demo-01AAAAAA-lane-a",
    )
    _write_mission(repo, "demo-mission", MISSION_A)
    _write_mission(managed, "demo-mission", MISSION_A)

    context = resolve_mission_operation_context(repo, MISSION_A, cwd=managed)

    assert context.checkout_kind is CheckoutKind.MANAGED
    assert context.repository_root == repo.resolve()
    assert context.mission_anchor_root == repo.resolve()
    assert context.identity.feature_dir == repo / "kitty-specs" / "demo-mission"


def test_managed_lane_remains_a_split_brain_conflict_probe(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    managed = _add_worktree(
        repo,
        repo / ".worktrees" / "demo-01AAAAAA-lane-a",
        "kitty/mission-demo-01AAAAAA-lane-a",
    )
    _write_mission(repo, "demo-mission", MISSION_A)
    _write_mission(managed, "demo-mission", MISSION_B)

    with pytest.raises(MissionSurfaceConflictError) as exc_info:
        resolve_mission_operation_context(repo, "demo-mission", cwd=managed)

    assert {candidate.mission_id for candidate in exc_info.value.candidates} == {
        MISSION_A,
        MISSION_B,
    }
    assert {candidate.root for candidate in exc_info.value.candidates} == {
        repo.resolve(),
        managed.resolve(),
    }


def test_foreign_git_common_directory_is_not_a_candidate(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    foreign = _init_repo(tmp_path / "foreign")
    _write_mission(repo, "demo-mission", MISSION_A)
    _write_mission(foreign, "demo-mission", MISSION_B)

    context = resolve_mission_operation_context(repo, "demo-mission", cwd=foreign)

    assert context.checkout_kind is CheckoutKind.REPOSITORY_ROOT
    assert context.mission_anchor_root == repo.resolve()
    assert context.mission_id == MISSION_A


def test_parallel_caller_worktrees_resolve_only_their_own_mission(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    caller_a = _add_worktree(repo, tmp_path / "caller-a", "codex/caller-a")
    caller_b = _add_worktree(repo, tmp_path / "caller-b", "codex/caller-b")
    _write_mission(caller_a, "mission-a", MISSION_A)
    _write_mission(caller_b, "mission-b", MISSION_B)

    context_a = resolve_mission_operation_context(repo, "mission-a", cwd=caller_a)
    context_b = resolve_mission_operation_context(repo, "mission-b", cwd=caller_b)

    assert (context_a.mission_anchor_root, context_a.mission_id) == (
        caller_a.resolve(),
        MISSION_A,
    )
    assert (context_b.mission_anchor_root, context_b.mission_id) == (
        caller_b.resolve(),
        MISSION_B,
    )


@pytest.mark.parametrize("selector", ["demo-mission", MISSION_B])
def test_slug_or_full_id_split_brain_fails_closed(
    tmp_path: Path,
    selector: str,
) -> None:
    repo = _init_repo(tmp_path / "repo")
    caller = _add_worktree(repo, tmp_path / "caller-owned", "codex/caller")
    _write_mission(repo, "demo-mission", MISSION_A)
    _write_mission(caller, "demo-mission", MISSION_B)

    with pytest.raises(MissionSurfaceConflictError) as exc_info:
        resolve_mission_operation_context(repo, selector, cwd=caller)

    error = exc_info.value
    assert error.error_code == "MISSION_SURFACE_CONFLICT"
    assert {candidate.mission_id for candidate in error.candidates} == {
        MISSION_A,
        MISSION_B,
    }
    assert {candidate.root for candidate in error.candidates} == {
        repo.resolve(),
        caller.resolve(),
    }
    expected_candidates = [
        {
            "root": str(root.resolve()),
            "mission_id": mission_id,
            "mission_slug": "demo-mission",
        }
        for root, mission_id in sorted(
            [(repo, MISSION_A), (caller, MISSION_B)],
            key=lambda item: os.path.normcase(str(item[0].resolve())),
        )
    ]
    payload = error.to_dict()
    assert list(payload) == ["error", "selector", "candidates"]
    assert payload == {
        "error": "MISSION_SURFACE_CONFLICT",
        "selector": selector,
        "candidates": expected_candidates,
    }
    assert all(
        list(candidate) == ["root", "mission_id", "mission_slug"]
        for candidate in payload["candidates"]
    )


def test_resolution_is_deterministic_across_one_hundred_calls(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    caller = _add_worktree(repo, tmp_path / "caller-owned", "codex/caller")
    _write_mission(caller, "demo-mission", MISSION_A)

    contexts = [resolve_mission_operation_context(repo, "demo-mission", cwd=caller) for _ in range(100)]

    assert len(set(contexts)) == 1
