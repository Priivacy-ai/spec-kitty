"""Regression tests for linked-worktree mission-root selection."""

from pathlib import Path

import pytest

from specify_cli.context.mission_resolver import ResolvedMission
from specify_cli.missions import operation_context


def _mission(root: Path, mission_id: str) -> ResolvedMission:
    return ResolvedMission(
        mission_id=mission_id,
        mission_slug="demo-mission-01MTEST",
        feature_dir=root / "kitty-specs" / "demo-mission-01MTEST",
        mid8=mission_id[:8],
    )


def _patch_roots(monkeypatch: pytest.MonkeyPatch, primary: Path, caller: Path) -> None:
    monkeypatch.setattr(operation_context, "get_main_repo_root", lambda root: primary)
    monkeypatch.setattr(operation_context, "get_status_read_root", lambda cwd: caller)


def test_prefers_caller_owned_mission_surface(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    caller = tmp_path / "caller"
    primary.mkdir()
    caller.mkdir()
    _patch_roots(monkeypatch, primary, caller)

    caller_mission = _mission(caller, "01MTESTCALLER00000000000000")
    monkeypatch.setattr(
        operation_context,
        "_probe",
        lambda root, selector: caller_mission if root == caller else None,
    )

    context = operation_context.resolve_mission_operation_context(
        primary,
        "demo-mission-01MTEST",
        cwd=caller,
    )

    assert context.repository_root == primary
    assert context.mission_anchor_root == caller
    assert context.identity == caller_mission


def test_falls_back_to_primary_when_caller_has_no_mission(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    primary = tmp_path / "primary"
    caller = tmp_path / "caller"
    primary.mkdir()
    caller.mkdir()
    _patch_roots(monkeypatch, primary, caller)

    primary_mission = _mission(primary, "01MTESTPRIMARY00000000000000")
    monkeypatch.setattr(
        operation_context,
        "_probe",
        lambda root, selector: primary_mission if root == primary else None,
    )

    context = operation_context.resolve_mission_operation_context(
        primary,
        "demo-mission-01MTEST",
        cwd=caller,
    )

    assert context.mission_anchor_root == primary
    assert context.identity == primary_mission


def test_rejects_conflicting_primary_and_caller_identities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    primary = tmp_path / "primary"
    caller = tmp_path / "caller"
    primary.mkdir()
    caller.mkdir()
    _patch_roots(monkeypatch, primary, caller)

    primary_mission = _mission(primary, "01MTESTPRIMARY00000000000000")
    caller_mission = _mission(caller, "01MTESTCALLER00000000000000")
    monkeypatch.setattr(
        operation_context,
        "_probe",
        lambda root, selector: primary_mission if root == primary else caller_mission,
    )

    with pytest.raises(operation_context.MissionSurfaceConflictError):
        operation_context.resolve_mission_operation_context(
            primary,
            "demo-mission-01MTEST",
            cwd=caller,
        )
