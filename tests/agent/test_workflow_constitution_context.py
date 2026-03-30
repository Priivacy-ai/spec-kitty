"""Regression tests for workflow.py and prompt_builder.py constitution context integration.

T038: verify downstream consumers handle the updated context contract correctly:
- `text` field always populated in ConstitutionContextResult
- bootstrap/compact mode handling
- graceful degradation when constitution artifacts are missing or partial
- no dependency on removed library materialization
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.cli.commands.agent.workflow import _render_constitution_context
from constitution.context import build_constitution_context
from specify_cli.next.prompt_builder import _governance_context

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_constitution_bundle(root: Path, *, include_governance: bool = True) -> Path:
    """Write a minimal constitution bundle under root/.kittify/constitution/."""
    constitution_dir = root / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True, exist_ok=True)
    (constitution_dir / "constitution.md").write_text(
        "# Project Constitution\n\n## Policy Summary\n\n- Intent: stable delivery\n",
        encoding="utf-8",
    )
    (constitution_dir / "references.yaml").write_text(
        'schema_version: "1.0.0"\nreferences: []\n',
        encoding="utf-8",
    )
    if include_governance:
        (constitution_dir / "governance.yaml").write_text(
            "doctrine:\n  selected_paradigms: []\n  selected_directives: []\n  template_set: software-dev-default\n",
            encoding="utf-8",
        )
    return constitution_dir


# ---------------------------------------------------------------------------
# ConstitutionContextResult.text is always a non-empty string
# ---------------------------------------------------------------------------


class TestConstitutionContextResultTextField:
    """text field is always populated regardless of mode."""

    def test_text_populated_in_bootstrap_mode(self, tmp_path: Path) -> None:
        _make_constitution_bundle(tmp_path)
        result = build_constitution_context(tmp_path, action="specify", mark_loaded=False)
        assert isinstance(result.text, str)
        assert result.text.strip(), "text must be non-empty in bootstrap mode"

    def test_text_populated_in_compact_mode(self, tmp_path: Path) -> None:
        _make_constitution_bundle(tmp_path)
        build_constitution_context(tmp_path, action="specify", mark_loaded=True)
        result = build_constitution_context(tmp_path, action="specify", mark_loaded=False)
        assert result.mode == "compact"
        assert isinstance(result.text, str)
        assert result.text.strip(), "text must be non-empty in compact mode"

    def test_text_populated_in_missing_mode(self, tmp_path: Path) -> None:
        # No constitution file written → mode == "missing"
        (tmp_path / ".kittify" / "constitution").mkdir(parents=True)
        result = build_constitution_context(tmp_path, action="specify", mark_loaded=False)
        assert result.mode == "missing"
        assert isinstance(result.text, str)
        assert result.text.strip(), "text must be non-empty even in missing mode"

    def test_text_populated_for_non_bootstrap_action(self, tmp_path: Path) -> None:
        _make_constitution_bundle(tmp_path)
        result = build_constitution_context(tmp_path, action="tasks", mark_loaded=False)
        assert result.mode == "compact"
        assert isinstance(result.text, str)
        assert result.text.strip()


# ---------------------------------------------------------------------------
# workflow._render_constitution_context
# ---------------------------------------------------------------------------


class TestWorkflowRenderConstitutionContext:
    """_render_constitution_context handles all artifact states gracefully."""

    def test_returns_context_text_when_constitution_present(self, tmp_path: Path) -> None:
        _make_constitution_bundle(tmp_path)
        text = _render_constitution_context(tmp_path, "implement")
        assert text.strip(), "Must return non-empty text when constitution is present"

    def test_returns_text_even_when_constitution_missing(self, tmp_path: Path) -> None:
        """Missing constitution returns the 'missing' mode text rather than crashing."""
        (tmp_path / ".kittify" / "constitution").mkdir(parents=True)
        text = _render_constitution_context(tmp_path, "implement")
        assert isinstance(text, str)
        assert text.strip(), "Must return non-empty text even when constitution is missing"

    def test_graceful_fallback_on_build_exception(self, tmp_path: Path) -> None:
        """An exception from build_constitution_context produces a readable fallback."""
        with patch(
            "specify_cli.cli.commands.agent.workflow.build_constitution_context",
            side_effect=RuntimeError("service unavailable"),
        ):
            text = _render_constitution_context(tmp_path, "review")
        assert "unavailable" in text.lower() or "governance" in text.lower()

    def test_does_not_require_library_directory(self, tmp_path: Path) -> None:
        """No library/ directory needed — workflow context must not fail when absent."""
        _make_constitution_bundle(tmp_path)
        # Explicitly confirm library/ does not exist
        assert not (tmp_path / ".kittify" / "constitution" / "library").exists()
        # Should still return valid text
        text = _render_constitution_context(tmp_path, "implement")
        assert text.strip()

    def test_partial_bundle_no_references_yaml(self, tmp_path: Path) -> None:
        """Missing references.yaml does not crash context rendering."""
        constitution_dir = tmp_path / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        (constitution_dir / "constitution.md").write_text(
            "# Project Constitution\n\n## Policy Summary\n\n- Intent: stable\n",
            encoding="utf-8",
        )
        # No references.yaml — partial bundle
        text = _render_constitution_context(tmp_path, "specify")
        assert text.strip()


# ---------------------------------------------------------------------------
# prompt_builder._governance_context
# ---------------------------------------------------------------------------


class TestPromptBuilderGovernanceContext:
    """_governance_context handles bootstrap, compact, and missing modes."""

    def test_bootstrap_mode_returns_constitution_context_text(self, tmp_path: Path) -> None:
        _make_constitution_bundle(tmp_path)
        text = _governance_context(tmp_path, action="specify")
        # Bootstrap mode injects constitution context, not generic Governance: label
        assert text.strip()
        # After first load, state is persisted; text must be non-empty either way
        assert len(text) > 10

    def test_compact_mode_falls_back_to_governance_label(self, tmp_path: Path) -> None:
        _make_constitution_bundle(tmp_path)
        # Prime first load so next call is compact
        _governance_context(tmp_path, action="specify")
        text = _governance_context(tmp_path, action="specify")
        assert "Governance:" in text

    def test_missing_constitution_falls_back_to_legacy_governance(self, tmp_path: Path) -> None:
        """Missing constitution skips context injection and falls back gracefully."""
        (tmp_path / ".kittify" / "constitution").mkdir(parents=True)
        text = _governance_context(tmp_path, action="specify")
        # _governance_context skips "missing" mode and delegates to _legacy_governance_context
        # which in turn calls resolve_governance (returns unresolved or full governance text)
        assert isinstance(text, str)
        assert text.strip()

    def test_exception_falls_back_to_legacy_governance(self, tmp_path: Path) -> None:
        with patch(
            "specify_cli.next.prompt_builder.build_constitution_context",
            side_effect=RuntimeError("boom"),
        ):
            text = _governance_context(tmp_path, action="implement")
        # Fallback must always return something
        assert isinstance(text, str)
        assert text.strip()

    def test_no_action_uses_legacy_governance(self, tmp_path: Path) -> None:
        """Calling _governance_context without action uses legacy path directly."""
        _make_constitution_bundle(tmp_path)
        text = _governance_context(tmp_path, action=None)
        assert "Governance:" in text
