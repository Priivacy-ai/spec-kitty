"""#2101 read-surface authority: map-requirements and finalize-tasks must resolve
the WP ``tasks/`` directory on the SAME (PRIMARY) surface.

This supersedes the #2064 framing. #2064 pointed ``map_requirements`` at
``resolve_feature_dir_for_mission`` (the coord worktree once materialized),
believing that was "finalize's seam" — but ``finalize_tasks`` anchors its input
read on ``primary_feature_dir_for_mission``, and the commit machinery
(``commit_for_mission``) stages PRIMARY->coord and change-detects in the primary
repo (where ``.worktrees/`` is gitignored). So planning artifacts are authored on
the PRIMARY checkout (``context resolve`` reports the primary ``feature_dir`` for
authoring actions) and only staged to the coordination branch at commit time.

``test_pre_fix_resolvers_diverge_on_coord_topology`` documents that the two raw
resolvers (slug-only vs mission) return different ``Path`` objects on a coord
topology (the precondition that made the surface split possible).
``test_map_and_finalize_agree_on_primary_authoring_surface`` proves the fix:
``_map_requirements_feature_dir`` resolves the SAME primary surface
``finalize_tasks`` reads, so PRIMARY-authored WP frontmatter is visible to BOTH →
zero unmapped functional requirements.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import CommitTarget, MissionTopology

from specify_cli.cli.commands.agent import tasks as tasks_mod
from specify_cli.cli.commands.agent.tasks import (
    _map_requirements_feature_dir,
    _review_currency_check_branch,
)
from specify_cli.coordination.workspace import CoordinationWorkspace
from specify_cli.missions._read_path_resolver import (
    primary_feature_dir_for_mission,
    resolve_feature_dir_for_mission,
    resolve_feature_dir_for_slug,
)
from specify_cli.requirement_mapping import (
    compute_coverage,
    read_all_wp_requirement_refs,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Production-shaped identity: a full 26-char Crockford-base32 ULID, NOT a
# handcrafted short slug. The operator HANDLE is the bare slug (no mid8 tail) —
# this is exactly the form that makes ``mid8_from_slug`` return ``""`` and the
# divergent ``resolve_feature_dir_for_slug`` miss the coord worktree.
_MISSION_ID = "01KVPR00ABCDEFGHJKMNPQRSTV"
_MID8 = _MISSION_ID[:8]
_SLUG = "single-planning-surface-authority"
_COORD_BRANCH = f"kitty/mission-{_SLUG}-{_MID8}"
_FUNCTIONAL_IDS = {"FR-001", "FR-002", "FR-003"}


def _write_meta(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mid8": _MID8,
                "coordination_branch": _COORD_BRANCH,
            }
        ),
        encoding="utf-8",
    )


def _write_wp(tasks_dir: Path, wp_id: str, refs: list[str]) -> None:
    tasks_dir.mkdir(parents=True, exist_ok=True)
    refs_block = "\n".join(f"- {ref}" for ref in refs)
    (tasks_dir / f"{wp_id}-coord-surface.md").write_text(
        f"---\nwork_package_id: {wp_id}\nrequirement_refs:\n{refs_block}\n---\n",
        encoding="utf-8",
    )


def _build_coord_topology(repo_root: Path) -> Path:
    """Build a coord-topology mission and return the COORD ``tasks/`` dir.

    The planning INPUT invariant: WP frontmatter is authored on PRIMARY and
    staged to coord at commit-time. By the time finalize reads, the canonical WP
    frontmatter lives in the materialized coordination worktree. We plant the
    full FR coverage in the coord ``tasks/`` dir and leave the primary
    ``tasks/`` dir empty — the exact shape that exposes #2064.
    """
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo_root, check=True)

    # Primary checkout: declares identity + coord branch, but no WP frontmatter.
    _write_meta(repo_root / "kitty-specs" / _SLUG)

    # Materialized coordination worktree: the canonical staged WP frontmatter.
    coord_root = CoordinationWorkspace.worktree_path(repo_root, _SLUG, _MID8)
    coord_feature_dir = coord_root / "kitty-specs" / f"{_SLUG}-{_MID8}"
    _write_meta(coord_feature_dir)
    coord_tasks = coord_feature_dir / "tasks"
    _write_wp(coord_tasks, "WP01", ["FR-001", "FR-002"])
    _write_wp(coord_tasks, "WP02", ["FR-003"])
    return coord_tasks


def test_pre_fix_resolvers_diverge_on_coord_topology(tmp_path: Path) -> None:
    """The #2064 precondition: the two PRE-fix read surfaces disagree.

    ``resolve_feature_dir_for_slug`` (the divergent path map_requirements used
    pre-WP06) resolves the PRIMARY dir because ``mid8_from_slug(<bare-slug>)`` is
    empty; ``resolve_feature_dir_for_mission`` (finalize's seam) reads the
    declared mid8 from primary ``meta.json`` and resolves into the COORD
    worktree. If these two ever returned the same dir for this fixture, the test
    would NOT be exercising the bug — so we assert they DIVERGE.
    """
    _build_coord_topology(tmp_path)

    slug_dir = resolve_feature_dir_for_slug(tmp_path, _SLUG)
    mission_dir = resolve_feature_dir_for_mission(tmp_path, _SLUG)

    assert slug_dir != mission_dir, (
        "Fixture does not reproduce #2064: the divergent resolvers agree, so the "
        "test would pass even on the buggy tree."
    )
    # The divergent path lands on PRIMARY (no coord) — the stale read.
    assert ".worktrees" not in str(slug_dir)
    # The seam finalize uses lands on the coord worktree — the canonical read.
    assert "-coord" in str(mission_dir)


def test_map_and_finalize_agree_on_primary_authoring_surface(tmp_path: Path) -> None:
    """#2101: map_requirements and finalize resolve the SAME PRIMARY dir.

    The earlier #2064 fix pointed ``map_requirements`` at
    ``resolve_feature_dir_for_mission`` believing that was "finalize's seam" — but
    ``finalize_tasks`` actually anchors its input read on
    ``primary_feature_dir_for_mission`` (and the commit machinery stages
    primary->coord, change-detecting in the primary repo where ``.worktrees/`` is
    gitignored). Planning artifacts are therefore authored on the PRIMARY checkout
    (``context resolve`` reports the primary ``feature_dir`` for authoring
    actions) and staged to coord at commit time. ``_map_requirements_feature_dir``
    must resolve that SAME primary surface, NOT the coord worktree — else
    map-requirements writes WP refs where finalize cannot read them.
    """
    _build_coord_topology(tmp_path)
    # Author the WP frontmatter on the PRIMARY surface (where the agent writes).
    primary_dir = primary_feature_dir_for_mission(tmp_path, _SLUG)
    _write_wp(primary_dir / "tasks", "WP01", ["FR-001", "FR-002"])
    _write_wp(primary_dir / "tasks", "WP02", ["FR-003"])

    map_feature_dir = _map_requirements_feature_dir(tmp_path, _SLUG)

    # One read surface: map-requirements resolves the SAME primary dir finalize
    # reads (``primary_feature_dir_for_mission``), never the coord worktree.
    assert map_feature_dir == primary_dir
    assert ".worktrees" not in str(map_feature_dir)

    # Cross-command consequence: reading the WP frontmatter through the shared
    # primary surface yields FULL coverage — zero unmapped functional requirements.
    refs = read_all_wp_requirement_refs(map_feature_dir / "tasks")
    coverage = compute_coverage(refs, _FUNCTIONAL_IDS)
    assert coverage["unmapped_functional"] == []


# --- T034: FR-005 predicate routing at the review-currency decision site ------


def _stub_placement(
    monkeypatch: pytest.MonkeyPatch, *, coord: bool
) -> CommitTarget:
    """Stub the ref-only placement + the STORED topology the routing decision reads.

    FR-001b: ``_review_currency_check_branch`` decides coord-vs-primary from the
    stored topology via ``routes_through_coordination(resolve_topology(...))``, not
    a per-ref enum — so both seams are stubbed consistently.
    """
    placement = CommitTarget(ref="kitty/mission-x-coord")
    topology = MissionTopology.COORD if coord else MissionTopology.SINGLE_BRANCH
    monkeypatch.setattr(
        tasks_mod, "resolve_placement_only", lambda _root, _slug: placement
    )
    monkeypatch.setattr(tasks_mod, "resolve_topology", lambda _root, _slug: topology)
    return placement


def test_review_currency_returns_placement_ref_for_coordination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-005: the coordination branch is taken via ``routes_through_coordination``.

    Directly exercises the T032 site (not an integration path): when the stored
    topology routes through coordination the placement ref is returned.
    """
    placement = _stub_placement(monkeypatch, coord=True)
    result = _review_currency_check_branch(
        main_repo_root=Path("/repo"),
        mission_slug="x",
        target_branch="feat/x",
        workspace=None,
    )
    assert result == placement.ref


def test_review_currency_returns_target_branch_for_non_coordination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-005: a coord-less topology falls back to ``target_branch``.

    ``routes_through_coordination`` is ``False`` for SINGLE_BRANCH/LANES, so the
    branch identical to the pre-refactor ``.kind is COORDINATION`` read is taken.
    """
    _stub_placement(monkeypatch, coord=False)
    result = _review_currency_check_branch(
        main_repo_root=Path("/repo"),
        mission_slug="x",
        target_branch="feat/x",
        workspace=None,
    )
    assert result == "feat/x"
