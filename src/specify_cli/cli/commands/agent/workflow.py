"""Workflow commands for AI agents - display prompts and instructions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from specify_cli.core.paths import locate_project_root
from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
from specify_cli.tasks_support import (
    extract_scalar,
    locate_work_package,
    split_frontmatter,
    set_scalar,
    append_activity_log,
    build_document,
)

app = typer.Typer(
    name="workflow",
    help="Workflow commands that display prompts and instructions for agents",
    no_args_is_help=True
)


def _find_feature_slug() -> str:
    """Find the current feature slug from the working directory or git branch.

    Returns:
        Feature slug (e.g., "008-unified-python-cli")

    Raises:
        typer.Exit: If feature slug cannot be determined
    """
    import re
    cwd = Path.cwd().resolve()

    def _strip_wp_suffix(slug: str) -> str:
        """Strip -WPxx suffix from feature slug if present.

        Worktree branches/dirs are named {feature-slug}-WPxx,
        so we need to extract just the feature slug.
        """
        # Match -WPxx at the end (case insensitive)
        return re.sub(r'-WP\d+$', '', slug, flags=re.IGNORECASE)

    # Strategy 1: Check if cwd contains kitty-specs/###-feature-slug
    if "kitty-specs" in cwd.parts:
        parts_list = list(cwd.parts)
        try:
            idx = parts_list.index("kitty-specs")
            if idx + 1 < len(parts_list):
                potential_slug = parts_list[idx + 1]
                # Validate format: ###-slug
                if len(potential_slug) >= 3 and potential_slug[:3].isdigit():
                    return _strip_wp_suffix(potential_slug)
        except (ValueError, IndexError):
            pass

    # Strategy 2: Get from git branch name
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        branch_name = result.stdout.strip()
        # Validate format: ###-slug (possibly with -WPxx suffix)
        if len(branch_name) >= 3 and branch_name[:3].isdigit():
            return _strip_wp_suffix(branch_name)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Strategy 3: Scan kitty-specs/ and pick lexically most recent feature
    try:
        repo_root = locate_project_root()
        if repo_root:
            kitty_specs_dir = repo_root / "kitty-specs"
            if kitty_specs_dir.exists():
                # Find all feature directories matching ###-* pattern
                feature_dirs = [
                    d.name for d in kitty_specs_dir.iterdir()
                    if d.is_dir() and len(d.name) >= 3 and d.name[:3].isdigit()
                ]
                if feature_dirs:
                    # Sort and pick the lexically most recent (highest number)
                    feature_dirs.sort()
                    return feature_dirs[-1]
    except Exception:
        pass

    print("Error: Could not auto-detect feature slug.")
    print("  - Not in a kitty-specs/###-feature-slug directory")
    print("  - Git branch name doesn't match ###-slug format")
    print("  - Use --feature <slug> to specify explicitly")
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
) -> None:
    """Display work package prompt with implementation instructions.

    This command outputs the full work package prompt content so agents can
    immediately see what to implement, without navigating the file system.

    Automatically moves WP from planned to doing lane (requires --agent to track who is working).

    Examples:
        spec-kitty agent workflow implement WP01 --agent claude
        spec-kitty agent workflow implement wp01 --agent codex
        spec-kitty agent workflow implement --agent gemini  # auto-detects first planned WP
    """
    try:
        # Get repo root and feature slug
        repo_root = locate_project_root()
        if repo_root is None:
            print("Error: Could not locate project root")
            raise typer.Exit(1)

        feature_slug = feature or _find_feature_slug()

        # Determine which WP to implement
        if wp_id:
            normalized_wp_id = _normalize_wp_id(wp_id)
        else:
            # Auto-detect first planned WP
            normalized_wp_id = _find_first_planned_wp(repo_root, feature_slug)
            if not normalized_wp_id:
                print("Error: No planned work packages found. Specify a WP ID explicitly.")
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

                    # Add .gitignore to prevent manual kitty-specs/ additions
                    gitignore_path = workspace_path / ".gitignore"
                    gitignore_entry = "# Prevent worktree-local kitty-specs/ (status managed in main repo)\nkitty-specs/\n"
                    if gitignore_path.exists():
                        content = gitignore_path.read_text(encoding="utf-8")
                        if "kitty-specs/" not in content:
                            gitignore_path.write_text(content.rstrip() + "\n" + gitignore_entry, encoding="utf-8")
                    else:
                        gitignore_path.write_text(gitignore_entry, encoding="utf-8")

                print(f"✓ Created workspace: {workspace_path}")

        # Output the prompt
        print("=" * 80)
        print(f"IMPLEMENT: {normalized_wp_id}")
        print("=" * 80)
        print()
        print(f"Source: {wp.path}")
        print()
        print(f"Workspace: {workspace_path}")
        print()

        # CRITICAL: WP isolation rules - must come first
        print("╔" + "=" * 78 + "╗")
        print("║  🚨 CRITICAL: WORK PACKAGE ISOLATION RULES                              ║")
        print("╠" + "=" * 78 + "╣")
        print(f"║  YOU ARE ASSIGNED TO: {normalized_wp_id:<55} ║")
        print("║                                                                          ║")
        print("║  ✅ DO:                                                                  ║")
        print(f"║     • Only modify status of {normalized_wp_id:<47} ║")
        print(f"║     • Only mark subtasks belonging to {normalized_wp_id:<36} ║")
        print("║     • Ignore git commits and status changes from other agents           ║")
        print("║                                                                          ║")
        print("║  ❌ DO NOT:                                                              ║")
        print(f"║     • Change status of any WP other than {normalized_wp_id:<34} ║")
        print("║     • React to or investigate other WPs' status changes                 ║")
        print(f"║     • Mark subtasks that don't belong to {normalized_wp_id:<33} ║")
        print("║                                                                          ║")
        print("║  WHY: Multiple agents work in parallel. Each owns exactly ONE WP.       ║")
        print("║       Git commits from other WPs are other agents - ignore them.        ║")
        print("╚" + "=" * 78 + "╝")
        print()

        # Show next steps FIRST so agent sees them immediately
        print("=" * 80)
        print("WHEN YOU'RE DONE:")
        print("=" * 80)
        print(f"✓ Implementation complete and tested:")
        print(f"  spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --note \"Ready for review\"")
        print()
        print(f"✗ Blocked or cannot complete:")
        print(f"  spec-kitty agent tasks add-history {normalized_wp_id} --note \"Blocked: <reason>\"")
        print("=" * 80)
        print()
        print(f"📍 WORKING DIRECTORY:")
        print(f"   cd {workspace_path}")
        print(f"   # All implementation work happens in this workspace")
        print(f"   # When done, return to main: cd {repo_root}")
        print()
        print("📋 STATUS TRACKING:")
        print(f"   kitty-specs/ is excluded via sparse-checkout (status tracked in main)")
        print(f"   Status changes auto-commit to main branch (visible to all agents)")
        print(f"   ⚠️  You will see commits from other agents - IGNORE THEM")
        print("=" * 80)
        print()

        if has_feedback:
            print("⚠️  This work package has review feedback. Check the '## Review Feedback' section below.")
            print()

        # Add visual marker before long content
        print("╔" + "=" * 78 + "╗")
        print("║  WORK PACKAGE PROMPT BEGINS - Scroll to bottom for completion steps   ║")
        print("╚" + "=" * 78 + "╝")
        print()

        # Output full prompt content (frontmatter + body)
        print(wp.path.read_text(encoding="utf-8"))

        # Add visual marker after content
        print()
        print("╔" + "=" * 78 + "╗")
        print("║  WORK PACKAGE PROMPT ENDS - See completion commands below   ║")
        print("╚" + "=" * 78 + "╝")
        print()

        # CRITICAL: Repeat completion instructions at the END
        print("=" * 80)
        print("🎯 IMPLEMENTATION COMPLETE? RUN THIS COMMAND:")
        print("=" * 80)
        print()
        print(f"✅ Implementation complete and tested:")
        print(f"   spec-kitty agent tasks move-task {normalized_wp_id} --to for_review --note \"Ready for review: <summary>\"")
        print()
        print(f"⚠️  Blocked or cannot complete:")
        print(f"   spec-kitty agent tasks add-history {normalized_wp_id} --note \"Blocked: <reason>\"")
        print()
        print("⚠️  NOTE: You MUST run the move-task command when done!")
        print("     This transitions the WP to for_review lane for reviewer agents.")
        print("=" * 80)

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


def _warn_dependents_in_progress(
    repo_root: Path,
    feature_slug: str,
    wp_id: str,
) -> None:
    """Warn if dependent WPs are in progress and may need rebase."""
    feature_dir = repo_root / "kitty-specs" / feature_slug
    graph = build_dependency_graph(feature_dir)
    dependents = get_dependents(wp_id, graph)
    if not dependents:
        return

    in_progress: list[str] = []
    for dependent_id in dependents:
        try:
            dependent_wp = locate_work_package(repo_root, feature_slug, dependent_id)
        except FileNotFoundError:
            continue

        lane = extract_scalar(dependent_wp.frontmatter, "lane")
        if lane in {"planned", "doing", "for_review"}:
            in_progress.append(dependent_id)

    if not in_progress:
        return

    dependents_list = ", ".join(sorted(in_progress))
    print("⚠️  Dependency Alert:")
    print(f"   {dependents_list} depend on {wp_id} and are in progress.")
    print("   If you request changes, notify those agents to rebase.")
    for dependent_id in sorted(in_progress):
        workspace = f".worktrees/{feature_slug}-{dependent_id}"
        base_branch = f"{feature_slug}-{wp_id}"
        print(f"   Rebase command: cd {workspace} && git rebase {base_branch}")
    print()


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

        feature_slug = feature or _find_feature_slug()

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

                    # Add .gitignore to prevent manual kitty-specs/ additions
                    gitignore_path = workspace_path / ".gitignore"
                    gitignore_entry = "# Prevent worktree-local kitty-specs/ (status managed in main repo)\nkitty-specs/\n"
                    if gitignore_path.exists():
                        content = gitignore_path.read_text(encoding="utf-8")
                        if "kitty-specs/" not in content:
                            gitignore_path.write_text(content.rstrip() + "\n" + gitignore_entry, encoding="utf-8")
                    else:
                        gitignore_path.write_text(gitignore_entry, encoding="utf-8")

                print(f"✓ Created workspace: {workspace_path}")

        _warn_dependents_in_progress(repo_root, feature_slug, normalized_wp_id)

        # Output the prompt
        print("=" * 80)
        print(f"REVIEW: {normalized_wp_id}")
        print("=" * 80)
        print()
        print(f"Source: {wp.path}")
        print()
        print(f"Workspace: {workspace_path}")
        print()

        # CRITICAL: WP isolation rules - must come first
        print("╔" + "=" * 78 + "╗")
        print("║  🚨 CRITICAL: WORK PACKAGE ISOLATION RULES                              ║")
        print("╠" + "=" * 78 + "╣")
        print(f"║  YOU ARE REVIEWING: {normalized_wp_id:<56} ║")
        print("║                                                                          ║")
        print("║  ✅ DO:                                                                  ║")
        print(f"║     • Only modify status of {normalized_wp_id:<47} ║")
        print("║     • Ignore git commits and status changes from other agents           ║")
        print("║                                                                          ║")
        print("║  ❌ DO NOT:                                                              ║")
        print(f"║     • Change status of any WP other than {normalized_wp_id:<34} ║")
        print("║     • React to or investigate other WPs' status changes                 ║")
        print(f"║     • Review or approve any WP other than {normalized_wp_id:<32} ║")
        print("║                                                                          ║")
        print("║  WHY: Multiple agents work in parallel. Each owns exactly ONE WP.       ║")
        print("║       Git commits from other WPs are other agents - ignore them.        ║")
        print("╚" + "=" * 78 + "╝")
        print()

        # Show next steps FIRST so agent sees them immediately
        print("=" * 80)
        print("WHEN YOU'RE DONE:")
        print("=" * 80)
        print(f"✓ Review passed, no issues:")
        print(f"  spec-kitty agent tasks move-task {normalized_wp_id} --to done --note \"Review passed\"")
        print()
        print(f"⚠️  Changes requested:")
        print(f"  1. Add feedback to the WP file's '## Review Feedback' section")
        print(f"  2. spec-kitty agent tasks move-task {normalized_wp_id} --to planned --note \"Changes requested\"")
        print("=" * 80)
        print()
        print(f"📍 WORKING DIRECTORY:")
        print(f"   cd {workspace_path}")
        print(f"   # Review the implementation in this workspace")
        print(f"   # Read code, run tests, check against requirements")
        print(f"   # When done, return to main: cd {repo_root}")
        print()
        print("📋 STATUS TRACKING:")
        print(f"   kitty-specs/ is excluded via sparse-checkout (status tracked in main)")
        print(f"   Status changes auto-commit to main branch (visible to all agents)")
        print(f"   ⚠️  You will see commits from other agents - IGNORE THEM")
        print("=" * 80)
        print()
        print("Review the implementation against the requirements below.")
        print("Check code quality, tests, documentation, and adherence to spec.")
        print()

        # Add visual marker before long content
        print("╔" + "=" * 78 + "╗")
        print("║   WORK PACKAGE PROMPT BEGINS - Scroll to bottom for completion steps  ║")
        print("╚" + "=" * 78 + "╝")
        print()

        # Output full prompt content (frontmatter + body)
        print(wp.path.read_text(encoding="utf-8"))

        # Add visual marker after content
        print()
        print("╔" + "=" * 78 + "╗")
        print("║   WORK PACKAGE PROMPT ENDS - See completion commands below  ║")
        print("╚" + "=" * 78 + "╝")
        print()

        # CRITICAL: Repeat completion instructions at the END
        print("=" * 80)
        print("🎯 REVIEW COMPLETE? RUN ONE OF THESE COMMANDS:")
        print("=" * 80)
        print()
        print(f"✅ APPROVE (no issues found):")
        print(f"   spec-kitty agent tasks move-task {normalized_wp_id} --to done --note \"Review passed: <summary>\"")
        print()
        print(f"❌ REQUEST CHANGES (issues found):")
        print(f"   1. Write feedback:")
        print(f"      cat > review-feedback.md <<'EOF'")
        print(f"**Issue 1**: <description and how to fix>")
        print(f"**Issue 2**: <description and how to fix>")
        print(f"EOF")
        print()
        print(f"   2. Move to planned with feedback:")
        print(f"      spec-kitty agent tasks move-task {normalized_wp_id} --to planned --review-feedback-file review-feedback.md")
        print()
        print("⚠️  NOTE: You MUST run one of these commands to complete the review!")
        print("     The Python script handles all file updates automatically.")
        print("=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        raise typer.Exit(1)
