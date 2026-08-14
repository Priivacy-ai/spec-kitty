"""Dual-root placement contracts for caller-owned linked worktrees."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import mission_runtime.resolution as resolution

from mission_runtime import (
    MissionArtifactKind,
    TopologySurface,
    mission_context_for,
    placement_seam,
    resolve_action_context,
    resolve_artifact_surface,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_SLUG = "caller-mission-01AAAAAAAAAAAAAAAAAAAAAAAB"
_MISSION_ID = "01AAAAAAAAAAAAAAAAAAAAAAAB"
_TARGET_BRANCH = "codex/caller-mission"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _caller_mission(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Spec Kitty Tests")
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.yaml").write_text("project: test\n", encoding="utf-8")
    (repo / "README.md").write_text("root remains clean\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "test: initialize repository")

    caller = tmp_path / "caller-owned"
    _git(repo, "worktree", "add", "-q", "-b", "codex/caller", str(caller))
    mission_dir = caller / "kitty-specs" / _SLUG
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mission_slug": _SLUG,
                "target_branch": _TARGET_BRANCH,
                "topology": "single_branch",
                "mission_type": "software-dev",
            }
        ),
        encoding="utf-8",
    )
    (mission_dir / "spec.md").write_text("# Caller Mission\n", encoding="utf-8")
    (mission_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    return repo, caller, mission_dir


def test_placement_seam_anchors_primary_and_flat_status_in_caller_worktree(
    tmp_path: Path,
) -> None:
    repo, caller, mission_dir = _caller_mission(tmp_path)
    root_before = (_git(repo, "rev-parse", "HEAD"), _git(repo, "status", "--porcelain"))

    seam = placement_seam(repo, _SLUG, mission_anchor_root=caller)

    assert seam.read_dir(MissionArtifactKind.SPEC) == mission_dir
    assert seam.read_dir(MissionArtifactKind.STATUS_STATE) == mission_dir
    assert seam.write_target(MissionArtifactKind.SPEC).ref == _TARGET_BRANCH
    assert (_git(repo, "rev-parse", "HEAD"), _git(repo, "status", "--porcelain")) == root_before


def test_artifact_surface_uses_anchor_for_primary_without_recanonicalizing_to_root(
    tmp_path: Path,
) -> None:
    repo, caller, mission_dir = _caller_mission(tmp_path)

    surface = resolve_artifact_surface(
        repo,
        _SLUG,
        MissionArtifactKind.PRIMARY_METADATA,
        mission_anchor_root=caller,
    )

    assert surface.path == mission_dir
    assert surface.surface_kind is TopologySurface.PRIMARY
    assert not (repo / "kitty-specs" / _SLUG).exists()


def test_mission_context_separates_primary_anchor_from_repository_topology_root(
    tmp_path: Path,
) -> None:
    repo, caller, mission_dir = _caller_mission(tmp_path)

    context = mission_context_for(repo, _SLUG, mission_anchor_root=caller)

    assert context.artifact(MissionArtifactKind.SPEC).read_dir == mission_dir
    assert context.artifact(MissionArtifactKind.STATUS_STATE).read_dir == mission_dir
    assert context.artifact(MissionArtifactKind.SPEC).commit_target is not None
    assert context.artifact(MissionArtifactKind.SPEC).commit_target.ref == _TARGET_BRANCH


def test_action_context_carries_repository_root_but_reads_caller_primary(
    tmp_path: Path,
) -> None:
    repo, caller, mission_dir = _caller_mission(tmp_path)

    context = resolve_action_context(
        repo,
        action="status",
        feature=_SLUG,
        cwd=caller,
        mission_anchor_root=caller,
    )

    assert context.feature_dir == str(mission_dir)
    assert context.target_branch == _TARGET_BRANCH
    assert context.workspace is not None
    assert context.workspace.primary_root == repo.resolve()
    assert context.status_surface is not None
    assert context.status_surface.status_read_dir == mission_dir


def test_placement_threads_anchor_metadata_to_lifecycle_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, caller, mission_dir = _caller_mission(tmp_path)
    captured_feature_dirs: list[Path | None] = []
    original = resolution.resolve_lifecycle_phase

    def capture_phase(
        mission_slug: str,
        repository_root: Path,
        *,
        resolver: object | None = None,
        feature_dir: Path | None = None,
    ) -> object:
        captured_feature_dirs.append(feature_dir)
        return original(
            mission_slug,
            repository_root,
            resolver=resolver,
            feature_dir=feature_dir,
        )

    monkeypatch.setattr(resolution, "resolve_lifecycle_phase", capture_phase)
    seam = placement_seam(repo, _SLUG, mission_anchor_root=caller)

    seam.write_target(MissionArtifactKind.SPEC)
    seam.read_dir(MissionArtifactKind.SPEC)

    assert captured_feature_dirs == [mission_dir, mission_dir]


def test_lifecycle_phase_reads_anchor_metadata_but_probes_repository_git(
    tmp_path: Path,
) -> None:
    repo, _caller, mission_dir = _caller_mission(tmp_path)
    meta_path = mission_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["baseline_merge_commit"] = _git(repo, "rev-parse", "HEAD")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    _git(repo, "branch", _TARGET_BRANCH)

    phase = resolution.resolve_lifecycle_phase(
        _SLUG,
        repo,
        feature_dir=mission_dir,
    )

    assert phase is resolution.LifecyclePhase.CONSOLIDATED
