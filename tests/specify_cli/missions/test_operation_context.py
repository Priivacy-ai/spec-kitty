"""Regression tests for linked-worktree mission-root selection."""

import json
from pathlib import Path

import pytest

from specify_cli.context.mission_resolver import ResolvedMission
from specify_cli.missions import operation_context

# Pure-logic FS fixtures (no subprocess/git invocation): selected by the
# fast-tests-missions CI job (`-m "fast and not windows_ci"`).
pytestmark = [pytest.mark.unit, pytest.mark.fast]


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


# ---------------------------------------------------------------------------
# Integration: the REAL ``resolve_mission`` wiring through ``_probe``.
# The unit tests above mock ``_probe``; these exercise the actual resolver so
# an exception-mapping or index-building regression cannot ship green.
# Only the module's declared root inputs are patched — never ``_probe``.
# ---------------------------------------------------------------------------


def _make_repo(root: Path, mission_id: str) -> None:
    """Create a minimal spec-kitty checkout carrying one identity-bearing mission."""
    slug = "demo-mission-01MTEST"
    specs = root / "kitty-specs" / slug
    specs.mkdir(parents=True)
    specs.joinpath("meta.json").write_text(
        json.dumps({"mission_id": mission_id}), encoding="utf-8"
    )


def _link_worktree(primary: Path, caller: Path) -> None:
    """Give ``caller`` a real linked-worktree ``.git`` pointer back to ``primary``."""
    gitdir = primary / ".git" / "worktrees" / "demo"
    gitdir.mkdir(parents=True)
    gitdir.joinpath("HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    caller.joinpath(".git").write_text(
        f"gitdir: {gitdir}\n", encoding="utf-8"
    )


def test_real_resolver_prefers_caller_worktree_mission(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    primary = tmp_path / "primary"
    caller = tmp_path / "caller"
    caller.mkdir()
    _make_repo(primary, "01MPRIMARYREAL000000000000A")
    # Both surfaces carry the SAME identity under the same slug; the caller's
    # copy must be selected so its own worktree state is read.
    _make_repo(caller, "01MPRIMARYREAL000000000000A")
    _link_worktree(primary, caller)

    context = operation_context.resolve_mission_operation_context(
        primary,
        "demo-mission-01MTEST",
        cwd=caller,
    )

    assert context.repository_root == primary.resolve()
    assert context.mission_anchor_root == caller.resolve()
    assert context.identity is not None
    assert context.identity.mission_id == "01MPRIMARYREAL000000000000A"


def test_real_resolver_falls_back_when_caller_has_no_kitty_specs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    primary = tmp_path / "primary"
    caller = tmp_path / "caller"
    caller.mkdir()
    _make_repo(primary, "01MPRIMARYREAL000000000000A")
    _link_worktree(primary, caller)

    context = operation_context.resolve_mission_operation_context(
        primary,
        "demo-mission-01MTEST",
        cwd=caller,
    )

    assert context.repository_root == primary.resolve()
    assert context.mission_anchor_root == primary.resolve()
    assert context.identity is not None
    assert context.identity.mission_id == "01MPRIMARYREAL000000000000A"


def test_real_resolver_rejects_conflicting_identities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    primary = tmp_path / "primary"
    caller = tmp_path / "caller"
    caller.mkdir()
    _make_repo(primary, "01MPRIMARYREAL000000000000A")
    _make_repo(caller, "01MCALLERREAL000000000000B")
    _link_worktree(primary, caller)

    with pytest.raises(operation_context.MissionSurfaceConflictError):
        operation_context.resolve_mission_operation_context(
            primary,
            "demo-mission-01MTEST",
            cwd=caller,
        )
