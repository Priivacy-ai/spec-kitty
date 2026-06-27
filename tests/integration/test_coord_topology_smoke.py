"""Smoke tests for the shared coord-topology fixture (T003, FR-014, WP01).

Proves:
(a) Both coord and flat topology fixtures materialise with the correct on-disk shape.
(b) ``candidate_feature_dir_for_mission`` returns the STATUS-only coord husk for a
    coord-topology mission (missing ``tasks/``) — demonstrating the divergence this
    fixture is built to detect.
(c) ``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`` returns the PRIMARY dir for
    the same mission.
(d) No topology resolver is patched in the fixture module — functions are the real
    production implementations.

Additionally verifies that the dual-leg asserters fail loudly on wrong-surface paths
(self-proof that they cannot be fooled by a compliant but wrong resolver).

Run with::

    PWHEADLESS=1 pytest tests/integration/ -k coord_topology -q
"""

from __future__ import annotations

import pytest

from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    FlatTopologyContext,
    assert_reads_primary,
    assert_status_from_coord,
    coord_topology_mission,
    flat_topology_mission,
)

# Re-export fixtures so pytest discovers them for this module.
# (Importing a @pytest.fixture into the test module's namespace makes it
# available as a fixture parameter within that module.)
__all__ = ["coord_topology_mission", "flat_topology_mission"]

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


class TestCoordTopologyFixtureSmoke:
    """Smoke tests for the coord-topology fixture shape (T003 part a)."""

    def test_coord_topology_primary_has_planning_artifacts(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """(a) Primary checkout carries meta.json, tasks/WP01.md, lanes.json."""
        ctx = coord_topology_mission
        assert (ctx.primary_feature_dir / "meta.json").exists(), (
            "meta.json absent from primary dir"
        )
        assert (ctx.primary_feature_dir / "tasks" / "WP01.md").exists(), (
            "tasks/WP01.md absent from primary dir"
        )
        assert (ctx.primary_feature_dir / "lanes.json").exists(), (
            "lanes.json absent from primary dir"
        )

    def test_coord_topology_husk_is_status_only(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """(a) Coord husk carries status.events.jsonl only — no tasks/, no meta.json."""
        ctx = coord_topology_mission
        assert ctx.coord_feature_dir.exists(), "coord husk dir must exist"
        assert ctx.status_events_path.exists(), "status.events.jsonl must exist on coord husk"
        assert not (ctx.coord_feature_dir / "tasks").exists(), (
            "coord husk must NOT carry tasks/ (STATUS-only husk invariant)"
        )
        assert not (ctx.coord_feature_dir / "lanes.json").exists(), (
            "coord husk must NOT carry lanes.json (STATUS-only husk invariant)"
        )
        assert not (ctx.coord_feature_dir / "meta.json").exists(), (
            "coord husk must NOT carry meta.json (STATUS-only husk invariant; "
            "see implement.py:1020-1028)"
        )

    def test_flat_topology_primary_has_all_artifacts(
        self,
        flat_topology_mission: FlatTopologyContext,
    ) -> None:
        """(a) Flat topology: primary has all artifacts, no coord worktree."""
        ctx = flat_topology_mission
        assert (ctx.primary_feature_dir / "meta.json").exists()
        assert (ctx.primary_feature_dir / "tasks" / "WP01.md").exists()
        assert (ctx.primary_feature_dir / "lanes.json").exists()
        assert ctx.status_events_path.exists()
        # No coord worktree directory exists.
        coord_worktree_parent = ctx.repo / ".worktrees"
        if coord_worktree_parent.exists():
            coord_dirs = list(coord_worktree_parent.iterdir())
            assert not coord_dirs, (
                f"Unexpected coord worktree dirs for flat topology: {coord_dirs}"
            )


class TestCoordTopologyResolverRouting:
    """Smoke tests proving resolver routing behaviour (T003 parts b and c)."""

    def test_candidate_resolver_returns_coord_husk_for_coord_mission(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """(b) candidate_feature_dir_for_mission → coord husk (demonstrates the bug)."""
        from specify_cli.missions._read_path_resolver import candidate_feature_dir_for_mission

        ctx = coord_topology_mission
        resolved = candidate_feature_dir_for_mission(ctx.repo, ctx.slug)

        # The topology-unaware resolver returns the coord husk, not primary.
        assert resolved == ctx.coord_feature_dir, (
            f"Expected coord husk dir from topology-unaware resolver.\n"
            f"  Expected : {ctx.coord_feature_dir}\n"
            f"  Got      : {resolved}"
        )
        # Demonstrate the routing divergence: tasks/ is absent on the husk.
        assert not (resolved / "tasks").exists(), (
            "tasks/ should be absent from the coord husk — "
            "this is the WORK_PACKAGE_TASK routing bug that downstream WPs fix."
        )

    def test_resolve_planning_read_dir_returns_primary_for_work_package_task(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """(c) resolve_planning_read_dir(kind=WORK_PACKAGE_TASK) → primary dir."""
        from mission_runtime import MissionArtifactKind
        from specify_cli.missions._read_path_resolver import resolve_planning_read_dir

        ctx = coord_topology_mission
        primary = resolve_planning_read_dir(
            ctx.repo,
            ctx.slug,
            kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        )
        assert_reads_primary(primary, ctx)

    def test_flat_topology_both_resolvers_return_primary(
        self,
        flat_topology_mission: FlatTopologyContext,
    ) -> None:
        """Flat topology: both resolvers return the primary dir (neutrality leg)."""
        from mission_runtime import MissionArtifactKind
        from specify_cli.missions._read_path_resolver import (
            candidate_feature_dir_for_mission,
            resolve_planning_read_dir,
        )

        ctx = flat_topology_mission
        resolved_unguarded = candidate_feature_dir_for_mission(ctx.repo, ctx.slug)
        assert_reads_primary(resolved_unguarded, ctx)

        resolved_kind = resolve_planning_read_dir(
            ctx.repo,
            ctx.slug,
            kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        )
        assert_reads_primary(resolved_kind, ctx)


class TestNoResolverPatchedInFixture:
    """Confirm that the fixture module patches no topology resolver (T003 part d)."""

    def test_fixture_module_contains_no_resolver_patches(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """(d) Resolver functions are real production callables, not mocks."""
        import unittest.mock
        from specify_cli.missions import _read_path_resolver as resolver_mod

        target_functions = [
            "candidate_feature_dir_for_mission",
            "resolve_planning_read_dir",
            "resolve_handle_to_read_path",
            "primary_feature_dir_for_mission",
        ]
        for fn_name in target_functions:
            fn = getattr(resolver_mod, fn_name)
            assert not isinstance(fn, (unittest.mock.MagicMock, unittest.mock.NonCallableMock)), (
                f"{fn_name} is a Mock — a resolver was patched when it should not be."
            )
            assert callable(fn), f"{fn_name} is not callable after fixture setup"

    def test_fixture_source_imports_no_mock_patch(self) -> None:
        """Structural check: coord_topology_fixture module never USES mock.patch.

        The word 'monkeypatch' may appear in docstrings/comments stating it is
        NOT used; the check looks for actual CALL / IMPORT patterns only.
        """
        import inspect
        from tests.integration import coord_topology_fixture

        source = inspect.getsource(coord_topology_fixture)
        # Check for actual mock usage patterns (not the word in comments).
        assert "monkeypatch." not in source, (
            "coord_topology_fixture.py must not CALL monkeypatch (e.g. monkeypatch.setattr)"
        )
        assert "from unittest.mock import patch" not in source, (
            "coord_topology_fixture.py must not import unittest.mock.patch"
        )
        assert "@patch(" not in source, (
            "coord_topology_fixture.py must not use @patch decorators"
        )
        assert "mock.patch(" not in source, (
            "coord_topology_fixture.py must not use mock.patch()"
        )


class TestDualLegAsserterSelfProof:
    """Verify asserters fail loudly on wrong-surface paths (DoD guard)."""

    def test_assert_reads_primary_fails_on_coord_husk_path(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """assert_reads_primary must reject the coord husk path (tasks/ absent)."""
        ctx = coord_topology_mission
        with pytest.raises(AssertionError):
            assert_reads_primary(ctx.coord_feature_dir, ctx)

    def test_assert_status_from_coord_fails_on_primary_decoy_path(
        self,
        coord_topology_mission: CoordTopologyContext,
    ) -> None:
        """assert_status_from_coord must reject the primary decoy events path."""
        ctx = coord_topology_mission
        with pytest.raises(AssertionError):
            assert_status_from_coord(ctx.decoy_events_path, ctx)

    def test_assert_status_from_coord_fails_on_wrong_path_entirely(
        self,
        coord_topology_mission: CoordTopologyContext,
        tmp_path: pytest.TempPathFactory,
    ) -> None:
        """assert_status_from_coord must fail on any path that is not the coord husk."""
        ctx = coord_topology_mission
        # A completely wrong path (no events file at all) also fails.
        wrong_path = ctx.primary_feature_dir / "status.events.jsonl"
        with pytest.raises(AssertionError):
            assert_status_from_coord(wrong_path, ctx)
