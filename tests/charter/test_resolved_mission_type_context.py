"""WP03 — enduring contract tests for the unified mission-type resolver seam.

Covers ``resolve_mission_type_context`` and the ``ResolvedGovernance`` /
``ResolvedMissionType`` bundle:

* T012 — bundle shape: ordered ``selected_*`` lists, reserved slots.
* T016 — cross-grain disjointness guard on **canonical URN** (FR-013).
* T017 — hard-fail policies + empty grain (FR-003 / FR-004).
* T018 — determinism (two resolutions byte-identical, NFR-007).

No transitional byte-parity scaffold survives in this suite (C-003) —
``tests/architectural/test_no_parity_scaffold.py`` enforces that as a
reappearance guard; the enduring determinism assertions live here.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from charter.mission_type_profiles import (
    CrossGrainDoubleDeclarationError,
    ResolvedGovernance,
    ResolvedMissionType,
    UnknownMissionTypeError,
    existing_mission_types,
    resolve_mission_type_context,
)
from charter.mission_type_profiles import (
    _canonical_artifact_key,  # internal — the FR-013 normalization is contract-critical
)


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# T016 — canonical URN normalization (the disjointness comparison key)
# ---------------------------------------------------------------------------


class TestCanonicalArtifactKey:
    """The three declaration forms MUST collapse to one comparison key."""

    def test_three_forms_normalize_equal(self) -> None:
        numeric = _canonical_artifact_key("003-language-driven-design")
        prefixed = _canonical_artifact_key("DIRECTIVE_003")
        urn = _canonical_artifact_key("urn:directive:003")
        assert numeric == prefixed == urn

    def test_distinct_codes_do_not_collide(self) -> None:
        assert _canonical_artifact_key("DIRECTIVE_003") != _canonical_artifact_key("DIRECTIVE_030")

    def test_slug_only_reference_is_stable(self) -> None:
        assert _canonical_artifact_key("python-style-guide") == _canonical_artifact_key(
            "urn:styleguide:python-style-guide"
        )


# ---------------------------------------------------------------------------
# T012 / T016 — ResolvedGovernance.from_grains: union, order, disjointness
# ---------------------------------------------------------------------------


class TestResolvedGovernanceFromGrains:
    """type-grain ∪ action-grain, ordered, URN-deconflicted (FR-013, NFR-007)."""

    def test_union_is_sorted_ordered_list(self) -> None:
        gov = ResolvedGovernance.from_grains(
            type_grain={"directives": ["DIRECTIVE_030", "DIRECTIVE_010"]},
            action_grain={"directives": ["DIRECTIVE_024"]},
        )
        assert gov.selected_directives == ["DIRECTIVE_010", "DIRECTIVE_024", "DIRECTIVE_030"]
        assert isinstance(gov.selected_directives, list)

    def test_empty_grains_yield_empty_selections(self) -> None:
        gov = ResolvedGovernance.from_grains(type_grain={}, action_grain={})
        assert gov.selected_directives == []
        assert gov.selected_tactics == []

    def test_within_grain_duplicate_is_deduped(self) -> None:
        gov = ResolvedGovernance.from_grains(
            type_grain={"tactics": ["language-driven-design", "language-driven-design"]},
            action_grain={},
        )
        assert gov.selected_tactics == ["language-driven-design"]

    def test_cross_grain_double_declaration_raises_on_canonical_urn(self) -> None:
        """The SAME artifact in both grains — via different forms — raises (FR-013)."""
        with pytest.raises(CrossGrainDoubleDeclarationError) as exc:
            ResolvedGovernance.from_grains(
                type_grain={"directives": ["DIRECTIVE_003"]},
                action_grain={"directives": ["003-language-driven-design"]},
            )
        assert exc.value.kind == "directives"

    def test_disjoint_grains_do_not_raise(self) -> None:
        gov = ResolvedGovernance.from_grains(
            type_grain={"directives": ["DIRECTIVE_010"]},
            action_grain={"directives": ["DIRECTIVE_024"]},
        )
        assert gov.selected_directives == ["DIRECTIVE_010", "DIRECTIVE_024"]

    def test_provenance_is_carried(self) -> None:
        gov = ResolvedGovernance.from_grains(
            type_grain={}, action_grain={}, provenance="project"
        )
        assert gov.provenance == "project"


# ---------------------------------------------------------------------------
# T017 — hard-fail policies + empty grain (FR-003 / FR-003a / FR-004)
# ---------------------------------------------------------------------------


def _write_config(repo_root: Path, activations: list[str]) -> None:
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"  - {mt}" for mt in activations)
    (kittify / "config.yaml").write_text(
        f"mission_type_activations:\n{lines}\n", encoding="utf-8"
    )


class TestResolverHardFailPolicies:
    def test_typeless_degrades_neutrally(self, tmp_path: Path) -> None:
        """No mission_type and no feature_dir → neutral bundle, never software-dev."""
        bundle = resolve_mission_type_context(tmp_path)
        assert bundle.mission_type is None
        assert bundle.governance is None
        assert bundle.governance_text == ""
        assert bundle.action_sequence == []
        assert bundle.template_set is None

    def test_unknown_typed_mission_hard_fails(self, tmp_path: Path) -> None:
        """A recognised-but-unactivated type with no override raises (FR-003)."""
        _write_config(tmp_path, ["software-dev"])
        with pytest.raises(UnknownMissionTypeError):
            resolve_mission_type_context(tmp_path, mission_type="totally-made-up")

    def test_known_type_resolves_bundle(self, tmp_path: Path) -> None:
        """A known, activated type resolves governance + action sequence (FR-004)."""
        bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        assert bundle.mission_type == "software-dev"
        assert bundle.governance is not None
        assert "Mission-Type Governance Profile: software-dev" in bundle.governance_text
        assert bundle.action_sequence  # non-empty for the canonical software-dev type

    def test_doctrine_slots_and_populated_step_contracts(self, tmp_path: Path) -> None:
        """Doctrine-backed slots expose the activated software-dev artifacts."""
        bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        assert isinstance(bundle, ResolvedMissionType)
        # WP10: expected_artifacts is now populated from the doctrine gate tree.
        assert bundle.expected_artifacts is not None
        assert isinstance(bundle.expected_artifacts, dict)
        assert bundle.expected_artifacts["mission_type"] == "software-dev"
        assert bundle.template_set == {
            "spec": "spec-template.md",
            "plan": "plan-template.md",
        }
        # WP11 routed step-contract resolution through the artefact bundle: a
        # registered type now resolves its ordered step-contract ids.
        assert bundle.step_contracts == ["implement", "plan", "review", "specify", "tasks"]


# ---------------------------------------------------------------------------
# T018 — determinism (two resolutions byte-identical, NFR-007)
# ---------------------------------------------------------------------------


class TestResolverDeterminism:
    def test_two_resolutions_are_byte_identical(self, tmp_path: Path) -> None:
        first = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        second = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        assert first == second
        assert first.governance_text == second.governance_text
        assert first.governance == second.governance
        assert first.action_sequence == second.action_sequence
        assert list(first.template_set.items()) == list(second.template_set.items())

    def test_governance_selections_are_ordered_lists(self, tmp_path: Path) -> None:
        bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        assert bundle.governance is not None
        for selection in (
            bundle.governance.selected_directives,
            bundle.governance.selected_tactics,
            bundle.governance.selected_agent_profiles,
        ):
            assert isinstance(selection, list)
            assert selection == sorted(selection)


# ---------------------------------------------------------------------------
# Template mapping projection — doctrine authority, lazy cache, immutability
# ---------------------------------------------------------------------------


def _write_profile_template_override(
    repo_root: Path, template_set: str, *, mission_type: str = "software-dev"
) -> None:
    """Write a legacy governance-profile string that must not author mappings."""
    override_dir = repo_root / ".kittify" / "doctrine" / "mission_types" / mission_type
    override_dir.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with (override_dir / "governance-profile.yaml").open("w") as fh:
        yaml.dump(
            {
                "id": mission_type,
                "mission_type": mission_type,
                "template_set": template_set,
            },
            fh,
        )


class TestResolvedTemplateSet:
    @pytest.mark.parametrize("mission_type", ["documentation", "research", "plan"])
    def test_non_software_builtin_preserves_explicit_null(
        self, tmp_path: Path, mission_type: str
    ) -> None:
        bundle = resolve_mission_type_context(tmp_path, mission_type=mission_type)
        assert bundle.template_set is None

    def test_mapping_is_lazy_and_cached_per_bundle(self, tmp_path: Path) -> None:
        from doctrine.missions.mission_type_repository import MissionTypeRepository

        original_default = MissionTypeRepository.default
        with patch.object(
            MissionTypeRepository,
            "default",
            side_effect=original_default,
        ) as repository_default:
            bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
            assert repository_default.call_count == 1  # action-sequence resolution only
            assert "template_set" not in bundle.__dict__

            first = bundle.template_set
            second = bundle.template_set

        assert repository_default.call_count == 2
        assert first is second
        assert first == {
            "spec": "spec-template.md",
            "plan": "plan-template.md",
        }

    def test_mapping_rejects_consumer_mutation(self, tmp_path: Path) -> None:
        bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        template_set = bundle.template_set
        assert template_set is not None

        with pytest.raises(TypeError):
            template_set["spec"] = "consumer-owned.md"  # type: ignore[index]

        later = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        assert later.template_set == {
            "spec": "spec-template.md",
            "plan": "plan-template.md",
        }

    def test_profile_string_override_cannot_author_artifact_mapping(
        self, tmp_path: Path
    ) -> None:
        _write_profile_template_override(tmp_path, "project-custom")

        bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")

        assert bundle.template_set == {
            "spec": "spec-template.md",
            "plan": "plan-template.md",
        }

    def test_unregistered_project_override_has_no_artifact_mapping(
        self, tmp_path: Path
    ) -> None:
        _write_config(tmp_path, ["software-dev"])
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True, exist_ok=True)
        (charter_dir / "governance.yaml").write_text(
            "doctrine:\n  selected_directives:\n    - DIRECTIVE_001\n",
            encoding="utf-8",
        )
        _write_profile_template_override(
            tmp_path,
            "project-custom",
            mission_type="project-only",
        )

        bundle = resolve_mission_type_context(tmp_path, mission_type="project-only")

        assert bundle.action_sequence == []
        assert bundle.template_set is None

    def test_action_sequence_hot_path_does_not_resolve_template_mapping(
        self, tmp_path: Path
    ) -> None:
        timings_ms: list[float] = []
        for _ in range(20):
            started = time.monotonic_ns()
            bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
            assert bundle.action_sequence
            timings_ms.append((time.monotonic_ns() - started) / 1_000_000)
            assert "template_set" not in bundle.__dict__

        timings_ms.sort()
        p95 = timings_ms[18]
        assert p95 < 100, f"action-sequence hot-path p95 = {p95:.3f}ms (budget: 100ms)"


# ---------------------------------------------------------------------------
# T007-T011 (WP03) — lazy governance thunk severs the FR-013 coupling
# ---------------------------------------------------------------------------


def _write_colliding_override(repo_root: Path) -> None:
    """Write a project override whose type-grain collides with software-dev's
    OWN built-in action grain (``001-architectural-integrity-standard`` is
    authored in ``src/doctrine/missions/software-dev/actions/*/index.yaml``).

    Declaring the SAME artifact (different form: ``DIRECTIVE_001``) in the
    type-grain override forces :class:`CrossGrainDoubleDeclarationError` the
    moment the FR-013 union actually runs — i.e. on first ``.governance``
    access, not at ``resolve_mission_type_context`` construction time.
    """
    override_dir = repo_root / ".kittify" / "doctrine" / "mission_types" / "software-dev"
    override_dir.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    data = {
        "mission_type": "software-dev",
        "id": "software-dev",
        "selected_directives": ["DIRECTIVE_001"],
    }
    with (override_dir / "governance-profile.yaml").open("w") as fh:
        yaml.dump(data, fh)


class TestGovernanceThunkSeversCoupling:
    """The lazy ``governance`` thunk (T007-T009) must not couple the hot
    ``action_sequence`` path — or the registration-based hard-fail guard — to
    the FR-013 disk-reading union.
    """

    def test_colliding_grain_does_not_fail_construction_or_action_sequence(
        self, tmp_path: Path
    ) -> None:
        """A cross-grain collision is invisible to construction and ``.action_sequence``.

        ``resolve_mission_type_context`` MUST NOT raise even though the
        resolved type's grains collide — the union (and its FR-013 raise) is
        deferred behind the ``governance`` thunk. ``.action_sequence`` reads a
        wholly separate slot (``_resolve_action_slot``) and MUST also resolve
        cleanly.
        """
        _write_colliding_override(tmp_path)

        bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")

        assert bundle.mission_type == "software-dev"
        assert bundle.action_sequence  # the strict action-sequence policy is unaffected

    def test_colliding_grain_raises_only_on_governance_access(self, tmp_path: Path) -> None:
        """``.governance`` — and only ``.governance`` — surfaces the FR-013 raise."""
        _write_colliding_override(tmp_path)

        bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        # action_sequence already resolved without error (previous test); prove
        # it again here so the ordering (access action_sequence THEN governance)
        # can't matter — the thunk isn't shared/consumed by action_sequence.
        assert bundle.action_sequence

        with pytest.raises(CrossGrainDoubleDeclarationError) as exc:
            _ = bundle.governance
        assert exc.value.kind == "directives"
        assert exc.value.artifact == "001-architectural-integrity-standard"

    def test_existing_mission_types_and_action_sequence_ignore_governance_grain(
        self, tmp_path: Path
    ) -> None:
        """``existing_mission_types`` / ``activated_mission_types`` / ``.action_sequence``
        never read the governance grain — a colliding override (which would
        blow up ``.governance``) leaves them untouched (C-001 regression pin).
        """
        _write_colliding_override(tmp_path)

        # existing_mission_types() reads only the activation set (PackContext),
        # never the profile's selected_* grain — unaffected by the collision.
        activated = existing_mission_types(tmp_path)
        assert activated == sorted(activated)
        assert "software-dev" in activated

        bundle = resolve_mission_type_context(tmp_path, mission_type="software-dev")
        assert bundle.action_sequence == [
            "specify",
            "plan",
            "tasks",
            "implement",
            "review",
        ]
