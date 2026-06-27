"""Shared un-stubbed coordination-topology test fixture (FR-014, WP01).

Materialises a post-#2106 coordination-topology mission shape:

* PRIMARY checkout: ``meta.json`` (``topology=coord`` + ``coordination_branch``),
  ``tasks/WP01.md``, ``lanes.json``, and a DECOY ``status.events.jsonl``.
* Coord worktree (STATUS-only husk): ``status.events.jsonl`` only —
  no ``tasks/``, no ``lanes.json``, no ``meta.json``.

A decoy events file with a DIFFERENT marker on primary makes wrong-leg status
reads fail LOUDLY rather than silently pass.

Also provides a flat/single-branch mission fixture for neutrality tests.

**No resolver is patched anywhere in this module.** All topology routing uses
real git + filesystem state — verifiable via the smoke test (T003).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Marker constants — coord vs. primary decoy must be distinct so wrong-leg
# reads are detectable in assert_status_from_coord.
# ---------------------------------------------------------------------------

_COORD_EVENT_MARKER = "COORD_AUTHORITY_MARKER_WP01_01KW2E7A"
_DECOY_EVENT_MARKER = "PRIMARY_DECOY_MARKER_WP01_01KW2E7A"


# ---------------------------------------------------------------------------
# Context dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoordTopologyContext:
    """All paths for a coord-topology mission fixture (T001).

    Holds the repo root and all derived paths so per-site tests can assert
    specific surfaces without re-deriving git paths.
    """

    repo: Path
    """Git repository root (primary checkout)."""

    slug: str
    """Full composed mission slug ``<human>-<mid8>``."""

    mid8: str
    """8-character mission ID prefix (first 8 chars of ``mission_id``)."""

    mission_id: str
    """Full 26-character ULID mission ID."""

    coord_branch: str
    """Coordination branch ``kitty/mission-<slug>``."""

    primary_feature_dir: Path
    """``<repo>/kitty-specs/<slug>/`` on the PRIMARY checkout."""

    coord_feature_dir: Path
    """``<repo>/.worktrees/<slug>-coord/kitty-specs/<slug>/`` in the coord husk."""

    status_events_path: Path
    """Canonical ``status.events.jsonl`` on the coord husk (authoritative STATUS)."""

    decoy_events_path: Path
    """Decoy ``status.events.jsonl`` on the primary (distinct content — wrong-leg probe)."""


@dataclass(frozen=True)
class FlatTopologyContext:
    """All paths for a flat/single-branch mission fixture.

    For neutrality tests: a mission with ``topology=single_branch`` and no coord
    worktree. Both resolvers should return the primary dir.
    """

    repo: Path
    """Git repository root."""

    slug: str
    """Full composed mission slug ``<human>-<mid8>``."""

    mid8: str
    """8-character mission ID prefix."""

    mission_id: str
    """Full 26-character ULID mission ID."""

    primary_feature_dir: Path
    """``<repo>/kitty-specs/<slug>/`` on the PRIMARY checkout."""

    status_events_path: Path
    """``status.events.jsonl`` on the primary checkout."""


# ---------------------------------------------------------------------------
# Private git helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    """Run ``git -C <repo> <args>`` and return stripped stdout."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_git_repo(parent: Path) -> Path:
    """Create a minimal initialised git repo with one commit under *parent*.

    Returns the absolute repo root path (``parent / "repo"``).
    """
    repo = parent / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    _git(repo, "config", "user.email", "coord-fixture@spec-kitty.test")
    _git(repo, "config", "user.name", "Coord Fixture")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "README.md").write_text("coord-topology fixture repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init: coord-topology-fixture baseline")
    return repo


# ---------------------------------------------------------------------------
# Private artifact helpers
# ---------------------------------------------------------------------------


def _write_wp_task(tasks_dir: Path, wp_id: str) -> None:
    """Write a minimal WP task file to *tasks_dir*."""
    content = (
        f"---\nwork_package_id: {wp_id}\ntitle: {wp_id} fixture task\n---\n# {wp_id}\n"
    )
    (tasks_dir / f"{wp_id}.md").write_text(content, encoding="utf-8")


def _write_lanes_json(feature_dir: Path, *, slug: str, mission_id: str) -> None:
    """Write a minimal but fully-parseable ``lanes.json`` to *feature_dir*.

    Includes all fields required by ``LanesManifest.from_dict``
    (``computed_at``, ``computed_from``) so tests that read lanes.json through
    the planning-read seam (LANE_STATE kind) get a valid manifest.
    """
    payload = {
        "version": 1,
        "mission_slug": slug,
        "mission_id": mission_id,
        "mission_branch": f"kitty/mission-{slug}",
        "target_branch": "main",
        "lanes": [
            {
                "lane_id": "lane-a",
                "wp_ids": ["WP01"],
                "write_scope": [],
                "predicted_surfaces": [],
                "depends_on_lanes": [],
                "parallel_group": 0,
            }
        ],
        "computed_at": "2026-06-26T00:00:00+00:00",
        "computed_from": "coord-topology-fixture",
        "planning_artifact_wps": [],
    }
    (feature_dir / "lanes.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _write_meta(
    feature_dir: Path,
    *,
    slug: str,
    mission_id: str,
    topology: str,
    coordination_branch: str | None,
) -> None:
    """Write ``meta.json`` for a mission to *feature_dir*."""
    meta: dict[str, object] = {
        "mission_id": mission_id,
        "mission_slug": slug,
        "slug": slug,
        "mission_type": "software-dev",
        "target_branch": "main",
        "vcs": "git",
        "topology": topology,
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def _status_event_line(slug: str, wp_id: str, *, marker: str) -> str:
    """Return one JSONL status-event line with *marker* embedded in ``evidence``."""
    return json.dumps(
        {
            "actor": "coord-fixture",
            "at": "2026-06-26T00:00:00+00:00",
            "event_id": "01KW2E7A0FIXTURE000000000" + marker[-1],
            "evidence": marker,
            "execution_mode": "code_change",
            "feature_slug": slug,
            "force": False,
            "from_lane": "planned",
            "reason": None,
            "review_ref": None,
            "to_lane": "claimed",
            "wp_id": wp_id,
        }
    )


# ---------------------------------------------------------------------------
# Fixtures (T001)
# ---------------------------------------------------------------------------


@pytest.fixture()
def coord_topology_mission(tmp_path: Path) -> CoordTopologyContext:
    """Materialise a post-#2106 coordination-topology mission (FR-014 / T001).

    Shape on disk after this fixture runs:

    * ``<repo>/kitty-specs/<slug>/`` (PRIMARY):
      - ``meta.json``  — ``topology=coord``, ``coordination_branch`` set
      - ``tasks/WP01.md``
      - ``lanes.json``
      - ``status.events.jsonl``  — DECOY (distinct content from coord)

    * ``<repo>/.worktrees/<slug>-coord/kitty-specs/<slug>/`` (coord husk):
      - ``status.events.jsonl``  — AUTHORITATIVE (coord marker)
      - NO ``tasks/``, NO ``lanes.json``, NO ``meta.json``

    **No resolver is patched** — topology routing uses real git + filesystem.
    """
    from specify_cli.coordination.workspace import CoordinationWorkspace

    # --- Identity constants for this fixture instance ---
    mission_id = "01KW2E7AFC0000000000000001"
    mid8 = "01KW2E7A"
    human_slug = "coord-topo-fixture"
    slug = f"{human_slug}-{mid8}"
    coord_branch = f"kitty/mission-{slug}"

    # 1. Initialise repo under a coord-specific subdir so a test that also
    #    requests flat_topology_mission does not collide on tmp_path/repo.
    repo = _make_git_repo(tmp_path / "coord")

    # 2. Create the coord branch pointing at the initial commit (no mission
    #    files yet).  The worktree checked out at this branch will carry
    #    ONLY the baseline content — no kitty-specs/ directory.
    _git(repo, "branch", coord_branch)

    # 3. Build the primary mission dir with all planning + decoy artifacts.
    primary_feature_dir = repo / "kitty-specs" / slug
    primary_feature_dir.mkdir(parents=True)

    _write_meta(
        primary_feature_dir,
        slug=slug,
        mission_id=mission_id,
        topology="coord",
        coordination_branch=coord_branch,
    )

    tasks_dir = primary_feature_dir / "tasks"
    tasks_dir.mkdir()
    _write_wp_task(tasks_dir, "WP01")

    _write_lanes_json(primary_feature_dir, slug=slug, mission_id=mission_id)

    # DECOY: primary carries a status.events.jsonl with a distinct marker.
    # A wrong-leg read that returns the primary path will expose the decoy marker,
    # causing assert_status_from_coord to fail LOUDLY.
    decoy_events_path = primary_feature_dir / "status.events.jsonl"
    decoy_events_path.write_text(
        _status_event_line(slug, "WP01", marker=_DECOY_EVENT_MARKER) + "\n",
        encoding="utf-8",
    )

    # 4. Commit the primary planning artifacts so the repo HEAD is clean.
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: coord-topology primary planning artifacts")

    # 5. Materialise the coord worktree via the REAL CoordinationWorkspace
    #    helper (no stub, no monkeypatch).  The worktree checks out the
    #    coord branch (initial commit) → no kitty-specs/ in its working tree.
    coord_worktree_root = CoordinationWorkspace.resolve(repo, slug, mid8)

    # 6. Create the mission dir inside the coord husk and write STATUS-only content.
    #    (In the real workflow BookkeepingTransaction does this; here we write
    #    directly so the fixture is self-contained.)
    coord_mission_dir = coord_worktree_root / "kitty-specs" / slug
    coord_mission_dir.mkdir(parents=True)

    status_events_path = coord_mission_dir / "status.events.jsonl"
    status_events_path.write_text(
        _status_event_line(slug, "WP01", marker=_COORD_EVENT_MARKER) + "\n",
        encoding="utf-8",
    )

    # 7. Structural self-checks: the husk must carry STATUS only.
    assert not (coord_mission_dir / "tasks").exists(), (
        "Fixture invariant violated: coord husk must not carry tasks/"
    )
    assert not (coord_mission_dir / "lanes.json").exists(), (
        "Fixture invariant violated: coord husk must not carry lanes.json"
    )
    assert not (coord_mission_dir / "meta.json").exists(), (
        "Fixture invariant violated: coord husk must not carry meta.json"
    )

    return CoordTopologyContext(
        repo=repo,
        slug=slug,
        mid8=mid8,
        mission_id=mission_id,
        coord_branch=coord_branch,
        primary_feature_dir=primary_feature_dir,
        coord_feature_dir=coord_mission_dir,
        status_events_path=status_events_path,
        decoy_events_path=decoy_events_path,
    )


@pytest.fixture()
def flat_topology_mission(tmp_path: Path) -> FlatTopologyContext:
    """Materialise a flat (single-branch) mission for neutrality tests.

    Shape on disk:

    * ``<repo>/kitty-specs/<slug>/`` (PRIMARY only — no coord worktree):
      - ``meta.json``  — ``topology=single_branch``, no ``coordination_branch``
      - ``tasks/WP01.md``
      - ``lanes.json``
      - ``status.events.jsonl``

    Both ``candidate_feature_dir_for_mission`` and
    ``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`` should return the
    primary dir for this topology.
    """
    mission_id = "01KW2E7BFC0000000000000001"
    mid8 = "01KW2E7B"
    human_slug = "flat-topo-fixture"
    slug = f"{human_slug}-{mid8}"

    # Use a distinct subdir to avoid colliding with coord_topology_mission's repo.
    repo = _make_git_repo(tmp_path / "flat")

    primary_feature_dir = repo / "kitty-specs" / slug
    primary_feature_dir.mkdir(parents=True)

    _write_meta(
        primary_feature_dir,
        slug=slug,
        mission_id=mission_id,
        topology="single_branch",
        coordination_branch=None,
    )

    tasks_dir = primary_feature_dir / "tasks"
    tasks_dir.mkdir()
    _write_wp_task(tasks_dir, "WP01")

    _write_lanes_json(primary_feature_dir, slug=slug, mission_id=mission_id)

    status_events_path = primary_feature_dir / "status.events.jsonl"
    status_events_path.write_text(
        _status_event_line(slug, "WP01", marker="FLAT_MARKER") + "\n",
        encoding="utf-8",
    )

    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: flat-topology mission")

    return FlatTopologyContext(
        repo=repo,
        slug=slug,
        mid8=mid8,
        mission_id=mission_id,
        primary_feature_dir=primary_feature_dir,
        status_events_path=status_events_path,
    )


# ---------------------------------------------------------------------------
# Dual-leg asserter helpers (T002)
# ---------------------------------------------------------------------------


def assert_reads_primary(
    resolved_path: Path,
    ctx: CoordTopologyContext | FlatTopologyContext,
    *,
    wp_id: str = "WP01",
) -> None:
    """Assert *resolved_path* equals the PRIMARY mission dir with tasks/ present.

    For a coord-topology mission this verifies that the resolver did NOT land on
    the STATUS-only coord husk (which lacks ``tasks/``). For a flat mission this
    is a simple identity check.

    Fails loudly if:
    - ``resolved_path`` differs from ``ctx.primary_feature_dir``
    - ``tasks/<wp_id>.md`` is absent at the resolved path (husk-read indicator)
    """
    assert resolved_path == ctx.primary_feature_dir, (
        f"PRIMARY dir mismatch.\n"
        f"  Expected : {ctx.primary_feature_dir}\n"
        f"  Got      : {resolved_path}\n"
        "A coord-topology bug routes to the STATUS-only husk instead of primary."
    )
    task_file = resolved_path / "tasks" / f"{wp_id}.md"
    assert task_file.exists(), (
        f"tasks/{wp_id}.md absent at {resolved_path}.\n"
        "Resolver landed on the coord husk (STATUS-only), not the primary dir.\n"
        f"  Primary dir : {ctx.primary_feature_dir}\n"
        f"  Resolved to : {resolved_path}"
    )


def assert_status_from_coord(
    events_path: Path,
    ctx: CoordTopologyContext,
) -> None:
    """Assert *events_path* is the authoritative coord-husk events file.

    The assertion is TWO-PRONGED so a wrong-leg read fails LOUDLY:

    1. **Path check**: ``events_path`` must equal ``ctx.status_events_path``
       (the coord husk path), NOT the primary decoy.
    2. **Content check**: the events file must contain the coord marker
       (``_COORD_EVENT_MARKER``) and must NOT contain the decoy marker.

    A wrong-leg read that returns the primary decoy path — or ANY path that
    holds the decoy content — triggers an AssertionError with a clear message.
    """
    assert events_path == ctx.status_events_path, (
        f"STATUS read path mismatch.\n"
        f"  Expected (coord husk) : {ctx.status_events_path}\n"
        f"  Got                   : {events_path}\n"
        "The resolver landed on the PRIMARY decoy instead of the coord husk."
    )
    content = events_path.read_text(encoding="utf-8")
    assert _COORD_EVENT_MARKER in content, (
        f"Coord marker absent in {events_path}.\n"
        f"  Marker expected : {_COORD_EVENT_MARKER!r}\n"
        "Wrong-leg read: the events file content looks like the primary decoy."
    )
    assert _DECOY_EVENT_MARKER not in content, (
        f"Primary DECOY marker found in {events_path}.\n"
        f"  Decoy marker    : {_DECOY_EVENT_MARKER!r}\n"
        "Wrong-leg read confirmed: reading from the primary decoy, not the coord husk."
    )


def assert_both_legs(
    resolved_primary_path: Path,
    events_path: Path,
    ctx: CoordTopologyContext,
    *,
    wp_id: str = "WP01",
) -> None:
    """Assert the full PRIMARY+STATUS split for a coord-topology mission.

    Combines :func:`assert_reads_primary` (tasks from PRIMARY) and
    :func:`assert_status_from_coord` (events from COORD) so per-site tests
    can assert the complete routing invariant in one call.
    """
    assert_reads_primary(resolved_primary_path, ctx, wp_id=wp_id)
    assert_status_from_coord(events_path, ctx)


__all__ = [
    "CoordTopologyContext",
    "FlatTopologyContext",
    "assert_both_legs",
    "assert_reads_primary",
    "assert_status_from_coord",
    "coord_topology_mission",
    "flat_topology_mission",
]
