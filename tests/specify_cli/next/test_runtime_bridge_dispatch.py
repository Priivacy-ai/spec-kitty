"""NFR-002 regression gate: _should_dispatch_via_composition via charter.resolve_mission_type_context.

WP07 / FR-007 / FR-008 / NFR-002.

These tests verify that after deleting _COMPOSED_ACTIONS_BY_MISSION, the dispatch
predicate still routes all built-in software-dev actions through composition, and that
the live charter.resolve_mission_type_context path is exercised (not a static frozenset).

The MissionTypeRepository is not yet implemented (later WP); these tests mock
charter.resolve_mission_type_context at the module level so they remain self-contained.
"""

from __future__ import annotations

import time
import types
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.next.runtime_bridge import (
    _normalize_action_for_composition,
    _should_dispatch_via_composition,
)


pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Known action sequences (mirrors built-in doctrine YAML values)
# ---------------------------------------------------------------------------

_SW_DEV_ACTIONS = ["specify", "plan", "tasks", "implement", "review"]
_DOCUMENTATION_ACTIONS = [
    "discover",
    "audit",
    "design",
    "generate",
    "validate",
    "publish",
    "accept",
]
_RESEARCH_ACTIONS = ["scoping", "methodology", "gathering", "synthesis", "output"]


def _inject_mission_type_repository_mock(
    mock_repo: MagicMock,
) -> dict:
    """Inject a mock MissionTypeRepository into sys.modules and return cleanup dict."""
    mock_repo_cls = MagicMock()
    mock_repo_cls.default.return_value = mock_repo

    fake_pkg = types.ModuleType("doctrine.missions")
    fake_module = types.ModuleType("doctrine.missions.mission_type_repository")
    fake_module.MissionTypeRepository = mock_repo_cls  # type: ignore[attr-defined]

    saved: dict = {}
    for key in ("doctrine.missions", "doctrine.missions.mission_type_repository"):
        saved[key] = sys.modules.get(key)

    if "doctrine.missions" not in sys.modules:
        sys.modules["doctrine.missions"] = fake_pkg
    sys.modules["doctrine.missions.mission_type_repository"] = fake_module
    return saved


def _restore_modules(saved: dict) -> None:
    for key, val in saved.items():
        if val is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = val


# ---------------------------------------------------------------------------
# NFR-002 regression gate: all software-dev steps dispatch via composition
# ---------------------------------------------------------------------------


class TestSoftwareDevDispatchNFR002:
    """Regression gate: spec-kitty next for all software-dev lanes dispatches correctly.

    NFR-002 requires zero regression in spec-kitty next behaviour for all
    existing software-dev missions after WP07.
    """

    def test_specify_step_dispatches_via_composition(self, tmp_path: Path) -> None:
        """software-dev at 'specify' lane dispatches via composition (not legacy DAG)."""
        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            return_value=types.SimpleNamespace(action_sequence=_SW_DEV_ACTIONS),
        ):
            assert _should_dispatch_via_composition(
                "software-dev", "specify", repo_root=tmp_path
            ) is True

    def test_plan_step_dispatches_via_composition(self, tmp_path: Path) -> None:
        """software-dev at 'plan' lane dispatches via composition."""
        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            return_value=types.SimpleNamespace(action_sequence=_SW_DEV_ACTIONS),
        ):
            assert _should_dispatch_via_composition(
                "software-dev", "plan", repo_root=tmp_path
            ) is True

    def test_tasks_step_dispatches_via_composition(self, tmp_path: Path) -> None:
        """software-dev at 'tasks' lane dispatches via composition."""
        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            return_value=types.SimpleNamespace(action_sequence=_SW_DEV_ACTIONS),
        ):
            assert _should_dispatch_via_composition(
                "software-dev", "tasks", repo_root=tmp_path
            ) is True

    def test_implement_step_dispatches_via_composition(self, tmp_path: Path) -> None:
        """software-dev at 'implement' lane dispatches via composition."""
        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            return_value=types.SimpleNamespace(action_sequence=_SW_DEV_ACTIONS),
        ):
            assert _should_dispatch_via_composition(
                "software-dev", "implement", repo_root=tmp_path
            ) is True

    def test_review_step_dispatches_via_composition(self, tmp_path: Path) -> None:
        """software-dev at 'review' lane dispatches via composition."""
        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            return_value=types.SimpleNamespace(action_sequence=_SW_DEV_ACTIONS),
        ):
            assert _should_dispatch_via_composition(
                "software-dev", "review", repo_root=tmp_path
            ) is True

    @pytest.mark.parametrize("action", _SW_DEV_ACTIONS)
    def test_all_software_dev_steps_dispatch_via_composition(
        self, action: str, tmp_path: Path
    ) -> None:
        """Parametrized gate: all five software-dev actions return True."""
        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            return_value=types.SimpleNamespace(action_sequence=_SW_DEV_ACTIONS),
        ):
            assert _should_dispatch_via_composition(
                "software-dev", action, repo_root=tmp_path
            ) is True


# ---------------------------------------------------------------------------
# Verify frozensets are gone
# ---------------------------------------------------------------------------


class TestFrozensetsDeletion:
    """Acceptance criterion: _COMPOSED_ACTIONS_BY_MISSION must not exist."""

    def test_composed_actions_by_mission_does_not_exist(self) -> None:
        """_COMPOSED_ACTIONS_BY_MISSION MUST NOT be importable from runtime_bridge."""
        import runtime.next.runtime_bridge as bridge

        assert not hasattr(bridge, "_COMPOSED_ACTIONS_BY_MISSION"), (
            "_COMPOSED_ACTIONS_BY_MISSION still exists in runtime_bridge — FR-007 violated"
        )

    def test_charter_call_site_reached(self, tmp_path: Path) -> None:
        """_should_dispatch_via_composition calls charter, not a static table."""
        call_log: list[str] = []

        def _record_call(
            repo_root: object, *, mission_type: str | None = None, feature_dir: object = None
        ) -> types.SimpleNamespace:
            call_log.append(mission_type)
            return types.SimpleNamespace(action_sequence=_SW_DEV_ACTIONS)

        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            side_effect=_record_call,
        ):
            result = _should_dispatch_via_composition(
                "software-dev", "specify", repo_root=tmp_path
            )

        assert result is True
        assert "software-dev" in call_log, (
            "_should_dispatch_via_composition did not call charter.resolve_mission_type_context"
        )


# ---------------------------------------------------------------------------
# Legacy tasks step normalization still works
# ---------------------------------------------------------------------------


class TestLegacyTasksNormalization:
    """Regression: legacy tasks_* step IDs still collapse to 'tasks'."""

    @pytest.mark.parametrize("step_id", ["tasks_outline", "tasks_packages", "tasks_finalize"])
    def test_legacy_step_collapses_to_tasks(self, step_id: str) -> None:
        assert _normalize_action_for_composition(step_id) == "tasks"

    @pytest.mark.parametrize(
        "step_id", ["specify", "plan", "tasks", "implement", "review", "accept"]
    )
    def test_non_legacy_steps_pass_through(self, step_id: str) -> None:
        assert _normalize_action_for_composition(step_id) == step_id

    def test_legacy_tasks_step_dispatches_via_composition(self, tmp_path: Path) -> None:
        """tasks_outline / tasks_packages / tasks_finalize normalize to 'tasks'."""
        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            return_value=types.SimpleNamespace(action_sequence=_SW_DEV_ACTIONS),
        ):
            for legacy_id in ("tasks_outline", "tasks_packages", "tasks_finalize"):
                assert _should_dispatch_via_composition(
                    "software-dev", legacy_id, repo_root=tmp_path
                ) is True, f"{legacy_id} should dispatch via composition after normalization"


# ---------------------------------------------------------------------------
# Graceful degradation: unknown mission type returns False, not an exception
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """If charter raises for an unknown mission type, degrade to False."""

    def test_unknown_mission_type_returns_false(self, tmp_path: Path) -> None:
        """An unknown mission type causes degradation to False (not a crash)."""
        from charter.mission_type_profiles import UnknownMissionTypeError

        with patch(
            "charter.mission_type_profiles.resolve_mission_type_context",
            side_effect=UnknownMissionTypeError("unknown-type"),
        ):
            result = _should_dispatch_via_composition(
                "unknown-type", "some-action", repo_root=tmp_path
            )

        assert result is False

    def test_none_repo_root_falls_through_gracefully(self) -> None:
        """When repo_root=None, the charter lookup is skipped (no crash)."""
        # Without repo_root, falls through to the custom widening path.
        # Without run_dir either, returns False.
        result = _should_dispatch_via_composition("software-dev", "specify")
        assert result is False


# ---------------------------------------------------------------------------
# NFR-001: Performance smoke test (≤100ms for warm filesystem)
# ---------------------------------------------------------------------------


class TestPerformance:
    """NFR-001: charter.resolve_mission_type_context completes within 100ms (warm filesystem)."""

    def test_resolve_mission_type_context_within_100ms(self, tmp_path: Path) -> None:
        """charter.resolve_mission_type_context(repo_root, mission_type='software-dev') < 100ms."""
        # Build a mock repo that returns immediately (no I/O).
        sw_dev = MagicMock()
        sw_dev.id = "software-dev"
        sw_dev.action_sequence = _SW_DEV_ACTIONS
        sw_dev.extends = None

        mock_repo = MagicMock()
        mock_repo.get.side_effect = lambda k: sw_dev if k == "software-dev" else None
        saved = _inject_mission_type_repository_mock(mock_repo)

        try:
            with patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["documentation", "plan", "research", "software-dev"],
            ):
                from charter.mission_type_profiles import resolve_mission_type_context

                # Warm the import cache.
                resolve_mission_type_context(tmp_path, mission_type="software-dev")

                # Time the second (warm) call.
                start = time.monotonic()
                result = resolve_mission_type_context(
                    tmp_path, mission_type="software-dev"
                ).action_sequence
                elapsed_ms = (time.monotonic() - start) * 1000
        finally:
            _restore_modules(saved)

        assert result == _SW_DEV_ACTIONS
        assert elapsed_ms < 100, (
            f"charter.resolve_mission_type_context took {elapsed_ms:.1f}ms — exceeds 100ms NFR-001 budget"
        )


class TestNFR001LazyGovernanceBoundary:
    """NFR-001: the real hot path never triggers action-grain I/O (WP05).

    The previous NFR-001 gate here (``test_pack_context_from_config_p99_under_100ms``)
    timed ``charter.pack_context.PackContext.from_config()`` — a function that
    never calls :func:`~charter.mission_type_profiles.resolve_mission_type_context`
    or ``load_action_index`` at all, so it could never regress under the budget
    it claimed to protect. It is replaced with a direct spy over the ACTUAL
    disk-reading call the budget exists for:
    ``charter.mission_type_profiles.aggregate_action_grain`` (imported from
    :mod:`charter.action_grain`), which the ``governance_thunk`` built by
    ``_resolve_governance_slot`` invokes lazily behind
    ``ResolvedMissionType.governance``'s ``@cached_property`` — and which
    transitively fans out to
    :func:`doctrine.missions.action_index.load_action_index` for every action
    a mission type ships.

    ``TestPerformance.test_resolve_mission_type_context_within_100ms`` above
    (mocks ``.action_sequence`` via an injected ``MissionTypeRepository``) is a
    separate smoke timing; it is not the hot-path proof — a call-count spy is a
    stronger, environment-independent guarantee than a millisecond budget.
    """

    def test_action_sequence_only_path_never_triggers_action_grain(
        self, tmp_path: Path
    ) -> None:
        """The real production hot path (``.action_sequence`` only) does zero action-grain I/O."""
        from charter.mission_type_profiles import resolve_mission_type_context

        with patch(
            "charter.mission_type_profiles.aggregate_action_grain"
        ) as spy_aggregate:
            bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
            # This is the real hot path: runtime-next's FSM reads only
            # `.action_sequence`, never `.governance`.
            assert bundle.action_sequence == _SW_DEV_ACTIONS

        spy_aggregate.assert_not_called()

    def test_first_governance_access_triggers_action_grain_aggregation(
        self, tmp_path: Path
    ) -> None:
        """Proves the lazy boundary is real: first ``.governance`` read DOES call it."""
        from charter.mission_type_profiles import resolve_mission_type_context

        with patch(
            "charter.mission_type_profiles.aggregate_action_grain",
            return_value={},
        ) as spy_aggregate:
            bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
            spy_aggregate.assert_not_called()

            _ = bundle.governance

        spy_aggregate.assert_called_once()
        called_type = spy_aggregate.call_args.args[1]
        assert called_type == "software-dev"
