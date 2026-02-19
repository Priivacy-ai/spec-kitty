"""Tests for central command templates used by spec-kitty init."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "src" / "doctrine" / "templates" / "command-templates"
EXPECTED_TEMPLATES = {
    "accept.md",
    "analyze.md",
    "checklist.md",
    "clarify.md",
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


def test_central_plan_template_workspace_per_wp() -> None:
    """Verify plan.md reflects main-repo planning workflow."""
    content = (TEMPLATE_DIR / "plan.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "main" in content_lower, "plan.md should mention main repository workflow"
    assert "worktree" in content_lower, "plan.md should mention worktree context (as negative or deferred)"


def test_central_tasks_template_dependency_workflow() -> None:
    """Verify tasks.md includes dependency handling and implement commands."""
    content = (TEMPLATE_DIR / "tasks.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "dependencies" in content_lower, "tasks.md should mention dependencies field"
    assert "--base" in content, "tasks.md should document --base flag for dependencies"
    assert "implement" in content_lower, "tasks.md should mention implement command"


def test_central_implement_template_workspace_creation() -> None:
    """Verify implement.md documents workspace creation and base flag."""
    content = (TEMPLATE_DIR / "implement.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "spec-kitty implement" in content, "implement.md should mention spec-kitty implement"
    assert "--base" in content, "implement.md should mention --base"
    assert "worktree" in content_lower or "workspace" in content_lower, \
        "implement.md should mention worktree/workspace creation"


def test_central_review_template_dependency_checks() -> None:
    """Verify review.md mentions dependency checks for workspace-per-WP."""
    content = (TEMPLATE_DIR / "review.md").read_text(encoding="utf-8")
    content_lower = content.lower()
    assert "dependencies" in content_lower, "review.md should mention dependencies"
    assert "rebase" in content_lower, "review.md should mention rebase warnings"
