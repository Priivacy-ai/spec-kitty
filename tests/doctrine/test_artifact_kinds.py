"""Unit tests for the canonical ArtifactKind enum."""

from __future__ import annotations

import pytest

from doctrine.artifact_kinds import ArtifactKind

pytestmark = pytest.mark.fast


class TestArtifactKindValues:
    def test_all_expected_members_present(self) -> None:
        expected = {
            "directive",
            "tactic",
            "styleguide",
            "toolguide",
            "paradigm",
            "procedure",
            "agent_profile",
            "mission_step_contract",
            "template",
        }
        assert {m.value for m in ArtifactKind} == expected

    def test_string_coercions(self) -> None:
        assert ArtifactKind("directive") is ArtifactKind.DIRECTIVE
        assert ArtifactKind("agent_profile") is ArtifactKind.AGENT_PROFILE


class TestPluralProperty:
    @pytest.mark.parametrize(
        ("kind", "expected_plural"),
        [
            (ArtifactKind.DIRECTIVE, "directives"),
            (ArtifactKind.TACTIC, "tactics"),
            (ArtifactKind.STYLEGUIDE, "styleguides"),
            (ArtifactKind.TOOLGUIDE, "toolguides"),
            (ArtifactKind.PARADIGM, "paradigms"),
            (ArtifactKind.PROCEDURE, "procedures"),
            (ArtifactKind.AGENT_PROFILE, "agent_profiles"),
            (ArtifactKind.TEMPLATE, "templates"),
        ],
    )
    def test_plural(self, kind: ArtifactKind, expected_plural: str) -> None:
        assert kind.plural == expected_plural

    def test_plurals_are_unique(self) -> None:
        plurals = [kind.plural for kind in ArtifactKind]
        assert len(plurals) == len(set(plurals))


class TestGlobPatternProperty:
    @pytest.mark.parametrize(
        ("kind", "expected_pattern"),
        [
            (ArtifactKind.DIRECTIVE, "*.directive.yaml"),
            (ArtifactKind.TACTIC, "*.tactic.yaml"),
            (ArtifactKind.STYLEGUIDE, "*.styleguide.yaml"),
            (ArtifactKind.TOOLGUIDE, "*.toolguide.yaml"),
            (ArtifactKind.PARADIGM, "*.paradigm.yaml"),
            (ArtifactKind.PROCEDURE, "*.procedure.yaml"),
            (ArtifactKind.AGENT_PROFILE, "*.agent.yaml"),
            (ArtifactKind.TEMPLATE, ""),
        ],
    )
    def test_glob_pattern(self, kind: ArtifactKind, expected_pattern: str) -> None:
        assert kind.glob_pattern == expected_pattern

    def test_only_template_has_empty_pattern(self) -> None:
        empty = [k for k in ArtifactKind if not k.glob_pattern]
        assert empty == [ArtifactKind.TEMPLATE]


class TestFromPlural:
    @pytest.mark.parametrize(
        ("plural", "expected"),
        [
            ("directives", ArtifactKind.DIRECTIVE),
            ("tactics", ArtifactKind.TACTIC),
            ("agent_profiles", ArtifactKind.AGENT_PROFILE),
            ("templates", ArtifactKind.TEMPLATE),
        ],
    )
    def test_from_plural(self, plural: str, expected: ArtifactKind) -> None:
        assert ArtifactKind.from_plural(plural) is expected

    def test_from_plural_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            ArtifactKind.from_plural("unknown_type")


class TestDerivedConstants:
    """Verify ARTIFACT_TYPES and _GLOB_PATTERNS are correctly derived."""

    def test_artifact_types_includes_agent_profiles(self) -> None:
        from doctrine.curation.state import ARTIFACT_TYPES

        assert "agent_profiles" in ARTIFACT_TYPES

    def test_artifact_types_excludes_templates(self) -> None:
        from doctrine.curation.state import ARTIFACT_TYPES

        assert "templates" not in ARTIFACT_TYPES

    def test_artifact_types_count(self) -> None:
        from doctrine.curation.state import ARTIFACT_TYPES

        # All kinds minus TEMPLATE
        assert len(ARTIFACT_TYPES) == len(ArtifactKind) - 1

    def test_glob_patterns_derived(self) -> None:
        from doctrine.curation.engine import _GLOB_PATTERNS

        assert _GLOB_PATTERNS["directives"] == "*.directive.yaml"
        assert _GLOB_PATTERNS["agent_profiles"] == "*.agent.yaml"
        assert "templates" not in _GLOB_PATTERNS

    def test_ref_type_map_includes_paradigm(self) -> None:
        from charter.reference_resolver import _REF_TYPE_MAP

        assert _REF_TYPE_MAP["paradigm"] == "paradigms"

    def test_ref_type_map_includes_agent_profile(self) -> None:
        from charter.reference_resolver import _REF_TYPE_MAP

        assert _REF_TYPE_MAP["agent_profile"] == "agent_profiles"

    def test_ref_type_map_covers_all_kinds(self) -> None:
        from charter.reference_resolver import _REF_TYPE_MAP

        for kind in ArtifactKind:
            assert kind.value in _REF_TYPE_MAP
            assert _REF_TYPE_MAP[kind.value] == kind.plural


class TestPydanticIntegration:
    """Verify ArtifactKind works as a Pydantic field type."""

    def test_directive_reference_deserializes(self) -> None:
        from doctrine.directives.models import DirectiveReference

        ref = DirectiveReference.model_validate({"type": "tactic", "id": "some-tactic"})
        assert ref.type is ArtifactKind.TACTIC

    def test_tactic_reference_deserializes(self) -> None:
        from doctrine.tactics.models import TacticReference

        ref = TacticReference.model_validate({"name": "foo", "type": "styleguide", "id": "sg-01", "when": "always"})
        assert ref.type is ArtifactKind.STYLEGUIDE

    def test_procedure_reference_deserializes(self) -> None:
        from doctrine.procedures.models import ProcedureReference

        ref = ProcedureReference.model_validate({"type": "paradigm", "id": "p-01"})
        assert ref.type is ArtifactKind.PARADIGM

    def test_invalid_type_raises(self) -> None:
        from pydantic import ValidationError
        from doctrine.directives.models import DirectiveReference

        with pytest.raises(ValidationError):
            DirectiveReference.model_validate({"type": "unknown_type", "id": "x"})
