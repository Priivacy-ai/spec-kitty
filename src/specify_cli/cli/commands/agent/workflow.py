"""Workflow commands for AI agents - display prompts and instructions."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from specify_cli.cli.commands.implement import implement as top_level_implement
from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
from specify_cli.core.implement_validation import (
    validate_and_resolve_base,
    validate_base_workspace_exists,
)
from specify_cli.core.paths import locate_project_root
from specify_cli.core.feature_detection import (
    detect_feature_slug,
    FeatureDetectionError,
)
from specify_cli.mission import get_deliverables_path, get_feature_mission_key
from specify_cli.tasks_support import (
    append_activity_log,
    build_document,
    extract_scalar,
    find_repo_root,
    locate_work_package,
    set_scalar,
    split_frontmatter,
)


def _write_prompt_to_file(
    command_type: str,
    wp_id: str,
    content: str,
) -> Path:
    """Write full prompt content to a temp file for agents with output limits.

    Args:
        command_type: "implement" or "review"
        wp_id: Work package ID (e.g., "WP01")
        content: Full prompt content to write

    Returns:
        Path to the written file
    """
    # Use system temp directory (gets cleaned up automatically)
    prompt_file = Path(tempfile.gettempdir()) / f"spec-kitty-{command_type}-{wp_id}.md"
    prompt_file.write_text(content, encoding="utf-8")
    return prompt_file

app = typer.Typer(
    name="workflow",
    help="Workflow commands that display prompts and instructions for agents",
    no_args_is_help=True
)


def _find_feature_slug(explicit_feature: str | None = None) -> str:
    """Find the current feature slug using centralized detection.

    Args:
        explicit_feature: Optional explicit feature slug from --feature flag

    Returns:
        Feature slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If feature slug cannot be determined
    """
    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)

    if repo_root is None:
        print("Error: Not in a spec-kitty project.")
        raise typer.Exit(1)

    try:
        return detect_feature_slug(
            repo_root,
            explicit_feature=explicit_feature,
            cwd=cwd,
            mode="strict"
        )
    except FeatureDetectionError as e:
        print(f"Error: {e}")
        raise typer.Exit(1)


def _normalize_wp_id(wp_arg: str) -> str:
    """Normalize WP ID from various formats to standard WPxx format.

    Args:
        wp_arg: User input (e.g., "wp01", "WP01", "WP01-foo-bar")

    Returns:
        Normalized WP ID (e.g., "WP01")
    """
    # Handle formats: wp01 → WP01, WP01 → WP01, WP01-foo-bar → WP01
    wp_upper = wp_arg.upper()

    # Extract just the WPxx part
    if wp_upper.startswith("WP"):
        # Split on hyphen and take first part
        return wp_upper.split("-")[0]
    else:
        # Assume it's like "01" or "1", prefix with WP
        return f"WP{wp_upper.lstrip('WP')}"


def _ensure_sparse_checkout(worktree_path: Path) -> bool:
    """Ensure worktree has sparse-checkout configured to exclude kitty-specs/.

    This function runs on EVERY implement/review command, not just when creating
    new worktrees. This fixes legacy worktrees that were created without
    sparse-checkout or where the setup failed silently.

    Args:
        worktree_path: Path to the worktree directory

    Returns:
        True if sparse-checkout is configured correctly, False if not a worktree
    """
    # For worktrees, .git is a file pointing to the real git dir
    git_path = worktree_path / ".git"
    if not git_path.is_file():
        return False  # Not a worktree (or doesn't exist yet)

    # Get actual git dir path from the .git file
    try:
        git_content = git_path.read_text().strip()
    except OSError:
        return False

    if not git_content.startswith("gitdir:"):
        return False

    git_dir = Path(git_content.split(":", 1)[1].strip())
    if not git_dir.exists():
        return False

    sparse_checkout_file = git_dir / "info" / "sparse-checkout"
    expected_content = "/*\n!/kitty-specs/\n!/kitty-specs/**\n"

    # Check if sparse-checkout needs to be set up or fixed
    needs_setup = False
    if not sparse_checkout_file.exists():
        needs_setup = True
    else:
        try:
            current_content = sparse_checkout_file.read_text()
            if current_content != expected_content:
                needs_setup = True
        except OSError:
            needs_setup = True

    if needs_setup:
        # Configure sparse-checkout
        subprocess.run(
            ["git", "config", "core.sparseCheckout", "true"],
            cwd=worktree_path, capture_output=True, check=False
        )
        subprocess.run(
            ["git", "config", "core.sparseCheckoutCone", "false"],
            cwd=worktree_path, capture_output=True, check=False
        )
        sparse_checkout_file.parent.mkdir(parents=True, exist_ok=True)
        sparse_checkout_file.write_text(expected_content, encoding="utf-8")
        subprocess.run(
            ["git", "read-tree", "-mu", "HEAD"],
            cwd=worktree_path, capture_output=True, check=False
        )

        # Remove orphaned kitty-specs if present (from before sparse-checkout was configured)
        orphan_kitty = worktree_path / "kitty-specs"
        if orphan_kitty.exists():
            shutil.rmtree(orphan_kitty)
            print(f"✓ Removed orphaned kitty-specs/ from worktree (now uses main repo)")

    return True


def _find_first_planned_wp(repo_root: Path, feature_slug: str) -> Optional[str]:
    """Find the first WP file with lane: "planned".

    Args:
        repo_root: Repository root path
        feature_slug: Feature slug

    Returns:
        WP ID of first planned task, or None if not found
    """
    from specify_cli.core.paths import is_worktree_context

    cwd = Path.cwd().resolve()

    # Check if we're in a worktree - if so, use worktree's kitty-specs
    if is_worktree_context(cwd):
        # We're in a worktree, look for kitty-specs relative to cwd
        if (cwd / "kitty-specs" / feature_slug).exists():
            tasks_dir = cwd / "kitty-specs" / feature_slug / "tasks"
        else:
            # Walk up to find kitty-specs
            current = cwd
            while current != current.parent:
                if (current / "kitty-specs" / feature_slug).exists():
                    tasks_dir = current / "kitty-specs" / feature_slug / "tasks"
                    break
                current = current.parent
            else:
                # Fallback to repo_root
                tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"
    else:
        # We're in main repo
        tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"

    if not tasks_dir.exists():
        return None

    # Find all WP files
    wp_files = sorted(tasks_dir.glob("WP*.md"))

    for wp_file in wp_files:
        content = wp_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        lane = extract_scalar(frontmatter, "lane")

        if lane == "planned":
            wp_id = extract_scalar(frontmatter, "work_package_id")
            if wp_id:
                return wp_id

    return None


@app.command(name="implement")
def implement(
    wp_id: Annotated[Optional[str], typer.Argument(help="Work package ID (e.g., WP01, wp01, WP01-slug) - auto-detects first planned if omitted")] = None,
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent name (required for auto-move to doing lane)")] = None,
    base: Annotated[Optional[str], typer.Option("--base", help="Base WP to branch from (e.g., WP01) - creates worktree if provided")] = None,
) -> None:
    """Display work package prompt with implementation instructions.

    This command outputs the full work package prompt content so agents can
    immediately see what to implement, without navigating the file system.

    Automatically moves WP from planned to doing lane (requires --agent to track who is working).

    If --base is provided, creates a worktree for this WP branching from the base WP's branch.

    Examples:
        spec-kitty agent workflow implement WP01 --agent claude
        spec-kitty agent workflow implement WP02 --agent claude --base WP01  # Create worktree from WP01
        spec-kitty agent workflow implement wp01 --agent codex
        spec-kitty agent workflow implement --agent gemini  # auto-detects first planned WP
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            print("Error: Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Determine which WP to implement
        if wp_id:
            normalized_wp_id = _normalize_wp_id(wp_id)
        else:
            # Auto-detect first planned WP
            normalized_wp_id = _find_first_planned_wp(repo_root, feature_slug)
            if not normalized_wp_id:
                print("Error: No planned work packages found. Specify a WP ID explicitly.")
                raise typer.Exit(1)

        # ALWAYS validate dependencies before creating workspace or displaying prompts
        # This prevents creating workspaces with wrong base branches

        # Find WP file to read dependencies
        try:
            wp = locate_work_package(repo_root, feature_slug, normalized_wp_id)
        except Exception as e:
            print(f"Error locating work package: {e}")
            raise typer.Exit(1)

        # Validate dependencies and resolve base workspace
        # This will error if:
        # - WP has single dependency but --base not provided
        # - Provided base doesn't match declared dependencies (warning only)
        try:
            resolved_base, auto_merge = validate_and_resolve_base(
                wp_id=normalized_wp_id,
                wp_file=wp.path,
                base=base,  # May be None
                feature_slug=feature_slug,
                repo_root=repo_root
            )
        except typer.Exit:
            # Validation failed (e.g., missing --base for single dependency)
            raise

        # If validation resolved a base (or auto-merge mode), validate base workspace exists
        if resolved_base:
            validate_base_workspace_exists(resolved_base, feature_slug, repo_root)

        # Create worktree only if explicitly requested via --base or auto-merge
        # Don't auto-create workspaces for WPs with no dependencies and no --base
        # (user can create manually later or provide --base explicitly)
        if base is not None or auto_merge:
            print(f"Creating workspace for {normalized_wp_id}...")
            try:
                top_level_implement(
                    wp_id=normalized_wp_id,
                    base=resolved_base,  # None for auto-merge or no deps
                    feature=feature_slug,
                    json_output=False
                )
            except typer.Exit:
                # Worktree creation failed - propagate error
                raise
            except Exception as e:
                print(f"Error creating worktree: {e}")
                raise typer.Exit(1)

        # Load work package
        wp = locate_work_package(repo_root, feature_slug, normalized_wp_id)

        # Move to "doing" lane if not already there
        current_lane = extract_scalar(wp.frontmatter, "lane") or "planned"
        if current_lane != "doing":
            # Require --agent parameter to track who is working
            if not agent:
                print("Error: --agent parameter required when starting implementation.")
                print(f"  Usage: spec-kitty agent workflow implement {normalized_wp_id} --agent <your-name>")
                print("  Example: spec-kitty agent workflow implement WP01 --agent claude")
                print()
                print("If you're using a generated agent command file, --agent is already included.")
                print("This tracks WHO is working on the WP (prevents abandoned tasks).")
                raise typer.Exit(1)

            from datetime import datetime, timezone
            import os

            # Capture current shell PID
            shell_pid = str(os.getppid())  # Parent process ID (the shell running this command)

            # Update lane, agent, and shell_pid in frontmatter
            updated_front = set_scalar(wp.frontmatter, "lane", "doing")
            updated_front = set_scalar(updated_front, "agent", agent)
            updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

            # Build history entry
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            history_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – lane=doing – Started implementation via workflow command"

            # Add history entry to body
            updated_body = append_activity_log(wp.body, history_entry)

            # Build and write updated document
            updated_doc = build_document(updated_front, updated_body, wp.padding)
            wp.path.write_text(updated_doc, encoding="utf-8")

            # Auto-commit to main (enables instant status sync)
            import subprocess

            # Get main repo root (might be in worktree)
            git_file = Path.cwd() / ".git"
            if git_file.is_file():
                git_content = git_file.read_text().strip()
                if git_content.startswith("gitdir:"):
                    gitdir = Path(git_content.split(":", 1)[1].strip())
                    main_repo_root = gitdir.parent.parent.parent
                else:
                    main_repo_root = repo_root
            else:
                main_repo_root = repo_root

            actual_wp_path = wp.path.resolve()
            commit_result = subprocess.run(
                ["git", "commit", str(actual_wp_path), "-m", f"chore: Start {normalized_wp_id} implementation [{agent}]"],
                cwd=main_repo_root,
                capture_output=True,
                text=True,
                check=False
            )

            if commit_result.returncode == 0:
                print(f"✓ Claimed {normalized_wp_id} (agent: {agent}, PID: {shell_pid})")
            else:
                # Commit failed - file might already be committed in this state
                pass

            # Reload to get updated content
            wp = locate_work_package(repo_root, feature_slug, normalized_wp_id)
        else:
            print(f"⚠️  {normalized_wp_id} is already in lane: {current_lane}. Workflow implement will not move it to doing.")

        # Check review status
        review_status = extract_scalar(wp.frontmatter, "review_status")
        has_feedback = review_status == "has_feedback"

        # Detect mission type and get deliverables_path for research missions
        feature_dir = repo_root / "kitty-specs" / feature_slug
        mission_key = get_feature_mission_key(feature_dir)
        deliverables_path = None
        if mission_key == "research":
            deliverables_path = get_deliverables_path(feature_dir, feature_slug)

        # Calculate workspace path
        workspace_name = f"{feature_slug}-{normalized_wp_id}"
        workspace_path = repo_root / ".worktrees" / workspace_name

        # Ensure workspace exists (create if needed)
        if not workspace_path.exists():
            import subprocess

            # Ensure .worktrees directory exists
            worktrees_dir = repo_root / ".worktrees"
            worktrees_dir.mkdir(parents=True, exist_ok=True)

            # Create worktree with sparse-checkout
            branch_name = workspace_name
            result = subprocess.run(
                ["git", "worktree", "add", str(workspace_path), "-b", branch_name],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                print(f"Warning: Could not create workspace: {result.stderr}")
            else:
                # Configure sparse-checkout to exclude kitty-specs/
                sparse_checkout_result = subprocess.run(
                    ["git", "rev-parse", "--git-path", "info/sparse-checkout"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if sparse_checkout_result.returncode == 0:
                    sparse_checkout_file = Path(sparse_checkout_result.stdout.strip())
                    subprocess.run(["git", "config", "core.sparseCheckout", "true"], cwd=workspace_path, capture_output=True, check=False)
                    subprocess.run(["git", "config", "core.sparseCheckoutCone", "false"], cwd=workspace_path, capture_output=True, check=False)
                    sparse_checkout_file.parent.mkdir(parents=True, exist_ok=True)
                    sparse_checkout_file.write_text("/*\n!/kitty-specs/\n!/kitty-specs/**\n", encoding="utf-8")
                    subprocess.run(["git", "read-tree", "-mu", "HEAD"], cwd=workspace_path, capture_output=True, check=False)

                    # Add .gitignore to block WP status files but allow research artifacts
                    gitignore_path = workspace_path / ".gitignore"
                    gitignore_entry = "# Block WP status files (managed in main repo, prevents merge conflicts)\n# Research artifacts in kitty-specs/**/research/ are allowed\nkitty-specs/**/tasks/*.md\n"
                    if gitignore_path.exists():
                        content = gitignore_path.read_text(encoding="utf-8")
                        if "kitty-specs/**/tasks/*.md" not in content:
                            # Remove old blanket rule if present
                            if "kitty-specs/\n" in content:
                                content = content.replace("# Prevent worktree-local kitty-specs/ (status managed in main repo)\nkitty-specs/\n", "")
                                content = content.replace("kitty-specs/\n", "")
                            gitignore_path.write_text(content.rstrip() + "\n" + gitignore_entry, encoding="utf-8")
                    else:
                        gitignore_path.write_text(gitignore_entry, encoding="utf-8")

                print(f"✓ Created workspace: {workspace_path}")

        # ALWAYS validate sparse-checkout (fixes legacy worktrees that were created
        # without sparse-checkout or where setup failed silently)
        if workspace_path.exists():
            _ensure_sparse_checkout(workspace_path)

        # Build full prompt content for file
        lines = []
        lines.append("=" * 80)
        lines.append(f"IMPLEMENT: {normalized_wp_id}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Source: {wp.path}")
        lines.append("")
        lines.append(f"Workspace: {workspace_path}")
        lines.append("")

        # CRITICAL: WP isolation rules
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  🚨 CRITICAL: WORK PACKAGE ISOLATION RULES                              ║")
        lines.append("╠" + "=" * 78 + "╣")
        lines.append(f"║  YOU ARE ASSIGNED TO: {normalized_wp_id:<55} ║")
        lines.append("║                                                                          ║")
        lines.append("║  ✅ DO:                                                                  ║")
        lines.append(f"║     • Only modify status of {normalized_wp_id:<47} ║")
        lines.append(f"║     • Only mark subtasks belonging to {normalized_wp_id:<36} ║")
        lines.append("║     • Ignore git commits and status changes from other agents           ║")
        lines.append("║                                                                          ║")
        lines.append("║  ❌ DO NOT:                                                              ║")
        lines.append(f"║     • Change status of any WP other than {normalized_wp_id:<34} ║")
        lines.append("║     • React to or investigate other WPs' status changes                 ║")
        lines.append(f"║     • Mark subtasks that don't belong to {normalized_wp_id:<33} ║")
        lines.append("║                                                                          ║")
        lines.append("║  WHY: Multiple agents work in parallel. Each owns exactly ONE WP.       ║")
        lines.append("║       Git commits from other WPs are other agents - ignore them.        ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")

        # Next steps
        lines.append("=" * 80)
        lines.append("WHEN YOU'RE DONE:")
        lines.append("=" * 80)
        lines.append(f"✓ Implementation complete and tested:")
        lines.append(f"  1. **Commit your implementation files:**")
        lines.append(f"     git status  # Check what you changed")
        lines.append(f"     git add <your-implementation-files>  # NOT WP status files")
        lines.append(f"     git commit -m \"feat({normalized_wp_id}): <brief description>\"")
        lines.append(f"     git log -1 --oneline  # Verify commit succeeded")
        lines.append(f"  2. Mark all subtasks as done:")
        lines.append(f"     spec-kitty agent tasks mark-status T001 T002 T003 --status done")
        lines.append(f"  3. Move WP to review:")
        lines.append(f"     spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --note \"Ready for review\"")
        lines.append("")
        lines.append(f"✗ Blocked or cannot complete:")
        lines.append(f"  spec-kitty agent tasks add-history {normalized_wp_id} --note \"Blocked: <reason>\"")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"📍 WORKING DIRECTORY:")
        lines.append(f"   cd {workspace_path}")
        lines.append(f"   # All implementation work happens in this workspace")
        lines.append(f"   # When done, return to main: cd {repo_root}")
        lines.append("")
        lines.append("📋 STATUS TRACKING:")
        lines.append(f"   kitty-specs/ is excluded via sparse-checkout (status tracked in main)")
        lines.append(f"   Status changes auto-commit to main branch (visible to all agents)")
        lines.append(f"   ⚠️  You will see commits from other agents - IGNORE THEM")
        lines.append("=" * 80)
        lines.append("")

        if has_feedback:
            lines.append("⚠️  This work package has review feedback. Check the '## Review Feedback' section below.")
            lines.append("")

        # Research mission: Show deliverables path prominently
        if mission_key == "research" and deliverables_path:
            lines.append("╔" + "=" * 78 + "╗")
            lines.append("║  🔬 RESEARCH MISSION - TWO ARTIFACT TYPES                                 ║")
            lines.append("╠" + "=" * 78 + "╣")
            lines.append("║                                                                          ║")
            lines.append("║  📁 RESEARCH DELIVERABLES (your output):                                 ║")
            deliv_line = f"║     {deliverables_path:<69} ║"
            lines.append(deliv_line)
            lines.append("║     ↳ Create findings, reports, data here                                ║")
            lines.append("║     ↳ Commit to worktree branch                                          ║")
            lines.append("║     ↳ Will merge to main when WP completes                               ║")
            lines.append("║                                                                          ║")
            lines.append("║  📋 PLANNING ARTIFACTS (kitty-specs/):                                   ║")
            lines.append("║     ↳ evidence-log.csv, source-register.csv                              ║")
            lines.append("║     ↳ Edit in main repo (rare during implementation)                     ║")
            lines.append("║                                                                          ║")
            lines.append("║  ⚠️  DO NOT put research deliverables in kitty-specs/!                   ║")
            lines.append("╚" + "=" * 78 + "╝")
            lines.append("")

        # WP content marker and content
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  WORK PACKAGE PROMPT BEGINS                                            ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")
        lines.append(wp.path.read_text(encoding="utf-8"))
        lines.append("")
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  WORK PACKAGE PROMPT ENDS                                              ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")

        # Completion instructions at end
        lines.append("=" * 80)
        lines.append("🎯 IMPLEMENTATION COMPLETE? RUN THESE COMMANDS:")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"✅ Implementation complete and tested:")
        lines.append(f"   1. **Commit your implementation files:**")
        lines.append(f"      git status  # Check what you changed")
        lines.append(f"      git add <your-implementation-files>  # NOT WP status files")
        lines.append(f"      git commit -m \"feat({normalized_wp_id}): <brief description>\"")
        lines.append(f"      git log -1 --oneline  # Verify commit succeeded")
        lines.append(f"      (Use fix: for bugs, chore: for maintenance, docs: for documentation)")
        lines.append(f"   2. Mark all subtasks as done:")
        lines.append(f"      spec-kitty agent tasks mark-status T001 T002 T003 --status done")
        lines.append(f"   3. Move WP to review (will check for uncommitted changes):")
        lines.append(f"      spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --note \"Ready for review: <summary>\"")
        lines.append("")
        lines.append(f"⚠️  Blocked or cannot complete:")
        lines.append(f"   spec-kitty agent tasks add-history {normalized_wp_id} --note \"Blocked: <reason>\"")
        lines.append("")
        lines.append("⚠️  NOTE: The move-task command will FAIL if you have uncommitted changes!")
        lines.append("     Commit all implementation files BEFORE moving to for_review.")
        lines.append("     Dependent work packages need your committed changes.")
        lines.append("=" * 80)

        # Write full prompt to file
        full_content = "\n".join(lines)
        prompt_file = _write_prompt_to_file("implement", normalized_wp_id, full_content)

        # Output concise summary with directive to read the prompt
        print()
        print(f"📍 Workspace: cd {workspace_path}")
        if has_feedback:
            print(f"⚠️  Has review feedback - check prompt file")
        if mission_key == "research" and deliverables_path:
            print(f"🔬 Research deliverables: {deliverables_path}")
            print(f"   (NOT in kitty-specs/ - those are planning artifacts)")
        print()
        print("▶▶▶ NEXT STEP: Read the full prompt file now:")
        print(f"    cat {prompt_file}")
        print()
        print("After implementation, run:")
        print(f"  1. git status && git add <your-files> && git commit -m \"feat({normalized_wp_id}): <description>\"")
        print(f"  2. spec-kitty agent tasks mark-status T001 T002 ... --status done")
        print(f"  3. spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --note \"Ready for review\"")
        print(f"     (Pre-flight check will verify no uncommitted changes)")

    except Exception as e:
        print(f"Error: {e}")
        raise typer.Exit(1)


def _find_first_for_review_wp(repo_root: Path, feature_slug: str) -> Optional[str]:
    """Find the first WP file with lane: "for_review".

    Args:
        repo_root: Repository root path
        feature_slug: Feature slug

    Returns:
        WP ID of first for_review task, or None if not found
    """
    from specify_cli.core.paths import is_worktree_context

    cwd = Path.cwd().resolve()

    # Check if we're in a worktree - if so, use worktree's kitty-specs
    if is_worktree_context(cwd):
        # We're in a worktree, look for kitty-specs relative to cwd
        if (cwd / "kitty-specs" / feature_slug).exists():
            tasks_dir = cwd / "kitty-specs" / feature_slug / "tasks"
        else:
            # Walk up to find kitty-specs
            current = cwd
            while current != current.parent:
                if (current / "kitty-specs" / feature_slug).exists():
                    tasks_dir = current / "kitty-specs" / feature_slug / "tasks"
                    break
                current = current.parent
            else:
                # Fallback to repo_root
                tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"
    else:
        # We're in main repo
        tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"

    if not tasks_dir.exists():
        return None

    # Find all WP files
    wp_files = sorted(tasks_dir.glob("WP*.md"))

    for wp_file in wp_files:
        content = wp_file.read_text(encoding="utf-8-sig")
        frontmatter, _, _ = split_frontmatter(content)
        lane = extract_scalar(frontmatter, "lane")

        if lane == "for_review":
            wp_id = extract_scalar(frontmatter, "work_package_id")
            if wp_id:
                return wp_id

    return None


@app.command(name="review")
def review(
    wp_id: Annotated[Optional[str], typer.Argument(help="Work package ID (e.g., WP01) - auto-detects first for_review if omitted")] = None,
    feature: Annotated[Optional[str], typer.Option("--feature", help="Feature slug (auto-detected if omitted)")] = None,
    agent: Annotated[Optional[str], typer.Option("--agent", help="Agent name (required for auto-move to doing lane)")] = None,
) -> None:
    """Display work package prompt with review instructions.

    This command outputs the full work package prompt (including any review
    feedback from previous reviews) so agents can review the implementation.

    Automatically moves WP from for_review to doing lane (requires --agent to track who is reviewing).

    Examples:
        spec-kitty agent workflow review WP01 --agent claude
        spec-kitty agent workflow review wp02 --agent codex
        spec-kitty agent workflow review --agent gemini  # auto-detects first for_review WP
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            print("Error: Could not locate project root")
            raise typer.Exit(1)

        feature_slug = _find_feature_slug(explicit_feature=feature)

        # Determine which WP to review
        if wp_id:
            normalized_wp_id = _normalize_wp_id(wp_id)
        else:
            # Auto-detect first for_review WP
            normalized_wp_id = _find_first_for_review_wp(repo_root, feature_slug)
            if not normalized_wp_id:
                print("Error: No work packages ready for review. Specify a WP ID explicitly.")
                raise typer.Exit(1)

        # Load work package
        wp = locate_work_package(repo_root, feature_slug, normalized_wp_id)

        # Move to "doing" lane if not already there
        current_lane = extract_scalar(wp.frontmatter, "lane") or "for_review"
        if current_lane != "doing":
            # Require --agent parameter to track who is reviewing
            if not agent:
                print("Error: --agent parameter required when starting review.")
                print(f"  Usage: spec-kitty agent workflow review {normalized_wp_id} --agent <your-name>")
                print("  Example: spec-kitty agent workflow review WP01 --agent claude")
                print()
                print("If you're using a generated agent command file, --agent is already included.")
                print("This tracks WHO is reviewing the WP (prevents abandoned reviews).")
                raise typer.Exit(1)

            from datetime import datetime, timezone
            import os

            # Capture current shell PID
            shell_pid = str(os.getppid())  # Parent process ID (the shell running this command)

            # Update lane, agent, and shell_pid in frontmatter
            updated_front = set_scalar(wp.frontmatter, "lane", "doing")
            updated_front = set_scalar(updated_front, "agent", agent)
            updated_front = set_scalar(updated_front, "shell_pid", shell_pid)

            # Build history entry
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            history_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – lane=doing – Started review via workflow command"

            # Add history entry to body
            updated_body = append_activity_log(wp.body, history_entry)

            # Build and write updated document
            updated_doc = build_document(updated_front, updated_body, wp.padding)
            wp.path.write_text(updated_doc, encoding="utf-8")

            # Auto-commit to main (enables instant status sync)
            import subprocess

            # Get main repo root (might be in worktree)
            git_file = Path.cwd() / ".git"
            if git_file.is_file():
                git_content = git_file.read_text().strip()
                if git_content.startswith("gitdir:"):
                    gitdir = Path(git_content.split(":", 1)[1].strip())
                    main_repo_root = gitdir.parent.parent.parent
                else:
                    main_repo_root = repo_root
            else:
                main_repo_root = repo_root

            actual_wp_path = wp.path.resolve()
            commit_result = subprocess.run(
                ["git", "commit", str(actual_wp_path), "-m", f"chore: Start {normalized_wp_id} review [{agent}]"],
                cwd=main_repo_root,
                capture_output=True,
                text=True,
                check=False
            )

            if commit_result.returncode == 0:
                print(f"✓ Claimed {normalized_wp_id} for review (agent: {agent}, PID: {shell_pid})")
            else:
                # Commit failed - file might already be committed in this state
                pass

            # Reload to get updated content
            wp = locate_work_package(repo_root, feature_slug, normalized_wp_id)
        else:
            print(f"⚠️  {normalized_wp_id} is already in lane: {current_lane}. Workflow review will not move it to doing.")

        # Calculate workspace path
        workspace_name = f"{feature_slug}-{normalized_wp_id}"
        workspace_path = repo_root / ".worktrees" / workspace_name

        # Ensure workspace exists (create if needed)
        if not workspace_path.exists():
            import subprocess

            # Ensure .worktrees directory exists
            worktrees_dir = repo_root / ".worktrees"
            worktrees_dir.mkdir(parents=True, exist_ok=True)

            # Create worktree with sparse-checkout
            branch_name = workspace_name
            result = subprocess.run(
                ["git", "worktree", "add", str(workspace_path), "-b", branch_name],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                print(f"Warning: Could not create workspace: {result.stderr}")
            else:
                # Configure sparse-checkout to exclude kitty-specs/
                sparse_checkout_result = subprocess.run(
                    ["git", "rev-parse", "--git-path", "info/sparse-checkout"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if sparse_checkout_result.returncode == 0:
                    sparse_checkout_file = Path(sparse_checkout_result.stdout.strip())
                    subprocess.run(["git", "config", "core.sparseCheckout", "true"], cwd=workspace_path, capture_output=True, check=False)
                    subprocess.run(["git", "config", "core.sparseCheckoutCone", "false"], cwd=workspace_path, capture_output=True, check=False)
                    sparse_checkout_file.parent.mkdir(parents=True, exist_ok=True)
                    sparse_checkout_file.write_text("/*\n!/kitty-specs/\n!/kitty-specs/**\n", encoding="utf-8")
                    subprocess.run(["git", "read-tree", "-mu", "HEAD"], cwd=workspace_path, capture_output=True, check=False)

                    # Add .gitignore to block WP status files but allow research artifacts
                    gitignore_path = workspace_path / ".gitignore"
                    gitignore_entry = "# Block WP status files (managed in main repo, prevents merge conflicts)\n# Research artifacts in kitty-specs/**/research/ are allowed\nkitty-specs/**/tasks/*.md\n"
                    if gitignore_path.exists():
                        content = gitignore_path.read_text(encoding="utf-8")
                        if "kitty-specs/**/tasks/*.md" not in content:
                            # Remove old blanket rule if present
                            if "kitty-specs/\n" in content:
                                content = content.replace("# Prevent worktree-local kitty-specs/ (status managed in main repo)\nkitty-specs/\n", "")
                                content = content.replace("kitty-specs/\n", "")
                            gitignore_path.write_text(content.rstrip() + "\n" + gitignore_entry, encoding="utf-8")
                    else:
                        gitignore_path.write_text(gitignore_entry, encoding="utf-8")

                print(f"✓ Created workspace: {workspace_path}")

        # ALWAYS validate sparse-checkout (fixes legacy worktrees that were created
        # without sparse-checkout or where setup failed silently)
        if workspace_path.exists():
            _ensure_sparse_checkout(workspace_path)

        # Capture dependency warning for both file and summary
        dependents_warning = []
        feature_dir = repo_root / "kitty-specs" / feature_slug
        graph = build_dependency_graph(feature_dir)
        dependents = get_dependents(normalized_wp_id, graph)
        if dependents:
            incomplete: list[str] = []
            for dependent_id in dependents:
                try:
                    dependent_wp = locate_work_package(repo_root, feature_slug, dependent_id)
                except FileNotFoundError:
                    continue
                lane = extract_scalar(dependent_wp.frontmatter, "lane")
                if lane in {"planned", "doing", "for_review"}:
                    incomplete.append(dependent_id)
            if incomplete:
                dependents_list = ", ".join(sorted(incomplete))
                dependents_warning.append(f"⚠️  Dependency Alert: {dependents_list} depend on {normalized_wp_id} (not yet done)")
                dependents_warning.append("   If you request changes, notify those agents to rebase.")

        # Build full prompt content for file
        lines = []
        lines.append("=" * 80)
        lines.append(f"REVIEW: {normalized_wp_id}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Source: {wp.path}")
        lines.append("")
        lines.append(f"Workspace: {workspace_path}")
        lines.append("")

        # Add dependency warning to file
        if dependents_warning:
            lines.extend(dependents_warning)
            lines.append("")

        # CRITICAL: WP isolation rules
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  🚨 CRITICAL: WORK PACKAGE ISOLATION RULES                              ║")
        lines.append("╠" + "=" * 78 + "╣")
        lines.append(f"║  YOU ARE REVIEWING: {normalized_wp_id:<56} ║")
        lines.append("║                                                                          ║")
        lines.append("║  ✅ DO:                                                                  ║")
        lines.append(f"║     • Only modify status of {normalized_wp_id:<47} ║")
        lines.append("║     • Ignore git commits and status changes from other agents           ║")
        lines.append("║                                                                          ║")
        lines.append("║  ❌ DO NOT:                                                              ║")
        lines.append(f"║     • Change status of any WP other than {normalized_wp_id:<34} ║")
        lines.append("║     • React to or investigate other WPs' status changes                 ║")
        lines.append(f"║     • Review or approve any WP other than {normalized_wp_id:<32} ║")
        lines.append("║                                                                          ║")
        lines.append("║  WHY: Multiple agents work in parallel. Each owns exactly ONE WP.       ║")
        lines.append("║       Git commits from other WPs are other agents - ignore them.        ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")

        # Next steps
        lines.append("=" * 80)
        lines.append("WHEN YOU'RE DONE:")
        lines.append("=" * 80)
        lines.append(f"✓ Review passed, no issues:")
        lines.append(f"  spec-kitty agent tasks move-task {normalized_wp_id} --to done --note \"Review passed\"")
        lines.append("")
        lines.append(f"⚠️  Changes requested:")
        lines.append(f"  1. Add feedback to the WP file's '## Review Feedback' section")
        lines.append(f"  2. spec-kitty agent tasks move-task {normalized_wp_id} --to planned --note \"Changes requested\"")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"📍 WORKING DIRECTORY:")
        lines.append(f"   cd {workspace_path}")
        lines.append(f"   # Review the implementation in this workspace")
        lines.append(f"   # Read code, run tests, check against requirements")
        lines.append(f"   # When done, return to main: cd {repo_root}")
        lines.append("")
        lines.append("📋 STATUS TRACKING:")
        lines.append(f"   kitty-specs/ is excluded via sparse-checkout (status tracked in main)")
        lines.append(f"   Status changes auto-commit to main branch (visible to all agents)")
        lines.append(f"   ⚠️  You will see commits from other agents - IGNORE THEM")
        lines.append("=" * 80)
        lines.append("")
        lines.append("Review the implementation against the requirements below.")
        lines.append("Check code quality, tests, documentation, and adherence to spec.")
        lines.append("")

        # WP content marker and content
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  WORK PACKAGE PROMPT BEGINS                                            ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")
        lines.append(wp.path.read_text(encoding="utf-8"))
        lines.append("")
        lines.append("╔" + "=" * 78 + "╗")
        lines.append("║  WORK PACKAGE PROMPT ENDS                                              ║")
        lines.append("╚" + "=" * 78 + "╝")
        lines.append("")

        # Completion instructions at end
        lines.append("=" * 80)
        lines.append("🎯 REVIEW COMPLETE? RUN ONE OF THESE COMMANDS:")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"✅ APPROVE (no issues found):")
        lines.append(f"   spec-kitty agent tasks move-task {normalized_wp_id} --to done --note \"Review passed: <summary>\"")
        lines.append("")
        # Create unique temp file path for review feedback (avoids conflicts between agents)
        review_feedback_path = Path(tempfile.gettempdir()) / f"spec-kitty-review-feedback-{normalized_wp_id}.md"

        lines.append(f"❌ REQUEST CHANGES (issues found):")
        lines.append(f"   1. Write feedback:")
        lines.append(f"      cat > {review_feedback_path} <<'EOF'")
        lines.append(f"**Issue 1**: <description and how to fix>")
        lines.append(f"**Issue 2**: <description and how to fix>")
        lines.append(f"EOF")
        lines.append("")
        lines.append(f"   2. Move to planned with feedback:")
        lines.append(f"      spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file {review_feedback_path}")
        lines.append("")
        lines.append("⚠️  NOTE: You MUST run one of these commands to complete the review!")
        lines.append("     The Python script handles all file updates automatically.")
        lines.append("=" * 80)

        # Write full prompt to file
        full_content = "\n".join(lines)
        prompt_file = _write_prompt_to_file("review", normalized_wp_id, full_content)

        # Create unique temp file path for review feedback (same as in prompt)
        review_feedback_path = Path(tempfile.gettempdir()) / f"spec-kitty-review-feedback-{normalized_wp_id}.md"

        # Output concise summary with directive to read the prompt
        print()
        if dependents_warning:
            for line in dependents_warning:
                print(line)
            print()
        print(f"📍 Workspace: cd {workspace_path}")
        print()
        print("▶▶▶ NEXT STEP: Read the full prompt file now:")
        print(f"    cat {prompt_file}")
        print()
        print("After review, run:")
        print(f"  ✅ spec-kitty agent tasks move-task {normalized_wp_id} --to done --note \"Review passed\"")
        print(f"  ❌ spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file {review_feedback_path}")

    except Exception as e:
        print(f"Error: {e}")
        raise typer.Exit(1)
