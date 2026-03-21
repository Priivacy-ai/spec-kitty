"""Tests for central command templates used by spec-kitty init."""

from __future__ import annotations

import pytest
from pathlib import Path

pytestmark = pytest.mark.fast

TEMPLATE_DIR = Path("src/specify_cli/templates/command-templates")
EXPECTED_TEMPLATES = {
    "accept.md",
    "analyze.md",
    "checklist.md",
    "constitution.md",
    "dashboard.md",
    "implement.md",
    "merge.md",
    "plan.md",
    "research.md",
    "review.md",
    "specify.md",
    "tasks.md",
}


def test_central_template_directory_exists() -> None:
    """Verify central template directory exists."""
    assert TEMPLATE_DIR.exists(), f"Template directory not found: {TEMPLATE_DIR}"
    assert TEMPLATE_DIR.is_dir(), "Template path is not a directory"


def test_central_template_set_complete() -> None:
    """Verify central template set is complete for init."""
    templates = {path.name for path in TEMPLATE_DIR.glob("*.md")}
    missing = EXPECTED_TEMPLATES - templates
    assert not missing, f"Missing central templates: {sorted(missing)}"


def test_central_specify_template_workspace_per_wp() -> None:
    """Verify specify.md reflects main-repo planning workflow."""
    content = (TEMPLATE_DIR / "specify.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "main" in content_lower, "specify.md should mention main repository workflow"
    assert "commit" in content_lower, "specify.md should mention committing artifacts"
    assert "branch strategy confirmation" in content_lower, (
        "specify.md should require explicit branch strategy confirmation"
    )
    assert "branch-context --json" in content, (
        "specify.md should resolve branch strategy from the Python helper"
    )
    assert "git branch --show-current" not in content, (
        "specify.md should not ask the LLM to rediscover branch state via git"
    )
    assert "merge_target_branch" in content, (
        "specify.md should mention the explicit merge target alias from helper JSON"
    )


def test_central_plan_template_workspace_per_wp() -> None:
    """Verify plan.md reflects main-repo planning workflow."""
    content = (TEMPLATE_DIR / "plan.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "main" in content_lower, "plan.md should mention main repository workflow"
    assert "worktree" in content_lower, "plan.md should mention worktree context (as negative or deferred)"
    assert "branch strategy confirmation" in content_lower, (
        "plan.md should require explicit branch strategy confirmation"
    )
    assert "git branch --show-current" not in content, (
        "plan.md should use deterministic JSON instead of probing git branch state"
    )
    assert "git rev-parse --abbrev-ref HEAD" not in content, (
        "plan.md should not ask the LLM to derive branch context from git directly"
    )
    assert "merge_target_branch" in content, (
        "plan.md should mention the final merge target explicitly"
    )


def test_central_tasks_template_dependency_workflow() -> None:
    """Verify tasks.md includes dependency handling and implement commands."""
    content = (TEMPLATE_DIR / "tasks.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "dependencies" in content_lower, "tasks.md should mention dependencies field"
    assert "--base" in content, "tasks.md should document --base flag for dependencies"
    assert "implement" in content_lower, "tasks.md should mention implement command"
    assert "planning_base_branch" in content, (
        "tasks.md should require persisting the planning branch into each WP prompt"
    )
    assert "merge_target_branch" in content, (
        "tasks.md should require persisting the merge target into each WP prompt"
    )
    assert "git branch --show-current" not in content, (
        "tasks.md should rely on helper JSON for branch context"
    )


def test_central_task_prompt_template_carries_branch_metadata() -> None:
    """WP prompt template should make branch intent explicit in frontmatter and body."""
    content = (Path("src/specify_cli/templates/task-prompt-template.md")).read_text(
        encoding="utf-8"
    )
    assert "planning_base_branch" in content
    assert "merge_target_branch" in content
    assert "branch_strategy" in content
    assert "## Branch Strategy" in content


def test_central_implement_template_workspace_creation() -> None:
    """Verify implement.md documents workspace creation and base flag."""
    content = (TEMPLATE_DIR / "implement.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "spec-kitty implement" in content, "implement.md should mention spec-kitty implement"
    assert "--base" in content, "implement.md should mention --base"
    assert "worktree" in content_lower or "workspace" in content_lower, (
        "implement.md should mention worktree/workspace creation"
    )


def test_central_review_template_dependency_checks() -> None:
    """Verify review.md mentions dependency checks for workspace-per-WP."""
    content = (TEMPLATE_DIR / "review.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "dependencies" in content_lower, "review.md should mention dependencies"
    assert "rebase" in content_lower, "review.md should mention rebase warnings"
