"""WP05 unit + integration tests — section selectors graceful-degrade (FR-010).

Pins the fix for **#3095** (its terminology-canon twin **#3094**, and its
code-review-checklist twin **#2552**): ``charter context --include
section:terminology-canon`` / ``section:code-review-checklist`` — required
by the generated ``implement``/``review`` prompts — used to dead-end with
``ValueError("No charter section found for selector ...")`` whenever the
charter carried no verbatim heading for those sections. A freshly-compiled
pack's seeded ``charter.md`` (``_CHARTER_MD_COMPANION_SEED`` in
``specify_cli.cli.commands.charter.generate``) is exactly such a charter —
it is a minimal starter that does not author either heading, so this bug
fired on every fresh pack (masked in-repo only because this repository's
own hand-authored ``.kittify/charter/charter.md`` happens to carry both
headings — a false-green per ``research.md`` Decision 1).

The fix lives entirely in
``charter.activation.context_renderers.section_bodies.render_critical_section_include``:
both of its ``return None`` sites for a *recognized* critical-section slug
(``if body is None: return None`` when the heading is absent from the
charter content, and the historical dead-end this fed at
``context.py:354``) now yield an honest, non-fabricated placeholder instead
of ``None`` — the selector always resolves to *something usable* (FR-010 /
SC-007) without inventing governance content (#2808-safe).

Coverage:

* T041a/b — ``render_critical_section_include`` returns a non-``None``
  placeholder for both ``Terminology Canon`` and ``Code Review Checklist``
  when the heading is absent (the ``if body is None: return None`` site).
* T041c/d — returns the real verbatim body when the heading is present.
* T041e — the placeholder text is honest: it names the missing heading and
  points at the real authoring surface (``.kittify/charter/charter.md``),
  never fabricating governance content.
* T041f/g — integration: ``build_charter_context_include`` (the
  ``charter context --include section:<id>`` engine, ``context.py:342``)
  resolves ``section:terminology-canon`` and ``section:code-review-checklist``
  to a rendered string — never raises "No charter section found for
  selector" — against a charter.md seeded from the *real* production
  ``_CHARTER_MD_COMPANION_SEED`` (a genuinely fresh, minimal pack's
  companion, not this repo's hand-authored charter.md, which would
  false-green per the bug's own root-cause analysis).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from charter.activation.context import build_charter_context_include
from charter.activation.context_renderers.section_bodies import (
    CODE_REVIEW_CHECKLIST,
    TERMINOLOGY_CANON,
    render_critical_section_include,
)
from specify_cli.cli.commands.charter.generate import _CHARTER_MD_COMPANION_SEED

pytestmark = pytest.mark.fast


_CHARTER_WITHOUT_CRITICAL_SECTIONS = textwrap.dedent(
    """\
    # Project Charter

    ## Purpose

    A charter that never authored either action-critical section.
    """
)

_CHARTER_WITH_TERMINOLOGY_CANON = textwrap.dedent(
    """\
    # Project Charter

    ## Terminology Canon

    - The canonical term for a unit of governed work is **Mission**.
    """
)

_CHARTER_WITH_CODE_REVIEW_CHECKLIST = textwrap.dedent(
    """\
    # Project Charter

    ## Code Review Checklist

    - Confirm tests were added for new functionality.
    """
)


class TestGracefulDegradePlaceholder:
    """``render_critical_section_include`` never dead-ends on a known slug."""

    def test_missing_terminology_canon_returns_placeholder_not_none(self) -> None:
        result = render_critical_section_include(
            _CHARTER_WITHOUT_CRITICAL_SECTIONS,
            "terminology-canon",
        )

        assert result is not None
        assert TERMINOLOGY_CANON in result
        assert ".kittify/charter/charter.md" in result

    def test_missing_code_review_checklist_returns_placeholder_not_none(self) -> None:
        result = render_critical_section_include(
            _CHARTER_WITHOUT_CRITICAL_SECTIONS,
            "code-review-checklist",
        )

        assert result is not None
        assert CODE_REVIEW_CHECKLIST in result
        assert ".kittify/charter/charter.md" in result

    def test_placeholder_is_honest_not_fabricated_governance(self) -> None:
        """The placeholder must not invent authoritative content (#2808-safe)."""
        result = render_critical_section_include(
            _CHARTER_WITHOUT_CRITICAL_SECTIONS,
            "terminology-canon",
        )

        assert result is not None
        assert "has not yet authored" in result
        # It must not smuggle in a real terminology rule -- only a pointer
        # to where the operator should author one.
        assert "canonical term is" not in result.lower()

    def test_present_terminology_canon_returns_real_body(self) -> None:
        result = render_critical_section_include(
            _CHARTER_WITH_TERMINOLOGY_CANON,
            "terminology-canon",
        )

        assert result is not None
        assert "The canonical term for a unit of governed work is" in result
        assert "has not yet authored" not in result

    def test_present_code_review_checklist_returns_real_body(self) -> None:
        result = render_critical_section_include(
            _CHARTER_WITH_CODE_REVIEW_CHECKLIST,
            "code-review-checklist",
        )

        assert result is not None
        assert "Confirm tests were added for new functionality." in result
        assert "has not yet authored" not in result

    def test_unrecognized_slug_still_returns_none(self) -> None:
        """Boundary check: an *unknown* selector is a different failure mode.

        FR-010 is scoped to *advertised* selectors (a recognized
        critical-section slug) whose content is absent -- not to arbitrary
        unrecognized ``section:<id>`` tokens. Those keep failing closed so
        ``context.py`` raises its own structured "No charter section found"
        error rather than fabricating a placeholder for a heading nobody
        asked about.
        """
        result = render_critical_section_include(
            _CHARTER_WITHOUT_CRITICAL_SECTIONS,
            "not-a-known-critical-section",
        )

        assert result is None


class TestFreshlyCompiledPackSelectorResolves:
    """Integration: the CLI-facing selector resolves against a fresh pack.

    ``_CHARTER_MD_COMPANION_SEED`` is the *real* production starter that
    ``charter generate`` writes when ``charter.md`` is absent
    (``specify_cli/cli/commands/charter/generate.py``). It is confirmed
    (below) to genuinely lack both action-critical headings, so it
    reproduces the exact fresh-pack shape from the bug report instead of
    a hand-rolled substitute -- and, critically, is NOT this repository's
    own hand-authored ``.kittify/charter/charter.md`` (which carries both
    headings and would false-green the regression, per the root-cause
    analysis in ``research.md`` Decision 1).
    """

    def test_seed_genuinely_lacks_both_critical_headings(self) -> None:
        """Guard: if the seed ever grows these headings, this test — not a
        silent false-green — is what should fail first."""
        assert "Terminology Canon" not in _CHARTER_MD_COMPANION_SEED
        assert "Code Review Checklist" not in _CHARTER_MD_COMPANION_SEED

    def _write_fresh_pack_charter_md(self, tmp_path: Path) -> None:
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text(
            _CHARTER_MD_COMPANION_SEED, encoding="utf-8"
        )

    def test_terminology_canon_selector_resolves_against_fresh_pack(
        self, tmp_path: Path
    ) -> None:
        self._write_fresh_pack_charter_md(tmp_path)

        result = build_charter_context_include(tmp_path, "section:terminology-canon")

        assert isinstance(result, str)
        assert result
        assert TERMINOLOGY_CANON in result

    def test_code_review_checklist_selector_resolves_against_fresh_pack(
        self, tmp_path: Path
    ) -> None:
        self._write_fresh_pack_charter_md(tmp_path)

        result = build_charter_context_include(
            tmp_path, "section:code-review-checklist"
        )

        assert isinstance(result, str)
        assert result
        assert CODE_REVIEW_CHECKLIST in result
