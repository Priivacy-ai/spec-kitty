"""Tests for topic_resolver.resolve() — table-driven coverage (T032).

Covers:
  - Tier-1 (kind_slug): hit, miss, local-first over tier-2
  - Tier-2 (drg_urn): hit with project-local artifacts, zero-match (EC-4), miss
  - Tier-3 (interview_section): hit, miss, empty results
  - Unresolved (all tiers fail): structured error + candidate ordering
  - US-3: tactic:how-we-apply-directive-003 → tier-1, not tier-2
  - directive:DIRECTIVE_003 → tier-2 (shipped URN, no local artifact)
  - SC-008: unresolved returns in < 2 s
  - Error surface: TopicSelectorUnresolvedError.candidates deterministic
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from charter.synthesizer.errors import TopicSelectorUnresolvedError
from charter.synthesizer.request import SynthesisTarget
from charter.synthesizer.topic_resolver import resolve


# ---------------------------------------------------------------------------
# Fixtures — shared test data
# ---------------------------------------------------------------------------


@pytest.fixture
def directive_artifact() -> SynthesisTarget:
    """Project-local directive with id=PROJECT_001, slug=mission-scope."""
    return SynthesisTarget(
        kind="directive",
        slug="mission-scope",
        title="Mission Scope Directive",
        artifact_id="PROJECT_001",
        source_section="mission_type",
        source_urns=("directive:DIRECTIVE_001",),
    )


@pytest.fixture
def tactic_artifact() -> SynthesisTarget:
    """Project-local tactic for US-3 (local-first rule)."""
    return SynthesisTarget(
        kind="tactic",
        slug="how-we-apply-directive-003",
        title="How We Apply Directive 003",
        artifact_id="how-we-apply-directive-003",
        source_section="testing_philosophy",
        source_urns=("directive:DIRECTIVE_003",),
    )


@pytest.fixture
def styleguide_artifact() -> SynthesisTarget:
    """Project-local styleguide."""
    return SynthesisTarget(
        kind="styleguide",
        slug="python-testing-style",
        title="Python Testing Style Guide",
        artifact_id="python-testing-style",
        source_section="testing_philosophy",
        source_urns=("directive:DIRECTIVE_003", "tactic:premortem-risk"),
    )


@pytest.fixture
def all_artifacts(
    directive_artifact: SynthesisTarget,
    tactic_artifact: SynthesisTarget,
    styleguide_artifact: SynthesisTarget,
) -> list[SynthesisTarget]:
    return [directive_artifact, tactic_artifact, styleguide_artifact]


@pytest.fixture
def merged_drg() -> dict[str, Any]:
    """Merged DRG with both shipped and project URNs."""
    return {
        "nodes": [
            # Shipped directives (uppercase prefix)
            {"urn": "directive:DIRECTIVE_003", "kind": "directive", "id": "DIRECTIVE_003"},
            {"urn": "directive:DIRECTIVE_001", "kind": "directive", "id": "DIRECTIVE_001"},
            # Shipped tactic
            {"urn": "tactic:premortem-risk", "kind": "tactic", "id": "premortem-risk"},
            # Shipped paradigm
            {"urn": "paradigm:evidence-first", "kind": "paradigm", "id": "evidence-first"},
        ],
        "edges": [],
        "schema_version": "1",
    }


@pytest.fixture
def interview_sections() -> list[str]:
    return [
        "mission_type",
        "language_scope",
        "testing_philosophy",
        "neutrality_posture",
        "risk_appetite",
    ]


# ---------------------------------------------------------------------------
# Tier-1: kind_slug (project-local, synthesizable kinds)
# ---------------------------------------------------------------------------


class TestTier1KindSlug:
    def test_directive_hit_by_artifact_id(
        self, all_artifacts, merged_drg, interview_sections, directive_artifact
    ) -> None:
        """directive:PROJECT_001 → tier-1 hit (matched by artifact_id)."""
        result = resolve("directive:PROJECT_001", all_artifacts, merged_drg, interview_sections)
        assert result.matched_form == "kind_slug"
        assert result.targets == [directive_artifact]
        assert result.matched_value == "directive:PROJECT_001"

    def test_tactic_hit_by_slug(
        self, all_artifacts, merged_drg, interview_sections, tactic_artifact
    ) -> None:
        """tactic:how-we-apply-directive-003 → tier-1 hit (matched by slug)."""
        result = resolve(
            "tactic:how-we-apply-directive-003", all_artifacts, merged_drg, interview_sections
        )
        assert result.matched_form == "kind_slug"
        assert result.targets == [tactic_artifact]

    def test_styleguide_hit(
        self, all_artifacts, merged_drg, interview_sections, styleguide_artifact
    ) -> None:
        """styleguide:python-testing-style → tier-1 hit."""
        result = resolve(
            "styleguide:python-testing-style", all_artifacts, merged_drg, interview_sections
        )
        assert result.matched_form == "kind_slug"
        assert result.targets == [styleguide_artifact]

    def test_us3_local_first_over_drg_urn(
        self, all_artifacts, merged_drg, interview_sections, tactic_artifact
    ) -> None:
        """US-3: tactic:how-we-apply-directive-003 routes to project artifact (tier-1),
        NOT to a DRG URN lookup (tier-2), even though DIRECTIVE_003 is in the DRG.

        This is the critical local-first correctness property.
        """
        result = resolve(
            "tactic:how-we-apply-directive-003", all_artifacts, merged_drg, interview_sections
        )
        # Must be tier-1, not tier-2
        assert result.matched_form == "kind_slug"
        assert len(result.targets) == 1
        assert result.targets[0].kind == "tactic"
        assert result.targets[0].slug == "how-we-apply-directive-003"

    def test_tier1_miss_falls_through_to_tier2(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """directive:DIRECTIVE_003 — LHS is synthesizable but NO project-local
        artifact has artifact_id=DIRECTIVE_003, so tier-1 misses and falls to tier-2.
        """
        # tactic_artifact + styleguide_artifact both reference directive:DIRECTIVE_003
        result = resolve("directive:DIRECTIVE_003", all_artifacts, merged_drg, interview_sections)
        # Falls to tier-2 (DRG URN lookup)
        assert result.matched_form == "drg_urn"
        # The two project-local artifacts whose source_urns contain directive:DIRECTIVE_003
        assert len(result.targets) == 2
        slugs = {t.slug for t in result.targets}
        assert "how-we-apply-directive-003" in slugs
        assert "python-testing-style" in slugs

    def test_unsynthesizable_kind_skips_tier1(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """paradigm:evidence-first — LHS not synthesizable → skips tier-1 entirely."""
        result = resolve("paradigm:evidence-first", all_artifacts, merged_drg, interview_sections)
        # Goes straight to tier-2 (DRG URN), finds it, zero project-local refs → EC-4
        assert result.matched_form == "drg_urn"
        assert result.targets == []


# ---------------------------------------------------------------------------
# Tier-2: DRG URN
# ---------------------------------------------------------------------------


class TestTier2DrgUrn:
    def test_drg_urn_with_project_local_refs(
        self, all_artifacts, merged_drg, interview_sections, tactic_artifact, styleguide_artifact
    ) -> None:
        """directive:DIRECTIVE_003 → DRG URN hit; 2 project artifacts reference it."""
        result = resolve("directive:DIRECTIVE_003", all_artifacts, merged_drg, interview_sections)
        assert result.matched_form == "drg_urn"
        assert len(result.targets) == 2

    def test_drg_urn_zero_match_ec4(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """directive:DIRECTIVE_001 → DRG URN exists; directive_artifact refs it.

        If we strip source_urns from artifacts → zero project refs = EC-4.
        """
        # Create artifacts with NO reference to DIRECTIVE_001
        stripped_artifacts = [
            SynthesisTarget(
                kind="tactic",
                slug="some-tactic",
                title="Some Tactic",
                artifact_id="some-tactic",
                source_section="mission_type",
                # No source_urns referencing DIRECTIVE_001
            )
        ]
        result = resolve("directive:DIRECTIVE_001", stripped_artifacts, merged_drg, interview_sections)
        assert result.matched_form == "drg_urn"
        assert result.targets == []  # EC-4 zero-match

    def test_shipped_directive_003_via_drg_urn(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """directive:DIRECTIVE_003 → tier-2 (shipped URN, no local PROJECT_ artifact)."""
        # Remove tactic and styleguide that reference DIRECTIVE_003
        directive_only = [
            SynthesisTarget(
                kind="directive",
                slug="mission-scope",
                title="Mission Scope",
                artifact_id="PROJECT_001",
                source_section="mission_type",
                source_urns=("directive:DIRECTIVE_001",),
            )
        ]
        result = resolve("directive:DIRECTIVE_003", directive_only, merged_drg, interview_sections)
        assert result.matched_form == "drg_urn"
        assert result.targets == []  # Zero local refs → EC-4

    def test_unknown_drg_kind_falls_through_to_unresolved(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """foo:bar — LHS not a known DRG kind → misses tier-2, eventually raises."""
        with pytest.raises(TopicSelectorUnresolvedError) as exc_info:
            resolve("foo:bar", all_artifacts, merged_drg, interview_sections)
        err = exc_info.value
        assert err.raw == "foo:bar"


# ---------------------------------------------------------------------------
# Tier-3: interview section label
# ---------------------------------------------------------------------------


class TestTier3InterviewSection:
    def test_section_hit_with_matching_artifacts(
        self, all_artifacts, merged_drg, interview_sections, tactic_artifact, styleguide_artifact
    ) -> None:
        """testing_philosophy → tier-3 hit; returns tactic + styleguide artifacts."""
        result = resolve("testing_philosophy", all_artifacts, merged_drg, interview_sections)
        assert result.matched_form == "interview_section"
        slugs = {t.slug for t in result.targets}
        assert "how-we-apply-directive-003" in slugs
        assert "python-testing-style" in slugs
        assert "mission-scope" not in slugs  # mission_type section, not testing_philosophy

    def test_hyphenated_section_alias_resolves_to_canonical_section(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """testing-philosophy is normalized to testing_philosophy for operator UX."""
        result = resolve("testing-philosophy", all_artifacts, merged_drg, interview_sections)
        assert result.matched_form == "interview_section"
        assert result.matched_value == "testing_philosophy"
        slugs = {t.slug for t in result.targets}
        assert "how-we-apply-directive-003" in slugs
        assert "python-testing-style" in slugs

    def test_section_hit_with_no_artifacts(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """language_scope → tier-3 hit but no artifacts reference that section."""
        result = resolve("language_scope", all_artifacts, merged_drg, interview_sections)
        assert result.matched_form == "interview_section"
        assert result.targets == []

    def test_section_hit_single_artifact(
        self, all_artifacts, merged_drg, interview_sections, directive_artifact
    ) -> None:
        """mission_type → tier-3 hit; only the directive artifact."""
        result = resolve("mission_type", all_artifacts, merged_drg, interview_sections)
        assert result.matched_form == "interview_section"
        assert len(result.targets) == 1
        assert result.targets[0].slug == "mission-scope"

    def test_unknown_section_raises(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """no_colon_but_not_a_section → unresolved."""
        with pytest.raises(TopicSelectorUnresolvedError) as exc_info:
            resolve("totally_unknown_section", all_artifacts, merged_drg, interview_sections)
        assert exc_info.value.raw == "totally_unknown_section"


# ---------------------------------------------------------------------------
# Unresolved (all tiers fail)
# ---------------------------------------------------------------------------


class TestUnresolved:
    def test_unresolved_structured_error_fields(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """Unresolved topic → TopicSelectorUnresolvedError with required fields."""
        with pytest.raises(TopicSelectorUnresolvedError) as exc_info:
            resolve("zzz:nonexistent", all_artifacts, merged_drg, interview_sections)
        err = exc_info.value
        assert err.raw == "zzz:nonexistent"
        assert isinstance(err.candidates, tuple)
        assert isinstance(err.attempted_forms, tuple)

    def test_candidates_are_bounded_to_5(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """Candidate list is capped at 5 entries."""
        with pytest.raises(TopicSelectorUnresolvedError) as exc_info:
            resolve("xyzzy:bogus", all_artifacts, merged_drg, interview_sections)
        err = exc_info.value
        assert len(err.candidates) <= 5

    def test_candidates_are_deterministic(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """Same inputs → same candidate ordering across calls."""
        results = []
        for _ in range(3):
            with pytest.raises(TopicSelectorUnresolvedError) as exc_info:
                resolve("directive:PROJECT_ZZZ", all_artifacts, merged_drg, interview_sections)
            results.append(exc_info.value.candidates)
        assert results[0] == results[1] == results[2]

    def test_attempted_forms_colon_synthesizable(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """Selector with ':' and synthesizable LHS records both kind_slug + drg_urn."""
        with pytest.raises(TopicSelectorUnresolvedError) as exc_info:
            resolve("directive:PROJECT_ZZZ", all_artifacts, merged_drg, interview_sections)
        err = exc_info.value
        # kind_slug attempted (tier-1), then drg_urn (tier-2)
        assert "kind_slug" in err.attempted_forms
        assert "drg_urn" in err.attempted_forms

    def test_attempted_forms_no_colon(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """Selector without ':' records interview_section form."""
        with pytest.raises(TopicSelectorUnresolvedError) as exc_info:
            resolve("no_colon_at_all", all_artifacts, merged_drg, interview_sections)
        err = exc_info.value
        assert "interview_section" in err.attempted_forms
        assert "kind_slug" not in err.attempted_forms

    def test_empty_selector_raises_value_error(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """Empty string raises ValueError (C-004 rejection)."""
        with pytest.raises(ValueError, match="non-empty"):
            resolve("", all_artifacts, merged_drg, interview_sections)

    def test_whitespace_only_selector_raises_value_error(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """Whitespace-only string raises ValueError."""
        with pytest.raises(ValueError):
            resolve("   ", all_artifacts, merged_drg, interview_sections)


# ---------------------------------------------------------------------------
# SC-008: unresolved < 2 s on cold cache
# ---------------------------------------------------------------------------


class TestPerformanceSc008:
    def test_unresolved_under_2_seconds(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """SC-008: TopicSelectorUnresolvedError return < 2 s."""
        start = time.monotonic()
        with pytest.raises(TopicSelectorUnresolvedError):
            resolve("zxqwerty:bogus", all_artifacts, merged_drg, interview_sections)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"SC-008 violated: took {elapsed:.3f}s (limit: 2.0s)"

    def test_resolved_tier1_fast(
        self, all_artifacts, merged_drg, interview_sections
    ) -> None:
        """Tier-1 resolution is always fast (in-memory dict scan)."""
        start = time.monotonic()
        resolve("directive:PROJECT_001", all_artifacts, merged_drg, interview_sections)
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, f"Tier-1 took {elapsed:.3f}s unexpectedly"
