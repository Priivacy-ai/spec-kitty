"""Tests for central command templates shipped in the doctrine package.

These tests validate content contracts on the base command templates that
``spec-kitty init`` merges with mission-specific overrides.  Templates are
resolved via ``CentralTemplateRepository`` -- the same API that doctrine
exposes for locating these assets.
"""

from __future__ import annotations

import importlib.resources
import pytest
from pathlib import Path

from doctrine.templates.repository import CentralTemplateRepository

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Fixture -- single repository instance shared across all tests
# ---------------------------------------------------------------------------

_repo = CentralTemplateRepository.default()

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
    root = _repo.root()
    assert root.exists(), f"Template directory not found: {root}"
    assert root.is_dir(), "Template path is not a directory"


def test_central_template_set_complete() -> None:
    """Verify central template set is complete for init."""
    available = set(_repo.list_templates())
    missing = EXPECTED_TEMPLATES - available
    assert not missing, f"Missing central templates: {sorted(missing)}"


def test_central_specify_template_workspace_per_wp() -> None:
    """Verify specify.md reflects main-repo planning workflow."""
    path = _repo.get("specify.md")
    assert path is not None, "specify.md not found via CentralTemplateRepository"
    content = path.read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "planning repository" in content_lower, "specify.md should mention planning repository"
    assert "commit" in content_lower, "specify.md should mention committing artifacts"
    assert "target branch" in content_lower, (
        "specify.md should reference the target branch"
    )
    assert "git branch --show-current" not in content, (
        "specify.md should not ask the LLM to rediscover branch state via git"
    )


def test_central_plan_template_workspace_per_wp() -> None:
    """Verify plan.md reflects main-repo planning workflow."""
    path = _repo.get("plan.md")
    assert path is not None, "plan.md not found via CentralTemplateRepository"
    content = path.read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "planning repository" in content_lower, "plan.md should mention planning repository"
    assert "worktree" in content_lower, "plan.md should mention worktree context (as negative or deferred)"
    assert "target branch" in content_lower, (
        "plan.md should reference the target branch"
    )
    # NOTE: plan.md legitimately uses `git rev-parse --abbrev-ref HEAD` as a
    # mission-detection heuristic when setup-plan JSON isn't available yet.
    # The earlier assertion banning this was from a prior design iteration.


def test_central_tasks_template_dependency_workflow() -> None:
    """Verify tasks.md includes dependency handling and implement commands."""
    path = _repo.get("tasks.md")
    assert path is not None, "tasks.md not found via CentralTemplateRepository"
    content = path.read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "dependencies" in content_lower, "tasks.md should mention dependencies field"
    assert "implement" in content_lower, "tasks.md should mention implement command"
    assert "target branch" in content_lower, (
        "tasks.md should reference the target branch"
    )
    # NOTE: tasks.md legitimately uses `git branch --show-current` as a
    # location-check heuristic.  The earlier ban was from a prior design iteration.


def test_central_task_prompt_template_carries_wp_metadata() -> None:
    """WP prompt template should carry core work-package metadata and guidance."""
    tpl = importlib.resources.files("doctrine").joinpath("templates", "task-prompt-template.md")
    content = Path(str(tpl)).read_text(encoding="utf-8")
    assert "work_package_id" in content, "template should declare work_package_id placeholder"
    assert "lane" in content, "template should declare lane frontmatter"
    assert "## Review Feedback" in content, "template should have Review Feedback section"
    assert "## Activity Log" in content, "template should have Activity Log section"
    assert "Dependency" in content, "template should address dependency handling"


def test_central_implement_template_workspace_creation() -> None:
    """Verify implement.md documents workspace creation and base flag."""
    path = _repo.get("implement.md")
    assert path is not None, "implement.md not found via CentralTemplateRepository"
    content = path.read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "spec-kitty implement" in content, "implement.md should mention spec-kitty implement"
    assert "--base" in content, "implement.md should mention --base"
    assert "worktree" in content_lower or "workspace" in content_lower, (
        "implement.md should mention worktree/workspace creation"
    )


def test_central_review_template_dependency_checks() -> None:
    """Verify review.md mentions dependency checks for workspace-per-WP."""
    path = _repo.get("review.md")
    assert path is not None, "review.md not found via CentralTemplateRepository"
    content = path.read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "dependencies" in content_lower, "review.md should mention dependencies"
    assert "rebase" in content_lower, "review.md should mention rebase warnings"
