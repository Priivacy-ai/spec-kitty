"""Merge command implementation."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import console, show_banner
from specify_cli.core.git_ops import run_command
from specify_cli.tasks_support import TaskCliError, find_repo_root


def merge(
    strategy: str = typer.Option("merge", "--strategy", help="Merge strategy: merge, squash, or rebase"),
    delete_branch: bool = typer.Option(True, "--delete-branch/--keep-branch", help="Delete feature branch after merge"),
    remove_worktree: bool = typer.Option(True, "--remove-worktree/--keep-worktree", help="Remove feature worktree after merge"),
    push: bool = typer.Option(False, "--push", help="Push to origin after merge"),
    target_branch: str = typer.Option("main", "--target", help="Target branch to merge into"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
) -> None:
    """Merge a completed feature branch into the target branch and clean up resources."""
    show_banner()

    tracker = StepTracker("Feature Merge")
    tracker.add("detect", "Detect current feature and branch")
    tracker.add("verify", "Verify merge readiness")
    tracker.add("checkout", f"Switch to {target_branch}")
    tracker.add("pull", f"Update {target_branch}")
    tracker.add("merge", "Merge feature branch")
    if push: tracker.add("push", "Push to origin")
    if remove_worktree: tracker.add("worktree", "Remove feature worktree")
    if delete_branch: tracker.add("branch", "Delete feature branch")
    console.print()

    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    feature_worktree_path = merge_root = repo_root
    tracker.start("detect")
    try:
        _, current_branch, _ = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True)
        if current_branch == target_branch:
            tracker.error("detect", f"already on {target_branch}")
            console.print(tracker.render())
            console.print(f"\n[red]Error:[/red] Already on {target_branch} branch. Switch to a feature branch first.")
            raise typer.Exit(1)

        _, git_dir_output, _ = run_command(["git", "rev-parse", "--git-dir"], capture=True)
        git_dir_path = Path(git_dir_output).resolve()
        in_worktree = "worktrees" in git_dir_path.parts
        if in_worktree:
            merge_root = git_dir_path.parents[2]
            if not merge_root.exists():
                raise RuntimeError(f"Primary repository path not found: {merge_root}")
        tracker.complete(
            "detect",
            f"on {current_branch}" + (f" (worktree → operating from {merge_root})" if in_worktree else ""),
        )
    except Exception as exc:
        tracker.error("detect", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    tracker.start("verify")
    try:
        _, status_output, _ = run_command(["git", "status", "--porcelain"], capture=True)
        if status_output.strip():
            tracker.error("verify", "uncommitted changes")
            console.print(tracker.render())
            console.print(f"\n[red]Error:[/red] Working directory has uncommitted changes.")
            console.print("Commit or stash your changes before merging.")
            raise typer.Exit(1)
        tracker.complete("verify", "clean working directory")
    except Exception as exc:
        tracker.error("verify", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    merge_root, feature_worktree_path = merge_root.resolve(), feature_worktree_path.resolve()
    if dry_run:
        console.print(tracker.render())
        console.print("\n[cyan]Dry run - would execute:[/cyan]")
        checkout_prefix = f"(from {merge_root}) " if in_worktree else ""
        steps = [
            f"{checkout_prefix}git checkout {target_branch}",
            "git pull --ff-only",
        ]
        if strategy == "squash":
            steps.extend([
                f"git merge --squash {current_branch}",
                f"git commit -m 'Merge feature {current_branch}'",
            ])
        elif strategy == "rebase":
            steps.append(f"git merge --ff-only {current_branch} (after rebase)")
        else:
            steps.append(f"git merge --no-ff {current_branch}")
        if push:
            steps.append(f"git push origin {target_branch}")
        if in_worktree and remove_worktree:
            steps.append(f"git worktree remove {feature_worktree_path}")
        if delete_branch:
            steps.append(f"git branch -d {current_branch}")
        for idx, step in enumerate(steps, start=1):
            console.print(f"  {idx}. {step}")
        return

    tracker.start("checkout")
    try:
        if in_worktree:
            console.print(f"[cyan]Detected worktree. Merge operations will run from {merge_root}[/cyan]")
        os.chdir(merge_root)
        _, target_status, _ = run_command(["git", "status", "--porcelain"], capture=True)
        if target_status.strip():
            raise RuntimeError(f"Target repository at {merge_root} has uncommitted changes.")
        run_command(["git", "checkout", target_branch])
        tracker.complete("checkout", f"using {merge_root}")
    except Exception as exc:
        tracker.error("checkout", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1)

    tracker.start("pull")
    try:
        run_command(["git", "pull", "--ff-only"])
        tracker.complete("pull")
    except Exception as exc:
        tracker.error("pull", str(exc))
        console.print(tracker.render())
        console.print(f"\n[yellow]Warning:[/yellow] Could not fast-forward {target_branch}.")
        console.print("You may need to resolve conflicts manually.")
        raise typer.Exit(1)

    tracker.start("merge")
    try:
        if strategy == "squash":
            run_command(["git", "merge", "--squash", current_branch])
            run_command(["git", "commit", "-m", f"Merge feature {current_branch}"])
            tracker.complete("merge", "squashed")
        elif strategy == "rebase":
            console.print("\n[yellow]Note:[/yellow] Rebase strategy requires manual intervention.")
            console.print(f"Please run: git checkout {current_branch} && git rebase {target_branch}")
            tracker.skip("merge", "requires manual rebase")
            console.print(tracker.render())
            raise typer.Exit(0)
        else:
            run_command(["git", "merge", "--no-ff", current_branch, "-m", f"Merge feature {current_branch}"])
            tracker.complete("merge", "merged with merge commit")
    except Exception as exc:
        tracker.error("merge", str(exc))
        console.print(tracker.render())
        console.print(f"\n[red]Merge failed.[/red] You may need to resolve conflicts.")
        raise typer.Exit(1)

    if push:
        tracker.start("push")
        try:
            run_command(["git", "push", "origin", target_branch])
            tracker.complete("push")
        except Exception as exc:
            tracker.error("push", str(exc))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Merge succeeded but push failed.")
            console.print(f"Run manually: git push origin {target_branch}")

    if in_worktree and remove_worktree:
        tracker.start("worktree")
        try:
            run_command(["git", "worktree", "remove", str(feature_worktree_path), "--force"])
            tracker.complete("worktree", f"removed {feature_worktree_path}")
        except Exception as exc:
            tracker.error("worktree", str(exc))
            console.print(tracker.render())
            console.print(f"\n[yellow]Warning:[/yellow] Could not remove worktree.")
            console.print(f"Run manually: git worktree remove {feature_worktree_path}")

    if delete_branch:
        tracker.start("branch")
        try:
            run_command(["git", "branch", "-d", current_branch])
            tracker.complete("branch", f"deleted {current_branch}")
        except Exception as exc:
            try:
                run_command(["git", "branch", "-D", current_branch])
                tracker.complete("branch", f"force deleted {current_branch}")
            except Exception:
                tracker.error("branch", str(exc))
                console.print(tracker.render())
                console.print(f"\n[yellow]Warning:[/yellow] Could not delete branch {current_branch}.")
                console.print(f"Run manually: git branch -d {current_branch}")

    console.print(tracker.render())
    console.print(f"\n[bold green]✓ Feature {current_branch} successfully merged into {target_branch}[/bold green]")
__all__ = ["merge"]
