---
work_package_id: WP02
title: .worktrees/ Writer Fix + Ratchet
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "95242"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/safe_commit.py
execution_mode: code_change
owned_files:
- src/specify_cli/merge/safe_commit.py
- src/specify_cli/bookkeeping/transaction.py
- tests/architectural/test_worktrees_index_clean.py
- tests/specify_cli/test_worktrees_index.py
priority: P1-Critical
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Stop `.worktrees/<coord>/` paths from entering the git index. Three defensive layers:

1. Fix `_feature_dir_file_paths` root anchor in `executor.py` (root cause).
2. Add `path_is_under_worktrees()` rejection gate in `safe_commit` (backstop).
3. Add `path_is_under_worktrees()` guard in `BookkeepingTransaction.write_artifact` (write-side backstop).
4. Add `tests/architectural/test_worktrees_index_clean.py` ratchet test.

**This WP does NOT remove the 26 already-tracked paths** — that is WP10, which can only land after this ratchet is in place and CI confirms green.

---

## Context

### The Bug (Issue #1887)

`_feature_dir_file_paths` in `executor.py:441` relativizes coordination-worktree paths against the PRIMARY repo root. Because the coordination worktree is a subdirectory of `.worktrees/`, the resulting relative paths include `.worktrees/...`. `git add --force` happily stages these, and `safe_commit` validates staged-vs-requested but not requested-vs-policy. The result: 26 `.worktrees/` paths appeared in `origin/main` (confirmed via `git ls-tree origin/main .worktrees/`).

### Existing Predicate

`path_is_under_worktrees(path, repo_root)` already exists at `merge.py:153`. Reuse it — do not re-implement.

### Root Fix Location

`executor.py:441` — `_feature_dir_file_paths`. The function computes paths relative to `repo_root` to pass to `safe_commit`. When `feature_dir` is inside `.worktrees/`, the relative paths are valid FROM the worktree checkout but should NOT be staged into the primary repo index. The fix is: detect when `feature_dir` is under `.worktrees/`, resolve the canonical equivalent path (relative to the coordination branch, not the primary checkout), and stage from that resolved path instead.

**Alternative approach** (also acceptable): raise `SafeCommitPathPolicyError` if any path in `_feature_dir_file_paths` would be under `.worktrees/` — and instead pass the coordination-branch path explicitly. The policy error is safer because it makes the caller fix the call site rather than silently mapping.

---

## Subtasks

### T006 — Fix `_feature_dir_file_paths` root anchor in `executor.py`

1. Read `src/specify_cli/merge/executor.py` lines 430–460 to understand the current root-anchor logic.
2. Read `src/specify_cli/merge/safe_commit.py` and `merge.py:153` for `path_is_under_worktrees`.
3. Add a guard at the top of `_feature_dir_file_paths` (or its call site): if `feature_dir` resolves to a path under `.worktrees/`, raise `SafeCommitPathPolicyError` with a clear message:
   ```
   safe_commit: refusing to stage path under .worktrees/: <path>.
   Planning artifacts must be committed from the coordination worktree, not the primary repo root.
   ```
4. The caller must pass the correct path (the coordination-branch-relative path) — do not silently remap.
5. Run `mypy --strict src/specify_cli/merge/executor.py` — zero issues.

### T007 — Add `path_is_under_worktrees()` rejection gate in `safe_commit`

1. Read `src/specify_cli/merge/safe_commit.py` in full.
2. Add a pre-stage check: before calling `git add --force` for each path, call `path_is_under_worktrees(path, repo_root)` and raise `SafeCommitPathPolicyError` if True.
3. The error message must name the offending path and the recovery action (commit from the coordination worktree).
4. `SafeCommitPathPolicyError` must be a new subclass of an appropriate existing exception class (check the existing hierarchy in `safe_commit.py` or a shared exceptions module).
5. Run `mypy --strict src/specify_cli/merge/safe_commit.py`.

### T008 — Add `path_is_under_worktrees()` guard in `BookkeepingTransaction.write_artifact`

1. Read `src/specify_cli/bookkeeping/transaction.py` for `write_artifact`.
2. Add a pre-write check: if the resolved output path is under `.worktrees/`, raise `SafeCommitPathPolicyError` before writing.
3. This guards against future callers that write bookkeeping artifacts to wrong locations.
4. Run `mypy --strict src/specify_cli/bookkeeping/transaction.py`.

### T009 — Architectural ratchet test: `git ls-files .worktrees/` must return empty

File: `tests/architectural/test_worktrees_index_clean.py` (new)

```python
import subprocess

def test_no_worktrees_paths_in_git_index():
    """No .worktrees/ paths may appear in the git index."""
    result = subprocess.run(
        ["git", "ls-files", ".worktrees/"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    assert lines == [], (
        f"Found {len(lines)} .worktrees/ path(s) in git index. "
        f"Run: git rm -r --cached .worktrees/\n"
        f"Paths: {lines[:5]!r}{'...' if len(lines) > 5 else ''}"
    )
```

**Note**: This test will FAIL until WP10 removes the 26 already-tracked paths. Mark it `xfail` with `reason="WP10 cleanup pending"` and the WP10 issue label, or skip it in CI until WP10 lands. Coordinate with the user before landing this test.

### T010 — Regression test for writer fix

File: `tests/specify_cli/test_worktrees_index.py` (new)

Write a pytest test that:
1. Creates a temporary git repo.
2. Creates a `.worktrees/test-coord/` subdirectory with a dummy file.
3. Calls `safe_commit` (or `_feature_dir_file_paths`) with a path pointing inside `.worktrees/`.
4. Asserts `SafeCommitPathPolicyError` is raised.
5. Asserts `git ls-files .worktrees/` returns empty (no paths staged).

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
spec-kitty agent action implement WP02 --agent <name>
```

---

## Definition of Done

- [ ] `_feature_dir_file_paths` raises `SafeCommitPathPolicyError` for `.worktrees/` paths
- [ ] `safe_commit` rejects `.worktrees/` paths before staging
- [ ] `BookkeepingTransaction.write_artifact` rejects `.worktrees/` output paths
- [ ] `test_worktrees_index_clean.py` present (xfail or skip until WP10)
- [ ] `test_worktrees_index.py` passes (regression)
- [ ] `mypy --strict` zero issues across all modified files
- [ ] `ruff check .` zero issues

## Risks

- **`xfail` test ordering**: The ratchet test must not cause CI to fail before WP10 cleanup lands. Coordinate with the user on the `xfail` strategy.
- **`path_is_under_worktrees` import**: Confirm the function is importable from `merge.py` or refactor to a shared utility before calling it from `safe_commit.py` and `transaction.py`.
- **`SafeCommitPathPolicyError` placement**: Define it in a shared location (`safe_commit.py` or a new `errors.py`) so both `executor.py` and `transaction.py` can import it without circular deps.

## Activity Log

- 2026-06-13T07:58:58Z – claude:sonnet-4-6:implementer:implementer – shell_pid=54877 – Assigned agent via action command
- 2026-06-13T08:07:29Z – claude:sonnet-4-6:implementer:implementer – shell_pid=54877 – Ready for review: .worktrees/ writer fix + rejection ratchet implemented
- 2026-06-13T08:07:45Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=95242 – Started review via action command
- 2026-06-13T08:16:09Z – user – shell_pid=95242 – Review passed: root anchor fixed in _feature_dir_file_paths, 3 guards present and live, ratchet test xfail pending WP10, 4 regression tests pass, 1 xfail as expected, 5 mypy errors are pre-existing baseline
