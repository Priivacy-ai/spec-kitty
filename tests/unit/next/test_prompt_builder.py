"""Unit tests for the prompt builder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.next.prompt_builder import (
    _feature_context_header,
    _governance_context,
    _read_wp_content,
    _write_to_temp,
    build_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    fd = tmp_path / "kitty-specs" / "042-test-feature"
    fd.mkdir(parents=True)
    return fd


@pytest.fixture
def feature_with_wp(feature_dir: Path) -> Path:
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\nlane: planned\n---\n# WP01 Content\nDo stuff.\n",
        encoding="utf-8",
    )
    return feature_dir


# ---------------------------------------------------------------------------
# _feature_context_header
# ---------------------------------------------------------------------------


class TestFeatureContextHeader:
    def test_contains_slug(self, feature_dir: Path) -> None:
        header = _feature_context_header("042-test-feature", feature_dir, "claude")
        assert "042-test-feature" in header

    def test_contains_agent(self, feature_dir: Path) -> None:
        header = _feature_context_header("042-test-feature", feature_dir, "claude")
        assert "claude" in header

    def test_contains_directory(self, feature_dir: Path) -> None:
        header = _feature_context_header("042-test-feature", feature_dir, "claude")
        assert str(feature_dir) in header


# ---------------------------------------------------------------------------
# _read_wp_content
# ---------------------------------------------------------------------------


class TestReadWPContent:
    def test_reads_existing_wp(self, feature_with_wp: Path) -> None:
        content = _read_wp_content(feature_with_wp, "WP01")
        assert "WP01 Content" in content

    def test_missing_wp(self, feature_dir: Path) -> None:
        (feature_dir / "tasks").mkdir()
        content = _read_wp_content(feature_dir, "WP99")
        assert "not found" in content.lower()

    def test_missing_tasks_dir(self, feature_dir: Path) -> None:
        content = _read_wp_content(feature_dir, "WP01")
        assert "missing" in content.lower()


# ---------------------------------------------------------------------------
# _write_to_temp
# ---------------------------------------------------------------------------


class TestWriteToTemp:
    def test_creates_file(self) -> None:
        path = _write_to_temp("implement", "WP01", "test content", agent="claude", feature_slug="042-feat")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "test content"
        path.unlink()  # cleanup

    def test_filename_includes_action_and_wp(self) -> None:
        path = _write_to_temp("review", "WP02", "content", agent="codex", feature_slug="042-feat")
        assert "review" in path.name
        assert "WP02" in path.name
        path.unlink()

    def test_filename_without_wp(self) -> None:
        path = _write_to_temp("specify", None, "content", agent="claude", feature_slug="042-feat")
        assert "specify" in path.name
        assert "WP" not in path.name
        path.unlink()

    def test_filename_includes_agent_and_feature(self) -> None:
        """Different agents/features produce different filenames (no collisions)."""
        p1 = _write_to_temp("implement", "WP01", "a", agent="claude", feature_slug="042-feat")
        p2 = _write_to_temp("implement", "WP01", "b", agent="codex", feature_slug="042-feat")
        p3 = _write_to_temp("implement", "WP01", "c", agent="claude", feature_slug="043-other")
        assert p1 != p2
        assert p1 != p3
        assert p2 != p3
        assert "claude" in p1.name
        assert "codex" in p2.name
        assert "043-other" in p3.name
        p1.unlink()
        p2.unlink()
        p3.unlink()


# ---------------------------------------------------------------------------
# build_prompt (implement/review actions)
# ---------------------------------------------------------------------------


class TestBuildPromptWP:
    def test_implement_prompt_structure(self, feature_with_wp: Path) -> None:
        repo_root = feature_with_wp.parent.parent
        text, path = build_prompt(
            action="implement",
            feature_dir=feature_with_wp,
            feature_slug="042-test-feature",
            wp_id="WP01",
            agent="claude",
            repo_root=repo_root,
            mission_key="software-dev",
        )
        assert "IMPLEMENT" in text
        assert "WP01" in text
        assert "ISOLATION RULES" in text
        assert "WORK PACKAGE PROMPT BEGINS" in text
        assert "WORK PACKAGE PROMPT ENDS" in text
        assert "WP01 Content" in text
        assert "for_review" in text  # completion instruction
        assert path.exists()
        path.unlink()

    def test_review_prompt_structure(self, feature_with_wp: Path) -> None:
        repo_root = feature_with_wp.parent.parent
        text, path = build_prompt(
            action="review",
            feature_dir=feature_with_wp,
            feature_slug="042-test-feature",
            wp_id="WP01",
            agent="codex",
            repo_root=repo_root,
            mission_key="software-dev",
        )
        assert "REVIEW" in text
        assert "WP01" in text
        assert "REVIEWING" in text
        assert "APPROVE" in text
        assert "REJECT" in text
        assert path.exists()
        path.unlink()


# ---------------------------------------------------------------------------
# build_prompt (template actions)
# ---------------------------------------------------------------------------


class TestBuildPromptTemplate:
    @patch("specify_cli.next.prompt_builder.resolve_command")
    @patch("specify_cli.next.prompt_builder.resolve_governance")
    def test_template_prompt_has_header(self, mock_governance, mock_resolve, feature_with_wp: Path) -> None:
        # Mock the resolver to return a fake template
        mock_path = feature_with_wp / "fake-template.md"
        mock_path.write_text("# Specify Template\nCreate spec.md.\n", encoding="utf-8")
        mock_result = MagicMock()
        mock_result.path = mock_path
        mock_resolve.return_value = mock_result
        mock_governance.return_value = MagicMock(
            template_set="software-dev-default",
            paradigms=["test-first"],
            directives=["TEST_FIRST"],
            tools=["git", "pytest"],
            diagnostics=[],
        )

        repo_root = feature_with_wp.parent.parent
        text, path = build_prompt(
            action="specify",
            feature_dir=feature_with_wp,
            feature_slug="042-test-feature",
            wp_id=None,
            agent="claude",
            repo_root=repo_root,
            mission_key="software-dev",
        )
        assert "042-test-feature" in text
        assert "claude" in text
        assert "Specify Template" in text
        assert "Governance:" in text
        assert "Template set: software-dev-default" in text
        assert path.exists()
        path.unlink()

    @patch("specify_cli.next.prompt_builder.resolve_command")
    def test_template_prompt_bootstrap_context_first_load(self, mock_resolve, feature_with_wp: Path) -> None:
        mock_path = feature_with_wp / "fake-template.md"
        mock_path.write_text("# Specify Template\nCreate spec.md.\n", encoding="utf-8")
        mock_result = MagicMock()
        mock_result.path = mock_path
        mock_resolve.return_value = mock_result

        repo_root = feature_with_wp.parent.parent
        constitution_dir = repo_root / ".kittify" / "constitution"
        constitution_dir.mkdir(parents=True)
        (constitution_dir / "constitution.md").write_text(
            """# Project Constitution

## Policy Summary

- Intent: deterministic change management
- Testing: pytest + coverage

## Governance Activation

```yaml
mission: software-dev
selected_paradigms: [test-first]
selected_directives: [TEST_FIRST]
available_tools: [git]
template_set: software-dev-default
```
""",
            encoding="utf-8",
        )
        (constitution_dir / "references.yaml").write_text(
            """schema_version: "1.0.0"
references:
  - id: USER:PROJECT_PROFILE
    kind: user_profile
    title: User Profile
    local_path: library/user-project-profile.md
""",
            encoding="utf-8",
        )
        (constitution_dir / "governance.yaml").write_text(
            """doctrine:
  selected_paradigms: [test-first]
  selected_directives: [TEST_FIRST]
  available_tools: [git]
  template_set: software-dev-default
""",
            encoding="utf-8",
        )
        (constitution_dir / "directives.yaml").write_text(
            """directives:
  - id: TEST_FIRST
    title: Keep tests strict
""",
            encoding="utf-8",
        )

        first_text, first_path = build_prompt(
            action="specify",
            feature_dir=feature_with_wp,
            feature_slug="042-test-feature",
            wp_id=None,
            agent="claude",
            repo_root=repo_root,
            mission_key="software-dev",
        )
        assert "Constitution Context (Bootstrap):" in first_text
        first_path.unlink()

        second_text, second_path = build_prompt(
            action="specify",
            feature_dir=feature_with_wp,
            feature_slug="042-test-feature",
            wp_id=None,
            agent="claude",
            repo_root=repo_root,
            mission_key="software-dev",
        )
        assert "Governance:" in second_text
        second_path.unlink()


class TestGovernanceContext:
    @patch("specify_cli.next.prompt_builder.resolve_governance")
    def test_governance_context_renders_resolution(self, mock_resolve, feature_dir: Path) -> None:
        mock_resolve.return_value = MagicMock(
            template_set="software-dev-default",
            paradigms=["test-first"],
            directives=["TEST_FIRST"],
            tools=["git", "pytest"],
            diagnostics=["Template set from constitution."],
        )
        text = _governance_context(feature_dir.parent.parent)
        assert "Governance:" in text
        assert "Template set: software-dev-default" in text
        assert "Paradigms: test-first" in text
        assert "Directives: TEST_FIRST" in text

    @patch("specify_cli.next.prompt_builder.resolve_governance")
    def test_governance_context_handles_failures(self, mock_resolve, feature_dir: Path) -> None:
        mock_resolve.side_effect = RuntimeError("boom")
        text = _governance_context(feature_dir.parent.parent)
        assert "Governance: unavailable" in text
