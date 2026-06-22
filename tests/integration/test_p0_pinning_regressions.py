"""P0 coord-topology pinning + regression tests (WP01 — FR-001/003/004).

These tests pin the behaviour of four P0 defects against the current tree:

* **#1889** (FR-004 pin) — a *flattened* mission (``meta.json`` declares NO
  ``coordination_branch``; the coord topology was intentionally torn down)
  must resolve to the **primary** mission directory with NO crash, and a bare
  unresolvable handle must raise a structured ``ActionContextError`` (not a raw
  traceback). Fixed upstream by PR #1850; pinned here so a regression flips it
  red. (WP03 R3 reconciliation, #1906: the pre-R3 fixture declared a coord
  branch whose ref was never created — that shape is now the distinct R3
  ``CoordinationBranchDeleted`` data-loss guard, not a flattened mission. The
  canonical flatten is removing the ``coordination_branch`` key, which is what
  this fixture now models.)

* **#1885 symptom** (FR-004 pin) — ``query_current_state`` on a resolvable
  mid8 handle returns the REAL mission type (``software-dev``), not the legacy
  ``unknown`` stub. Also fixed upstream; pinned here.

* **#1884** (FR-001 / C-GATE-1, FR-011 collapse) — ``is_committed`` verifies a
  coord-only-committed spec against the surface it actually lives on. WP01
  originally threaded a ``placement: CommitTarget`` to add a coordination-ref
  leg; WP07 (FR-011) collapsed that OR — the setup-plan caller already feeds
  the READ-resolved ``spec_file`` (the coord worktree path for a materialized
  coordination topology), so the single-surface ``HEAD`` check on that path
  reads it as committed. These pins now exercise the read-resolved coord-worktree
  surface (where the spec lives), not the primary-checkout path.
* **#1954** (FR-001 / C-GATE-1 sibling) — the same committedness check must
  pass when the caller's ``spec_file`` path lives inside the coordination
  worktree, where on-disk ``.worktrees/<name>/`` is not part of the branch tree
  path.

Reconciled with PR #1910 (now on main), which independently fixed #1884 and the
#1885 residual via ``is_committed`` and ``MissionNotFoundError``.
#1884/#1885's full structured-error verification now lives in #1910's own tests
(``test_is_committed_coord_aware.py``, ``tests/contract/test_next_no_unknown_state.py``,
``tests/next/test_query_mode_unit.py``); this file retains the #1889 R3/flatten
pins, the #1885 *symptom* pin, and a coord-placement ``is_committed`` pin.

The fixtures use the real git surface (no monkey-patching) because the
contracts under test are on-disk topology behaviours. Repro recipes are
documented in ``research/research-p0-rootcauses.md``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


def _init_git_repo(repo_root: Path) -> None:
    _run(repo_root, "git", "init", "--initial-branch=main")
    _run(repo_root, "git", "config", "user.email", "test@example.invalid")
    _run(repo_root, "git", "config", "user.name", "WP01 Pin")
    _run(repo_root, "git", "config", "commit.gpgsign", "false")
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")
    _run(repo_root, "git", "add", "README.md")
    _run(repo_root, "git", "commit", "-m", "seed")


def _write_meta(
    feature_dir: Path,
    *,
    mission_id: str,
    mission_slug: str,
    coordination_branch: str | None,
) -> None:
    meta: dict[str, object] = {
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "mid8": mission_id[:8],
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-06-12T00:00:00+00:00",
        "friendly_name": mission_slug,
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


_SUBSTANTIVE_SPEC = """# Spec

## Functional Requirements
| ID | Title | Description | Priority | Status |
| FR-001 | Real title | A genuine substantive requirement description here | High | Open |
"""


# ---------------------------------------------------------------------------
# #1889 — flattened mission resolves to primary, no crash (FR-004 pin)
# ---------------------------------------------------------------------------


@pytest.fixture()
def flattened_mission(tmp_path: Path) -> dict[str, object]:
    """A genuinely FLATTENED mission: meta declares NO ``coordination_branch``.

    WP03 R3 authority reconciliation (#1906): the original fixture declared a
    ``coordination_branch`` whose git ref was never created. Under the
    registry-based topology authority that shape is no longer a "flattened"
    mission — it is the R3 *declared-but-deleted* coordination branch, which the
    surface resolver now (correctly) rejects with ``CoordinationBranchDeleted``
    to guard against unmerged-status data loss. The R3 error message itself
    states the canonical way to flatten a mission is to **remove the
    ``coordination_branch`` key** from meta.json.

    The #1889 pin's documented intent (research-p0-rootcauses.md §#1889 and the
    module docstring) is "a flattened mission resolves to the PRIMARY dir with
    no crash". A genuinely flattened mission carries no coord declaration, so
    this fixture omits the key — faithfully modelling the flatten pattern under
    the new authority while preserving the pin's primary-resolution contract.
    """
    _init_git_repo(tmp_path)
    mission_id = "01ABCDEFZZZZZZZZZZZZZZZZZZ"
    slug = "myfeat"
    mid8 = mission_id[:8]
    feature_dir = tmp_path / "kitty-specs" / f"{slug}-{mid8}"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_meta(
        feature_dir,
        mission_id=mission_id,
        mission_slug=slug,
        coordination_branch=None,
    )
    _run(tmp_path, "git", "add", "kitty-specs")
    _run(tmp_path, "git", "commit", "-m", "seed flattened mission")
    return {
        "repo_root": tmp_path,
        "feature_dir": feature_dir,
        "slug": slug,
        "mid8": mid8,
    }


def test_1889_flattened_mission_resolves_to_primary_no_crash(
    flattened_mission: dict[str, object],
) -> None:
    """#1889 pin: declared-but-unmaterialized coord resolves to primary dir."""
    from specify_cli.missions._read_path_resolver import (
        _resolve_mission_read_path as resolve_mission_read_path,
    )

    repo_root = flattened_mission["repo_root"]
    feature_dir = flattened_mission["feature_dir"]
    slug = flattened_mission["slug"]
    mid8 = flattened_mission["mid8"]

    assert isinstance(repo_root, Path) and isinstance(feature_dir, Path)
    assert isinstance(slug, str) and isinstance(mid8, str)

    # Both require_exists modes return the PRIMARY directory, no raise.
    assert resolve_mission_read_path(repo_root, slug, mid8, require_exists=False) == feature_dir
    assert resolve_mission_read_path(repo_root, slug, mid8, require_exists=True) == feature_dir


def test_1889_resolve_feature_dir_for_flattened_mission(
    flattened_mission: dict[str, object],
) -> None:
    """#1889 pin: the higher-level feature-dir resolver also returns primary."""
    from specify_cli.missions._read_path_resolver import (
        resolve_feature_dir_for_mission,
    )

    repo_root = flattened_mission["repo_root"]
    feature_dir = flattened_mission["feature_dir"]
    slug = flattened_mission["slug"]
    mid8 = flattened_mission["mid8"]
    assert isinstance(repo_root, Path) and isinstance(feature_dir, Path)
    assert isinstance(slug, str) and isinstance(mid8, str)

    resolved = resolve_feature_dir_for_mission(repo_root, f"{slug}-{mid8}")
    assert resolved == feature_dir


def test_1889_bare_unresolvable_handle_is_structured_error(
    flattened_mission: dict[str, object],
) -> None:
    """#1889 pin: an unresolvable handle raises a structured ActionContextError."""
    from mission_runtime import ActionContextError, resolve_action_context

    repo_root = flattened_mission["repo_root"]
    assert isinstance(repo_root, Path)

    with pytest.raises(ActionContextError):
        resolve_action_context(repo_root, action="tasks", feature="nonexistent-handle")


# ---------------------------------------------------------------------------
# #1885 — query_current_state mid8 handle + residual structured error
# ---------------------------------------------------------------------------


def test_1885_symptom_query_returns_real_mission_type(
    flattened_mission: dict[str, object],
) -> None:
    """#1885 symptom pin: a resolvable mid8 handle yields the real mission type."""
    from runtime.next.runtime_bridge import query_current_state

    repo_root = flattened_mission["repo_root"]
    mid8 = flattened_mission["mid8"]
    assert isinstance(repo_root, Path) and isinstance(mid8, str)

    decision = query_current_state("orchestrator", mid8, repo_root)
    assert decision.mission == "software-dev"
    assert decision.mission != "unknown"
    assert decision.mission_state != "unknown"


# NOTE (#1910 reconcile): the #1885 residual / not-materialized structured-error
# pins formerly here asserted our superseded ``QueryModeValidationError`` (+
# ``MISSION_DIR_NOT_MATERIALIZED``) contract. PR #1910 (now on main) replaced that
# surface with ``MissionNotFoundError`` and ships its own verification in
# ``tests/contract/test_next_no_unknown_state.py`` + ``tests/next/test_query_mode_unit.py``.
# Those pins were removed (not converted) to avoid duplicating #1910's contract
# tests; the no-silent-stub behavior remains covered there. The #1885 *symptom*
# pin (real mission type for a resolvable handle) is retained above.


# ---------------------------------------------------------------------------
# #1884 — committedness gate reads the placement authority (FR-001 / C-GATE-1)
# ---------------------------------------------------------------------------


@pytest.fixture()
def coord_only_committed_spec(tmp_path: Path) -> dict[str, object]:
    """Spec committed ONLY on the coordination ref (present, uncommitted, on primary)."""
    _init_git_repo(tmp_path)
    mission_id = "01CO0RDXXZZZZZZZZZZZZZZZZZZ"
    slug = "myplan"
    mid8 = mission_id[:8]
    coord_branch = f"kitty/mission-{slug}-{mid8}-coord"

    feature_dir = tmp_path / "kitty-specs" / f"{slug}-{mid8}"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_meta(
        feature_dir,
        mission_id=mission_id,
        mission_slug=slug,
        coordination_branch=coord_branch,
    )
    _run(tmp_path, "git", "add", "kitty-specs")
    _run(tmp_path, "git", "commit", "-m", "seed mission meta on main")

    # Create the coordination branch + worktree and commit spec.md there only.
    _run(tmp_path, "git", "branch", coord_branch, "main")
    coord_wt = tmp_path / ".worktrees" / f"{slug}-{mid8}-coord"
    coord_wt.parent.mkdir(parents=True, exist_ok=True)
    _run(tmp_path, "git", "worktree", "add", str(coord_wt), coord_branch)
    coord_feature = coord_wt / "kitty-specs" / f"{slug}-{mid8}"
    coord_feature.mkdir(parents=True, exist_ok=True)
    (coord_feature / "spec.md").write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")
    _run(coord_wt, "git", "add", "-A")
    _run(coord_wt, "git", "commit", "-m", "commit spec on coord only")

    # The spec is ALSO present in the primary working tree (as setup-plan sees
    # it via spec_file.exists()) but is NOT committed on primary HEAD.
    spec_primary = feature_dir / "spec.md"
    spec_primary.write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")

    return {
        "repo_root": tmp_path,
        "slug": f"{slug}-{mid8}",
        "spec_primary": spec_primary,
        "spec_coord": coord_feature / "spec.md",
        "coord_branch": coord_branch,
    }


def test_1884_is_committed_false_on_primary_head_alone(
    coord_only_committed_spec: dict[str, object],
) -> None:
    """Baseline: without the authority ref, the primary-HEAD check misses.

    This pins the defect mechanism: the coord-only spec is genuinely NOT on
    primary HEAD, so the historical primary-only check returns False.
    """
    from specify_cli.missions._substantive import is_committed

    repo_root = coord_only_committed_spec["repo_root"]
    spec = coord_only_committed_spec["spec_primary"]
    assert isinstance(repo_root, Path) and isinstance(spec, Path)

    assert is_committed(spec, repo_root) is False


def test_1884_is_committed_true_via_read_resolved_coord_surface(
    coord_only_committed_spec: dict[str, object],
) -> None:
    """FR-001 / C-GATE-1 (FR-011): the read-resolved coord-worktree spec reads committed.

    WP07 collapsed the 3-leg OR: the setup-plan caller feeds the READ-resolved
    ``spec_file``, which for a materialized coordination topology is the spec
    inside the coordination worktree (``spec_coord``). The single-surface
    ``HEAD`` check on that path — the surface where the spec was actually
    committed — therefore passes. The primary-checkout path (``spec_primary``,
    where the spec is uncommitted) is the surface the caller never resolves to;
    the false-negative below pins that the primary surface still reads False.
    """
    from specify_cli.missions._substantive import is_committed

    repo_root = coord_only_committed_spec["repo_root"]
    spec_coord = coord_only_committed_spec["spec_coord"]
    assert isinstance(repo_root, Path) and isinstance(spec_coord, Path)

    # The read-resolved coord-worktree surface carries the spec at HEAD.
    assert is_committed(spec_coord, repo_root) is True


def test_1954_is_committed_true_for_coord_worktree_path(
    coord_only_committed_spec: dict[str, object],
) -> None:
    """The gate passes when setup-plan resolves spec_file inside the coord worktree.

    FR-011: the worktree-relative tree-path must be checked against the
    worktree's branch ``HEAD`` (``.worktrees/<name>/`` is not part of the branch
    tree path). This is the surface the read path resolves to for a materialized
    coordination topology.
    """
    from specify_cli.missions._substantive import is_committed

    repo_root = coord_only_committed_spec["repo_root"]
    spec = coord_only_committed_spec["spec_coord"]
    assert isinstance(repo_root, Path) and isinstance(spec, Path)

    assert is_committed(spec, repo_root) is True


def test_1884_is_committed_no_false_positive_for_absent_spec(
    coord_only_committed_spec: dict[str, object],
) -> None:
    """A spec absent on the resolved surface must NOT read as committed."""
    from specify_cli.missions._substantive import is_committed

    repo_root = coord_only_committed_spec["repo_root"]
    slug = coord_only_committed_spec["slug"]
    assert isinstance(repo_root, Path) and isinstance(slug, str)

    ghost = repo_root / "kitty-specs" / slug / "does-not-exist.md"
    assert is_committed(ghost, repo_root) is False
