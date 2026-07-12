"""Regression + characterization tests — WP01 (closes #2574): subtask-gate single seam.

T001 (red-first): proves, through the PRE-EXISTING production entry point
(``coordination.status_transition._prepare_event``), that a coord-topology
mission with ``request.repo_root=None`` used to read the coordination-branch
husk (which never carries ``tasks.md`` -- TASKS_INDEX is a PRIMARY-partition
artifact) instead of recovering the PRIMARY ``tasks.md`` via git ancestry --
the FR-002 weak site this WP closes. RED before T005, GREEN after.

T006: a DIRECT 3-branch unit test of the new
``missions._read_path_resolver.resolve_subtasks_gate_dir`` seam (the seam is
otherwise only covered through call sites) plus a characterization test
proving the two already-strong sites (``status/emit.py``, ``status/aggregate.py``)
resolve byte-identically to their pre-consolidation inline computation
(NFR-001).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.missions._read_path_resolver import resolve_subtasks_gate_dir
from specify_cli.status.models import Lane, TransitionRequest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_git_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".kittify").mkdir()
    (repo / "README.md").write_text("test repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    return repo


def _build_coord_mission_with_primary_tasks(
    tmp_path: Path, slug: str, tasks_md_body: str
) -> tuple[Path, str, Path]:
    """Build a coord-topology mission whose PRIMARY carries ``tasks.md``.

    The materialized coord worktree never gets a ``tasks.md`` of its own --
    ``tasks.md`` is a PRIMARY-partition artifact (``TASKS_INDEX``) -- so a
    read of the coord husk directly (the pre-#2574 weak-site behavior) always
    finds nothing there regardless of what the primary copy says. Mirrors the
    fixture in ``tests/specify_cli/status/test_infer_subtasks_primary.py``.

    Returns ``(repo_root, mid8, coord_husk_feature_dir)``.
    """
    mission_id = "01ABCDEF1234567890123456"
    mid8 = mission_id[:8]
    coord_branch = f"kitty/mission-{slug}-{mid8}"
    repo = _make_git_repo(tmp_path)

    primary_dir = repo / "kitty-specs" / slug
    primary_dir.mkdir(parents=True)
    (primary_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "coordination_branch": coord_branch,
                "mission_slug": slug,
            }
        ),
        encoding="utf-8",
    )
    (primary_dir / "tasks.md").write_text(tasks_md_body, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "primary planning artifacts")

    _git(repo, "checkout", "-b", coord_branch)
    coord_branch_dir = repo / "kitty-specs" / f"{slug}-{mid8}"
    coord_branch_dir.mkdir(parents=True)
    (coord_branch_dir / "status.events.jsonl").write_text("", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "coord scaffold")
    _git(repo, "checkout", "main")

    # Materialize the coord worktree the SAME way production does, so the
    # husk dir genuinely exists on disk (not the create-window primary
    # fallback).
    from specify_cli.coordination.workspace import CoordinationWorkspace

    coord_worktree = CoordinationWorkspace.resolve(repo, slug, mid8)
    coord_husk_feature_dir = coord_worktree / "kitty-specs" / f"{slug}-{mid8}"

    return repo, mid8, coord_husk_feature_dir


def test_prepare_event_recovers_primary_when_repo_root_none(tmp_path: Path) -> None:
    """FR-002 (#2574): ``repo_root=None`` on a coord-topology mission must
    recover the PRIMARY ``tasks.md`` via git ancestry, not silently read the
    coordination husk directly.

    Before T005 this is RED: ``_prepare_event`` read ``feature_dir`` (the
    coord husk) unchanged when ``request.repo_root`` was ``None``, found no
    ``tasks.md`` there, and failed the transition closed even though every
    row in the PRIMARY ``tasks.md`` is checked.
    """
    from specify_cli.coordination.status_transition import _prepare_event

    slug = "coord-gate-seam"
    tasks_md = "# Tasks\n\n## WP01\n- [x] T001 implement thing\n"
    _repo, _mid8, coord_husk_feature_dir = _build_coord_mission_with_primary_tasks(
        tmp_path, slug, tasks_md
    )

    request = TransitionRequest(
        feature_dir=coord_husk_feature_dir,
        mission_slug=slug,
        wp_id="WP01",
        to_lane="for_review",
        actor="codex",
        repo_root=None,
        implementation_evidence_present=True,
    )

    event, resolved_lane = _prepare_event(
        feature_dir=coord_husk_feature_dir,
        request=request,
        mission_slug=slug,
        mission_id="01ABCDEF1234567890123456",
        from_lane=str(Lane.IN_PROGRESS),
    )

    assert resolved_lane == str(Lane.FOR_REVIEW)
    assert event is not None
    assert event.to_lane == Lane.FOR_REVIEW


def test_resolve_subtasks_gate_dir_direct_three_branches(tmp_path: Path) -> None:
    """Direct pin of the seam's own contract (plan D1) -- otherwise only
    covered through call sites:

    (a) explicit ``repo_root`` -> passthrough (``feature_dir`` is IGNORED --
        a decoy, nonexistent ``feature_dir`` proves it).
    (b) ``repo_root=None`` + git-rooted ``feature_dir`` -> recovers PRIMARY
        via git ancestry.
    (c) ``repo_root=None`` + a bare non-git ``tmp_path`` -> ``WorkspaceRootNotFound``
        internally -> returns ``feature_dir`` unchanged (also satisfies the
        T006 "non-git tmp_path -> feature_dir" characterization).
    """
    slug = "coord-three-branch"
    tasks_md = "# Tasks\n\n## WP01\n- [x] T001 done\n"
    repo, _mid8, coord_husk_feature_dir = _build_coord_mission_with_primary_tasks(
        tmp_path, slug, tasks_md
    )
    primary_dir = repo / "kitty-specs" / slug

    # (a) explicit repo_root passthrough.
    decoy_feature_dir = tmp_path / "decoy-does-not-exist"
    passthrough = resolve_subtasks_gate_dir(decoy_feature_dir, repo, slug)
    assert passthrough == primary_dir

    # (b) repo_root=None + git-rooted -> recovers PRIMARY from feature_dir's ancestry.
    recovered = resolve_subtasks_gate_dir(coord_husk_feature_dir, None, slug)
    assert recovered == primary_dir

    # (c) repo_root=None + bare tmp_path (no git ancestry) -> feature_dir unchanged.
    bare_dir = tmp_path / "bare-no-git"
    bare_dir.mkdir()
    fallback = resolve_subtasks_gate_dir(bare_dir, None, "irrelevant-slug")
    assert fallback == bare_dir


def test_strong_sites_match_pre_existing_resolve_planning_read_dir(tmp_path: Path) -> None:
    """NFR-001: the two already-strong sites (``status/emit.py``'s
    explicit-``repo_root`` branch, ``status/aggregate.py``'s always-present
    ``self.repo_root`` branch) must resolve byte-identically to what their
    pre-consolidation inline call --
    ``resolve_planning_read_dir(repo_root, mission_slug, kind=TASKS_INDEX)``
    -- produced. 0 behavioral diff on the preserved paths.
    """
    from mission_runtime import MissionArtifactKind

    from specify_cli.missions._read_path_resolver import resolve_planning_read_dir

    slug = "coord-strong-sites"
    tasks_md = "# Tasks\n\n## WP01\n- [x] T001 done\n"
    repo, _mid8, coord_husk_feature_dir = _build_coord_mission_with_primary_tasks(
        tmp_path, slug, tasks_md
    )

    pre_existing = resolve_planning_read_dir(repo, slug, kind=MissionArtifactKind.TASKS_INDEX)
    seam_result = resolve_subtasks_gate_dir(coord_husk_feature_dir, repo, slug)

    assert seam_result == pre_existing
