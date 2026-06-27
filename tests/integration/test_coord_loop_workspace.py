"""Integration tests for WP05: workspace/context + context/resolver + task_utils
reads routed to planning seam.

Per-site RED-first tests proving the coord-topology routing invariant for each
routed site in:
- ``workspace/context.py`` (build_normalized_wp_index, get_normalized_wp,
  resolve_active_wp_for_branch, resolve_workspace_for_wp, resolve_feature_worktree)
- ``context/resolver.py`` (resolve_context)
- ``task_utils/support.py`` (locate_work_package)

RED-first proof (documented inline per site): before WP05, the routed sites used
coord-aware resolvers (``resolve_feature_dir_for_slug``,
``resolve_feature_dir_for_mission``) for ``tasks/`` and ``lanes.json`` reads. The
coord husk carries NO ``tasks/`` directory and NO ``lanes.json`` — STATUS-only
invariant (INV-2) — so all functions would either:
- Return empty / raise ValueError (tasks/ missing) when the mission has coord topology
- Raise MissingLanesError / return None (lanes.json missing from coord husk)

After WP05, ``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`` routes PRIMARY-
partition tasks reads to the primary checkout, and ``resolve_planning_read_dir(
kind=LANE_STATE)`` routes lanes.json reads to the primary checkout. The STATUS leg
(``get_all_wp_lanes``) stays on the coord-aware ``resolve_feature_dir_for_slug``
(C-001 per-leg split, MIXED-read discipline).

Fixture layout (from ``coord_topology_mission``):

* ``primary_feature_dir/``      — meta.json, tasks/WP01.md, lanes.json, DECOY events
* ``coord_feature_dir/``        — status.events.jsonl ONLY (coord marker)
* No tasks/ or lanes.json in coord_feature_dir

See ``tests/integration/coord_topology_fixture.py`` for fixture details.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    coord_topology_mission,
)

# Re-export fixture so pytest discovers it in this module.
__all__ = ["coord_topology_mission"]

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# ---------------------------------------------------------------------------
# Real ULID event IDs — Crockford base32, 26 chars (testing-principles styleguide)
# ---------------------------------------------------------------------------

_COORD_EVENT_WP01_PLANNED_CLAIMED = "01KW2E7AFC0000000000000011"
_COORD_EVENT_WP01_CLAIMED_INPROG = "01KW2E7AFC0000000000000012"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_parseable_in_progress_events(ctx: CoordTopologyContext) -> None:
    """Replace coord husk events with valid, parseable events for WP01 at in_progress.

    After this call:
    - Coord husk: WP01 at ``in_progress`` (planned→claimed + claimed→in_progress).
    - Primary DECOY: original fixture content (marker string evidence — causes
      StatusEvent.from_dict TypeError → reducer fallback ``planned``).

    A wrong-leg STATUS read produces lane=``planned``; the correct coord read
    produces lane=``in_progress`` — a clear per-leg signal.
    """
    events = [
        {
            "actor": "wp05-test",
            "at": "2026-06-26T00:00:00+00:00",
            "event_id": _COORD_EVENT_WP01_PLANNED_CLAIMED,
            "evidence": None,
            "execution_mode": "code_change",
            "feature_slug": ctx.slug,
            "force": False,
            "from_lane": "planned",
            "reason": None,
            "review_ref": None,
            "to_lane": "claimed",
            "wp_id": "WP01",
        },
        {
            "actor": "wp05-test",
            "at": "2026-06-26T01:00:00+00:00",
            "event_id": _COORD_EVENT_WP01_CLAIMED_INPROG,
            "evidence": None,
            "execution_mode": "code_change",
            "feature_slug": ctx.slug,
            "force": False,
            "from_lane": "claimed",
            "reason": None,
            "review_ref": None,
            "to_lane": "in_progress",
            "wp_id": "WP01",
        },
    ]
    with ctx.status_events_path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")


def _write_explicit_code_change_wp(feature_dir: Path, wp_id: str = "WP01") -> None:
    """Overwrite the fixture WP task file with explicit execution_mode: code_change.

    The fixture's WP01.md uses minimal frontmatter (no execution_mode). This helper
    rewrites it with an explicit ``execution_mode: code_change`` so WP-metadata
    reads are unambiguous and inference is not needed.
    """
    content = (
        f"---\n"
        f"work_package_id: {wp_id}\n"
        f"title: {wp_id} WP05 test task\n"
        f"execution_mode: code_change\n"
        f"owned_files:\n"
        f"- src/placeholder.py\n"
        f"---\n"
        f"# {wp_id}\n"
        f"\nA WP05 integration test work package.\n"
    )
    (feature_dir / "tasks" / f"{wp_id}.md").write_text(content, encoding="utf-8")


def _write_complete_lanes_json(
    feature_dir: Path, *, slug: str, mission_id: str
) -> None:
    """Write a lanes.json with all required fields (computed_at, computed_from).

    The fixture's _write_lanes_json omits computed_at/computed_from; LanesManifest
    .from_dict requires them. This helper writes a fully parseable manifest.
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
        "computed_from": "wp05-test-fixture",
        "planning_artifact_wps": [],
    }
    (feature_dir / "lanes.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _write_parseable_status_events(feature_dir: Path, slug: str) -> None:
    """Write parseable (evidence=None) status events to feature_dir/status.events.jsonl.

    The fixture writes string evidence values which cause StoreError when parsed
    by the status reducer. This helper replaces them with null evidence so tests
    that need the events to be parseable (e.g. locate_work_package → get_wp_lane)
    can proceed.
    """
    events_path = feature_dir / "status.events.jsonl"
    event = {
        "actor": "wp05-test",
        "at": "2026-06-26T00:00:00+00:00",
        "event_id": "01KW2E7AFC0000000000000021",
        "evidence": None,
        "execution_mode": "code_change",
        "feature_slug": slug,
        "force": False,
        "from_lane": "planned",
        "reason": None,
        "review_ref": None,
        "to_lane": "claimed",
        "wp_id": "WP01",
    }
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")


def _make_workspace_context_json(
    slug: str,
    lane_branch: str,
    worktree_path: str,
) -> dict[str, object]:
    """Build a minimal workspace context dict for saving to .kittify/workspaces/."""
    return {
        "wp_id": "WP01",
        "mission_slug": slug,
        "worktree_path": worktree_path,
        "branch_name": lane_branch,
        "base_branch": "main",
        "base_commit": None,
        "dependencies": [],
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": "wp05-test",
        "vcs_backend": "git",
        "lane_id": "lane-a",
        "lane_wp_ids": ["WP01"],
        "current_wp": "WP01",
        "lane_test_env": None,
    }


def _save_workspace_context(repo: Path, slug: str, lane_branch: str) -> None:
    """Create a .kittify/workspaces/ context file for the coord fixture lane."""
    workspaces_dir = repo / ".kittify" / "workspaces"
    workspaces_dir.mkdir(parents=True, exist_ok=True)
    # Workspace file name mirrors the lane worktree dir name.
    # For "lane-a" without mission_id → "<slug>-lane-a.json"
    workspace_name = f"{slug}-lane-a"
    ctx_data = _make_workspace_context_json(
        slug=slug,
        lane_branch=lane_branch,
        worktree_path=f".worktrees/{workspace_name}",
    )
    (workspaces_dir / f"{workspace_name}.json").write_text(
        json.dumps(ctx_data, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# T021 — build_normalized_wp_index: tasks/ reads PRIMARY for coord topology
# ---------------------------------------------------------------------------


class TestBuildNormalizedWpIndex:
    """WP05/T021: build_normalized_wp_index tasks/ read routes to PRIMARY.

    RED-FIRST PROOF (pre-WP05):
    Before routing, ``build_normalized_wp_index`` uses
    ``resolve_feature_dir_for_slug`` (coord-aware) → the coord husk → no
    ``tasks/`` directory → ``tasks_dir.is_dir()`` is False → returns ``{}``.
    Assertion ``"WP01" in result`` therefore FAILS (RED).

    After WP05, ``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`` returns the
    PRIMARY dir → ``tasks/WP01.md`` is present → result contains ``"WP01"`` (GREEN).
    """

    def test_coord_topology_reads_tasks_from_primary(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """tasks/ reads for a coord-topology mission resolve to PRIMARY, not coord husk.

        RED-first: coord husk has no tasks/ → build_normalized_wp_index returns {}
        → "WP01" not in result (FAILS before WP05 fix).
        """
        from specify_cli.workspace.context import (
            build_normalized_wp_index,
            clear_workspace_resolution_caches,
        )

        ctx = coord_topology_mission
        _write_explicit_code_change_wp(ctx.primary_feature_dir)
        clear_workspace_resolution_caches()

        result = build_normalized_wp_index(ctx.repo, ctx.slug)

        assert "WP01" in result, (
            f"build_normalized_wp_index returned {list(result.keys())!r} — "
            "expected WP01 to be found. "
            "Before WP05 the coord husk has no tasks/ dir; after routing it reads "
            "from the primary checkout where tasks/WP01.md exists."
        )
        assert result["WP01"].metadata.execution_mode == "code_change"
        # Path must come from PRIMARY (not coord husk).
        assert str(ctx.primary_feature_dir) in str(result["WP01"].path), (
            f"WP01 path {result['WP01'].path} should be under PRIMARY "
            f"{ctx.primary_feature_dir}."
        )


# ---------------------------------------------------------------------------
# T021 — get_normalized_wp :714 not-found path uses PRIMARY dir in message
# ---------------------------------------------------------------------------


class TestGetNormalizedWpNotFoundPath:
    """WP05/T021: :714 not-found message refers to the PRIMARY tasks/ dir.

    RED-FIRST PROOF (pre-WP05):
    Before routing, the inline ``resolve_feature_dir_for_slug(...)  / 'tasks'``
    expression at :714 names the COORD husk tasks dir (absent on disk). The error
    message therefore contains the coord-husk path, not the primary path.
    Assertion ``str(ctx.primary_feature_dir / "tasks") in str(exc.value)``
    therefore FAILS (RED — message names coord dir).

    After WP05, the expression routes to PRIMARY → the primary tasks/ path
    appears in the message (GREEN).
    """

    def test_not_found_message_names_primary_tasks_dir(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """get_normalized_wp :714 error message names the PRIMARY tasks/ path.

        RED-first: coord-aware resolver gives coord husk path → message has coord
        dir, not primary → assertion on primary path FAILS before WP05 fix.
        """
        from specify_cli.workspace.context import (
            clear_workspace_resolution_caches,
            get_normalized_wp,
        )

        ctx = coord_topology_mission
        _write_explicit_code_change_wp(ctx.primary_feature_dir)
        clear_workspace_resolution_caches()

        with pytest.raises(ValueError) as exc_info:
            get_normalized_wp(ctx.repo, ctx.slug, "WP99")

        error_msg = str(exc_info.value)
        expected_path = str(ctx.primary_feature_dir / "tasks")
        assert expected_path in error_msg, (
            f"Error message does not name the PRIMARY tasks dir.\n"
            f"  Expected path : {expected_path}\n"
            f"  Error message : {error_msg}\n"
            "Before WP05 the message names the coord husk path; after routing it "
            "names the primary path where tasks actually live."
        )


# ---------------------------------------------------------------------------
# T022 — resolve_active_wp_for_branch: tasks PRIMARY, status COORD (MIXED split)
# ---------------------------------------------------------------------------


class TestResolveActiveWpForBranchMixedSplit:
    """WP05/T022: resolve_active_wp_for_branch per-leg split.

    - PRIMARY leg (WP-frontmatter read): routes to primary checkout so
      ``_find_wp_file(planning_dir / "tasks", active_wp_id)`` finds WP01.md.
    - STATUS leg (``get_all_wp_lanes``): stays coord-aware so canonical events
      from the coord husk are used for lane resolution.

    RED-FIRST PROOF (pre-WP05):
    Before routing, ``_find_wp_file(feature_dir / "tasks", "WP01")`` uses the
    coord-aware ``feature_dir`` → coord husk → no ``tasks/`` → returns None →
    result.diagnostic_code == "ACTIVE_WP_METADATA_MISSING". The assertion
    ``result.diagnostic_code is None`` therefore FAILS (RED).

    After WP05, the split uses ``planning_dir / "tasks"`` (PRIMARY) →
    WP01.md found → result.diagnostic_code is None (GREEN).
    """

    def test_tasks_from_primary_status_from_coord(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """resolve_active_wp_for_branch: WP frontmatter reads PRIMARY; status reads COORD.

        RED-first: tasks/ read goes to coord husk (no tasks/) → ACTIVE_WP_METADATA_MISSING
        → result.diagnostic_code is not None → assertion FAILS before WP05 fix.
        """
        from specify_cli.workspace.context import (
            clear_workspace_resolution_caches,
            resolve_active_wp_for_branch,
        )

        ctx = coord_topology_mission
        # Write WP01.md with explicit code_change to primary (not coord husk).
        _write_explicit_code_change_wp(ctx.primary_feature_dir)
        # Put WP01 at in_progress on the coord husk (authoritative STATUS leg).
        _write_parseable_in_progress_events(ctx)
        # Create a workspace context with a lane branch the resolver can find.
        lane_branch = f"kitty/mission-{ctx.slug}-lane-a"
        _save_workspace_context(ctx.repo, ctx.slug, lane_branch)
        clear_workspace_resolution_caches()

        result = resolve_active_wp_for_branch(ctx.repo, lane_branch)

        assert result.diagnostic_code is None, (
            f"Expected no diagnostic, got {result.diagnostic_code!r}: "
            f"{result.diagnostic_message!r}.\n"
            "Before WP05 the tasks read goes to the coord husk (no tasks/ dir) → "
            "ACTIVE_WP_METADATA_MISSING. After routing it reads from PRIMARY."
        )
        assert result.wp_id == "WP01", (
            f"Expected wp_id='WP01', got {result.wp_id!r}."
        )

    def test_status_leg_stays_coord_for_in_progress(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """STATUS leg: get_all_wp_lanes reads from the coord husk (C-001 invariant).

        The coord husk's events put WP01 at in_progress. A wrong PRIMARY-leg STATUS
        read would use the DECOY events (non-parseable → reducer fallback →
        no in_progress candidates → ACTIVE_WP_CONTEXT_AMBIGUOUS or
        ACTIVE_WP_STATUS_UNAVAILABLE). Reading from COORD is the correct behavior.

        RED-first: before WP05 the tasks read fails → ACTIVE_WP_METADATA_MISSING
        → result.diagnostic_code is not None (FAILS). After WP05, both legs are
        routed correctly: tasks from PRIMARY (WP01.md found) AND status from COORD
        (in_progress) → diagnostic_code is None (GREEN).
        """
        from specify_cli.workspace.context import (
            clear_workspace_resolution_caches,
            resolve_active_wp_for_branch,
        )

        ctx = coord_topology_mission
        _write_explicit_code_change_wp(ctx.primary_feature_dir)
        _write_parseable_in_progress_events(ctx)
        lane_branch = f"kitty/mission-{ctx.slug}-lane-a"
        _save_workspace_context(ctx.repo, ctx.slug, lane_branch)
        clear_workspace_resolution_caches()

        result = resolve_active_wp_for_branch(ctx.repo, lane_branch)

        # Full resolution must succeed (both legs correct).
        assert result.diagnostic_code is None, (
            f"Expected no diagnostic, got {result.diagnostic_code!r}: "
            f"{result.diagnostic_message!r}. "
            "After WP05 tasks come from PRIMARY (found WP01.md) AND status comes "
            "from COORD (found in_progress for WP01). If status were wrong-legged "
            "to PRIMARY (DECOY events → non-parseable) the status read would fail."
        )
        assert result.wp_id == "WP01"
        # context_source == "canonical_status" proves the status was read and WP01
        # was confirmed active; "workspace_context" would mean stale context used.
        assert result.context_source == "canonical_status"


# ---------------------------------------------------------------------------
# T021 — resolve_workspace_for_wp (code_change arm): lanes.json reads PRIMARY
# ---------------------------------------------------------------------------


class TestResolveWorkspaceForWpLanesFromPrimary:
    """WP05/T021: resolve_workspace_for_wp code_change arm lanes.json reads PRIMARY.

    RED-FIRST PROOF (pre-WP05):
    Before routing, ``build_normalized_wp_index`` uses the coord-aware resolver →
    coord husk → no ``tasks/`` → returns ``{}`` → ``get_normalized_wp`` raises
    ValueError("WP01 not found"). The top-level assertion (``result.lane_id ==
    "lane-a"``) FAILS (RED) — the call errors out before reaching lanes.json.

    After all WP05 routes applied:
    - ``build_normalized_wp_index`` reads from PRIMARY → WP01 found.
    - ``require_lanes_json(lanes_read_dir)`` routes to PRIMARY → lanes.json found.
    - ``result.lane_id == "lane-a"`` (GREEN).
    """

    def test_lanes_json_read_from_primary_for_code_change_wp(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """resolve_workspace_for_wp: lanes.json resolved from PRIMARY checkout.

        RED-first: coord-aware resolver → tasks/ absent on coord husk → ValueError
        on WP01 not found → test FAILS before WP05 (both tasks and lanes routing
        needed to go GREEN).
        """
        from specify_cli.workspace.context import (
            clear_workspace_resolution_caches,
            resolve_workspace_for_wp,
        )

        ctx = coord_topology_mission
        _write_explicit_code_change_wp(ctx.primary_feature_dir)
        # lanes.json already written by coord_topology_mission fixture (complete).
        clear_workspace_resolution_caches()

        result = resolve_workspace_for_wp(ctx.repo, ctx.slug, "WP01")

        assert result.lane_id == "lane-a", (
            f"Expected lane_id='lane-a', got {result.lane_id!r}.\n"
            "lanes.json is on the PRIMARY checkout; before routing the coord-aware "
            "resolver gives the coord husk where lanes.json is absent → either "
            "ValueError (tasks not found) or MissingLanesError (lanes not found). "
            "After routing both tasks and lanes.json are found on PRIMARY."
        )
        assert result.mission_slug == ctx.slug

    def test_require_lanes_json_fail_closed_semantics_preserved(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """lanes.json absent from PRIMARY still raises MissingLanesError (fail-closed).

        After WP05 routes the lanes.json read to PRIMARY, removing lanes.json from
        the primary dir must still raise MissingLanesError. This verifies the
        fail-closed semantics are preserved: routing to PRIMARY does not swallow
        the absence.

        RED-first: before WP05, this raises ValueError (tasks not found on coord
        husk) rather than MissingLanesError — but the test is RED either way
        because the assertion ``pytest.raises(MissingLanesError)`` is not what
        fires (it fails with the wrong exception before WP05).
        """
        from specify_cli.lanes.persistence import MissingLanesError
        from specify_cli.workspace.context import (
            clear_workspace_resolution_caches,
            resolve_workspace_for_wp,
        )

        ctx = coord_topology_mission
        _write_explicit_code_change_wp(ctx.primary_feature_dir)
        # lanes.json already written by coord_topology_mission fixture (complete).
        # Remove lanes.json from PRIMARY to test fail-closed behavior.
        lanes_file = ctx.primary_feature_dir / "lanes.json"
        lanes_file.unlink()
        clear_workspace_resolution_caches()

        with pytest.raises(MissingLanesError):
            resolve_workspace_for_wp(ctx.repo, ctx.slug, "WP01")

        # Restore lanes.json so the coord worktree remains valid.
        _write_complete_lanes_json(ctx.primary_feature_dir, slug=ctx.slug, mission_id=ctx.mission_id)


# ---------------------------------------------------------------------------
# T021 — resolve_feature_worktree: lanes.json reads PRIMARY
# ---------------------------------------------------------------------------


class TestResolveFeatureWorktreeLanesFromPrimary:
    """WP05/T021: resolve_feature_worktree lanes.json reads PRIMARY.

    RED-FIRST PROOF (pre-WP05):
    Before routing, ``resolve_feature_dir_for_slug`` (coord-aware) gives the coord
    husk → ``read_lanes_json(coord_dir)`` returns None (no lanes.json on husk) →
    the lanes loop is skipped → function returns None.

    Proof approach: corrupt the PRIMARY lanes.json. Before WP05, coord husk is
    consulted → no lanes.json → returns None (no CorruptLanesError). After WP05,
    PRIMARY is consulted → corrupted lanes.json → CorruptLanesError raised. The
    test asserts ``pytest.raises(CorruptLanesError)``, which FAILS (DID NOT RAISE)
    before WP05 (RED) and PASSES after (GREEN).
    """

    def test_lanes_json_consulted_from_primary(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """resolve_feature_worktree: lanes.json from PRIMARY is consulted.

        Corruption probe: corrupt PRIMARY lanes.json → before WP05, coord husk has
        no lanes.json → read_lanes_json returns None → DID NOT RAISE (RED). After
        WP05, PRIMARY is read → CorruptLanesError raised (GREEN).
        """
        from specify_cli.lanes.persistence import CorruptLanesError
        from specify_cli.workspace.context import (
            clear_workspace_resolution_caches,
            resolve_feature_worktree,
        )

        ctx = coord_topology_mission
        # Corrupt the primary lanes.json to prove it IS read (raises CorruptLanesError).
        (ctx.primary_feature_dir / "lanes.json").write_text(
            "NOT VALID JSON {{{{", encoding="utf-8"
        )
        clear_workspace_resolution_caches()

        with pytest.raises(CorruptLanesError):
            resolve_feature_worktree(ctx.repo, ctx.slug)

    def test_returns_none_when_no_lane_worktree_exists(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """resolve_feature_worktree: returns None when no matching lane worktree on disk.

        After WP05, PRIMARY lanes.json is consulted. The fixture's lane-a worktree
        path does not exist on disk → the function returns None. Verifies that a
        valid PRIMARY lanes.json is correctly read (not silently skipped) by
        confirming the resolution completes without error.
        """
        from specify_cli.workspace.context import (
            clear_workspace_resolution_caches,
            resolve_feature_worktree,
        )

        ctx = coord_topology_mission
        # lanes.json already written by coord_topology_mission fixture (complete).
        clear_workspace_resolution_caches()

        # No lane worktrees exist → None returned (lanes.json read but no path on disk).
        result = resolve_feature_worktree(ctx.repo, ctx.slug)

        assert result is None, (
            f"Expected None (no lane worktree on disk), got {result!r}.\n"
            "The lanes.json is read from PRIMARY but no lane-a worktree was created."
        )


# ---------------------------------------------------------------------------
# T023 — context/resolver.py resolve_context: WP reads PRIMARY
# ---------------------------------------------------------------------------


class TestResolveContextReadsFromPrimary:
    """WP05/T023: context/resolver.resolve_context WP reads route to PRIMARY.

    RED-FIRST PROOF (pre-WP05):
    Before routing, ``resolve_feature_dir_for_mission`` (coord-aware) returns the
    coord husk → ``_read_meta_json(coord_dir)`` raises MissingIdentityError
    (meta.json absent on husk) → FeatureNotFoundError propagated.
    The assertion that resolve_context succeeds FAILS (RED).

    After WP05 (primary-anchor pattern), the actual reads (meta, WP frontmatter,
    lanes.json) use the PRIMARY dir → meta.json + tasks/ + lanes.json found →
    resolve_context succeeds (GREEN).
    """

    def test_resolve_context_reads_wp_from_primary(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """resolve_context: WP frontmatter and lanes.json are read from PRIMARY.

        RED-first: coord-aware resolver gives coord husk → _read_meta_json raises
        MissingIdentityError (no meta.json on husk) → test FAILS before WP05.
        """
        from specify_cli.context.errors import FeatureNotFoundError
        from specify_cli.context.resolver import resolve_context

        ctx = coord_topology_mission
        # Write explicit WP01.md with code_change to primary (coord husk has no tasks/).
        _write_explicit_code_change_wp(ctx.primary_feature_dir)
        # lanes.json already written by coord_topology_mission fixture (complete).
        # Ensure .kittify/config.yaml exists (required by _read_project_uuid).
        kittify_dir = ctx.repo / ".kittify"
        kittify_dir.mkdir(parents=True, exist_ok=True)
        config_path = kittify_dir / "config.yaml"
        config_path.write_text(
            "project:\n  uuid: 01KW2E7A-TEST-UUID-FOR-WP05-FIXTURE\n",
            encoding="utf-8",
        )

        try:
            context = resolve_context(
                wp_code="WP01",
                mission_slug=ctx.slug,
                agent="wp05-test",
                repo_root=ctx.repo,
            )
        except FeatureNotFoundError as exc:
            pytest.fail(
                f"resolve_context raised FeatureNotFoundError: {exc}\n"
                "Before WP05 the coord husk has no meta.json, so the coord-aware "
                "resolver fails on _read_meta_json. After the primary-anchor fix "
                "meta.json is read from PRIMARY."
            )

        assert context.mission_slug == ctx.slug
        assert context.wp_code == "WP01"


# ---------------------------------------------------------------------------
# T023 — task_utils/support.py locate_work_package: tasks/ reads PRIMARY
# ---------------------------------------------------------------------------


class TestLocateWorkPackageReadsFromPrimary:
    """WP05/T023: locate_work_package tasks/ read routes to PRIMARY.

    RED-FIRST PROOF (pre-WP05):
    Before routing, ``resolve_feature_dir_for_slug`` (coord-aware) returns the
    coord husk → ``tasks_root = feature_path / "tasks"`` → coord husk has no
    tasks/ → ``TaskCliError("Feature has no tasks directory")`` raised.
    The assertion that WP01 is found FAILS (RED).

    After WP05, ``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`` returns
    PRIMARY → tasks/WP01.md exists → WorkPackage returned (GREEN).
    """

    def test_locate_work_package_reads_tasks_from_primary(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """locate_work_package: tasks/ resolved from PRIMARY checkout for coord topology.

        RED-first: coord husk has no tasks/ → TaskCliError raised → test FAILS
        before WP05 fix.
        """
        from specify_cli.task_utils.support import TaskCliError, locate_work_package

        ctx = coord_topology_mission
        _write_explicit_code_change_wp(ctx.primary_feature_dir)
        # Write parseable status events so get_wp_lane succeeds.
        _write_parseable_status_events(ctx.primary_feature_dir, ctx.slug)

        try:
            wp = locate_work_package(ctx.repo, ctx.slug, "WP01")
        except TaskCliError as exc:
            pytest.fail(
                f"locate_work_package raised TaskCliError: {exc}\n"
                "Before WP05 the coord husk has no tasks/ dir; after routing it "
                "reads from the primary checkout where tasks/WP01.md exists."
            )

        assert wp is not None
        # The path must come from PRIMARY (not the coord husk).
        assert str(ctx.primary_feature_dir) in str(wp.path), (
            f"WorkPackage path {wp.path} should be under PRIMARY "
            f"{ctx.primary_feature_dir}."
        )
