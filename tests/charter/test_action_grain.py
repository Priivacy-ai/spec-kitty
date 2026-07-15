"""Unit tests for charter.action_grain (WP02 / IC-07).

Covers:
- T004: action_index_to_mapping pure adapter round-trips (populated + empty)
- T005: aggregate_action_grain for a non-empty built-in type (software-dev),
  an empty-content built-in type (plan), and a synthetic missing-actions-dir
  fixture (the defensive branch no real built-in type exercises)
- T006: scan_builtin_cross_grain_duplicates is clean for all four shipped
  mission types (no CrossGrainDoubleDeclarationError)

Self-contained: uses the real built-in missions root (via the session-scoped
``repo_root`` fixture already provided by tests/charter/conftest.py) and
``tmp_path`` for the synthetic fixture — no new conftest.py is added.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from charter.action_grain import (
    action_index_to_mapping,
    aggregate_action_grain,
    scan_builtin_cross_grain_duplicates,
)
from charter.mission_type_profiles import CANONICAL_MISSION_TYPES
from doctrine.missions.action_index import ActionIndex


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


@pytest.fixture
def missions_root(repo_root: Path) -> Path:
    """The real shipped missions root: ``src/doctrine/missions``."""
    return repo_root / "src" / "doctrine" / "missions"


# ---------------------------------------------------------------------------
# T004 — action_index_to_mapping
# ---------------------------------------------------------------------------


class TestActionIndexToMapping:
    """Pure adapter: ActionIndex -> dict[str, list[str]], no I/O."""

    def test_populated_index_round_trips(self) -> None:
        index = ActionIndex(
            action="implement",
            directives=["010-specification-fidelity-requirement"],
            tactics=["stopping-conditions"],
            paradigms=["tdd"],
            styleguides=["kitty-glossary-writing"],
            toolguides=["pytest"],
            procedures=["mission-wrap-up-sequence"],
            agent_profiles=["python-pedro"],
        )

        mapping = action_index_to_mapping(index)

        assert mapping == {
            "directives": ["010-specification-fidelity-requirement"],
            "tactics": ["stopping-conditions"],
            "paradigms": ["tdd"],
            "styleguides": ["kitty-glossary-writing"],
            "toolguides": ["pytest"],
            "procedures": ["mission-wrap-up-sequence"],
            "agent_profiles": ["python-pedro"],
        }

    def test_empty_index_yields_all_empty_lists(self) -> None:
        index = ActionIndex(action="specify")

        mapping = action_index_to_mapping(index)

        assert set(mapping.keys()) == {
            "directives",
            "tactics",
            "paradigms",
            "styleguides",
            "toolguides",
            "procedures",
            "agent_profiles",
        }
        assert all(value == [] for value in mapping.values())

    def test_mapping_values_are_independent_copies(self) -> None:
        """Mutating the returned mapping MUST NOT mutate the source ActionIndex."""
        index = ActionIndex(action="review", directives=["003-decision-documentation-requirement"])

        mapping = action_index_to_mapping(index)
        mapping["directives"].append("injected")

        assert index.directives == ["003-decision-documentation-requirement"]

    def test_governance_kinds_match_action_index_fields(self) -> None:
        """1:1 drift guard: ``_GOVERNANCE_KINDS`` MUST mirror the ``ActionIndex``
        governance fields exactly.

        ``action_index_to_mapping`` projects an ``ActionIndex`` onto
        ``_GOVERNANCE_KINDS`` via ``getattr``. If a new artifact-kind field is
        added to ``ActionIndex`` but not to ``_GOVERNANCE_KINDS``, that kind is
        silently dropped from every action grain (and from FR-013 cross-grain
        detection) with no test failure — the exact whack-a-field drift this
        mission exists to close. Pin the two lists together so the omission is
        a hard failure at the source, not a silent gap downstream.
        """
        from charter.mission_type_profiles import _GOVERNANCE_KINDS  # noqa: PLC0415 — lazy; mirrors the module's own cycle-avoidance convention

        action_index_fields = {f.name for f in dataclasses.fields(ActionIndex)}
        # ``action`` names the action itself, not a governance kind.
        assert action_index_fields - {"action"} == set(_GOVERNANCE_KINDS)


# ---------------------------------------------------------------------------
# T005 — aggregate_action_grain
# ---------------------------------------------------------------------------


class TestAggregateActionGrain:
    """Union of every action's grain for one mission type."""

    def test_software_dev_yields_non_empty_union(self, missions_root: Path) -> None:
        grain = aggregate_action_grain(missions_root, "software-dev")

        assert set(grain.keys()) == {
            "directives",
            "tactics",
            "paradigms",
            "styleguides",
            "toolguides",
            "procedures",
            "agent_profiles",
        }
        # software-dev/actions/{implement,plan,retrospect,review,specify,tasks}
        # collectively declare directives and tactics (confirmed by direct
        # inspection of the shipped index.yaml files).
        assert grain["directives"], "software-dev action grain must be non-empty for directives"
        assert grain["tactics"], "software-dev action grain must be non-empty for tactics"

    def test_plan_yields_empty_content_not_missing_dir(self, missions_root: Path) -> None:
        """plan/actions/* exist but are intentionally empty-content (FR-004)."""
        actions_dir = missions_root / "plan" / "actions"
        assert actions_dir.is_dir(), "plan must ship a real actions/ dir (empty CONTENT, not a missing dir)"

        grain = aggregate_action_grain(missions_root, "plan")

        assert set(grain.keys()) == {
            "directives",
            "tactics",
            "paradigms",
            "styleguides",
            "toolguides",
            "procedures",
            "agent_profiles",
        }
        assert all(value == [] for value in grain.values())

    def test_missing_actions_dir_degrades_to_empty_mapping(self, tmp_path: Path) -> None:
        """Synthetic fixture: a mission type with no actions/ dir at all (NFR-002).

        No real built-in type exercises this branch (every shipped type has
        an actions/ dir), so this fixture covers it directly.
        """
        (tmp_path / "no-actions-type").mkdir()

        grain = aggregate_action_grain(tmp_path, "no-actions-type")

        assert set(grain.keys()) == {
            "directives",
            "tactics",
            "paradigms",
            "styleguides",
            "toolguides",
            "procedures",
            "agent_profiles",
        }
        assert all(value == [] for value in grain.values())

    def test_result_keys_are_exactly_governance_kinds(self, missions_root: Path) -> None:
        from charter.mission_type_profiles import _GOVERNANCE_KINDS

        grain = aggregate_action_grain(missions_root, "research")

        assert set(grain.keys()) == set(_GOVERNANCE_KINDS)


# ---------------------------------------------------------------------------
# T006 — scan_builtin_cross_grain_duplicates
# ---------------------------------------------------------------------------


class TestScanBuiltinCrossGrainDuplicates:
    """IC-11 dup-scan: no cross-grain URN collision for any shipped type."""

    def test_all_four_shipped_types_are_disjoint(self) -> None:
        scanned = scan_builtin_cross_grain_duplicates()

        assert set(scanned) == set(CANONICAL_MISSION_TYPES)

    def test_explicit_built_in_dir_matches_default(self, missions_root: Path) -> None:
        scanned = scan_builtin_cross_grain_duplicates(built_in_dir=missions_root)

        assert set(scanned) == set(CANONICAL_MISSION_TYPES)
