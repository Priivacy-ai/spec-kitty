---
work_package_id: WP03
title: External Reviewer Handoff
dependencies: []
requirement_refs:
- C-002
- C-003
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-066-review-loop-stabilization
base_commit: 4dbb05e1ae46b17dad6ae64402cfb2861107f268
created_at: '2026-04-06T16:42:31.077898+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
shell_pid: "53389"
agent: "claude:opus-4-6:reviewer:reviewer"
history:
- timestamp: '2026-04-06T16:32:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/dirty_classifier.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/dirty_classifier.py
- tests/review/test_dirty_classifier.py
- tests/integration/test_review_handoff.py
---

# WP03: External Reviewer Handoff

## Objective

Make review handoff self-contained for external reviewers by implementing dirty-state classification (blocking vs. benign) and surfacing a writable in-repo feedback path in the review prompt.

**Issues**: [#439](https://github.com/Priivacy-ai/spec-kitty/issues/439)
**Dependencies**: None (independent of WP01/WP02)

## Context

### Current Problem

`_validate_ready_for_review()` in `tasks.py` (lines 468-750) treats any dirty file as blocking. The only escape is `--force`, which disables ALL validation (tasks.py lines 491-492: early return, no checks at all). There is no middle ground.

When multiple agents work concurrently, status artifacts (`status.events.jsonl`, `status.json`), other WPs' task files, and generated metadata are frequently dirty for legitimate reasons. External reviewers cannot complete the reject-with-feedback flow without the orchestrator manually handling dirty-state issues.

### Target Behavior

A classification layer partitions `git status --porcelain` output by path pattern and WP ownership:
- **Blocking**: uncommitted changes to files owned by the current WP (source files in worktree, WP's own task file)
- **Benign**: status artifacts, other WPs' task files, generated metadata

Review handoff succeeds without `--force` when only benign files are dirty.

### Integration Points

This WP modifies `_validate_ready_for_review()` in `tasks.py` (lines 468-750), which is ~200 lines away from WP01's changes to `_persist_review_feedback()` (lines 245-265). No shared helper calls — parallel execution is safe per plan merge coordination.

Also modifies the review prompt in `workflow.py` to surface the writable feedback path.

### WP01 Interaction

WP03 changes where the review prompt tells the reviewer to write. The `--review-feedback-file` flag still accepts any path — the reviewer writes to the in-repo path, and `move-task` reads from it. If WP01 hasn't landed yet, `move-task` persists to `.git/` (old behavior). After WP01 lands, `move-task` persists to the same in-repo location. The convergence is natural and requires no coordination beyond using the same path convention.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktree: allocated per lane (independent lane from Track A)

## Subtask Details

### T012: Create dirty_classifier.py

**Purpose**: Core classification logic in a standalone module.

**Steps**:
1. Create `src/specify_cli/review/dirty_classifier.py`
2. Define the main function:
   ```python
   def classify_dirty_paths(
       dirty_paths: list[str],
       wp_id: str,
       mission_slug: str,
       wp_slug: str | None = None,
   ) -> tuple[list[str], list[str]]:
       """Classify dirty paths as blocking or benign.

       Args:
           dirty_paths: Paths from git status --porcelain (the file path portion)
           wp_id: Current WP ID (e.g., "WP01")
           mission_slug: Mission slug (e.g., "066-review-loop-stabilization")
           wp_slug: WP slug for task file matching (e.g., "WP01-persisted-review-artifact-model")

       Returns:
           (blocking, benign) — two lists of path strings
       """
   ```
3. Export from `src/specify_cli/review/__init__.py`

**Files**: `src/specify_cli/review/dirty_classifier.py` (new)

### T013: Implement classification rules

**Purpose**: Define the exact rules for blocking vs. benign classification.

**Steps**:
1. **Benign patterns** (these dirty paths should NOT block review handoff):
   ```python
   BENIGN_PATTERNS = [
       # Status model artifacts (updated by concurrent agents)
       "status.events.jsonl",
       "status.json",
       # Other WPs' task files (not this WP)
       # Matched dynamically: tasks/WP*.md where WP != wp_id
       # Generated metadata
       "meta.json",
       ".kittify/",
       # Lane/workspace state
       "lanes.json",
   ]
   ```

2. **Blocking logic**: A path is blocking if:
   - It is NOT matched by any benign pattern
   - AND it is either:
     - In the worktree's source tree (any file not under `kitty-specs/`)
     - OR it is this WP's own task file (`tasks/{wp_slug}.md`)

3. **Other WP task files**: A file matching `kitty-specs/<mission>/tasks/WP*.md` is benign UNLESS the WP ID in the filename matches `wp_id`. Implementation:
   ```python
   import re
   WP_TASK_PATTERN = re.compile(r"kitty-specs/.+/tasks/(WP\d+)-.+\.md$")
   match = WP_TASK_PATTERN.search(path)
   if match and match.group(1) != wp_id:
       return "benign"  # another WP's task file
   ```

4. Edge case: paths outside `kitty-specs/` that are NOT source files (e.g., `.gitignore`, `pyproject.toml`) — classify as blocking by default (conservative approach).

### T014: Update _validate_ready_for_review()

**Purpose**: Replace the "any dirty file blocks" logic with the classifier.

**Steps**:
1. In `tasks.py`, find the section in `_validate_ready_for_review()` that runs `git status --porcelain` and checks for dirty files (around lines 504-512 for planning repo, 654-697 for worktree)

2. **Planning repo dirtiness** (kitty-specs/ check):
   - Currently: treats any dirty file in `kitty-specs/` as blocking (with a filter for auto-committed files)
   - Replace with: call `classify_dirty_paths()` with the list of dirty paths
   - Only fail if `blocking` list is non-empty

3. **Worktree dirtiness** (source code check):
   - Currently: treats any staged/unstaged change as blocking
   - Keep this behavior — worktree source changes should still block review
   - The classifier only relaxes planning repo dirtiness

4. **Output formatting**:
   ```python
   blocking, benign = classify_dirty_paths(dirty_paths, wp_id, mission_slug, wp_slug)
   if blocking:
       guidance.append(f"Blocking: {len(blocking)} uncommitted file(s) owned by {wp_id}:")
       for p in blocking:
           guidance.append(f"  - {p}")
       guidance.append("Commit these files before moving to for_review.")
       return False, guidance
   if benign:
       # Info only — don't block
       console.print(f"[dim]Note: {len(benign)} unrelated dirty file(s) ignored (not owned by {wp_id})[/dim]")
   ```

5. **Preserve --force**: The early return at the top of the function when `force=True` stays unchanged.

### T015: Update review prompt — writable feedback path

**Purpose**: Replace the temp-file feedback path in the review prompt with a writable in-repo path.

**Steps**:
1. In `workflow.py` review() function (around lines 1205-1221), find where the feedback file path is surfaced:
   - Current: `review_feedback_path = f"/tmp/spec-kitty-review-feedback-{wp_id}.md"`
   - New: `review_feedback_path = f"kitty-specs/{mission_slug}/tasks/{wp_slug}/review-cycle-{next_cycle}.md"`

2. Determine `next_cycle` by counting existing `review-cycle-*.md` files in the sub-artifact directory (same logic as WP01's `next_cycle_number()`, but can be computed inline here)

3. Update the review instructions to explain the in-repo path:
   ```
   Write your feedback to: {review_feedback_path}
   Then run: spec-kitty agent tasks move-task {wp_id} --to planned --review-feedback-file {review_feedback_path} --mission {mission_slug}
   ```

4. If the sub-artifact directory doesn't exist yet, create it (WP01 may not have landed)

### T016: Write tests

**Purpose**: Test the classification rules and integration.

**Test files**: `tests/review/test_dirty_classifier.py`, `tests/integration/test_review_handoff.py`

**Unit tests** (test_dirty_classifier.py):
1. `test_empty_dirty_list` — returns ([], [])
2. `test_status_artifacts_are_benign` — status.events.jsonl, status.json classified as benign
3. `test_other_wp_task_files_are_benign` — WP02-*.md is benign when checking WP01
4. `test_own_task_file_is_blocking` — WP01-*.md is blocking when checking WP01
5. `test_source_files_are_blocking` — src/foo.py classified as blocking
6. `test_meta_json_is_benign` — meta.json classified as benign
7. `test_kittify_paths_are_benign` — .kittify/* classified as benign
8. `test_mixed_dirty_paths` — mix of blocking and benign, correct partition

**Integration tests** (test_review_handoff.py):
9. `test_validate_with_only_benign_dirtiness_passes` — should NOT block
10. `test_validate_with_blocking_dirtiness_fails` — should block with guidance
11. `test_validate_with_force_bypasses_all` — --force skips everything
12. `test_review_prompt_includes_in_repo_path` — writable path appears in review prompt

**Coverage target**: 90%+ for `src/specify_cli/review/dirty_classifier.py`

## Definition of Done

- [ ] classify_dirty_paths() correctly partitions blocking vs. benign
- [ ] _validate_ready_for_review() only blocks on blocking dirty files
- [ ] Review prompt surfaces writable in-repo feedback path
- [ ] --force escape hatch preserved unchanged
- [ ] Benign dirty files logged as info, not errors
- [ ] 90%+ test coverage on dirty_classifier.py
- [ ] All existing tests pass

## Reviewer Guidance

- Test with real multi-WP dirty state: run two WPs in different lanes, verify one's status changes don't block the other's review handoff
- Verify the classification regex handles edge cases (WP IDs with different digit counts: WP01 vs WP10)
- Check that the in-repo feedback path uses the correct WP slug (kebab-case), not just the WP ID

## Activity Log

- 2026-04-06T16:42:31Z – claude:sonnet-4-6:implementer:implementer – shell_pid=47989 – Started implementation via action command
- 2026-04-06T16:51:43Z – claude:sonnet-4-6:implementer:implementer – shell_pid=47989 – Ready for review: dirty-state classification implemented, all 16 tests pass (12 unit + 4 integration), 97% coverage on dirty_classifier.py
- 2026-04-06T16:52:08Z – claude:opus-4-6:reviewer:reviewer – shell_pid=53389 – Started review via action command
