"""Profile-binding for the supply-chain security layer (WP05, T018).

Mission ``supply-chain-security-checks-layer-01KZBFBS``. Proves the 7 targeted
profiles (``reviewer-renata``, ``implementer-ivan``, ``node-norris``,
``frontend-freddy``, ``python-pedro``, ``java-jenny``, ``architect-alphonso``)
resolve -- through :meth:`AgentProfileRepository.resolve_profile`, the same
inheritance-aware resolution path production code uses, not a raw YAML read --
with a substantive reference to directive ``051`` (Supply-Chain Install
Safety) and to a tactic that actually carries supply-chain content
(``dependency-hygiene``, extended by WP01, or the new
``supply-chain-install-safety`` tactic). It also proves ``reviewer-renata``
specifically carries the adversarial-evidence disposition vocabulary
(``accepted`` / ``changed`` / ``deferred_with_rationale``) required by
``contracts/adversarial-evidence-contract.md`` so that a contested
supply-chain finding can never be dropped silently during review.
"""

from __future__ import annotations

import pytest

from charter.offering.agent_profiles.profile import AgentProfile
from charter.offering.agent_profiles.repository import AgentProfileRepository
from charter.offering.directives.repository import DirectiveRepository

pytestmark = [pytest.mark.fast, pytest.mark.doctrine, pytest.mark.corpus]

_TARGETED_PROFILES = (
    "reviewer-renata",
    "implementer-ivan",
    "node-norris",
    "frontend-freddy",
    "python-pedro",
    "java-jenny",
    "architect-alphonso",
)
_DIRECTIVE_CODE = "051"
_SUPPLY_CHAIN_DIRECTIVE_TITLE = "Supply-Chain Install Safety"
_SUPPLY_CHAIN_TACTIC_IDS = frozenset({"dependency-hygiene", "supply-chain-install-safety"})
_SUPPLY_CHAIN_KEYWORDS = ("supply-chain", "lifecycle-script")
_DISPOSITION_TERMS = ("accepted", "changed", "deferred_with_rationale")


@pytest.fixture(scope="module")
def repo() -> AgentProfileRepository:
    return AgentProfileRepository()


@pytest.fixture(scope="module")
def directive_repo() -> DirectiveRepository:
    return DirectiveRepository()


class TestTargetedProfilesReferenceSupplyChainDirective:
    """Every targeted profile resolves with a substantive directive-051 reference."""

    @pytest.mark.parametrize("profile_id", _TARGETED_PROFILES)
    def test_resolves_and_references_directive_051(
        self, repo: AgentProfileRepository, profile_id: str
    ) -> None:
        profile = repo.resolve_profile(profile_id)
        codes = [ref.code for ref in profile.directive_references]
        assert _DIRECTIVE_CODE in codes, (
            f"{profile_id}: expected directive code '{_DIRECTIVE_CODE}' in "
            f"directive_references, got {codes}"
        )

        matching = next(ref for ref in profile.directive_references if ref.code == _DIRECTIVE_CODE)
        assert matching.rationale.strip(), f"{profile_id}: directive 051 rationale is empty"

    @pytest.mark.parametrize("profile_id", _TARGETED_PROFILES)
    def test_directive_051_resolves_to_supply_chain_title(
        self,
        repo: AgentProfileRepository,
        directive_repo: DirectiveRepository,
        profile_id: str,
    ) -> None:
        """Guard against a repeat of the 047/051 code-vs-directive mismatch:

        resolve the bound code through the real ``DirectiveRepository`` and
        assert the resolved directive's title is actually "Supply-Chain
        Install Safety" -- not merely that some code string matches. A future
        renumber that updates the code but points at the wrong directive
        would still fail this test.
        """
        profile = repo.resolve_profile(profile_id)
        matching = next(ref for ref in profile.directive_references if ref.code == _DIRECTIVE_CODE)

        directive = directive_repo.get(matching.code)
        assert directive is not None, (
            f"{profile_id}: directive code '{matching.code}' did not resolve "
            "to a known directive via DirectiveRepository"
        )
        assert directive.title == _SUPPLY_CHAIN_DIRECTIVE_TITLE, (
            f"{profile_id}: directive code '{matching.code}' resolved to "
            f"'{directive.title}', expected '{_SUPPLY_CHAIN_DIRECTIVE_TITLE}'"
        )


class TestTargetedProfilesReferenceSupplyChainTactic:
    """Every targeted profile resolves with a tactic reference that actually
    carries supply-chain content in its rationale -- not just a coincidental
    id match.
    """

    @pytest.mark.parametrize("profile_id", _TARGETED_PROFILES)
    def test_references_supply_chain_capable_tactic_with_substantive_rationale(
        self, repo: AgentProfileRepository, profile_id: str
    ) -> None:
        profile = repo.resolve_profile(profile_id)
        candidates = [
            ref for ref in profile.tactic_references if ref.id in _SUPPLY_CHAIN_TACTIC_IDS
        ]
        assert candidates, (
            f"{profile_id}: expected a tactic reference in "
            f"{sorted(_SUPPLY_CHAIN_TACTIC_IDS)}, got "
            f"{[ref.id for ref in profile.tactic_references]}"
        )

        assert any(
            keyword in ref.rationale.lower()
            for ref in candidates
            for keyword in _SUPPLY_CHAIN_KEYWORDS
        ), (
            f"{profile_id}: matched tactic reference(s) "
            f"{[c.id for c in candidates]} do not mention supply-chain content"
        )


class TestReviewerRenataCarriesAdversarialEvidenceVocabulary:
    """reviewer-renata specifically must surface the disposition vocabulary --
    not merely reference the directive/tactic like the other 6 profiles.
    """

    @pytest.fixture(scope="class")
    def profile(self, repo: AgentProfileRepository) -> AgentProfile:
        return repo.resolve_profile("reviewer-renata")

    def test_disposition_vocabulary_present_in_resolved_profile(
        self, profile: AgentProfile
    ) -> None:
        haystacks: list[str] = []
        haystacks.extend(mode.description for mode in profile.mode_defaults)
        haystacks.extend(ref.rationale for ref in profile.tactic_references)
        haystacks.extend(ref.rationale for ref in profile.directive_references)
        combined = "\n".join(haystacks).lower()

        missing = [term for term in _DISPOSITION_TERMS if term.lower() not in combined]
        assert missing == [], (
            f"reviewer-renata: missing adversarial-evidence disposition terms "
            f"{missing} across resolved mode-defaults/tactic-references/"
            "directive-references"
        )

    def test_adversarial_evidence_disposition_binding_present(
        self, profile: AgentProfile
    ) -> None:
        """The adversarial-evidence-disposition binding is re-homed onto a
        canonical reference rationale.

        Mission doctrine-drg-silent-drop-boundary-01M0PE7E retired the
        ``context-sources.additional`` surface where this binding used to live.
        It is NOT silently dropped: the ``supply-chain-install-safety``
        tactic-reference rationale already names the adversarial-evidence
        disposition contract explicitly, which this test now pins.
        """
        rationales = "\n".join(ref.rationale for ref in profile.tactic_references).lower()
        assert "adversarial-evidence-contract" in rationales, (
            "reviewer-renata: expected the adversarial-evidence disposition "
            "binding to survive on a tactic-reference rationale after the "
            "context-sources consolidation"
        )
