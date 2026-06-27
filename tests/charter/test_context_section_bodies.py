"""WP04 unit tests — ``render_critical_section_bodies`` (FR-001).

These tests exercise the pure renderer in
``charter.context_renderers.section_bodies`` against the five-row table
in the WP04 task spec (subtask T018).  They pin:

* verbatim section bodies surface when the heading is present;
* missing sections degrade to the fetch + when-doing stanza (no crash);
* action-specific section sets are honoured;
* unknown actions yield no block (empty string).
"""

from __future__ import annotations

import textwrap

import pytest

from charter.context_renderers import (
    CRITICAL_SECTION_WHEN_CLAUSES,
    critical_section_header,
    render_critical_section_bodies,
    render_critical_section_include,
)

pytestmark = pytest.mark.fast


_CHARTER_WITH_ALL_SECTIONS = textwrap.dedent(
    """\
    # Project Charter

    ## Purpose

    Minimal fixture for section-body rendering tests.

    ## Terminology Canon

    - The canonical term for a unit of governed work is **Mission**.
    - ``feature`` is forbidden in canonical, operator, and user-facing language.

    ## Regression Vigilance (2026-04-06)

    When renaming an identifier-bearing term, the reviewer MUST grep the
    diff for the old term and MUST consult ``docs/context/`` before
    approving.

    ## Code Review Checklist

    - The WP diff respects the agent profile's directive-references.
    - Terminology in code and docs aligns with the project glossary.
    """
)

_CHARTER_WITHOUT_REGRESSION_VIGILANCE = textwrap.dedent(
    """\
    # Project Charter

    ## Terminology Canon

    - canonical term is **Mission**.

    ## Code Review Checklist

    - check terminology alignment.
    """
)


_CHARTER_WITH_FENCED_MARKDOWN_HEADINGS = textwrap.dedent(
    """\
    # Project Charter

    ## Terminology Canon

    - canonical term is **Mission**.

    ## Regression Vigilance

    Preserve cleanup instructions around command examples:

    ```bash
    ## STEP 1
    spec-kitty glossary scan
        ```
    ## STEP 2
    spec-kitty glossary validate
    ```

    After cleanup, rerun the mission review.

    ## Code Review Checklist

    - This is the next section and not part of Regression Vigilance.
    """
)


_CHARTER_WITH_FENCED_SECTION_HEADING_EXAMPLE = textwrap.dedent(
    """\
    # Project Charter

    ## Purpose

    A documentation example can mention a critical section heading:

    ```markdown
    ## Regression Vigilance
    This is example text, not the charter rule.
    ```

    ## Terminology Canon

    - canonical term is **Mission**.

    ## Regression Vigilance

    The real rule requires the reviewer to consult docs/context/.

    ## Code Review Checklist

    - check terminology alignment.
    """
)


_CHARTER_WITH_NESTED_CRITICAL_SECTIONS = textwrap.dedent(
    """\
    # Project Charter

    ## Code Quality

    ### Code Review Checklist

    - Tests added for new functionality.
    - Type annotations present.

    ### Quality Gates

    - Required pytest surface passes.

    ## Terminology Canon (Mission vs Feature)

    - canonical term is **Mission**.

    ### Regression Vigilance (2026-04-06)

    Reviewers MUST grep the diff for the old term before approving.

    ## Charter Resolution Hints

    Not part of the critical section.
    """
)


_CHARTER_WITH_UNBALANCED_FENCE = textwrap.dedent(
    """\
    # Project Charter

    ## Terminology Canon

    - canonical term is **Mission**.

    ## Regression Vigilance

    Preserve cleanup instructions around command examples:

    ```bash
    ## STEP 1
    spec-kitty glossary scan

    ## Code Review Checklist

    - This is the next section and must not be swallowed by Regression Vigilance.
    """
)


def _rendered_section_body(rendered: str, heading: str) -> str:
    section_start = rendered.index(f"### {heading}")
    body_start = rendered.index("\n", section_start) + 1
    fetch_start = rendered.index("  Run: spec-kitty charter context --include", body_start)
    return rendered[body_start:fetch_start].rstrip()


class TestVerbatimBodies:
    """Existing headings render their body verbatim under a ``### <heading>`` line."""

    def test_terminology_canon_body_surfaces_verbatim_when_present(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITH_ALL_SECTIONS, action="implement"
        )
        assert critical_section_header("implement") in result
        assert "### Terminology Canon" in result
        # The literal body text must survive intact (whitespace + bullets).
        assert (
            "The canonical term for a unit of governed work is **Mission**"
            in result
        )

    def test_fenced_markdown_headings_do_not_truncate_section_body(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITH_FENCED_MARKDOWN_HEADINGS, action="implement"
        )

        body = _rendered_section_body(result, "Regression Vigilance")

        assert "## STEP 1" in body
        assert "## STEP 2" in body
        assert "After cleanup, rerun the mission review." in body
        assert "This is the next section" not in body

    def test_fenced_section_heading_example_does_not_spoof_section_start(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITH_FENCED_SECTION_HEADING_EXAMPLE, action="implement"
        )

        body = _rendered_section_body(result, "Regression Vigilance")

        assert "consult docs/context/" in body
        assert "This is example text" not in body
        assert "canonical term is **Mission**" not in body
        assert "check terminology alignment" not in body

    def test_unbalanced_fence_does_not_swallow_following_sections(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITH_UNBALANCED_FENCE, action="implement"
        )

        body = _rendered_section_body(result, "Regression Vigilance")

        assert "Preserve cleanup instructions" in body
        assert "```bash" not in body
        assert "## STEP 1" not in body
        assert "This is the next section" not in body
        assert result.count("  Run: spec-kitty charter context --include") == 3

    def test_section_include_ignores_fenced_heading_examples(self) -> None:
        result = render_critical_section_include(
            _CHARTER_WITH_FENCED_SECTION_HEADING_EXAMPLE,
            "regression-vigilance",
        )

        assert result is not None
        assert "consult docs/context/" in result
        assert "This is example text" not in result

    def test_nested_critical_headings_are_recoverable(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITH_NESTED_CRITICAL_SECTIONS,
            action="implement",
        )

        assert "Tests added for new functionality." in result
        assert "Reviewers MUST grep the diff" in result
        assert "Required pytest surface passes." not in result
        assert "Not part of the critical section." not in result

    def test_section_include_recovers_nested_critical_heading(self) -> None:
        result = render_critical_section_include(
            _CHARTER_WITH_NESTED_CRITICAL_SECTIONS,
            "regression-vigilance",
        )

        assert result is not None
        assert result.startswith("### Regression Vigilance")
        assert "Reviewers MUST grep the diff" in result
        assert "Not part of the critical section." not in result

    def test_section_include_fail_closed_on_unbalanced_fence(self) -> None:
        result = render_critical_section_include(
            _CHARTER_WITH_UNBALANCED_FENCE,
            "code-review-checklist",
        )

        assert result is None


class TestMissingSectionFetchStanza:
    """Missing headings degrade to the fetch + when-doing stanza."""

    def test_missing_section_emits_fetch_stanza(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITHOUT_REGRESSION_VIGILANCE, action="implement"
        )
        # The selector slug matches the kebab-cased heading.
        assert "section:regression-vigilance" in result
        # The when-doing clause is exactly the contract phrase.
        when_clause = CRITICAL_SECTION_WHEN_CLAUSES["Regression Vigilance"]
        assert f"When you {when_clause}" in result
        # No crash means the rest of the block still rendered too.
        assert critical_section_header("implement") in result


class TestActionSectionSets:
    """The set of critical sections is action-scoped."""

    def test_action_implement_uses_implement_section_set(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITH_ALL_SECTIONS, action="implement"
        )
        for heading in ("Terminology Canon", "Code Review Checklist", "Regression Vigilance"):
            assert f"### {heading}" in result

    def test_action_review_uses_review_section_set(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITH_ALL_SECTIONS, action="review"
        )
        for heading in ("Terminology Canon", "Code Review Checklist", "Regression Vigilance"):
            assert f"### {heading}" in result

    def test_unknown_action_emits_no_section(self) -> None:
        result = render_critical_section_bodies(
            _CHARTER_WITH_ALL_SECTIONS, action="unknown-action"
        )
        assert result == ""
