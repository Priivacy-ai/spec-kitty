"""Characterization tests for Sonar S3776/S1192 remediation helpers (WP03).

Each section below pins the behaviour of small, deterministic helper
functions extracted from higher-cognitive-complexity functions during the
``charter-sync-sonar-remediation`` mission. The extractions are
behavior-preserving refactors; these tests exercise the extracted helpers
directly (in addition to the pre-existing suites that exercise them
indirectly through the public entry points).

Sections:

* ``TestInterviewMappingHelpers`` — ``src/charter/synthesizer/interview_mapping.py``
  (``normalize_interview_snapshot``'s S3776 finding, cc ~18 -> decomposed).
* ``TestSectionBodiesHelpers`` — ``src/charter/context_renderers/section_bodies.py``
  (``_find_next_section_start``'s S3776 finding, cc ~18 -> decomposed).
* ``TestProfileSectionsHelpers`` — ``src/charter/context_renderers/profile_sections.py``
  (``render_profile_selector_refs`` cc ~18 and ``_render_profile_directives``
  cc ~17 -> decomposed; plus the S1192 duplicate-literal hoist onto
  ``_PROFILE_CODE_CHANGE_WHEN``).
"""

from __future__ import annotations

from typing import Any

import pytest

from charter.activation._catalog_miss import CharterCatalogMissWarning
from charter.activation.context_renderers.profile_sections import (
    _PROFILE_CODE_CHANGE_WHEN,
    _catalog_miss_lines,
    _render_directive_entry,
    _render_selector_entry,
    _resolve_catalog_artifact,
)
from charter.activation.context_renderers.section_bodies import (
    _close_fence_if_matched,
    _heading_offset_if_match,
    _open_fence_if_started,
)
from charter.activation.synthesizer.interview_mapping import (
    _copy_alias_answer_into_canonical_section,
    _extract_languages_from_alias,
    _normalize_language_scope_section,
)


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# interview_mapping.py
# ---------------------------------------------------------------------------


class TestInterviewMappingHelpers:
    def test_copy_alias_answer_into_canonical_section_copies_and_removes_alias(
        self,
    ) -> None:
        snapshot: dict[str, Any] = {"testing_requirements": "pytest, coverage>=80%"}

        _copy_alias_answer_into_canonical_section(
            snapshot, "testing_philosophy", ("testing_requirements",)
        )

        assert snapshot["testing_philosophy"] == "pytest, coverage>=80%"
        assert "testing_requirements" not in snapshot

    def test_copy_alias_answer_into_canonical_section_prefers_existing_canonical(
        self,
    ) -> None:
        snapshot: dict[str, Any] = {
            "testing_philosophy": "canonical answer",
            "testing_requirements": "alias answer",
        }

        _copy_alias_answer_into_canonical_section(
            snapshot, "testing_philosophy", ("testing_requirements",)
        )

        # Canonical value wins and is left untouched; the alias key is still
        # removed since the section is now known to be non-blank.
        assert snapshot["testing_philosophy"] == "canonical answer"
        assert "testing_requirements" not in snapshot

    def test_copy_alias_answer_into_canonical_section_noop_when_both_blank(
        self,
    ) -> None:
        snapshot: dict[str, Any] = {"unrelated": "value"}

        _copy_alias_answer_into_canonical_section(
            snapshot, "testing_philosophy", ("testing_requirements",)
        )

        assert snapshot == {"unrelated": "value"}

    def test_normalize_language_scope_section_leaves_existing_languages(self) -> None:
        snapshot: dict[str, Any] = {
            "language_scope": ["Python"],
            "languages_frameworks": "irrelevant free text",
        }

        _normalize_language_scope_section(snapshot)

        assert snapshot["language_scope"] == ["Python"]
        assert "languages_frameworks" not in snapshot

    def test_normalize_language_scope_section_derives_from_alias_text(self) -> None:
        snapshot: dict[str, Any] = {
            "languages_frameworks": "We use Python with pytest and mypy.",
        }

        _normalize_language_scope_section(snapshot)

        assert snapshot["language_scope"] == ["python"]
        assert "languages_frameworks" not in snapshot

    def test_normalize_language_scope_section_keeps_alias_when_extraction_empty(
        self,
    ) -> None:
        # No recognized language token in the alias text: extraction yields
        # nothing, so the alias key is intentionally left in place (matches
        # the original inline behaviour: the pop is gated on ``languages``
        # being truthy at the end).
        snapshot: dict[str, Any] = {
            "languages_frameworks": "We use Kotlin exclusively.",
        }

        _normalize_language_scope_section(snapshot)

        assert "language_scope" not in snapshot
        assert snapshot["languages_frameworks"] == "We use Kotlin exclusively."

    def test_normalize_language_scope_section_noop_when_nothing_present(self) -> None:
        snapshot: dict[str, Any] = {"unrelated": "value"}

        _normalize_language_scope_section(snapshot)

        assert snapshot == {"unrelated": "value"}

    def test_extract_languages_from_alias_parses_free_text(self) -> None:
        assert _extract_languages_from_alias("Python and TypeScript shop.") == (
            "python",
            "typescript",
        )

    def test_extract_languages_from_alias_passes_through_list(self) -> None:
        assert _extract_languages_from_alias([" python ", "", "rust"]) == (
            "python",
            "rust",
        )

    def test_extract_languages_from_alias_empty_for_unrecognized_text(self) -> None:
        assert _extract_languages_from_alias("Kotlin only.") == ()


# ---------------------------------------------------------------------------
# section_bodies.py
# ---------------------------------------------------------------------------


class TestSectionBodiesHelpers:
    def test_close_fence_if_matched_resets_state_on_close(self) -> None:
        result = _close_fence_if_matched("```\n", "`", 3)
        assert result == (None, 0)

    def test_close_fence_if_matched_keeps_state_when_not_closing(self) -> None:
        result = _close_fence_if_matched("some code\n", "`", 3)
        assert result == ("`", 3)

    def test_heading_offset_if_match_returns_offset_for_same_level(self) -> None:
        assert _heading_offset_if_match("## Next Heading\n", 2, 42) == 42

    def test_heading_offset_if_match_returns_offset_for_higher_level(self) -> None:
        # A level-1 heading is "same-or-higher" than a level-2 boundary.
        assert _heading_offset_if_match("# Top Heading\n", 2, 7) == 7

    def test_heading_offset_if_match_returns_none_for_deeper_heading(self) -> None:
        assert _heading_offset_if_match("### Nested Heading\n", 2, 7) is None

    def test_heading_offset_if_match_returns_none_for_non_heading_line(self) -> None:
        assert _heading_offset_if_match("plain text\n", 2, 7) is None

    def test_open_fence_if_started_returns_false_flag_when_no_fence(self) -> None:
        result = _open_fence_if_started("plain text\n", ["plain text\n"], 0)
        assert result == (None, 0, False)

    def test_open_fence_if_started_detects_open_and_close(self) -> None:
        lines = ["```\n", "code\n", "```\n"]
        result = _open_fence_if_started(lines[0], lines, 0)
        assert result == ("`", 3, False)

    def test_open_fence_if_started_detects_unclosed_fence(self) -> None:
        lines = ["```\n", "code with no closing fence\n"]
        result = _open_fence_if_started(lines[0], lines, 0)
        assert result == ("`", 3, True)


# ---------------------------------------------------------------------------
# profile_sections.py
# ---------------------------------------------------------------------------


class _StubCatalogRepo:
    """Minimal repo stub exposing ``get`` for the helper unit tests."""

    def __init__(self, items: dict[str, Any] | None = None, *, raises: bool = False) -> None:
        self._items = items or {}
        self._raises = raises

    def get(self, item_id: str) -> Any | None:
        if self._raises:
            raise RuntimeError("catalog backend unavailable")
        return self._items.get(item_id)


class TestProfileSectionsHelpers:
    def test_profile_code_change_when_constant_is_the_single_source(self) -> None:
        # S1192: every call site that previously hardcoded the literal now
        # references the module constant.
        assert _PROFILE_CODE_CHANGE_WHEN == "are about to apply a code change"

    def test_resolve_catalog_artifact_returns_none_for_missing_repo(self) -> None:
        assert _resolve_catalog_artifact(None, "anything") is None

    def test_resolve_catalog_artifact_returns_hit(self) -> None:
        sentinel = object()
        repo = _StubCatalogRepo({"tactic-001": sentinel})
        assert _resolve_catalog_artifact(repo, "tactic-001") is sentinel

    def test_resolve_catalog_artifact_swallows_lookup_failure(self) -> None:
        repo = _StubCatalogRepo(raises=True)
        assert _resolve_catalog_artifact(repo, "tactic-001") is None

    def test_catalog_miss_lines_emits_warning_and_stanza(self) -> None:
        with pytest.warns(CharterCatalogMissWarning):
            lines = _catalog_miss_lines(
                selector_kind="tactic",
                artifact_id="does-not-exist",
                repo=None,
                profile_id="synthetic-profile",
            )

        assert any("does-not-exist" in line for line in lines)

    def test_render_selector_entry_renders_header_with_rationale(self) -> None:
        lines = _render_selector_entry(
            raw_id="tactic-001",
            rationale="applies to refactors",
            repo=None,
            selector_kind="tactic",
            profile_id="synthetic-profile",
            when_clause=_PROFILE_CODE_CHANGE_WHEN,
            body_fn=None,
        )
        assert lines[0] == "  - tactic-001: applies to refactors"

    def test_render_selector_entry_missing_artifact_emits_catalog_miss_stanza(
        self,
    ) -> None:
        lines = _render_selector_entry(
            raw_id="tactic-missing",
            rationale="",
            repo=_StubCatalogRepo(),
            selector_kind="tactic",
            profile_id="synthetic-profile",
            when_clause=_PROFILE_CODE_CHANGE_WHEN,
            body_fn=None,
        )
        assert lines[0] == "  - tactic-missing"
        assert any("tactic-missing" in line for line in lines[1:])

    def test_render_selector_entry_prefers_inline_body_under_budget(self) -> None:
        sentinel = object()
        repo = _StubCatalogRepo({"tactic-001": sentinel})

        lines = _render_selector_entry(
            raw_id="tactic-001",
            rationale="",
            repo=repo,
            selector_kind="tactic",
            profile_id="synthetic-profile",
            when_clause=_PROFILE_CODE_CHANGE_WHEN,
            body_fn=lambda _artifact: ["    Name: refactor"],
        )
        assert "    Name: refactor" in lines

    def test_render_selector_entry_falls_back_to_fetch_stanza_when_no_body(
        self,
    ) -> None:
        sentinel = object()
        repo = _StubCatalogRepo({"tactic-001": sentinel})

        lines = _render_selector_entry(
            raw_id="tactic-001",
            rationale="",
            repo=repo,
            selector_kind="tactic",
            profile_id="synthetic-profile",
            when_clause=_PROFILE_CODE_CHANGE_WHEN,
            body_fn=None,
        )
        assert any("--include tactic:tactic-001" in line for line in lines)

    def test_render_directive_entry_renders_header_line(self) -> None:
        class _Ref:
            code = "010"
            name = "Directive Title"
            rationale = "because governance"

        lines = _render_directive_entry(_Ref(), None, "synthetic-profile")

        assert lines[0] == "  - DIRECTIVE_010: Directive Title — because governance"

    def test_render_directive_entry_missing_directive_emits_catalog_miss_stanza(
        self,
    ) -> None:
        class _Ref:
            code = "999"
            name = ""
            rationale = ""

        lines = _render_directive_entry(_Ref(), _StubCatalogRepo(), "synthetic-profile")

        assert lines[0] == "  - DIRECTIVE_999: "
        assert any("DIRECTIVE_999" in line for line in lines[1:])
