"""Unit tests for the WP05 token-budget enforcement (NFR-001).

The tests cover the standalone :func:`apply_token_budget` helper plus
the end-to-end self-sufficiency check that the full bootstrap render
respects the budget for the ``python-pedro`` profile fixture.
"""

from __future__ import annotations

import re

import pytest

from charter.context_renderers import (
    BUDGET_DEFAULT,
    RenderedSection,
    apply_token_budget,
    fetch_stanza,
    warning_line,
)
from charter.context_renderers.fetch_stanza import (
    DEFAULT_WHEN_CLAUSE,
    format_selector,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit]

def _make_section(
    section_id: str,
    body: str,
    *,
    selector: str = "",
    substitutable: bool = True,
    header: str = "",
    when: str = "are about to apply a code change",
    indent: str = "",
) -> RenderedSection:
    """Build a RenderedSection with reasonable defaults for the test grid."""

    if selector == "" and substitutable:
        selector = f"section:{section_id}"
    return RenderedSection(
        section_id=section_id,
        header=header,
        body=body,
        selector=selector,
        when_doing_clause=when,
        substitutable=substitutable,
        indent=indent,
    )


# ---------------------------------------------------------------------------
# apply_token_budget — substitution algorithm
# ---------------------------------------------------------------------------


class TestUnderBudget:
    """The under-budget path emits the original text and reports no swaps."""

    def test_under_budget_no_substitution(self) -> None:
        sections = [
            _make_section("alpha", "a" * 2_000),
            _make_section("beta", "b" * 3_000),
            _make_section("gamma", "g" * 3_000),
        ]
        joined, notes = apply_token_budget(sections, budget=32_000)

        assert notes == []
        # Original bodies survive verbatim
        assert "a" * 2_000 in joined
        assert "b" * 3_000 in joined
        assert "g" * 3_000 in joined
        # No warning line
        assert "# Governance payload" not in joined


class TestOverBudgetSubstitution:
    """The over-budget path swaps the longest body first."""

    def test_over_budget_substitutes_longest_first(self) -> None:
        long_body = "L" * 30_000
        sections = [
            _make_section("alpha", "a" * 200),
            _make_section("longest", long_body, selector="directive:DIRECTIVE_010"),
            _make_section("gamma", "g" * 5_000),
        ]
        joined, notes = apply_token_budget(sections, budget=10_000)

        # Longest body is gone
        assert long_body not in joined
        # Replaced with the canonical fetch stanza
        assert "spec-kitty charter context --include directive:DIRECTIVE_010" in joined
        assert "When you" in joined
        # Shorter bodies survive
        assert "a" * 200 in joined
        assert "g" * 5_000 in joined
        # Note recorded the swap
        assert any("longest" in note for note in notes)

    def test_severely_over_budget_substitutes_all_bodies(self) -> None:
        big_a = "A" * 20_000
        big_b = "B" * 20_000
        big_c = "C" * 20_000
        sections = [
            _make_section("alpha", big_a, selector="directive:A"),
            _make_section("beta", big_b, selector="tactic:B"),
            _make_section("gamma", big_c, selector="section:C"),
        ]
        joined, notes = apply_token_budget(sections, budget=10_000)

        # All three bodies replaced
        assert big_a not in joined
        assert big_b not in joined
        assert big_c not in joined
        # All three selectors appear in the substituted output
        assert "directive:A" in joined
        assert "tactic:B" in joined
        assert "section:C" in joined
        # All three swapped
        assert len(notes) == 3

    def test_substitution_is_deterministic_under_ties(self) -> None:
        # Three bodies of equal length — section_id ascending wins the tie.
        sections = [
            _make_section("zebra", "x" * 5_000, selector="directive:Z"),
            _make_section("apple", "x" * 5_000, selector="directive:A"),
            _make_section("mango", "x" * 5_000, selector="directive:M"),
        ]
        # Force two swaps
        _, notes1 = apply_token_budget(sections, budget=11_000)
        _, notes2 = apply_token_budget(sections, budget=11_000)

        assert notes1 == notes2
        # apple sorts first under ties (ascending section_id)
        assert "apple" in notes1[0]


# ---------------------------------------------------------------------------
# Warning line emission
# ---------------------------------------------------------------------------


class TestWarningLine:
    def test_warning_line_emitted_when_any_substitution_happens(self) -> None:
        long_body = "L" * 30_000
        sections = [
            _make_section("longest", long_body, selector="directive:DIRECTIVE_010"),
            _make_section("small", "s" * 100),
        ]
        joined, notes = apply_token_budget(sections, budget=5_000)

        assert notes  # at least one swap
        # The warning line is appended at the tail.
        assert joined.rstrip().endswith(
            warning_line(len(notes), 5_000)
        )

    def test_warning_line_absent_when_no_substitution(self) -> None:
        sections = [
            _make_section("alpha", "a" * 500),
            _make_section("beta", "b" * 500),
        ]
        joined, notes = apply_token_budget(sections, budget=32_000)

        assert notes == []
        assert "# Governance payload" not in joined

    def test_warning_line_counts_against_budget_after_substitution(self) -> None:
        long_body = "L" * 1_000
        short_body = "S" * 400
        sections = [
            _make_section("longest", long_body, selector="directive:DIRECTIVE_010"),
            _make_section("short", short_body, selector="tactic:TACTIC_010"),
        ]
        first_swap_text = "\n\n".join(
            [
                fetch_stanza("directive:DIRECTIVE_010", "are about to apply a code change"),
                short_body,
            ]
        )
        budget = len(first_swap_text) + 30

        joined, notes = apply_token_budget(sections, budget=budget)

        assert len(joined) <= budget
        assert long_body not in joined
        assert short_body not in joined
        assert len(notes) == 2
        assert joined.rstrip().endswith(warning_line(len(notes), budget))

    def test_production_context_budget_counts_warning_line(self) -> None:
        from charter.context import _enforce_token_budget

        section_block = "S" * 1_000
        profile_block = "P" * 400
        text = f"Charter Context (Bootstrap):\n\n{section_block}\n\n{profile_block}"
        first_swap_text = text.replace(
            section_block,
            fetch_stanza(
                "section:critical-implement",
                "need to consult the action-critical charter sections",
                indent="  ",
            ),
            1,
        )
        budget = len(first_swap_text) + 30

        result = _enforce_token_budget(
            text,
            action="implement",
            profile_block=profile_block,
            section_block=section_block,
            budget=budget,
        )

        assert len(result) <= budget
        assert section_block not in result
        assert profile_block not in result
        assert result.rstrip().endswith(warning_line(2, budget))


# ---------------------------------------------------------------------------
# Fetch stanza contract
# ---------------------------------------------------------------------------


class TestFetchStanzaContract:
    """The substituted fetch stanza MUST satisfy the ATDD regex pair."""

    _FETCH_CMD_RE = re.compile(
        r"spec-kitty\s+charter\s+context\b",
        re.IGNORECASE,
    )
    _WHEN_DOING_RE = re.compile(
        r"when\s+you\s+(are\s+about\s+to|need\s+to|encounter|introduce|rename|review)",
        re.IGNORECASE,
    )

    def test_fetch_stanza_carries_when_doing_clause(self) -> None:
        long_body = "L" * 30_000
        sections = [
            _make_section(
                "directive_010",
                long_body,
                selector="directive:DIRECTIVE_010",
                when="are about to apply a code change",
            ),
        ]
        joined, _notes = apply_token_budget(sections, budget=5_000)

        # The fetch command line and the when-doing line both match the
        # contract regexes pinned by the ATDD helper.
        assert self._FETCH_CMD_RE.search(joined), joined
        assert self._WHEN_DOING_RE.search(joined), joined
        # The selector is present verbatim.
        assert "directive:DIRECTIVE_010" in joined

    def test_default_when_clause_used_when_omitted(self) -> None:
        long_body = "L" * 30_000
        sections = [
            _make_section(
                "directive_010",
                long_body,
                selector="directive:DIRECTIVE_010",
                when="",  # falls back to DEFAULT_WHEN_CLAUSE
            ),
        ]
        joined, notes = apply_token_budget(sections, budget=5_000)

        assert notes
        assert DEFAULT_WHEN_CLAUSE in joined

    def test_fetch_stanza_helper_matches_contract(self) -> None:
        stanza = fetch_stanza("directive:DIRECTIVE_010", "rename or introduce a term in the diff")
        lines = stanza.splitlines()
        assert len(lines) == 2
        assert lines[0] == "Run: spec-kitty charter context --include directive:DIRECTIVE_010"
        assert lines[1].startswith("When you rename or introduce a term in the diff,")

    def test_format_selector_canonical_forms(self) -> None:
        assert format_selector("directive", "DIRECTIVE_010") == "directive:DIRECTIVE_010"
        assert format_selector("tactic", "lang-driven-design") == "tactic:lang-driven-design"
        assert format_selector("section", "terminology-canon") == "section:terminology-canon"
        # Unknown but non-empty kind round-trips (callers may extend).
        assert format_selector("custom", "x") == "custom:x"
        # Empty inputs collapse to the empty string.
        assert format_selector("", "x") == ""
        assert format_selector("directive", "") == ""


# ---------------------------------------------------------------------------
# Non-substitutable sections
# ---------------------------------------------------------------------------


class TestNonSubstitutable:
    """Authority paths and core doctrine MUST stay inline regardless of budget."""

    def test_authority_paths_never_substituted(self) -> None:
        # The authority-paths block is small but marked non-substitutable;
        # the long substitutable section is the only swap candidate.
        authority_block = "Project authority paths:\n  - docs/context/    (canonical terminology)"
        long_body = "L" * 30_000
        sections = [
            _make_section(
                "authority-paths",
                authority_block,
                selector="",
                substitutable=False,
            ),
            _make_section(
                "long-section",
                long_body,
                selector="section:long",
            ),
        ]
        joined, notes = apply_token_budget(sections, budget=5_000)

        # Authority block survives byte-for-byte.
        assert authority_block in joined
        # Long body is swapped.
        assert long_body not in joined
        assert any("long-section" in note for note in notes)

    def test_no_swap_when_only_non_substitutable_over_budget(self) -> None:
        # When every section is non-substitutable the algorithm returns
        # the over-budget text rather than looping forever.
        sections = [
            _make_section("only", "x" * 50_000, substitutable=False),
        ]
        joined, notes = apply_token_budget(sections, budget=10_000)

        assert notes == []
        assert len(joined) > 10_000  # over budget but content preserved


# ---------------------------------------------------------------------------
# Defaults + edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_input_returns_empty_text(self) -> None:
        joined, notes = apply_token_budget([], budget=32_000)
        assert joined == ""
        assert notes == []

    def test_default_budget_is_32k(self) -> None:
        assert BUDGET_DEFAULT == 32_000

    def test_non_positive_budget_is_noop(self) -> None:
        sections = [_make_section("a", "x" * 100)]
        joined, notes = apply_token_budget(sections, budget=0)
        assert notes == []
        assert "x" * 100 in joined


# ---------------------------------------------------------------------------
# Aggregate self-sufficiency — end-to-end render under budget
# ---------------------------------------------------------------------------


class TestAggregateUnderBudget:
    """The full bootstrap render against the python-pedro fixture stays under budget."""

    def test_aggregate_self_sufficiency_under_budget(self, tmp_path) -> None:
        from pathlib import Path

        from charter.context import build_charter_context

        # Use the spec-kitty repo's own charter as a representative fixture.
        repo_root = Path(__file__).resolve().parents[2]
        if not (repo_root / ".kittify" / "charter" / "charter.md").exists():
            pytest.skip("No charter.md present in repo (fixture unavailable)")

        result = build_charter_context(
            repo_root,
            profile="python-pedro",
            action="implement",
            mark_loaded=False,
        )
        assert len(result.text) <= BUDGET_DEFAULT, (
            f"Bootstrap render produced {len(result.text)} chars, "
            f"exceeding NFR-001 budget of {BUDGET_DEFAULT}."
        )
