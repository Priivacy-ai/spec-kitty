"""Pre-commit hook installer for worktrees.

Installs a Python-based pre-commit hook that invokes the commit guard.
Handles the git worktree .git file indirection correctly.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

HOOK_SCRIPT = """\
#!/bin/sh
# Spec Kitty commit guard — auto-installed by spec-kitty implement
# Validates staged files against WP ownership and protected paths.
python -m specify_cli.policy.commit_guard_hook "$@"
exit_code=$?
if [ $exit_code -ne 0 ]; then
    exit $exit_code
fi
"""


def install_commit_guard(worktree_path: Path, repo_root: Path) -> Path | None:
    """Install pre-commit hook into a worktree.

    Resolves the worktree's git hooks directory via `git rev-parse --git-dir`
    and writes the hook script there. Idempotent — overwrites existing hook.

    Args:
        worktree_path: Path to the worktree.
        repo_root: Path to the main repository.

    Returns:
        Path to the installed hook, or None if installation failed.
    """
    # Resolve the git directory for this worktree.
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = worktree_path / git_dir

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(HOOK_SCRIPT, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

    return hook_path
