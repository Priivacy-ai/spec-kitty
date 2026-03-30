# Git Operations Matrix

Complete matrix of every git command spec-kitty executes and every git
command agents are expected to run.

## Python-Executed Git Commands

| Command | When | Source File | Function |
|---|---|---|---|
| `git worktree add -b <branch> <path> [base]` | `spec-kitty implement WP##` | `core/vcs/git.py` | `create_workspace()` |
| `git config core.sparseCheckout true` | After worktree creation | `core/vcs/git.py` | `create_workspace()` |
| `git read-tree -mu HEAD` | Sparse checkout setup | `core/vcs/git.py` | `create_workspace()` |
| `git add -f kitty-specs/<mission>/` | Before worktree creation (auto-commit) | `cli/commands/implement.py` | `_ensure_planning_artifacts_committed_git()` |
| `git commit -m "chore: Planning..."` | Before worktree creation (auto-commit) | `cli/commands/implement.py` | `_ensure_planning_artifacts_committed_git()` |
| `git stash` | Lane transition safe-commit | `git/commit_helpers.py` | `safe_commit()` |
| `git add <wp-file>` | Lane transition safe-commit | `git/commit_helpers.py` | `safe_commit()` |
| `git commit -m "chore: Start WP##..."` | Lane transition safe-commit | `git/commit_helpers.py` | `safe_commit()` |
| `git stash pop` | Lane transition safe-commit | `git/commit_helpers.py` | `safe_commit()` |
| `git fetch origin <branch>` | Pre-flight (non-fatal) | `merge/preflight.py` | `run_preflight()` |
| `git status --porcelain` | Pre-flight worktree check | `merge/preflight.py` | `check_worktree_status()` |
| `git rev-list --left-right --count` | Pre-flight divergence check | `merge/preflight.py` | `run_preflight()` |
| `git rev-parse --verify <branch>` | Pre-flight branch check | `merge/preflight.py` | `run_preflight()` |
| `git checkout <target>` | Merge execution | `merge/executor.py` | `execute_merge()` |
| `git pull --ff-only` | Merge execution (if tracking) | `merge/executor.py` | `execute_merge()` |
| `git merge --no-ff <wp-branch>` | Merge execution (default strategy) | `merge/executor.py` | `execute_merge()` |
| `git merge --squash <wp-branch>` | Merge execution (squash strategy) | `merge/executor.py` | `execute_merge()` |
| `git rebase <wp-branch>` | Merge execution (rebase strategy) | `merge/executor.py` | `execute_merge()` |
| `git push origin <target>` | Merge execution (opt-in `--push`) | `merge/executor.py` | `execute_merge()` |
| `git worktree remove <path> --force` | After successful merge | `merge/executor.py` | `execute_merge()` |
| `git branch -d <wp-branch>` | After successful merge | `merge/executor.py` | `execute_merge()` |
| `git rev-list --count <base>..HEAD` | Topology analysis (read-only) | `core/worktree_topology.py` | `_count_commits_ahead()` |
| `git worktree list` | Worktree discovery | `core/worktree_topology.py` | `discover_worktrees()` |
| `git rev-parse --show-toplevel` | Repo root detection | Multiple files | Various |
| `git branch --show-current` | Branch detection | `core/mission_detection.py` | `_detect_from_branch()` |

## Agent-Expected Git Commands

| Command | When | Why |
|---|---|---|
| `git add <files>` | After writing implementation code | Stage deliverables |
| `git commit -m "feat(WP##): ..."` | After implementation work | Record changes |
| `git rebase <base-branch>` | When base WP has new changes | Sync dependent WP |
| `git merge <other-wp-branch>` | Multi-parent dependency | Manual merge second parent |
| `git add . && git rebase --continue` | During rebase conflict resolution | Complete rebase |
| `git push origin <branch>` | When explicitly asked by user | Publish changes |

## Operations Nobody Should Do

| Anti-Pattern | Why Not |
|---|---|
| `git worktree add` (manual) | No workspace context, no sparse checkout, wrong branch naming |
| `git commit` in main repo during implementation | Implementation belongs in worktree |
| `git push` without user request | Never auto-push |
| `git checkout` in worktree to another branch | Breaks worktree isolation |
| Edit `.git/hooks/` | Spec-kitty doesn't use hooks (codec layer instead) |
| `git reset --hard` in worktree | Destroys agent work without recovery |
