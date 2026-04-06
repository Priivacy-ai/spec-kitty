---
work_package_id: WP01
title: Persisted Review Artifact Model
dependencies: []
requirement_refs:
- C-001
- FR-003
- FR-004
- FR-005
- FR-006
- FR-016
- NFR-002
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- timestamp: '2026-04-06T16:32:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/artifacts.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/__init__.py
- src/specify_cli/review/artifacts.py
- tests/review/__init__.py
- tests/review/test_artifacts.py
---

# WP01: Persisted Review Artifact Model

## Objective

Move review feedback persistence from ephemeral `.git/spec-kitty/feedback/` to committed, versioned artifacts at `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md`. Add backward-compatible pointer resolution so pre-066 `feedback://` pointers continue resolving.

**Issues**: [#432](https://github.com/Priivacy-ai/spec-kitty/issues/432), storage side of [#433](https://github.com/Priivacy-ai/spec-kitty/issues/433)

## Context

### Current State

Review feedback is written to `.git/spec-kitty/feedback/{mission_slug}/{task_id}/{timestamp}-{uuid}.md` by `_persist_review_feedback()` at `src/specify_cli/cli/commands/agent/tasks.py:245-265`. This location is:
- Git-internal (not committed)
- Not versioned (unique timestamp filenames, no cycle numbering)
- Not visible across clones or sessions
- Referenced via `feedback://{mission_slug}/{task_id}/{filename}` pointer in StatusEvent.review_ref

### Target State

New review feedback artifacts live at `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md`:
- Committed to the repository
- Versioned with incrementing cycle numbers
- Visible across clones and sessions
- Machine-parseable YAML frontmatter with structured fields
- Referenced via `review-cycle://{mission_slug}/{wp_slug}/review-cycle-{N}.md` pointer

### Integration Points

This WP also modifies two functions in existing files (not exclusively owned — cross-lane modifications resolved at merge time):
- `_persist_review_feedback()` in `tasks.py` (lines 245-265): rewrite to create ReviewCycleArtifact
- `_resolve_review_feedback_pointer()` in `workflow.py` (lines 87-100): add dual resolution

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktree: allocated per lane by `lanes.json` after finalize-tasks

## Subtask Details

### T001: Create review module scaffold

**Purpose**: Establish the new `src/specify_cli/review/` module that all WPs in this mission will contribute to.

**Steps**:
1. Create `src/specify_cli/review/__init__.py` with public API exports:
   ```python
   from specify_cli.review.artifacts import (
       AffectedFile,
       ReviewCycleArtifact,
   )
   __all__ = ["AffectedFile", "ReviewCycleArtifact"]
   ```
2. Create `src/specify_cli/review/artifacts.py` with two frozen dataclasses:

   ```python
   @dataclass(frozen=True)
   class AffectedFile:
       path: str                    # relative to repo root
       line_range: str | None = None  # "start-end" or None
   ```

   ```python
   @dataclass(frozen=True)
   class ReviewCycleArtifact:
       cycle_number: int
       wp_id: str
       mission_slug: str
       reviewer_agent: str
       verdict: str               # "rejected" | "approved"
       reviewed_at: str           # ISO 8601 UTC
       affected_files: list[AffectedFile]
       reproduction_command: str | None = None
       body: str = ""             # markdown body (not in frontmatter)
   ```

3. Follow existing patterns from `src/specify_cli/status/models.py`:
   - Frozen dataclasses
   - `to_dict()` / `from_dict()` class methods
   - Sorted dict keys in `to_dict()` for deterministic serialization

4. Create `tests/review/__init__.py` (empty) and `tests/review/test_artifacts.py` (skeleton).

**Files**: `src/specify_cli/review/__init__.py` (new), `src/specify_cli/review/artifacts.py` (new), `tests/review/__init__.py` (new), `tests/review/test_artifacts.py` (new)

### T002: Implement write() for ReviewCycleArtifact

**Purpose**: Render a ReviewCycleArtifact to disk as a markdown file with YAML frontmatter.

**Steps**:
1. Add `write(self, path: Path) -> None` method to ReviewCycleArtifact
2. Use `ruamel.yaml` (already a project dependency) to render frontmatter:
   ```yaml
   ---
   cycle_number: 1
   wp_id: WP01
   mission_slug: "066-review-loop-stabilization"
   reviewer_agent: "claude"
   verdict: "rejected"
   reviewed_at: "2026-04-06T12:00:00Z"
   affected_files:
     - path: "src/specify_cli/cli/commands/agent/tasks.py"
       line_range: "245-265"
   reproduction_command: "pytest tests/agent/test_review_feedback_pointer_2x_unit.py -x"
   ---
   ```
3. Write body after the closing `---` separator
4. Ensure parent directory exists (`path.parent.mkdir(parents=True, exist_ok=True)`)
5. Use `ruamel.yaml.YAML()` with `yaml.preserve_quotes = True` for consistent output

**Validation**: Round-trip test — write artifact, read back, compare all fields.

### T003: Implement from_file() and latest()

**Purpose**: Parse existing review-cycle artifacts from disk and find the latest one.

**Steps**:
1. Add `@classmethod from_file(cls, path: Path) -> ReviewCycleArtifact`:
   - Read file content
   - Split on `---` delimiters to extract frontmatter and body
   - Parse YAML frontmatter with ruamel.yaml
   - Construct AffectedFile list from `affected_files` field
   - Return populated ReviewCycleArtifact

2. Add `@staticmethod latest(sub_artifact_dir: Path) -> ReviewCycleArtifact | None`:
   - Glob for `review-cycle-*.md` in the directory
   - If none found, return None
   - Sort by cycle number (extract N from `review-cycle-{N}.md`)
   - Parse and return the highest-numbered artifact

3. Add `@staticmethod next_cycle_number(sub_artifact_dir: Path) -> int`:
   - Count existing `review-cycle-*.md` files
   - Return count + 1

**Edge cases**:
- Empty directory → `latest()` returns None, `next_cycle_number()` returns 1
- Corrupted frontmatter → raise with clear error message including file path
- Missing optional fields (reproduction_command) → default to None

### T004: Rewrite _persist_review_feedback()

**Purpose**: Replace the current function that copies files to `.git/` with one that creates ReviewCycleArtifacts.

**Steps**:
1. In `tasks.py`, modify `_persist_review_feedback()` (lines 245-265):
   - Keep the same function signature for backward compatibility: `(main_repo_root, mission_slug, task_id, feedback_source) -> (Path, str)`
   - Add new parameters: `reviewer_agent: str`, `affected_files: list[dict] | None = None`
   - Read the feedback source file content (this becomes the artifact body)
   - Resolve the WP sub-artifact directory: `kitty-specs/<mission>/tasks/<WP-slug>/`
   - Determine the WP slug from task_id (lookup in tasks directory)
   - Call `ReviewCycleArtifact.next_cycle_number()` to get cycle N
   - Create ReviewCycleArtifact with:
     - cycle_number = N
     - wp_id = task_id
     - mission_slug = mission_slug
     - reviewer_agent = reviewer_agent (or "unknown" if not provided)
     - verdict = "rejected"
     - reviewed_at = current UTC timestamp
     - affected_files = parsed from feedback or empty list
     - body = feedback file content
   - Write artifact to `review-cycle-{N}.md`
   - Return `(persisted_path, "review-cycle://{mission_slug}/{wp_slug}/review-cycle-{N}.md")`

2. Update callers of `_persist_review_feedback()` in move_task() (around line 977-990) to pass `reviewer_agent` from the `--agent` flag.

**Critical**: Do NOT delete the old `.git/spec-kitty/feedback/` directory or its contents. Legacy data stays where it is.

### T005: Update _resolve_review_feedback_pointer()

**Purpose**: Add dual resolution so both legacy `feedback://` and new `review-cycle://` pointers resolve to real file paths.

**Steps**:
1. In `workflow.py`, modify `_resolve_review_feedback_pointer()` (lines 87-100):
   - Current logic: parse `feedback://mission/task/filename` → `.git/spec-kitty/feedback/mission/task/filename`
   - Add new branch: parse `review-cycle://mission/wp_slug/review-cycle-N.md` → `kitty-specs/mission/tasks/wp_slug/review-cycle-N.md`
   - Return None if format is unrecognized or file doesn't exist

2. Pattern matching:
   ```python
   if pointer.startswith("review-cycle://"):
       parts = pointer[len("review-cycle://"):].split("/", 2)
       # mission_slug / wp_slug / filename
       return repo_root / "kitty-specs" / parts[0] / "tasks" / parts[1] / parts[2]
   elif pointer.startswith("feedback://"):
       # existing legacy logic unchanged
       ...
   ```

3. Handle edge case: `"force-override"` string (existing behavior, not a pointer — return None)

**Validation**: Test with both pointer formats. Test with malformed pointers. Test with non-existent files.

### T006: Write tests

**Purpose**: Comprehensive test coverage for the review artifact model.

**Test file**: `tests/review/test_artifacts.py`

**Required test cases**:
1. `test_review_cycle_artifact_to_dict_round_trip` — create artifact, to_dict, from_dict, compare
2. `test_write_and_from_file_round_trip` — write to temp dir, read back, compare all fields including body
3. `test_next_cycle_number_empty_dir` — returns 1
4. `test_next_cycle_number_with_existing` — create 3 files, returns 4
5. `test_latest_empty_dir` — returns None
6. `test_latest_with_multiple` — returns highest cycle number
7. `test_affected_file_optional_line_range` — line_range can be None
8. `test_frontmatter_field_completeness` — all required fields present in written file
9. `test_legacy_feedback_pointer_resolution` — `feedback://` resolves to `.git/` path
10. `test_new_review_cycle_pointer_resolution` — `review-cycle://` resolves to `kitty-specs/` path
11. `test_force_override_pointer_returns_none` — `"force-override"` string returns None
12. `test_persist_review_feedback_creates_artifact` — call rewritten function, verify artifact file exists

**Coverage target**: 90%+ for `src/specify_cli/review/artifacts.py`

## Definition of Done

- [ ] ReviewCycleArtifact and AffectedFile dataclasses pass mypy --strict
- [ ] write() / from_file() round-trip preserves all fields including body
- [ ] _persist_review_feedback() creates committed artifacts in kitty-specs/
- [ ] Legacy feedback:// pointers still resolve correctly
- [ ] New review-cycle:// pointers resolve correctly
- [ ] 90%+ test coverage on review/artifacts.py
- [ ] All existing tests pass (no regressions)

## Reviewer Guidance

- Verify frontmatter field order is deterministic (ruamel.yaml should handle this)
- Check that cycle number derivation is filesystem-count-based, not event-log-based
- Verify legacy pointer resolution works with actual `.git/spec-kitty/feedback/` paths
- Confirm no writes to `.git/` in the new code path
