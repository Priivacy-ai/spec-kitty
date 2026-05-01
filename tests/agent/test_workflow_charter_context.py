"""Regression tests for workflow.py and prompt_builder.py charter context integration.

T038: verify downstream consumers handle the updated context contract correctly:
- `text` field always populated in CharterContextResult
- bootstrap/compact mode handling
- graceful degradation when charter artifacts are missing or partial
- no dependency on removed library materialization
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.cli.commands.agent.workflow import _render_charter_context
from charter.context import build_charter_context
from specify_cli.next.prompt_builder import _governance_context
import contextlib

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _git_init_tmp_path(request: pytest.FixtureRequest) -> None:
    """WP03: chokepoint requires a git-tracked tmp_path fixture root."""
    if "tmp_path" in request.fixturenames:
        tmp_path: Path = request.getfixturevalue("tmp_path")
        if not (tmp_path / ".git").exists():
            with contextlib.suppress(FileNotFoundError, OSError):
                subprocess.run(
                    ["git", "init", "--quiet", str(tmp_path)],
                    check=False,
                    capture_output=True,
                )
    yield
    try:
        from charter.resolution import resolve_canonical_repo_root

        resolve_canonical_repo_root.cache_clear()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_charter_bundle(root: Path, *, include_governance: bool = True) -> Path:
    """Write a minimal charter bundle under root/.kittify/charter/."""
    charter_dir = root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(
        "# Project Charter\n\n## Policy Summary\n\n- Intent: stable delivery\n",
        encoding="utf-8",
    )
    (charter_dir / "references.yaml").write_text(
        'schema_version: "1.0.0"\nreferences: []\n',
        encoding="utf-8",
    )
    if include_governance:
        (charter_dir / "governance.yaml").write_text(
            "doctrine:\n  selected_paradigms: []\n  selected_directives: []\n  template_set: software-dev-default\n",
            encoding="utf-8",
        )
    return charter_dir


# ---------------------------------------------------------------------------
# CharterContextResult.text is always a non-empty string
# ---------------------------------------------------------------------------


class TestCharterContextResultTextField:
    """text field is always populated regardless of mode."""

    def test_text_populated_in_bootstrap_mode(self, tmp_path: Path) -> None:
        _make_charter_bundle(tmp_path)
        result = build_charter_context(tmp_path, action="specify", mark_loaded=False)
        assert isinstance(result.text, str)
        assert result.text.strip(), "text must be non-empty in bootstrap mode"

    def test_text_populated_in_compact_mode(self, tmp_path: Path) -> None:
        _make_charter_bundle(tmp_path)
        build_charter_context(tmp_path, action="specify", mark_loaded=True)
        result = build_charter_context(tmp_path, action="specify", mark_loaded=False)
        assert result.mode == "compact"
        assert isinstance(result.text, str)
        assert result.text.strip(), "text must be non-empty in compact mode"

    def test_text_populated_in_missing_mode(self, tmp_path: Path) -> None:
        # No charter file written → mode == "missing"
        (tmp_path / ".kittify" / "charter").mkdir(parents=True)
        result = build_charter_context(tmp_path, action="specify", mark_loaded=False)
        assert result.mode == "missing"
        assert isinstance(result.text, str)
        assert result.text.strip(), "text must be non-empty even in missing mode"

    def test_text_populated_for_non_bootstrap_action(self, tmp_path: Path) -> None:
        _make_charter_bundle(tmp_path)
        result = build_charter_context(tmp_path, action="tasks", mark_loaded=False)
        assert result.mode == "compact"
        assert isinstance(result.text, str)
        assert result.text.strip()


# ---------------------------------------------------------------------------
# workflow._render_charter_context
# ---------------------------------------------------------------------------


class TestWorkflowRenderCharterContext:
    """_render_charter_context handles all artifact states gracefully."""

    def test_returns_context_text_when_charter_present(self, tmp_path: Path) -> None:
        _make_charter_bundle(tmp_path)
        text = _render_charter_context(tmp_path, "implement")
        assert text.strip(), "Must return non-empty text when charter is present"

    def test_returns_text_even_when_charter_missing(self, tmp_path: Path) -> None:
        """Missing charter returns the 'missing' mode text rather than crashing."""
        (tmp_path / ".kittify" / "charter").mkdir(parents=True)
        text = _render_charter_context(tmp_path, "implement")
        assert isinstance(text, str)
        assert text.strip(), "Must return non-empty text even when charter is missing"

    def test_graceful_fallback_on_build_exception(self, tmp_path: Path) -> None:
        """An exception from build_charter_context produces a readable fallback."""
        with patch(
            "specify_cli.cli.commands.agent.workflow.build_charter_context",
            side_effect=RuntimeError("service unavailable"),
        ):
            text = _render_charter_context(tmp_path, "review")
        assert "unavailable" in text.lower() or "governance" in text.lower()

    def test_does_not_require_library_directory(self, tmp_path: Path) -> None:
        """No library/ directory needed — workflow context must not fail when absent."""
        _make_charter_bundle(tmp_path)
        # Explicitly confirm library/ does not exist
        assert not (tmp_path / ".kittify" / "charter" / "library").exists()
        # Should still return valid text
        text = _render_charter_context(tmp_path, "implement")
        assert text.strip()

    def test_partial_bundle_no_references_yaml(self, tmp_path: Path) -> None:
        """Missing references.yaml does not crash context rendering."""
        charter_dir = tmp_path / ".kittify" / "charter"
        charter_dir.mkdir(parents=True)
        (charter_dir / "charter.md").write_text(
            "# Project Charter\n\n## Policy Summary\n\n- Intent: stable\n",
            encoding="utf-8",
        )
        # No references.yaml — partial bundle
        text = _render_charter_context(tmp_path, "specify")
        assert text.strip()


# ---------------------------------------------------------------------------
# prompt_builder._governance_context
# ---------------------------------------------------------------------------


class TestPromptBuilderGovernanceContext:
    """_governance_context handles bootstrap, compact, and missing modes."""

    def test_bootstrap_mode_returns_charter_context_text(self, tmp_path: Path) -> None:
        _make_charter_bundle(tmp_path)
        text = _governance_context(tmp_path, action="specify")
        # Bootstrap mode injects charter context, not generic Governance: label
        assert text.strip()
        # After first load, state is persisted; text must be non-empty either way
        assert len(text) > 10

    def test_compact_mode_falls_back_to_governance_label(self, tmp_path: Path) -> None:
        _make_charter_bundle(tmp_path)
        # Prime first load so next call is compact
        _governance_context(tmp_path, action="specify")
        text = _governance_context(tmp_path, action="specify")
        assert "Governance:" in text

    def test_compact_mode_auto_syncs_missing_governance_bundle(self, tmp_path: Path) -> None:
        charter_dir = _make_charter_bundle(tmp_path, include_governance=False)

        _governance_context(tmp_path, action="specify")
        text = _governance_context(tmp_path, action="specify")

        assert "Governance:" in text
        assert (charter_dir / "governance.yaml").exists()
        assert (charter_dir / "directives.yaml").exists()
        assert (charter_dir / "metadata.yaml").exists()

    def test_missing_charter_falls_back_to_legacy_governance(self, tmp_path: Path) -> None:
        """Missing charter skips context injection and falls back gracefully."""
        (tmp_path / ".kittify" / "charter").mkdir(parents=True)
        text = _governance_context(tmp_path, action="specify")
        # _governance_context skips "missing" mode and delegates to _legacy_governance_context
        # which in turn calls resolve_governance (returns unresolved or full governance text)
        assert isinstance(text, str)
        assert text.strip()

    def test_exception_falls_back_to_legacy_governance(self, tmp_path: Path) -> None:
        with patch(
            "specify_cli.next.prompt_builder.build_charter_context",
            side_effect=RuntimeError("boom"),
        ):
            text = _governance_context(tmp_path, action="implement")
        # Fallback must always return something
        assert isinstance(text, str)
        assert text.strip()

    def test_no_action_uses_legacy_governance(self, tmp_path: Path) -> None:
        """Calling _governance_context without action uses legacy path directly."""
        _make_charter_bundle(tmp_path)
        text = _governance_context(tmp_path, action=None)
        assert "Governance:" in text
