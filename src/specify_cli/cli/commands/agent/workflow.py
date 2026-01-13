"""Workflow commands for AI agents - display prompts and instructions."""

from __future__ import annotations

import os
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

    # Strategy 0: Environment override
    env_slug = os.getenv("SPECIFY_FEATURE", "").strip()
    if env_slug:
        return _strip_wp_suffix(env_slug)

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

    # Strategy 3: Fall back to latest feature in repo root
    repo_root = locate_project_root(cwd)
    if repo_root:
        specs_dir = repo_root / "kitty-specs"
        if specs_dir.exists():
            feature_dirs = [
                d.name for d in specs_dir.iterdir()
                if d.is_dir() and re.match(r'^\d{3}-', d.name)
            ]
            if feature_dirs:
                def _feature_num(name: str) -> int:
                    try:
                        return int(name.split("-", 1)[0])
                    except (ValueError, IndexError):
                        return -1
                return max(feature_dirs, key=_feature_num)

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
) -> None:
    """Display work package prompt with implementation instructions.

    This command outputs the full work package prompt content so agents can
    immediately see what to implement, without navigating the file system.

    Examples:
        spec-kitty agent workflow implement WP01
        spec-kitty agent workflow implement wp01
        spec-kitty agent workflow implement WP01-add-feature
        spec-kitty agent workflow implement  # auto-detects first planned WP
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

        # Move to "doing" lane only from planned (avoid undoing review/complete lanes)
        current_lane = extract_scalar(wp.frontmatter, "lane") or "planned"
        if current_lane == "planned":
            from datetime import datetime, timezone

            # Update lane in frontmatter
            updated_front = set_scalar(wp.frontmatter, "lane", "doing")

            # Build history entry
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            agent_name = extract_scalar(updated_front, "agent") or "agent"
            history_entry = f"- {timestamp} – {agent_name} – lane=doing – Started implementation via workflow command"

            # Add history entry to body
            updated_body = append_activity_log(wp.body, history_entry)

            # Build and write updated document
            updated_doc = build_document(updated_front, updated_body, wp.padding)
            wp.path.write_text(updated_doc, encoding="utf-8")

            # Reload to get updated content
            wp = locate_work_package(repo_root, feature_slug, normalized_wp_id)
        elif current_lane in {"for_review", "done"}:
            print(f"⚠️  {normalized_wp_id} is already in lane: {current_lane}. Workflow implement will not move it to doing.")

        # Check review status
        review_status = extract_scalar(wp.frontmatter, "review_status")
        has_feedback = review_status == "has_feedback"

        # Calculate workspace path
        workspace_name = f"{feature_slug}-{normalized_wp_id}"
        workspace_path = repo_root / ".worktrees" / workspace_name

        # Output the prompt
        print("=" * 80)
        print(f"IMPLEMENT: {normalized_wp_id}")
        print("=" * 80)
        print()
        print(f"Source: {wp.path}")
        print()
        print(f"Workspace: {workspace_path}")
        print()

        # Show next steps FIRST so agent sees them immediately
        print("=" * 80)
        print("WHEN YOU'RE DONE:")
        print("=" * 80)
        print("✓ Implementation complete and tested:")
        print("  This workflow will auto-move the work package to for_review.")
        print()
        print("✗ Blocked or cannot complete:")
        print("  Record the block in the Activity Log before re-running the workflow.")
        print("=" * 80)
        print()
        print(f"📍 WORKING DIRECTORY:")
        print(f"   cd {workspace_path}")
        print(f"   # All implementation work happens in this workspace")
        print(f"   # When done, return to main: cd {repo_root}")
        print("=" * 80)
        print()

        if has_feedback:
            print("⚠️  This work package has review feedback. Check the '## Review Feedback' section below.")
            print()

        # Output full prompt content (frontmatter + body)
        print(wp.path.read_text(encoding="utf-8"))

        # Auto-move to for_review after displaying the prompt
        from specify_cli.cli.commands.agent.tasks import move_task
        move_task(
            normalized_wp_id,
            to="for_review",
            feature=feature_slug,
            note="Auto-moved to for_review after implement workflow"
        )

    except typer.Exit:
        raise
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
        if lane == "doing":
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
) -> None:
    """Display work package prompt with review instructions.

    This command outputs the full work package prompt (including any review
    feedback from previous reviews) so agents can review the implementation.

    Examples:
        spec-kitty agent workflow review WP01
        spec-kitty agent workflow review wp02
        spec-kitty agent workflow review  # auto-detects first for_review WP
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

        # Move to "doing" lane only from for_review
        current_lane = extract_scalar(wp.frontmatter, "lane") or "planned"
        if current_lane == "for_review":
            from datetime import datetime, timezone

            # Update lane in frontmatter
            updated_front = set_scalar(wp.frontmatter, "lane", "doing")

            # Build history entry
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            agent_name = extract_scalar(updated_front, "agent") or "agent"
            history_entry = f"- {timestamp} – {agent_name} – lane=doing – Started review via workflow command"

            # Add history entry to body
            updated_body = append_activity_log(wp.body, history_entry)

            # Build and write updated document
            updated_doc = build_document(updated_front, updated_body, wp.padding)
            wp.path.write_text(updated_doc, encoding="utf-8")

            # Reload to get updated content
            wp = locate_work_package(repo_root, feature_slug, normalized_wp_id)
        elif current_lane not in {"doing"}:
            print(f"Error: {normalized_wp_id} is in lane '{current_lane}'. Only for_review WPs can be reviewed.")
            raise typer.Exit(1)

        # Calculate workspace path
        workspace_name = f"{feature_slug}-{normalized_wp_id}"
        workspace_path = repo_root / ".worktrees" / workspace_name

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

        # Show next steps FIRST so agent sees them immediately
        print("=" * 80)
        print("WHEN YOU'RE DONE:")
        print("=" * 80)
        print("✓ Review passed, no issues:")
        print("  This workflow will auto-move the work package to done.")
        print()
        print("⚠️  Changes requested:")
        print("  Add feedback in the WP file's '## Review Feedback' section.")
        print("  The workflow will auto-move the work package back to planned.")
        print("=" * 80)
        print()
        print(f"📍 WORKING DIRECTORY:")
        print(f"   cd {workspace_path}")
        print(f"   # Review the implementation in this workspace")
        print(f"   # Read code, run tests, check against requirements")
        print(f"   # When done, return to main: cd {repo_root}")
        print("=" * 80)
        print()
        print("Review the implementation against the requirements below.")
        print("Check code quality, tests, documentation, and adherence to spec.")
        print()

        # Output full prompt content (frontmatter + body)
        print(wp.path.read_text(encoding="utf-8"))

        # Auto-move to planned or done after displaying the prompt
        target_lane = "planned" if extract_scalar(wp.frontmatter, "review_status") == "has_feedback" else "done"
        note = "Changes requested" if target_lane == "planned" else "Review passed"
        from specify_cli.cli.commands.agent.tasks import move_task
        move_task(
            normalized_wp_id,
            to=target_lane,
            feature=feature_slug,
            note=note
        )

    except typer.Exit:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise typer.Exit(1)
