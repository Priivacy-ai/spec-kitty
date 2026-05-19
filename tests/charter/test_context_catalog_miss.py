"""RISK-3 (Mission B post-merge) — catalog-miss surfacing tests.

Pins the behaviour added by mission ``layered-doctrine-org-layer`` /
RISK-3 remediation: the renderer must no longer hide catalog misses
behind a generic ``(catalog entry not found; verify charter selection)``
placeholder.  Instead it emits a structured stanza that classifies the
cause (typo / missing / schema-validation-suspected), provides an
actionable suggestion, and routes a warning through both
``warnings.warn`` (so it surfaces in normal stderr) and the module
logger (so it appears in any structured log surface).

Coverage:

* :class:`TestClassifyCatalogMiss` — pure-function classification.
* :class:`TestFormatCatalogMissStanza` — the rendered stanza shape.
* :class:`TestEmitCatalogMissWarning` — warning + logger plumbing.
* :class:`TestRendererIntegration` — end-to-end through
  ``_render_selected_styleguides`` covering the three documented causes
  (typo, missing artifact, schema-failure suggestion).
* :class:`TestProfileRendererIntegration` — same surfacing for profile-
  cited directive misses.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

import pytest

from charter._catalog_miss import (
    CatalogMissCause,
    CatalogMissDiagnosis,
    CharterCatalogMissError,
    CharterCatalogMissWarning,
    classify_catalog_miss,
    emit_catalog_miss_warning,
    format_catalog_miss_stanza,
)
from charter.context import (
    _render_profile_directives,
    _render_selected_styleguides,
)
from doctrine.agent_profiles import AgentProfile


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Stubs (intentionally minimal — exercise only the catalog-miss path)
# ---------------------------------------------------------------------------


class _StubRepo:
    """Repository stub that exposes ``get`` and ``list_all``.

    The catalog-miss diagnosis path uses ``list_all`` (preferred) or
    falls back to the stub's ``_items`` dict, so we exercise the
    canonical surface here.
    """

    def __init__(self, items: dict[str, Any] | None = None) -> None:
        self._items = items or {}

    def get(self, item_id: str) -> Any | None:
        return self._items.get(item_id)

    def list_all(self) -> list[Any]:
        return list(self._items.values())


class _Item:
    """Bare object carrying an ``id`` attribute for ``list_all`` iteration."""

    def __init__(self, item_id: str, **extra: Any) -> None:
        self.id = item_id
        for key, value in extra.items():
            setattr(self, key, value)


class _StubService:
    def __init__(self, *, styleguides: _StubRepo | None = None) -> None:
        self.styleguides = styleguides or _StubRepo()


# ---------------------------------------------------------------------------
# Pure-function classification
# ---------------------------------------------------------------------------


class TestClassifyCatalogMiss:
    def test_typo_returns_typo_suspected_with_closest_match(self) -> None:
        diagnosis = classify_catalog_miss(
            "caveman-comemnts",
            ["caveman-comments", "verbose-comments", "tdd-discipline"],
        )
        assert diagnosis.cause is CatalogMissCause.TYPO_SUSPECTED
        assert diagnosis.suggestion == "caveman-comments"

    def test_no_close_match_returns_missing_artifact(self) -> None:
        diagnosis = classify_catalog_miss(
            "completely-unrelated-name",
            ["alpha", "beta", "gamma"],
        )
        assert diagnosis.cause is CatalogMissCause.MISSING_ARTIFACT
        assert diagnosis.suggestion is None

    def test_empty_corpus_returns_missing_artifact(self) -> None:
        diagnosis = classify_catalog_miss("anything", [])
        assert diagnosis.cause is CatalogMissCause.MISSING_ARTIFACT
        assert diagnosis.suggestion is None

    def test_non_string_corpus_entries_ignored(self) -> None:
        # Defensive: the corpus may come from a duck-typed source.
        diagnosis = classify_catalog_miss(
            "caveman-comments",
            ["caveman-comments", 42, None],  # type: ignore[list-item]
        )
        assert diagnosis.cause is CatalogMissCause.TYPO_SUSPECTED


# ---------------------------------------------------------------------------
# Stanza formatting
# ---------------------------------------------------------------------------


class TestFormatCatalogMissStanza:
    def test_typo_stanza_includes_did_you_mean(self) -> None:
        diagnosis = CatalogMissDiagnosis(
            cause=CatalogMissCause.TYPO_SUSPECTED,
            suggestion="caveman-comments",
        )
        lines = format_catalog_miss_stanza(
            selector_kind="styleguide",
            artifact_id="caveman-comemnts",
            diagnosis=diagnosis,
        )
        joined = "\n".join(lines)
        assert "styleguide:caveman-comemnts" in joined
        assert "Cause: typo_suspected" in joined
        assert "did you mean 'caveman-comments'?" in joined

    def test_missing_artifact_stanza_suggests_both_paths(self) -> None:
        diagnosis = CatalogMissDiagnosis(cause=CatalogMissCause.MISSING_ARTIFACT)
        lines = format_catalog_miss_stanza(
            selector_kind="tactic",
            artifact_id="ghost-tactic",
            diagnosis=diagnosis,
        )
        joined = "\n".join(lines)
        assert "tactic:ghost-tactic" in joined
        assert "Cause: missing_artifact" in joined
        # Missing-artifact stanza must mention BOTH possible causes.
        assert "doctrine validate" in joined
        assert "project, org, and built-in" in joined

    def test_schema_failure_stanza_cites_doctrine_validate(self) -> None:
        diagnosis = CatalogMissDiagnosis(
            cause=CatalogMissCause.SCHEMA_VALIDATION_SUSPECTED
        )
        lines = format_catalog_miss_stanza(
            selector_kind="styleguide",
            artifact_id="caveman-comments",
            diagnosis=diagnosis,
        )
        joined = "\n".join(lines)
        assert "Cause: schema_validation_suspected" in joined
        assert "spec-kitty doctrine validate" in joined
        assert "Pydantic validation" in joined

    def test_indent_is_respected(self) -> None:
        diagnosis = CatalogMissDiagnosis(cause=CatalogMissCause.MISSING_ARTIFACT)
        lines = format_catalog_miss_stanza(
            selector_kind="procedure",
            artifact_id="x",
            diagnosis=diagnosis,
            indent="        ",
        )
        for line in lines:
            assert line.startswith("        ")


# ---------------------------------------------------------------------------
# Warning + logger plumbing
# ---------------------------------------------------------------------------


class TestEmitCatalogMissWarning:
    def test_warning_class_and_message(self) -> None:
        diagnosis = CatalogMissDiagnosis(
            cause=CatalogMissCause.TYPO_SUSPECTED,
            suggestion="caveman-comments",
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            emit_catalog_miss_warning(
                selector_kind="styleguide",
                artifact_id="caveman-comemnts",
                diagnosis=diagnosis,
            )
        miss_warnings = [
            w for w in captured if issubclass(w.category, CharterCatalogMissWarning)
        ]
        assert len(miss_warnings) == 1
        text = str(miss_warnings[0].message)
        assert "styleguide:caveman-comemnts" in text
        assert "cause=typo_suspected" in text
        assert "suggestion='caveman-comments'" in text

    def test_logger_extra_carries_structured_fields(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        diagnosis = CatalogMissDiagnosis(cause=CatalogMissCause.MISSING_ARTIFACT)
        with (
            caplog.at_level(logging.WARNING, logger="charter._catalog_miss"),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore", CharterCatalogMissWarning)
            emit_catalog_miss_warning(
                selector_kind="tactic",
                artifact_id="ghost",
                diagnosis=diagnosis,
                context="profile:python-pedro",
            )
        relevant = [
            r for r in caplog.records if r.name == "charter._catalog_miss"
        ]
        assert len(relevant) == 1
        record = relevant[0]
        assert record.kind == "tactic"  # type: ignore[attr-defined]
        assert record.id == "ghost"  # type: ignore[attr-defined]
        assert record.cause == "missing_artifact"  # type: ignore[attr-defined]
        assert record.context == "profile:python-pedro"  # type: ignore[attr-defined]

    def test_exception_class_is_distinct_from_value_error(self) -> None:
        err = CharterCatalogMissError(
            "styleguide:x",
            cause=CatalogMissCause.MISSING_ARTIFACT,
        )
        assert isinstance(err, Exception)
        assert not isinstance(err, ValueError)
        assert err.selector == "styleguide:x"
        assert err.cause is CatalogMissCause.MISSING_ARTIFACT


# ---------------------------------------------------------------------------
# Renderer integration — the three documented cases
# ---------------------------------------------------------------------------


class TestRendererIntegration:
    """End-to-end: catalog-miss flows through the renderer and surfaces."""

    def test_typo_case_renders_suggestion_and_warns(self) -> None:
        # Catalog carries the canonical ID; charter selected a typo.
        sg = _Item("caveman-comments", title="Caveman", principles=["UGG"])
        service = _StubService(
            styleguides=_StubRepo(items={"caveman-comments": sg})
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            lines = _render_selected_styleguides(["caveman-comemnts"], service)
        joined = "\n".join(lines)

        # Stanza content
        assert "styleguide:caveman-comemnts" in joined
        assert "Cause: typo_suspected" in joined
        assert "did you mean 'caveman-comments'?" in joined
        # Fetch stanza still present so the prompt remains actionable.
        assert (
            "spec-kitty charter context --include styleguide:caveman-comemnts"
            in joined
        )

        # Warning surfaced through the standard channel.
        miss = [
            w for w in captured if issubclass(w.category, CharterCatalogMissWarning)
        ]
        assert len(miss) == 1
        assert "typo_suspected" in str(miss[0].message)

    def test_missing_artifact_case_renders_dual_hint_and_warns(self) -> None:
        # No close match available — cause is MISSING_ARTIFACT, stanza
        # suggests both layer-check and `doctrine validate`.
        service = _StubService(
            styleguides=_StubRepo(
                items={
                    "alpha-style": _Item("alpha-style"),
                    "beta-style": _Item("beta-style"),
                }
            )
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            lines = _render_selected_styleguides(
                ["totally-distinct-name"], service
            )
        joined = "\n".join(lines)

        assert "styleguide:totally-distinct-name" in joined
        assert "Cause: missing_artifact" in joined
        assert "doctrine validate" in joined
        assert "project, org, and built-in" in joined

        miss = [
            w for w in captured if issubclass(w.category, CharterCatalogMissWarning)
        ]
        assert len(miss) == 1
        assert "missing_artifact" in str(miss[0].message)

    def test_schema_failure_case_surfaces_validate_hint(self) -> None:
        # Simulates the RISK-2 root cause: the loader silently dropped
        # the artifact because Pydantic ``extra='forbid'`` rejected it.
        # From the renderer's perspective, the catalog simply doesn't
        # carry the ID — but because no close match is available either,
        # the MISSING_ARTIFACT stanza's dual-hint (which includes the
        # `doctrine validate` advice) is exactly the surface we need.
        service = _StubService(styleguides=_StubRepo(items={}))
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            lines = _render_selected_styleguides(
                ["dropped-by-schema-validation"], service
            )
        joined = "\n".join(lines)

        assert "Cause: missing_artifact" in joined
        # The actionable hint pointing at the validate command must be
        # present so an operator hit by a schema-drop has a clear next
        # step (this is the RISK-3 contract).
        assert "spec-kitty doctrine validate" in joined

        miss = [
            w for w in captured if issubclass(w.category, CharterCatalogMissWarning)
        ]
        assert len(miss) == 1


# ---------------------------------------------------------------------------
# Profile-cited renderer integration
# ---------------------------------------------------------------------------


class TestProfileRendererIntegration:
    """Profile-cited directive misses route through the same surface."""

    def test_profile_cited_directive_miss_warns_with_profile_context(
        self,
    ) -> None:
        profile = AgentProfile.model_validate(
            {
                "profile-id": "ghost-cite",
                "name": "Ghost Cite",
                "roles": ["implementer"],
                "purpose": "test fixture",
                "specialization": {"primary-focus": "testing"},
                "directive-references": [
                    {
                        "code": "999",
                        "name": "Nonexistent",
                        "rationale": "force a miss",
                    }
                ],
            }
        )

        class _DirRepoEmpty:
            def get(self, _code: str) -> Any | None:
                return None

            def list_all(self) -> list[Any]:
                return []

        class _ServiceWithDirectives:
            directives = _DirRepoEmpty()

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            lines = _render_profile_directives(profile, _ServiceWithDirectives())
        joined = "\n".join(lines)

        # Structured stanza, not the legacy placeholder.
        assert "directive:DIRECTIVE_999" in joined
        assert "Cause: missing_artifact" in joined

        # Warning carries the profile context so log aggregators can
        # correlate the miss to the offending profile.
        miss = [
            w for w in captured if issubclass(w.category, CharterCatalogMissWarning)
        ]
        assert len(miss) == 1
        assert "profile:ghost-cite" in str(miss[0].message)
