"""Unit tests for charter.mission_type_profiles (WP05).

Covers:
- MissionTypeProfile.mission_type accepts any str (no Literal constraint)
- UnknownMissionTypeError carries mission_type_id and registered_ids
- resolve_mission_type_context() uses existing_mission_types() for validation
- Backward-compat: the hard-fail policy still works for truly unknown types

T034 — update ATDD test suite: MissionTypeProfile(mission_type="custom-type", ...)
       succeeds; UnknownMissionTypeError raised by resolve_mission_type_context.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from charter.mission_type_profiles import (
    MissionTypeEmptyActionSequenceError,
    MissionTypeProfile,
    UnknownMissionTypeError,
    resolve_mission_type_context,
)
from charter.pack_context import PackContext
from doctrine.missions.mission_type_repository import MissionTypeRepository


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# T029 — MissionTypeProfile.mission_type is now str (no Literal constraint)
# ---------------------------------------------------------------------------


class TestMissionTypeProfileOpenStr:
    """MissionTypeProfile.mission_type MUST accept any string at model construction
    time. The Literal constraint was removed in T029 (FR-009).
    """

    def test_canonical_types_still_accepted(self) -> None:
        """The four canonical mission types remain valid."""
        for mt in ("software-dev", "documentation", "research", "plan"):
            profile = MissionTypeProfile(mission_type=mt)
            assert profile.mission_type == mt

    def test_custom_type_accepted_without_validation_error(self) -> None:
        """MissionTypeProfile(mission_type='custom-type') MUST NOT raise ValidationError.

        Before T029 this would fail with pydantic.ValidationError because the
        field was typed as Literal["software-dev", "documentation", "research", "plan"].
        After T029 the annotation is str — any value is accepted at model time.
        """
        profile = MissionTypeProfile(mission_type="custom-type")
        assert profile.mission_type == "custom-type"

    def test_arbitrary_string_accepted(self) -> None:
        """Any non-empty string is valid at model construction time."""
        profile = MissionTypeProfile(mission_type="compliance-audit")
        assert profile.mission_type == "compliance-audit"

    def test_pydantic_validation_error_not_raised_for_unknown(self) -> None:
        """The historical ValidationError for non-Literal values MUST NOT be raised."""
        try:
            from pydantic import ValidationError  # noqa: PLC0415
        except ImportError:
            pytest.skip("pydantic not installed")

        # This used to raise: before T029, any value outside the Literal set
        # caused a pydantic ValidationError at construction time.
        try:
            profile = MissionTypeProfile(mission_type="totally-custom")
        except ValidationError:
            pytest.fail(
                "MissionTypeProfile raised pydantic.ValidationError for "
                "mission_type='totally-custom'. T029 requires the annotation "
                "to be str, not Literal[...]. Remove the Literal constraint."
            )
        assert profile.mission_type == "totally-custom"


# ---------------------------------------------------------------------------
# T030 — UnknownMissionTypeError carries registered_ids
# ---------------------------------------------------------------------------


class TestUnknownMissionTypeError:
    """UnknownMissionTypeError MUST include registered_ids (FR-009)."""

    def test_message_contains_mission_type_id(self) -> None:
        """The exception message MUST contain the unknown mission_type_id verbatim."""
        err = UnknownMissionTypeError("compliance-audit")
        assert "compliance-audit" in str(err)

    def test_message_contains_registered_ids_when_provided(self) -> None:
        """When registered_ids are provided, the message lists them."""
        err = UnknownMissionTypeError(
            "compliance-audit",
            registered_ids=["documentation", "plan", "research", "software-dev"],
        )
        msg = str(err)
        assert "compliance-audit" in msg
        assert "documentation" in msg
        assert "software-dev" in msg

    def test_registered_ids_attribute_is_set(self) -> None:
        """err.registered_ids MUST be the list passed at construction."""
        ids = ["documentation", "plan", "research", "software-dev"]
        err = UnknownMissionTypeError("unknown-type", registered_ids=ids)
        assert err.registered_ids == ids

    def test_registered_ids_defaults_to_empty_list(self) -> None:
        """When no registered_ids are provided, the attribute defaults to []."""
        err = UnknownMissionTypeError("something")
        assert err.registered_ids == []

    def test_mission_type_id_attribute_is_set(self) -> None:
        """err.mission_type_id MUST equal the first positional argument."""
        err = UnknownMissionTypeError("compliance-audit", registered_ids=["software-dev"])
        assert err.mission_type_id == "compliance-audit"

    def test_is_value_error_subclass(self) -> None:
        """UnknownMissionTypeError MUST remain a ValueError subclass."""
        err = UnknownMissionTypeError("bad-type")
        assert isinstance(err, ValueError)

    def test_formatted_message_matches_fr009_contract(self) -> None:
        """FR-009: message format is 'Unknown mission type X. Registered types: A, B, C.'"""
        err = UnknownMissionTypeError(
            "compliance-audit",
            registered_ids=["documentation", "plan", "research", "software-dev"],
        )
        msg = str(err)
        assert "Unknown mission type" in msg
        assert "compliance-audit" in msg
        assert "Registered types:" in msg


# ---------------------------------------------------------------------------
# T033 — resolve_mission_type_context uses existing_mission_types()
# ---------------------------------------------------------------------------


def _git_init_minimal(repo_root: Path) -> None:
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


class TestResolveMissionTypeGovernanceValidation:
    """resolve_mission_type_context() uses existing_mission_types() for
    validation (T033).
    """

    def test_known_type_resolves_successfully(self, tmp_path: Path) -> None:
        """A mission type returned by existing_mission_types() resolves without error."""
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "test-mission-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_type": "software-dev", "mission_slug": "test-mission-001"}),
            encoding="utf-8",
        )

        # Mock existing_mission_types to return a controlled set including software-dev
        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=["documentation", "plan", "research", "software-dev"],
        ):
            bundle = resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

        assert bundle.mission_type == "software-dev"

    def test_unknown_type_raises_unknown_mission_type_error(self, tmp_path: Path) -> None:
        """A mission type not in existing_mission_types() raises UnknownMissionTypeError."""
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "unknown-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps(
                {"mission_type": "totally-custom-type", "mission_slug": "unknown-001"}
            ),
            encoding="utf-8",
        )

        # Mock: no project overrides, limited activation set
        with (
            patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["documentation", "plan", "research", "software-dev"],
            ),
            patch(
                "charter.mission_type_profiles._project_has_doctrine_overrides",
                return_value=False,
            ),
            pytest.raises(UnknownMissionTypeError) as exc_info,
        ):
            resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

        assert "totally-custom-type" in str(exc_info.value)

    def test_error_includes_registered_ids(self, tmp_path: Path) -> None:
        """UnknownMissionTypeError from resolve_mission_type_context carries registered_ids."""
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "unknown-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps(
                {"mission_type": "compliance-audit", "mission_slug": "unknown-001"}
            ),
            encoding="utf-8",
        )

        activated = ["documentation", "plan", "research", "software-dev"]
        with (
            patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=activated,
            ),
            patch(
                "charter.mission_type_profiles._project_has_doctrine_overrides",
                return_value=False,
            ),
            pytest.raises(UnknownMissionTypeError) as exc_info,
        ):
            resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

        err = exc_info.value
        assert err.registered_ids == activated

    def test_project_with_overrides_does_not_hard_fail_for_unknown_type(
        self, tmp_path: Path
    ) -> None:
        """When project has doctrine overrides, unknown type skips the profile
        (no hard fail) — the governance grain's *tolerant* policy.
        """
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "custom-mission-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps(
                {"mission_type": "custom-type", "mission_slug": "custom-mission-001"}
            ),
            encoding="utf-8",
        )

        with (
            patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["documentation", "plan", "research", "software-dev"],
            ),
            patch(
                "charter.mission_type_profiles._project_has_doctrine_overrides",
                return_value=True,
            ),
        ):
            # Should NOT raise — project overrides bypass the unknown-type check.
            bundle = resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

        assert bundle.mission_type == "custom-type"
        # An unregistered-but-tolerated type has no built-in action sequence.
        assert bundle.action_sequence == []

    def test_activated_but_unresolvable_profile_message_is_not_contradictory(
        self, tmp_path: Path
    ) -> None:
        """An activated custom type with no loadable profile must not be told,
        in the same breath, that it is both unknown and registered (#3183,
        FR-006 / SC-003).

        Unlike ``test_unknown_type_raises_unknown_mission_type_error`` (which
        covers an id absent from ``existing_mission_types()``), this test's
        id IS present in the activation set — that is the actual defect
        scenario. There is deliberately no built-in ``my-custom`` doctrine
        mission-type definition on disk, so ``_resolve_action_slot`` cannot
        resolve a profile for it even though it is activated.
        """
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "custom-002"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_type": "my-custom", "mission_slug": "custom-002"}),
            encoding="utf-8",
        )

        # "my-custom" IS activated (present in existing_mission_types()) but
        # has no resolvable MissionTypeProfile / mission-type YAML on disk.
        with (
            patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["my-custom"],
            ),
            pytest.raises(UnknownMissionTypeError) as exc_info,
        ):
            resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

        msg = str(exc_info.value)
        assert "my-custom" in msg

        # The defect: the id appears in BOTH an "Unknown mission type ..."
        # clause AND a "Registered types: my-custom" list in the same
        # message. Assert that self-contradiction is absent, without pinning
        # exact prose.
        if "Registered types:" in msg:
            registered_clause = msg.split("Registered types:", 1)[1]
            assert "my-custom" not in registered_clause, (
                "Message calls 'my-custom' unknown while also listing it "
                f"among the registered types: {msg!r}"
            )

        # Positive shape: the message must separately state the two real
        # facts -- the id is activated, and it has no loadable profile.
        lowered = msg.lower()
        assert "activated" in lowered, f"Message does not mention activation: {msg!r}"
        assert "no loadable profile" in lowered, (
            f"Message does not state the profile-loadability fact: {msg!r}"
        )

    def test_other_activated_types_clause_excludes_self(self, tmp_path: Path) -> None:
        """When multiple types are activated, the "Other activated mission
        types:" clause must not re-list the failing id (reviewer follow-up
        on WP06, #3183 / FR-006).

        ``test_activated_but_unresolvable_profile_message_is_not_contradictory``
        pins self-exclusion from the "Registered types:" sentence, but its
        ``registered_ids`` fixture is a single-element list
        (``["my-custom"]``), so the ``if other_registered:`` branch that
        renders "Other activated mission types: ..." never executes there —
        that test cannot catch a regression that re-lists the id under this
        second clause instead. This test activates ``my-custom`` alongside
        two other types so the clause actually renders, then asserts the
        failing id occurs exactly once in the whole message — a check that
        is agnostic to *which* clause a future regression re-lists it under.
        """
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "custom-003"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_type": "my-custom", "mission_slug": "custom-003"}),
            encoding="utf-8",
        )

        # "my-custom" IS activated, alongside two other registered types, so
        # the "Other activated mission types:" clause renders. It still has
        # no resolvable MissionTypeProfile / mission-type YAML on disk.
        with (
            patch(
                "charter.mission_type_profiles.existing_mission_types",
                return_value=["my-custom", "research", "software-dev"],
            ),
            pytest.raises(UnknownMissionTypeError) as exc_info,
        ):
            resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

        msg = str(exc_info.value)
        assert "Other activated mission types:" in msg, (
            f"Expected the multi-activated clause to render: {msg!r}"
        )
        assert msg.count("my-custom") == 1, (
            "'my-custom' must appear exactly once in the message -- once "
            "as the failing id, and NOT again inside the 'Other activated "
            f"mission types:' clause: {msg!r}"
        )
        assert "research" in msg
        assert "software-dev" in msg

    def test_missing_mission_type_key_degrades_neutrally(self, tmp_path: Path) -> None:
        """meta.json without 'mission_type' key degrades to the neutral bundle (FR-003a).

        The retired ``resolve_mission_type_governance`` raised a ValueError here;
        the WP02 canonicalizer + resolver now treat an absent type as *typeless*
        and degrade neutrally — never a software-dev default.
        """
        _git_init_minimal(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "no-type-001"
        feature_dir.mkdir(parents=True)
        (feature_dir / "meta.json").write_text(
            json.dumps({"mission_slug": "no-type-001"}),
            encoding="utf-8",
        )

        with patch(
            "charter.mission_type_profiles.existing_mission_types",
            return_value=["software-dev"],
        ):
            bundle = resolve_mission_type_context(tmp_path, feature_dir=feature_dir)

        assert bundle.mission_type is None
        assert bundle.governance is None
        assert bundle.governance_text == ""
        assert bundle.action_sequence == []


# ---------------------------------------------------------------------------
# WP04/T010 — thread the real PackContext into action-sequence/template-set
# projection (FR-002). Written and committed FIRST, RED against the
# pre-WP04 code (``_resolve_action_slot`` still calling
# ``MissionTypeRepository.default()``, ``_resolve_template_set_slot`` still
# hardcoding ``pack_context=None``), per C-011 red-first discipline.
# ---------------------------------------------------------------------------


def _write_layered_mission_type_yaml(
    directory: Path,
    filename: str,
    mission_type_id: str,
    *,
    action_sequence: list[str] | None = None,
) -> None:
    """Write a minimal mission-type YAML for the layered lookup (WP03 shape).

    Mirrors ``tests/doctrine/missions/test_mission_type_repository.py``'s
    own ``_mission_type_yaml`` helper. ``action_sequence=None`` omits the
    field entirely (the CL-003 empty-action-sequence edge case).
    """
    directory.mkdir(parents=True, exist_ok=True)
    lines = [
        "schema_version: 1",
        f"id: {mission_type_id}",
        f"display_name: {mission_type_id.title()}",
    ]
    if action_sequence is not None:
        lines.append("action_sequence:")
        lines.extend(f"  - {step}" for step in action_sequence)
    (directory / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_org_mission_step_yaml(
    org_root: Path,
    mission_type_id: str,
    step_id: str,
    *,
    artifact_key: str,
    template_file: str,
    sequence_index: int = 0,
) -> None:
    """Write a step.yaml in the org-pack layout carrying a template ref.

    Org-pack layout convention (mirrors
    ``tests/doctrine/missions/test_mission_step_resolver.py::_write_org_step``):
    ``{org_root}/mission-steps/{mission_type_id}/{step_id}/step.yaml``.
    """
    step_dir = org_root / "mission-steps" / mission_type_id / step_id
    step_dir.mkdir(parents=True, exist_ok=True)
    (step_dir / "step.yaml").write_text(
        f"id: {step_id}\n"
        f"display_name: {step_id.title()}\n"
        "step_type: agent\n"
        "prompt_template: prompt.md\n"
        "in_action_sequence: true\n"
        f"sequence_index: {sequence_index}\n"
        "template:\n"
        f"  artifact_key: {artifact_key}\n"
        f"  template_file: {template_file}\n",
        encoding="utf-8",
    )


class TestPackContextProjection:
    """FR-002 (WP04/T010): ``resolve_mission_type_context`` threads the real
    ``PackContext`` it already constructs into both the action-sequence and
    template-set projection slots, so an org/project mission type resolves
    real, non-empty projected fields instead of degrading to built-in-only
    defaults (User Story 1 AC2).

    RED-first (C-011): both tests below fail against the pre-WP04 code --
    ``_resolve_action_slot`` calls the built-in-only
    ``MissionTypeRepository.default()`` with no ``pack_context`` parameter
    at all, so an org-pack-only type id resolves to ``mission is None`` and
    raises :class:`UnknownMissionTypeError` instead of returning the
    org-pack's declared fields.
    """

    def setup_method(self) -> None:
        # PR-TESTS-002 (pre-merge squad, mission up-mission-type-seam-01KZY1JB):
        # every other test file that patches ``PackContext.from_config`` and
        # drives resolution through ``resolve_layered_mission_types``'s
        # module-level cache also clears it before/after -- this class
        # previously relied only on the incidental fact that ``PackContext``
        # is a frozen, field-hashed dataclass built from pytest's
        # per-test-unique ``tmp_path``, so no two tests here could construct
        # an *equal* cache key. Explicit discipline now, matching
        # ``tests/cli/test_charter_mission_type_commands.py`` and
        # ``tests/doctrine/missions/test_mission_type_repository.py``.
        MissionTypeRepository.cache_clear()

    def teardown_method(self) -> None:
        MissionTypeRepository.cache_clear()

    def test_org_pack_type_projects_real_action_sequence_and_template_set(
        self, tmp_path: Path
    ) -> None:
        """An org-pack type with a populated action_sequence, activated in a
        test project, resolves through ``resolve_mission_type_context`` with
        real, non-empty projected fields matching the org-pack's declared
        steps exactly -- not empty, not silently substituted with a
        built-in default (spec.md User Story 1 AC2).
        """
        _git_init_minimal(tmp_path)
        org_root = tmp_path / "org-pack"
        _write_layered_mission_type_yaml(
            org_root / "mission_types",
            "qa.yaml",
            "qa",
            action_sequence=["design", "implement"],
        )
        _write_org_mission_step_yaml(
            org_root,
            "qa",
            "design",
            artifact_key="spec",
            template_file="qa-spec-template.md",
        )
        pack_context = PackContext(
            activated_kinds=frozenset(),
            activated_mission_types=frozenset({"qa"}),
            pack_roots=(tmp_path / "unused-builtin-placeholder", org_root),
            org_pack_names=("org-pack",),
            repo_root=tmp_path,
        )

        with patch(
            "charter.pack_context.PackContext.from_config", return_value=pack_context
        ):
            bundle = resolve_mission_type_context(tmp_path, mission_type="qa")

        assert bundle.action_sequence == ["design", "implement"]
        assert bundle.template_set is not None
        assert dict(bundle.template_set) == {"spec": "qa-spec-template.md"}

    def test_project_layer_omitting_action_sequence_raises_named_error(
        self, tmp_path: Path
    ) -> None:
        """A project-layer file overriding an org-layer entry with the same
        ``id``, where the project-layer file omits ``action_sequence``, must
        raise :class:`MissionTypeEmptyActionSequenceError` naming the
        ``project`` layer -- not a field-merged inherit of the org-layer's
        populated value (spec.md Edge Cases, full per-compound-key
        replacement -- MissionTypeRepository does not inherit
        BaseDoctrineRepository, so the field-merge ADR
        ``docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md`` does
        not govern it) and not a silent resolve to ``[]`` (CL-003/FR-004,
        closed by WP06).

        Before WP06 this test asserted ``bundle.action_sequence == []`` --
        its own docstring at the time said so explicitly ("This test does
        not yet assert the eventual loud failure ... that is WP06's job").
        That was always documented as the CL-003 silent-degradation gap
        WP06 closes, not a contract this test intended to freeze, so it is
        re-pinned to the loud-failure contract here (DIRECTIVE_041: judge
        the test, not git-blame) rather than deleted -- the setup (project
        overriding org, full-replace semantics) remains valid coverage.
        """
        _git_init_minimal(tmp_path)
        org_root = tmp_path / "org-pack"
        _write_layered_mission_type_yaml(
            org_root / "mission_types",
            "shared.yaml",
            "shared",
            action_sequence=["org-step"],
        )
        _write_layered_mission_type_yaml(
            tmp_path / ".kittify" / "missions" / "mission_types",
            "shared.yaml",
            "shared",
            action_sequence=None,
        )
        pack_context = PackContext(
            activated_kinds=frozenset(),
            activated_mission_types=frozenset({"shared"}),
            pack_roots=(tmp_path / "unused-builtin-placeholder", org_root),
            org_pack_names=("org-pack",),
            repo_root=tmp_path,
        )

        with (
            patch("charter.pack_context.PackContext.from_config", return_value=pack_context),
            pytest.raises(MissionTypeEmptyActionSequenceError) as exc_info,
        ):
            resolve_mission_type_context(tmp_path, mission_type="shared")

        # Full-replace, not field-merge: the project layer's own missing
        # action_sequence wins outright -- it must NOT silently inherit the
        # org layer's populated ["org-step"], and it must not silently
        # resolve to [] either (CL-003/FR-004).
        err = exc_info.value
        assert isinstance(err, MissionTypeEmptyActionSequenceError)
        assert err.mission_type_id == "shared"
        assert err.layer == "project"


# ---------------------------------------------------------------------------
# WP06/T013-T014 — loud-fail for the empty-action-sequence degradation
# (FR-004/CL-003/NFR-005). The regression test below was committed RED
# first (NFR-005): at that commit MissionTypeEmptyActionSequenceError did
# not exist in production code and _resolve_action_slot still returned
# `list(mission.action_sequence or [])` unconditionally, silently
# degrading to `[]` -- confirmed by running this test in isolation before
# the fix commit landed (see this WP's commit history for the verbatim RED
# output). The fix commit (T014) added the exception class and its raise
# site and made this test GREEN.
# ---------------------------------------------------------------------------


class TestResolveActionSequenceLayerHelper:
    """Direct coverage of ``resolve_action_sequence_layer``'s own two
    remaining branches (WP06 diff-coverage): the protected-pack-root skip
    and the built-in fallback. Neither is reachable through the full
    ``resolve_mission_type_context()`` pipeline, given that helper's own
    precondition -- it is only ever called once a type's action sequence is
    already known to be empty, which no built-in type's is (see
    :class:`MissionTypeEmptyActionSequenceError`'s docstring) -- so this
    exercises the private helper directly, mirroring this file's own
    ``_action_sequence()``-direct-import convention in
    ``test_action_sequence_dispatch.py``.
    """

    def test_protected_pack_root_is_skipped_and_falls_through_to_builtin(
        self, tmp_path: Path
    ) -> None:
        """A ``pack_root`` equal to the built-in-equivalent directory's
        parent is skipped (already covered by that layer), and when no
        other layer has the file either, the helper falls through to the
        honest ``"built-in"`` default rather than raising a second error.
        """
        from charter.mission_type_profiles import resolve_action_sequence_layer

        mission_types_dirs = (tmp_path / "builtin-equivalent" / "mission_types",)
        pack_context = PackContext(
            activated_kinds=frozenset(),
            activated_mission_types=frozenset(),
            pack_roots=(tmp_path / "builtin-equivalent",),
            org_pack_names=(),
            repo_root=tmp_path,
        )

        layer = resolve_action_sequence_layer(
            "no-such-type",
            mission_types_dirs=mission_types_dirs,
            pack_context=pack_context,
        )

        assert layer == "built-in"


class TestEmptyActionSequenceLoudFail:
    """FR-004/CL-003 (WP06): resolving a non-built-in-layer mission type
    whose YAML carries only ``schema_version``/``id``/``display_name`` (no
    ``action_sequence``) must raise :class:`MissionTypeEmptyActionSequenceError`
    naming both the mission-type id and the resolving layer -- not silently
    degrade to ``[]``. This is the mission's own dominant risk (CL-003): a
    mission of that type would otherwise resolve "successfully" and plan
    nothing, with no error anywhere.
    """

    def setup_method(self) -> None:
        # PR-TESTS-002: see ``TestPackContextProjection.setup_method``.
        MissionTypeRepository.cache_clear()

    def teardown_method(self) -> None:
        MissionTypeRepository.cache_clear()

    def test_org_layer_type_with_no_action_sequence_raises_named_error(
        self, tmp_path: Path
    ) -> None:
        """The canonical CL-003 example: an org-pack mission-type YAML with
        no ``action_sequence`` key at all resolves loudly, naming the id and
        the ``org`` layer it resolved from -- not a clean resolve to ``[]``.
        """
        _git_init_minimal(tmp_path)
        org_root = tmp_path / "org-pack"
        _write_layered_mission_type_yaml(
            org_root / "mission_types",
            "qa.yaml",
            "qa",
            action_sequence=None,
        )
        pack_context = PackContext(
            activated_kinds=frozenset(),
            activated_mission_types=frozenset({"qa"}),
            pack_roots=(tmp_path / "unused-builtin-placeholder", org_root),
            org_pack_names=("org-pack",),
            repo_root=tmp_path,
        )

        with (
            patch("charter.pack_context.PackContext.from_config", return_value=pack_context),
            pytest.raises(MissionTypeEmptyActionSequenceError) as exc_info,
        ):
            resolve_mission_type_context(tmp_path, mission_type="qa")

        err = exc_info.value
        assert isinstance(err, MissionTypeEmptyActionSequenceError)
        assert err.mission_type_id == "qa"
        assert err.layer == "org"
        assert "qa" in str(err)
        assert "org" in str(err)


# ---------------------------------------------------------------------------
# WP06/T015 — mission create propagates the same exception TYPE (User Story
# 2 AC2). isinstance-only, never message substring-matching.
# ---------------------------------------------------------------------------


class TestMissionCreatePropagatesEmptyActionSequenceError:
    """``mission create`` against a misconfigured org/project mission type
    propagates :class:`MissionTypeEmptyActionSequenceError` -- the SAME
    exception type FR-004's resolver-level raise produces, asserted via
    ``isinstance`` (User Story 2 AC2), not message substring-matching.

    Call-path trace confirming no intermediate ``except Exception`` swallows
    or re-wraps the exception: ``create_mission_core``
    (``src/specify_cli/core/mission_creation.py``) calls
    ``resolve_mission_type_context`` directly at its mission-type-resolution
    step, with no surrounding try/except of its own -- the only two
    ``except Exception`` blocks in that function guard unrelated
    best-effort event emission far downstream, after the point this call
    never reaches once it raises. ``create_mission_core``'s own docstring
    states it is "the programmatic API ... [it] returns a structured result
    and raises domain exceptions instead of calling ``typer.Exit()``" --
    unlike the Typer CLI command wrapper
    (``specify_cli/cli/commands/agent/mission_create.py``'s
    ``_run_create_core_phase``), which DOES catch ``except Exception`` and
    convert to ``typer.Exit(1)`` at the CLI presentation boundary. This test
    calls ``create_mission_core`` directly for that reason -- it is the
    documented entry point that raises the real exception type rather than
    a process exit code.
    """

    def setup_method(self) -> None:
        # PR-TESTS-002: see ``TestPackContextProjection.setup_method``.
        MissionTypeRepository.cache_clear()

    def teardown_method(self) -> None:
        MissionTypeRepository.cache_clear()

    def test_create_mission_propagates_named_exception_type(self, tmp_path: Path) -> None:
        from specify_cli.core.mission_creation import create_mission_core  # noqa: PLC0415

        _git_init_minimal(tmp_path)
        subprocess.run(
            ["git", "commit", "-m", "init", "--allow-empty"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        org_root = tmp_path / "org-pack"
        _write_layered_mission_type_yaml(
            org_root / "mission_types",
            "qa.yaml",
            "qa",
            action_sequence=None,
        )
        pack_context = PackContext(
            activated_kinds=frozenset(),
            activated_mission_types=frozenset({"qa"}),
            pack_roots=(tmp_path / "unused-builtin-placeholder", org_root),
            org_pack_names=("org-pack",),
            repo_root=tmp_path,
        )

        with (
            patch("charter.pack_context.PackContext.from_config", return_value=pack_context),
            pytest.raises(MissionTypeEmptyActionSequenceError) as exc_info,
        ):
            create_mission_core(
                tmp_path,
                "qa-mission",
                mission="qa",
                friendly_name="QA Mission",
                purpose_tldr="Exercise the misconfigured qa type.",
                purpose_context=(
                    "Confirms create_mission_core propagates FR-004's exception "
                    "type end to end, not a re-wrapped generic error."
                ),
            )

        err = exc_info.value
        assert isinstance(err, MissionTypeEmptyActionSequenceError)
        assert err.mission_type_id == "qa"
        assert err.layer == "org"
