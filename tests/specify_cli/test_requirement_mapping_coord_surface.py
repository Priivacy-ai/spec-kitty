"""#2064 read-surface desync regression: map-requirements and finalize-tasks
must resolve the WP ``tasks/`` directory through ONE seam-resolved surface.

WP06 / FR-008 / SC-005. The bug: ``tasks.py::map_requirements`` was the lone read
path on ``resolve_feature_dir_for_slug`` (whose slug-only ``mid8_from_slug``
heuristic misses the coordination worktree when the operator handle carries no
mid8 tail), while ``tasks.py::finalize_tasks`` (and the rest of ``tasks.py``)
resolve through ``resolve_feature_dir_for_mission`` (the
``resolve_action_context(action="tasks")`` seam, which reads the declared mid8
from primary ``meta.json``). On a coord topology the two return DIFFERENT
``tasks/`` directories, so ``map-requirements`` writes/reads one and finalize
reads the other → spurious ``unmapped_functional_requirements``.

These tests are NON-FAKEABLE: ``test_pre_fix_resolvers_diverge_on_coord_topology``
proves the precondition that makes #2064 real (the two PRE-fix read surfaces
return different ``Path`` objects for this fixture), and
``test_map_and_finalize_agree_on_coord_topology`` proves the consequence — that
the unified resolver ``map_requirements`` now uses agrees with finalize's, so the
WP frontmatter staged into the coord ``tasks/`` dir is visible to BOTH, yielding
zero unmapped functional requirements. A bare ``compute_coverage`` assertion in
isolation would be insufficient (coverage math was never the bug); these tests
exercise the cross-command directory agreement on a real coord topology.
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


def test_map_and_finalize_agree_on_coord_topology(tmp_path: Path) -> None:
    """Post-WP06: map_requirements and finalize resolve the SAME coord dir.

    ``_map_requirements_feature_dir`` (the unified resolver map_requirements now
    uses) and ``resolve_feature_dir_for_mission`` (finalize's seam) must return
    the SAME ``tasks/`` directory, so the WP frontmatter staged into coord is
    visible to BOTH commands → zero ``unmapped_functional_requirements``.
    """
    coord_tasks = _build_coord_topology(tmp_path)

    map_feature_dir = _map_requirements_feature_dir(tmp_path, _SLUG)
    finalize_feature_dir = resolve_feature_dir_for_mission(tmp_path, _SLUG)

    # One read surface: same ``tasks/`` Path for both commands.
    assert map_feature_dir == finalize_feature_dir
    assert (map_feature_dir / "tasks") == coord_tasks

    # Cross-command consequence: reading the WP frontmatter through the unified
    # surface yields FULL coverage — zero unmapped functional requirements.
    refs = read_all_wp_requirement_refs(map_feature_dir / "tasks")
    coverage = compute_coverage(refs, _FUNCTIONAL_IDS)
    assert coverage["unmapped_functional"] == []

    # Witness the bug it replaces: the PRE-fix (divergent) surface reads the
    # PRIMARY ``tasks/`` dir, which has NO WP frontmatter → every FR is unmapped.
    pre_fix_dir = resolve_feature_dir_for_slug(tmp_path, _SLUG)
    pre_fix_refs = read_all_wp_requirement_refs(pre_fix_dir / "tasks")
    pre_fix_coverage = compute_coverage(pre_fix_refs, _FUNCTIONAL_IDS)
    assert sorted(pre_fix_coverage["unmapped_functional"]) == sorted(_FUNCTIONAL_IDS)


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
    # write-surface-coherence WP01: ``resolve_placement_only`` now takes a REQUIRED
    # ``kind`` keyword. ``_review_currency_check_branch`` calls it with
    # ``kind=STATUS_STATE`` (the coord-base read), so the stub must accept ``kind``
    # — a positional-only lambda raises TypeError, gets swallowed by the helper's
    # except arm, and silently falls back to ``target_branch`` (the stale-stub trap).
    monkeypatch.setattr(
        tasks_mod, "resolve_placement_only", lambda _root, _slug, *, kind: placement
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
