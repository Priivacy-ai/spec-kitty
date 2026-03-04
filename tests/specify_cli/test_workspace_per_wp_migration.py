"""Migration tests for workspace-per-WP feature (0.11.0) - CORRECTED.

Tests validate that template SOURCE files in src/specify_cli/missions/software-dev/command-templates/
are updated correctly for the workspace-per-WP workflow.

Agent directories (.claude/, .gemini/, etc.) are GITIGNORED and generated at runtime
from these template sources, so we test the sources, not the generated files.

Architecture:
  Template Sources (committed) → generate_agent_assets() → Agent Directories (gitignored)

This test suite validates the 4 template source files that are the single source of truth.
"""

from __future__ import annotations

from pathlib import Path


# Template source directory (committed to repo)
REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "src" / "specify_cli" / "missions" / "software-dev" / "command-templates"


# T009: Test template directory exists
def test_template_directory_exists():
    """Verify template source directory exists."""
    assert TEMPLATE_DIR.exists(), f"Template directory not found: {TEMPLATE_DIR}"
    assert TEMPLATE_DIR.is_dir(), "Template path is not a directory"


# T010: Test specify.md template updates
def test_specify_template_updated():
    """Verify specify.md template updated for workspace-per-WP."""
    specify_template = TEMPLATE_DIR / "specify.md"
    assert specify_template.exists(), "specify.md template not found"

    content = specify_template.read_text()

    # Should NOT contain instructions to create worktrees during specify
    # Check ANY mention of .worktrees (case-insensitive, no gating on "feature" word)
    content_lower = content.lower()

    if ".worktrees" in content_lower:
        # If .worktrees mentioned, must be in negative or deferred context
        lines_with_worktrees = [line for line in content.split("\n") if ".worktrees" in line.lower()]
        for line in lines_with_worktrees:
            line_lower = line.lower()
            # Allow only if explicitly negated or deferred to implement phase
            is_negated = any(
                neg in line_lower for neg in ["no worktree", "not create", "don't create", "does not create"]
            )
            is_deferred = "implement" in line_lower and ("later" in line_lower or "during" in line_lower)

            assert is_negated or is_deferred, (
                f"specify.md mentions .worktrees without proper negation or deferral: '{line.strip()}'"
            )

    # SHOULD contain main repo workflow
    assert "main" in content.lower(), "specify.md doesn't mention main repository/branch"

    # Should mention commit workflow
    assert "commit" in content.lower(), "specify.md doesn't mention committing artifacts"


# T011: Test plan.md template updates
def test_plan_template_updated():
    """Verify plan.md template updated for main repo workflow."""
    plan_template = TEMPLATE_DIR / "plan.md"
    assert plan_template.exists(), "plan.md template not found"

    content = plan_template.read_text()
    content_lower = content.lower()

    # Should NOT reference worktree navigation (old workflow)
    # Strengthen check: ANY mention of "worktree" should be in negative/clarifying context
    if "worktree" in content_lower:
        # If "worktree" mentioned, must be explicitly negated or clarifying it's not used
        lines_with_worktree = [line for line in content.split("\n") if "worktree" in line.lower()]
        for line in lines_with_worktree:
            line_lower = line.lower()
            # Allow only if negated ("not in worktree", "no worktree", etc.)
            # OR if explaining the old model vs new ("previously used worktrees, now uses main")
            is_negated = any(
                neg in line_lower
                for neg in [
                    "not in",
                    "not a",
                    "no worktree",
                    "not from",
                    "instead of",
                    "not use",
                    "don't use",
                    "does not",
                    "without worktree",
                ]
            )
            is_explaining_change = any(word in line_lower for word in ["old", "previously", "legacy", "0.10"])

            assert is_negated or is_explaining_change, (
                f"plan.md references worktrees without negation or version context: '{line.strip()}'. "
                f"Planning now happens in main repo, not worktrees."
            )

    # SHOULD mention working in main repository or kitty-specs
    main_repo_indicators = ["main repo", "kitty-specs", "main branch"]
    found_indicators = [ind for ind in main_repo_indicators if ind.lower() in content.lower()]

    assert found_indicators, (
        f"plan.md doesn't mention working in main repository. Expected one of: {', '.join(main_repo_indicators)}"
    )


# T012: Test tasks.md template updates
def test_tasks_template_updated():
    """Verify tasks.md template includes dependency generation."""
    tasks_template = TEMPLATE_DIR / "tasks.md"
    assert tasks_template.exists(), "tasks.md template not found"

    content = tasks_template.read_text()
    content_lower = content.lower()

    # SHOULD mention dependencies field
    assert "dependencies" in content_lower, "tasks.md doesn't mention dependencies field"

    # SHOULD mention parsing or detecting dependencies
    parsing_keywords = ["parse", "detect", "extract", "identify"]
    found_keywords = [kw for kw in parsing_keywords if kw in content_lower]

    assert found_keywords, (
        f"tasks.md doesn't mention dependency detection. Expected one of: {', '.join(parsing_keywords)}"
    )

    # SHOULD mention frontmatter
    assert "frontmatter" in content_lower, "tasks.md doesn't mention frontmatter generation"

    # SHOULD mention implement command (new in 0.11.0)
    assert "implement" in content_lower, "tasks.md doesn't mention implement command"

    # SHOULD mention --base flag for dependencies
    assert "--base" in tasks_template.read_text(), "tasks.md doesn't document --base flag for dependent WPs"


# T013: Test implement.md template exists (NEW)
def test_implement_template_exists():
    """Verify implement.md template exists (new in 0.11.0)."""
    implement_template = TEMPLATE_DIR / "implement.md"
    assert implement_template.exists(), "implement.md template not found (should be NEW file in 0.11.0)"

    content = implement_template.read_text()
    content_lower = content.lower()

    # SHOULD document spec-kitty implement/workflow implement command
    assert (
        "spec-kitty implement" in content
        or "spec-kitty agent workflow implement" in content
        or "implement wp" in content_lower
    ), "implement.md doesn't document implement command"

    # --base flag is on spec-kitty implement (not workflow implement used in slash command)
    # The slash command uses $ARGUMENTS which includes the WP ID
    assert "$ARGUMENTS" in content or "--agent" in content, "implement.md should document command arguments"

    # SHOULD include WP placeholder or examples showing usage
    has_wp_ref = "wp##" in content_lower or "wp01" in content_lower or "example" in content_lower
    assert has_wp_ref, "implement.md doesn't reference WP IDs or include examples"

    # SHOULD mention workspace/worktree creation or be a slash command template
    # Slash command templates may be minimal (just command invocation)
    has_workspace_ref = "workspace" in content_lower or "worktree" in content_lower
    has_command_ref = "spec-kitty" in content
    assert has_workspace_ref or has_command_ref, "implement.md doesn't explain workspace creation or provide command"


# T015 is implicit - running pytest validates tests FAIL initially
