"""Seam-equivalence tests for WP06 — consumer switch (mission-step-authority-01KXNZMT).

WP02 injects a projected ``action_sequence``/``template_set`` into every
:class:`~doctrine.missions.models.MissionType` at
``MissionTypeRepository._load`` time (see
``_inject_projected_fields``/``project_action_sequence``/
``project_template_set``). WP03/WP05 populated the mission-step data so the
projection is now non-empty for **all four** built-in mission types.

WP06's job was to confirm every *genuine* authority read of
``action_sequence``/``template_set`` consumes that injected/projected value —
not a bypass re-read of raw YAML — and to lock the finding with tests so a
future change cannot silently reintroduce a 5th authority (C-003).

Investigation result (T018/T019 — no code changes required, confirmation only):

- ``charter.mission_type_profiles._resolve_action_slot`` (:694/697) and
  ``_resolve_template_set_slot`` (:750) both call
  ``doctrine.missions.mission_type_repository.MissionTypeRepository.default()``
  and read ``mission.action_sequence`` / ``mission.template_set`` straight off
  the loaded model — the exact field WP02's ``_inject_projected_fields``
  overlays before ``MissionType.model_validate()`` runs. There is no
  alternate/raw YAML re-parse anywhere in either resolver.
- ``runtime.next.decision._build_prompt_or_error`` (:606) and
  ``runtime.next.runtime_bridge_composition._should_dispatch_via_composition``
  (:186) / ``_composition_dispatch_inputs`` (:321) all call
  ``charter.mission_type_profiles.resolve_mission_type_context(...).action_sequence``
  — the bundle built from ``_resolve_action_slot`` above — so they consume the
  projected value transitively. No consumer reads a raw/flat field directly.

This module locks that finding with:

1. Seam-equivalence — the four built-in types' ``action_sequence``/
   ``template_set`` resolved through the seam equal the pinned authored (formerly raw
   YAML-authored) contract values (T020).
2. Consumer transitivity — the three cited call sites observe the seam's
   resolved value rather than bypassing it (T019).
3. The ``extends`` fallback check (T020) — none of the four built-in types
   sets ``extends``, so switching resolvers onto the cached model does not
   change existing ``extends``-widening behavior (there is none to change).
4. No hot-path uncached I/O (T020) — ``MissionTypeRepository.default()`` is
   memoized (``functools.cache``), so repeated resolver calls never re-walk
   the ``mission-steps/`` tree.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from charter.mission_type_profiles import ResolvedMissionType, resolve_mission_type_context
from doctrine.missions.mission_step_repository import MissionStepRepository
from doctrine.missions.mission_type_repository import MissionTypeRepository

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_BUILTIN_TYPE_IDS = ("documentation", "plan", "research", "software-dev")


# Hand-pinned authored contract for the 4 built-in types. Post-WP07 the flat
# ``action_sequence``/``template_set`` are removed from the mission_types YAML
# (the projection from step.yaml is the sole authority), so the seam-equivalence
# assertions can no longer read the YAML as ground truth — they compare against
# this independent, human-authored pin instead (an enduring behavioural contract,
# not a tautology against the projection the seam itself uses).
_EXPECTED_AUTHORED: dict[str, dict[str, Any]] = {
    "software-dev": {
        "action_sequence": ["specify", "plan", "tasks", "implement", "review"],
        "template_set": {"spec": "spec-template.md", "plan": "plan-template.md"},
    },
    "documentation": {
        "action_sequence": [
            "discover", "audit", "design", "generate", "validate", "publish", "accept",
        ],
        "template_set": None,
    },
    "research": {
        "action_sequence": ["scoping", "methodology", "gathering", "synthesis", "output"],
        "template_set": None,
    },
    "plan": {
        "action_sequence": ["specify", "research", "plan", "review"],
        "template_set": None,
    },
}


def _expected_authored(mission_type_id: str) -> dict[str, Any]:
    """The independent hand-pinned authored contract for a built-in type.

    Replaces the pre-WP07 raw-YAML read (the YAML no longer carries these fields);
    the seam-resolved value must equal this known contract.
    """
    return _EXPECTED_AUTHORED[mission_type_id]


def _resolve_via_seam(tmp_path: Path, mission_type_id: str) -> ResolvedMissionType:
    with patch(
        "charter.mission_type_profiles.existing_mission_types",
        return_value=list(_BUILTIN_TYPE_IDS),
    ):
        return resolve_mission_type_context(tmp_path, mission_type=mission_type_id)


# ---------------------------------------------------------------------------
# 1. Seam-equivalence (T020) — resolved value == pinned authored contract, all 4 types
# ---------------------------------------------------------------------------


class TestSeamEquivalence:
    """The seam's resolved action_sequence/template_set equal the pinned authored contract."""

    @pytest.mark.parametrize("mission_type_id", _BUILTIN_TYPE_IDS)
    def test_action_sequence_matches_authored_contract(
        self, tmp_path: Path, mission_type_id: str
    ) -> None:
        expected = _expected_authored(mission_type_id)
        bundle = _resolve_via_seam(tmp_path, mission_type_id)

        assert bundle.action_sequence == expected["action_sequence"]

    @pytest.mark.parametrize("mission_type_id", _BUILTIN_TYPE_IDS)
    def test_template_set_matches_authored_contract(
        self, tmp_path: Path, mission_type_id: str
    ) -> None:
        expected = _expected_authored(mission_type_id)
        bundle = _resolve_via_seam(tmp_path, mission_type_id)

        expected_template_set = expected.get("template_set")
        if expected_template_set is None:
            assert bundle.template_set is None
        else:
            assert bundle.template_set is not None
            assert dict(bundle.template_set) == expected_template_set

    def test_software_dev_template_set_is_non_empty_dict(self, tmp_path: Path) -> None:
        """Ground the dict-branch: software-dev is the only type authoring a
        non-null template_set (its two content templates)."""
        bundle = _resolve_via_seam(tmp_path, "software-dev")
        assert bundle.template_set == {
            "spec": "spec-template.md",
            "plan": "plan-template.md",
        }

    @pytest.mark.parametrize("mission_type_id", ["documentation", "plan", "research"])
    def test_non_software_dev_template_set_is_none(
        self, tmp_path: Path, mission_type_id: str
    ) -> None:
        bundle = _resolve_via_seam(tmp_path, mission_type_id)
        assert bundle.template_set is None


# ---------------------------------------------------------------------------
# 2. Consumer transitivity (T019) — the three cited call sites read the seam
# ---------------------------------------------------------------------------


class TestConsumerTransitivity:
    """decision.py:606 and runtime_bridge_composition.py:186/321 observe the
    seam's resolved action_sequence rather than bypassing it.
    """

    def test_should_dispatch_via_composition_true_for_seam_action(
        self, tmp_path: Path
    ) -> None:
        from runtime.next.runtime_bridge_composition import (
            _should_dispatch_via_composition,
        )

        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=list(_BUILTIN_TYPE_IDS),
        ):
            result = _should_dispatch_via_composition(
                "software-dev", "specify", run_dir=None, repo_root=tmp_path
            )

        assert result is True

    def test_should_dispatch_via_composition_false_for_action_outside_sequence(
        self, tmp_path: Path
    ) -> None:
        from runtime.next.runtime_bridge_composition import (
            _should_dispatch_via_composition,
        )

        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=list(_BUILTIN_TYPE_IDS),
        ):
            result = _should_dispatch_via_composition(
                "software-dev",
                "not-a-real-action",
                run_dir=None,
                repo_root=tmp_path,
            )

        assert result is False

    def test_composition_dispatch_inputs_short_circuits_on_seam_action(
        self, tmp_path: Path
    ) -> None:
        from runtime.next.runtime_bridge_composition import (
            _composition_dispatch_inputs,
        )

        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=list(_BUILTIN_TYPE_IDS),
        ):
            result = _composition_dispatch_inputs(
                repo_root=tmp_path,
                run_dir=tmp_path / "does-not-exist",
                mission="software-dev",
                step_id="specify",
                action="specify",
            )

        # A seam-recognised action short-circuits to (None, None) without
        # ever touching run_dir (which does not exist on disk).
        assert result == (None, None)

    def test_build_prompt_or_error_bypasses_prompt_builder_for_seam_action(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """decision.py's composed-action fast path (:606) never reaches the
        file-based ``build_prompt`` for an action the seam recognises."""
        from runtime.next.decision import _build_prompt_or_error

        def _fail_if_called(**_kwargs: object) -> None:
            raise AssertionError(
                "build_prompt should not be called for a seam-recognised "
                "composed action"
            )

        monkeypatch.setattr(
            "runtime.next.prompt_builder.build_prompt", _fail_if_called
        )

        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=list(_BUILTIN_TYPE_IDS),
        ):
            path, err = _build_prompt_or_error(
                action="specify",
                feature_dir=tmp_path / "kitty-specs" / "some-mission",
                mission_slug="some-mission",
                wp_id=None,
                agent="claude",
                repo_root=tmp_path,
                mission_type="software-dev",
            )

        assert err is None
        assert path is not None
        assert Path(path).exists()


# ---------------------------------------------------------------------------
# 3. extends-fallback check (T020) — inert for all 4 built-in types
# ---------------------------------------------------------------------------


class TestExtendsFallbackInert:
    """None of the 4 built-in mission types relies on the ``extends``
    fallback in ``_resolve_action_slot`` (:692-695) to supply an
    otherwise-empty ``action_sequence``.

    Switching the resolvers onto the cached projected model therefore cannot
    regress ``extends``-based inheritance for any built-in type: there is
    none in play today. This is a pre-existing-behavior-preservation check,
    not a new feature.
    """

    @pytest.mark.parametrize("mission_type_id", _BUILTIN_TYPE_IDS)
    def test_builtin_type_does_not_set_extends(self, mission_type_id: str) -> None:
        mission = MissionTypeRepository.default().get(mission_type_id)
        assert mission is not None
        assert mission.extends is None

    @pytest.mark.parametrize("mission_type_id", _BUILTIN_TYPE_IDS)
    def test_builtin_type_action_sequence_is_authored_not_inherited(
        self, mission_type_id: str
    ) -> None:
        """Every built-in type's action_sequence comes from its own (projected)
        value, never from a parent via ``extends`` (there is no parent)."""
        mission = MissionTypeRepository.default().get(mission_type_id)
        assert mission is not None
        assert mission.action_sequence  # non-empty per the model's validator


# ---------------------------------------------------------------------------
# 4. No hot-path uncached I/O (T020) — memoized default()
# ---------------------------------------------------------------------------


class TestMemoizedDefaultNoHotPathIO:
    """``MissionTypeRepository.default()`` is memoized: repeated resolver
    calls never re-walk the ``mission-steps/`` tree that the WP02 injection
    reads via ``MissionStepRepository.resolve_all_for_mission_type``.
    """

    def test_default_returns_identical_cached_instance(self) -> None:
        first = MissionTypeRepository.default()
        second = MissionTypeRepository.default()
        assert first is second

    def test_default_does_not_rewalk_mission_steps_on_repeat_calls(self) -> None:
        MissionTypeRepository.default.cache_clear()
        original = MissionStepRepository.resolve_all_for_mission_type
        calls: list[str] = []

        def _spy(
            self: MissionStepRepository,
            mission_type_id: str,
            pack_context: Any = None,
        ) -> dict[str, Any]:
            calls.append(mission_type_id)
            return original(self, mission_type_id, pack_context)

        try:
            with patch.object(
                MissionStepRepository, "resolve_all_for_mission_type", _spy
            ):
                MissionTypeRepository.default()
                MissionTypeRepository.default()
                MissionTypeRepository.default()
        finally:
            # Rebuild the real (unpatched) cache so later tests in the same
            # process see the genuine repository, not one built via the spy
            # wrapper's closure.
            MissionTypeRepository.default.cache_clear()
            MissionTypeRepository.default()

        # One walk per built-in type during the SINGLE underlying _load(),
        # not one walk per default() call (3 calls above, 4 built-in types).
        assert len(calls) == len(_BUILTIN_TYPE_IDS)
        assert set(calls) == set(_BUILTIN_TYPE_IDS)
