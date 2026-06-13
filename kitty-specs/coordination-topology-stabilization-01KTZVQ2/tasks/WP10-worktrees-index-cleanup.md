---
work_package_id: WP10
title: .worktrees/ Index Cleanup
dependencies:
- WP01
- WP02
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T045
- T046
- T047
- T049
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "42546"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: .gitignore
execution_mode: code_change
owned_files:
- .gitignore
priority: P3-Medium
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Remove the 26 currently tracked `.worktrees/` paths from the git index (without deleting the files on disk). Verify `spec-kitty doctor` passes after cleanup. Test the IC-01/IC-02 interaction defect — specifically that `is_committed()` behavior is tested in both pre- and post-cleanup states.

**This WP depends on WP01 and WP02**: The writer fix (WP02) must be in place before cleanup, to prevent re-introduction. The coord-aware `is_committed()` (WP01) changes the gate behavior for these files post-cleanup.

---

## Context

### The Problem (Issue #1887, cleanup half)

`git ls-tree origin/main .worktrees/` reveals 26 tracked paths. These are artifacts from PR #1825 (squash commit 6518c852a) that used a `_feature_dir_file_paths` root anchor against the primary repo root instead of the coord-worktree root.

After WP02 lands (the writer fix), no new `.worktrees/` paths can enter the index. This WP removes the 26 already-tracked ones.

### IC-01/IC-02 Interaction Defect

The 26 tracked paths include `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H-coord/` artifacts committed via the coordination worktree. Before WP01:
- `is_committed("kitty-specs/.../spec.md", repo_root)` → TRUE (path is in primary HEAD index)

After cleanup (WP10 removes them):
- `is_committed("kitty-specs/.../spec.md", repo_root)` → FALSE (path removed from primary HEAD)
- `is_committed("kitty-specs/.../spec.md", repo_root, placement=...)` → TRUE (path is on coord branch)

This is the live demo of bug #1884 — WP10 flips the old behavior from "accidentally works" to "correctly requires WP01". Both states must be tested.

---

## Subtasks

### T045 — Remove 26 tracked `.worktrees/` paths via `git rm -r --cached`

1. Run `git ls-files .worktrees/` to list the exact paths.
2. Verify count is 26 (or current count — may have changed since investigation).
3. Run:
   ```bash
   git rm -r --cached .worktrees/
   ```
4. Confirm `.worktrees/` still exists on disk (files are not deleted, only removed from index).
5. Commit the removal with a descriptive message:
   ```
   fix: remove .worktrees/ paths from git index (#1887, WP10)

   These 26 paths were inadvertently tracked via the _feature_dir_file_paths
   root-anchor bug (fixed in WP02). Remove from index without deleting files.
   ```
6. Verify `git ls-files .worktrees/` returns empty after commit.

**IMPORTANT**: This commit changes `is_committed()` behavior for the legacy `do-dispatch-open-op-lifecycle-01KTSJ2H-coord` mission. After this commit, the old 2-arg `is_committed()` returns False for those files. WP01 must be in place for the 3-arg form to still return True via the coord-branch lookup. Coordinate the merge order with the user.

### T046 — Verify `spec-kitty doctor` passes after cleanup

1. After the T045 commit, run:
   ```bash
   .venv/bin/spec-kitty doctor --json
   ```
2. Assert output shows no errors related to `.worktrees/` paths.
3. Run:
   ```bash
   .venv/bin/spec-kitty doctor identity --json
   ```
4. Assert all missions have valid identity (the cleanup should not invalidate any mission IDs).
5. If doctor reports errors, investigate and fix before merging this WP.

### T049 — Remove xfail marker from `test_worktrees_index_clean.py` after WP02 ratchet lands

This subtask makes the architectural ratchet test active once the WP02 writer fix is in place.

1. Confirm WP02 has merged and `path_is_under_worktrees()` gates are active in `safe_commit`.
2. Open `tests/architectural/test_worktrees_index_clean.py` (created in WP02 T009).
3. Remove the `@pytest.mark.xfail(reason="WP10 cleanup pending")` decorator (or equivalent `pytest.skip` call).
4. Run the test: `pytest tests/architectural/test_worktrees_index_clean.py -v`
5. If it fails, the T045 cleanup has not landed yet — coordinate with the user before removing the marker.
6. Once the test passes without the xfail marker, commit:
   ```
   test: activate test_worktrees_index_clean ratchet — WP02+WP10 complete
   ```

**Note**: This subtask intentionally comes after T045 (index cleanup) and T046 (doctor verification). Do not remove the xfail marker until T045 has been committed and verified.

### T047 — Verify `is_committed` interaction defect in both states

Extend `tests/specify_cli/test_worktrees_index.py` (from WP02) with:

1. **Pre-cleanup state test** (uses a fixture that simulates the 26 tracked paths in the primary index):
   - `is_committed(spec_path, repo_root)` → True (path is in primary HEAD — the "accidentally works" state)
   - `is_committed(spec_path, repo_root, placement=coord_placement)` → True (works via coord branch)

2. **Post-cleanup state test** (simulates after `git rm -r --cached`):
   - `is_committed(spec_path, repo_root)` → False (path removed from primary HEAD)
   - `is_committed(spec_path, repo_root, placement=coord_placement)` → True (WP01 fix makes this work)

3. The tests document the interaction defect and confirm WP01 + WP10 together produce the correct behavior.

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
# Only after WP01 and WP02 are approved/done:
spec-kitty agent action implement WP10 --agent <name>
```

---

## Definition of Done

- [ ] `git ls-files .worktrees/` returns empty after commit
- [ ] Files on disk in `.worktrees/` are NOT deleted (only removed from index)
- [ ] `spec-kitty doctor --json` passes (no new errors)
- [ ] `spec-kitty doctor identity --json` passes
- [ ] `test_worktrees_index_clean.py` ratchet test now passes (xfail marker removed, T049)
- [ ] `test_worktrees_index.py` has both pre- and post-cleanup state tests
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues

## Risks

- **Merge order**: This WP MUST merge AFTER WP01 and WP02. Merging WP10 first breaks the `is_committed()` gate for the legacy mission until WP01 is in place.
- **Commit count**: Verify the count of 26 tracked paths before the PR. If the count has changed (due to other PRs), update the commit message.
- **`.gitignore`**: Consider adding `.worktrees/` to `.gitignore` as an additional guard. Confirm it doesn't conflict with any intentionally tracked worktree metadata.

## Activity Log

- 2026-06-13T08:16:43Z – claude:sonnet-4-6:implementer:implementer – shell_pid=19728 – Assigned agent via action command
- 2026-06-13T08:22:08Z – claude:sonnet-4-6:implementer:implementer – shell_pid=19728 – Ready for review: 48 .worktrees/ paths removed (was 26 original + 22 from coord-worktree itself), .gitignore already had .worktrees/ at line 58, ratchet test now hard-passing
- 2026-06-13T08:22:41Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=42546 – Started review via action command
- 2026-06-13T08:24:03Z – user – shell_pid=42546 – Review passed: 48 .worktrees/ paths untracked, .gitignore present, ratchet test hard-passing
