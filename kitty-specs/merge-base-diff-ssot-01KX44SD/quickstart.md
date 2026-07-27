# Quickstart: canonical merge-base/diff surface

## Using the surface

```python
from specify_cli.core.vcs.git import (
    git_merge_base,
    git_diff_names,
    merge_base_changed_files,
)

# HEAD-relative changed files vs a base branch (the common case)
changed = merge_base_changed_files(worktree, base_branch)          # tuple[str, ...]
spec_changes = merge_base_changed_files(worktree, base_branch, pathspec="kitty-specs/")

# Explicit two-ref comparison (e.g. lane vs mission, neither is HEAD)
mb = git_merge_base(repo_root, lane_branch, mission_branch)         # str | None
if mb is not None:
    files = set(git_diff_names(repo_root, mb, mission_branch))      # adapt tuple -> set

# Inspect commits HEAD is behind on (branch, not HEAD, is the diff target)
mb = git_merge_base(repo_root, "HEAD", check_branch)
upstream = git_diff_names(repo_root, mb, check_branch) if mb else ()
```

## Verifying the consolidation

```bash
# 1. No inline merge-base copies remain among the 4 sites (NFR-002 / SC-001)
grep -rn "git\", \"merge-base" src/specify_cli/lanes/stale_check.py \
  src/specify_cli/cli/commands/agent/tasks_move_task.py \
  src/specify_cli/cli/commands/agent/tasks_shared.py \
  src/specify_cli/cli/commands/agent/tasks_dependency_graph.py
# → expect zero matches (all route through core/vcs/git.py)

# 2. Behaviour unchanged (NFR-001 / SC-002): full suite green, no expected-value edits
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider

# 3. Helper branches proven directly (FR-006 / SC-003)
pytest tests/ -k "merge_base or diff_names or changed_files" -q

# 4. Gate cleanliness
ruff check . && mypy src/specify_cli/core/vcs/git.py
pytest tests/architectural/test_no_legacy_terminology.py -q
```

## Definition of done (mission)

- FR-001–FR-006 satisfied; FR-007 done or explicitly deferred to a follow-up WP.
- SC-001 (single implementation), SC-002 (zero behaviour change), SC-003 (direct branch coverage) all verified.
- `tests/architectural/` sweep + terminology guard green; ruff/mypy clean.
