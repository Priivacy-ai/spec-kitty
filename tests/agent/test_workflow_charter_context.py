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
from runtime.next.prompt_builder import _build_wp_prompt, _governance_context

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


@pytest.fixture(autouse=True)
def _git_init_tmp_path(request: pytest.FixtureRequest) -> None:
    """WP03: chokepoint requires a git-tracked tmp_path fixture root."""
    if "tmp_path" in request.fixturenames:
        tmp_path: Path = request.getfixturevalue("tmp_path")
        if not (tmp_path / ".git").exists():
            try:
                subprocess.run(
                    ["git", "init", "--quiet", str(tmp_path)],
                    check=False,
                    capture_output=True,
                )
            except (FileNotFoundError, OSError):
                pass
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
            "runtime.next.prompt_builder.build_charter_context",
            side_effect=RuntimeError("boom"),
        ):
            text = _governance_context(tmp_path, action="implement")
        # Fallback must always return something
        assert isinstance(text, str)
        assert text.strip()

    def test_scope_not_found_is_not_swallowed(self, tmp_path: Path) -> None:
        from charter.scope import CharterScopeNotFound

        with (
            patch(
                "runtime.next.prompt_builder.build_with_scope",
                side_effect=CharterScopeNotFound("outside configured scopes"),
            ),
            pytest.raises(CharterScopeNotFound, match="outside configured scopes"),
        ):
            _governance_context(
                tmp_path,
                action="implement",
                feature_dir=tmp_path / "outside" / "mission",
            )

    def test_no_action_uses_legacy_governance(self, tmp_path: Path) -> None:
        """Calling _governance_context without action uses legacy path directly."""
        _make_charter_bundle(tmp_path)
        text = _governance_context(tmp_path, action=None)
        assert "Governance:" in text

    def test_governance_context_forwards_profile_kwarg_to_charter_context(
        self, tmp_path: Path
    ) -> None:
        """WP06 (FR-004): ``_governance_context(..., profile=<id>)`` MUST
        forward the profile to ``build_charter_context``.
        """
        _make_charter_bundle(tmp_path)
        with patch(
            "runtime.next.prompt_builder.build_charter_context"
        ) as build:
            build.return_value.mode = "bootstrap"
            build.return_value.text = "stub"
            _governance_context(tmp_path, action="implement", profile="python-pedro")
        assert build.called, "build_charter_context must be invoked"
        call_kwargs = build.call_args.kwargs
        assert call_kwargs.get("profile") == "python-pedro", (
            "profile kwarg MUST be forwarded so the resolver renders profile-cited "
            "directives and tactics"
        )

    def test_governance_context_default_profile_is_none(self, tmp_path: Path) -> None:
        """Calling without profile preserves the prior NFR-005 byte-identical
        behaviour (profile=None -> resolver behaves as before WP03).
        """
        _make_charter_bundle(tmp_path)
        with patch(
            "runtime.next.prompt_builder.build_charter_context"
        ) as build:
            build.return_value.mode = "bootstrap"
            build.return_value.text = "stub"
            _governance_context(tmp_path, action="implement")
        assert build.call_args.kwargs.get("profile") is None


# ---------------------------------------------------------------------------
# WP06: _build_wp_prompt forwards WP frontmatter agent_profile to
# _governance_context.
# ---------------------------------------------------------------------------


_WP_WITH_PROFILE = """\
---
work_package_id: WP01
title: Test WP
dependencies: []
requirement_refs: [FR-001]
subtasks: [T001]
agent: claude
agent_profile: python-pedro
role: implementer
authoritative_surface: src/foo.py
owned_files: [src/foo.py]
execution_mode: code_change
history: []
---
# WP01 — Test
"""


_WP_WITHOUT_PROFILE = """\
---
work_package_id: WP01
title: Test WP
dependencies: []
requirement_refs: [FR-001]
subtasks: [T001]
agent: claude
role: implementer
authoritative_surface: src/foo.py
owned_files: [src/foo.py]
execution_mode: code_change
history: []
---
# WP01 — Test
"""


class TestBuildWpPromptForwardsAgentProfile:
    """WP06 (FR-004 wiring side): ``_build_wp_prompt`` MUST read the WP
    frontmatter ``agent_profile`` field and forward it to
    ``_governance_context(profile=<id>)``.
    """

    def _make_feature(self, tmp_path: Path, mission_slug: str, wp_body: str) -> Path:
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        (feature_dir / "tasks").mkdir(parents=True)
        (feature_dir / "tasks" / "WP01.md").write_text(wp_body, encoding="utf-8")
        from tests.lane_test_utils import write_single_lane_manifest

        write_single_lane_manifest(feature_dir, wp_ids=("WP01",))
        return feature_dir

    def test_implement_forwards_agent_profile_from_wp_frontmatter(
        self, tmp_path: Path
    ) -> None:
        mission_slug = "999-test"
        feature_dir = self._make_feature(tmp_path, mission_slug, _WP_WITH_PROFILE)
        _make_charter_bundle(tmp_path)
        with patch(
            "runtime.next.prompt_builder._governance_context"
        ) as gov:
            gov.return_value = "stub"
            _build_wp_prompt(
                action="implement",
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id="WP01",
                agent="claude",
                repo_root=tmp_path,
                mission_type="software-dev",
            )
        assert gov.called
        assert gov.call_args.kwargs.get("profile") == "python-pedro", (
            "_build_wp_prompt MUST extract the WP frontmatter ``agent_profile`` "
            "and forward it via profile= to _governance_context. Without this, "
            "the profile-cited directives the resolver renders never reach the "
            "agent's prompt."
        )

    def test_implement_passes_none_when_frontmatter_lacks_agent_profile(
        self, tmp_path: Path
    ) -> None:
        mission_slug = "999-noprofile"
        feature_dir = self._make_feature(tmp_path, mission_slug, _WP_WITHOUT_PROFILE)
        _make_charter_bundle(tmp_path)
        with patch(
            "runtime.next.prompt_builder._governance_context"
        ) as gov:
            gov.return_value = "stub"
            _build_wp_prompt(
                action="implement",
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id="WP01",
                agent="claude",
                repo_root=tmp_path,
                mission_type="software-dev",
            )
        assert gov.call_args.kwargs.get("profile") is None, (
            "When WP frontmatter has no agent_profile field, the profile kwarg "
            "MUST be None (NFR-005 byte-identical fallback)."
        )
