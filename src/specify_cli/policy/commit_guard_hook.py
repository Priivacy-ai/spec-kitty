"""Pre-commit hook entry point.

Invoked by the git pre-commit hook installed by hook_installer.py.
Reads staged files, detects WP context from branch name and lanes.json,
loads policy, and runs the commit guard.

Exit code 0 = allow, 1 = block.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run the commit guard. Returns exit code."""
    from specify_cli.policy.commit_guard import validate_staged_files
    from specify_cli.policy.config import load_policy_config

    # Find repo root.
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return 0  # Not in a git repo — allow

    worktree_root = Path(result.stdout.strip())

    # Find main repo root (for policy config).
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        capture_output=True, text=True,
    )
    repo_root = Path(result.stdout.strip()).parent if result.returncode == 0 else worktree_root

    # Get current branch.
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return 0
    branch = result.stdout.strip()

    # Get staged files.
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return 0
    staged = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    if not staged:
        return 0

    # Load policy.
    policy = load_policy_config(repo_root)
    if not policy.commit_guard.enabled or policy.commit_guard.mode == "off":
        return 0

    # Try to find owned_files from WP context.
    owned_files = _detect_owned_files(worktree_root, repo_root, branch)

    # Run guard.
    guard_result = validate_staged_files(staged, owned_files, branch, policy.commit_guard)

    if guard_result.warnings:
        for w in guard_result.warnings:
            print(f"[spec-kitty guard] WARNING: {w}", file=sys.stderr)

    if not guard_result.allowed:
        for v in guard_result.violations:
            print(f"[spec-kitty guard] BLOCKED: {v}", file=sys.stderr)
        print("[spec-kitty guard] Commit blocked by ownership policy.", file=sys.stderr)
        return 1

    return 0


def _detect_owned_files(
    worktree_root: Path, repo_root: Path, branch: str,
) -> list[str]:
    """Try to detect owned_files for the current WP from workspace context or lanes."""
    # Try workspace context.
    try:
        from specify_cli.workspace_context import list_contexts

        for ctx in list_contexts(repo_root):
            if ctx.branch_name == branch:
                # Found matching context — try to read WP frontmatter for owned_files.
                from specify_cli.frontmatter import read_frontmatter

                feature_dir = repo_root / "kitty-specs" / ctx.mission_slug
                tasks_dir = feature_dir / "tasks"
                wp_id = ctx.current_wp or ctx.wp_id
                for wp_file in tasks_dir.glob(f"{wp_id}*.md"):
                    fm, _ = read_frontmatter(wp_file)
                    owned = fm.get("owned_files", [])
                    if owned:
                        return list(owned)
    except Exception:
        pass

    return []


if __name__ == "__main__":
    sys.exit(main())
