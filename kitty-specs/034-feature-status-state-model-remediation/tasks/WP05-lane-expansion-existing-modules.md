---
work_package_id: WP05
title: Lane Expansion in Existing Modules
lane: "doing"
dependencies:
- WP01
base_branch: 2.x
base_commit: 1b37d3a7c2a626005000cff7b1dd2e76a87de203
created_at: '2026-02-08T14:31:49.889878+00:00'
subtasks:
- T022
- T023
- T024
- T025
- T026
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-wp05"
shell_pid: "42857"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 -- Lane Expansion in Existing Modules

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP05 --base WP01
```

This WP depends on WP01 (uses Lane enum as reference for the canonical 7-lane set). Branch from WP01's branch. WP05 can be implemented in parallel with WP02 and WP04.

---

## Objectives & Success Criteria

Expand the existing 4-lane model (`planned`, `doing`, `for_review`, `done`) to 7 canonical lanes (`planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`) throughout the codebase. This is the most impactful change to existing code -- every module that references lanes needs updating. This WP delivers:

1. Updated `LANES` tuple in `tasks_support.py` with 7 canonical lanes
2. `LANE_ALIASES` dict in `tasks_support.py` mapping `doing` to `in_progress`
3. Updated `valid_lanes` in `frontmatter.py` to accept all 7 canonical lanes plus `doing` as alias
4. Updated `ensure_lane()` to resolve aliases before validation
5. Codebase audit and update of all hardcoded 4-lane references
6. Updated tests for expanded lane validation

**Success**: All 7 lanes accepted in validation. `doing` alias resolves to `in_progress` everywhere. All existing tests still pass (updated where needed). No hardcoded 4-lane lists remain in the codebase.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- FR-007 (7-lane state machine), FR-011 (alias handling)
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- AD-3 (Transition Matrix), Integration Points table
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- Lane enum, Aliases section

**Key constraints**:
- Old LANES: `("planned", "doing", "for_review", "done")`
- New LANES: `("planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled")`
- `doing` must remain accepted at all input boundaries (backward compatibility)
- `doing` must NEVER be persisted -- always resolved to `in_progress` before writing
- `tasks_support.py` is marked DEPRECATED but still actively used -- update it
- Existing tests that assert on the 4-lane set must be updated to 7 lanes
- No breaking changes to existing CLI behavior

**Existing code to modify**:
- `src/specify_cli/tasks_support.py` -- LANES tuple, `ensure_lane()` function
- `src/specify_cli/frontmatter.py` -- `validate()` method lane checking
- `src/specify_cli/agent_utils/status.py` -- lane references in status display
- `src/specify_cli/merge/status_resolver.py` -- `LANE_PRIORITY` dict
- Various test files that assert on lane values

---

## Subtasks & Detailed Guidance

### Subtask T022 -- Update `src/specify_cli/tasks_support.py`

**Purpose**: Expand the LANES tuple from 4 canonical lanes to 7, and add the LANE_ALIASES map.

**Steps**:
1. Open `src/specify_cli/tasks_support.py`
2. Find the current LANES definition:
   ```python
   LANES: Tuple[str, ...] = ("planned", "doing", "for_review", "done")
   ```
3. Replace with:
   ```python
   LANES: Tuple[str, ...] = (
       "planned", "claimed", "in_progress", "for_review",
       "done", "blocked", "canceled",
   )
   LANE_ALIASES: Dict[str, str] = {"doing": "in_progress"}
   ```
4. Note that `doing` is removed from LANES and moved to LANE_ALIASES. The canonical lanes no longer include `doing`.

**Files**: `src/specify_cli/tasks_support.py` (modify existing)

**Validation**:
- `"claimed" in LANES` is True
- `"in_progress" in LANES` is True
- `"doing" in LANES` is False (it is an alias, not a canonical lane)
- `LANE_ALIASES["doing"]` returns `"in_progress"`

**Edge Cases**:
- Code that does `if lane in LANES` with `lane="doing"` will now return False -- this is correct, but callers need to resolve aliases first (handled in T024)
- The LANES tuple order matches the canonical lifecycle order for display purposes

---

### Subtask T023 -- Update `src/specify_cli/frontmatter.py`

**Purpose**: Expand the valid_lanes list in the frontmatter validation to accept all 7 canonical lanes plus `doing` as an accepted input alias.

**Steps**:
1. Open `src/specify_cli/frontmatter.py`
2. Find the `validate()` method in `FrontmatterManager` class
3. Locate the valid_lanes check. It may look like:
   ```python
   valid_lanes = ["planned", "doing", "for_review", "done"]
   ```
4. Replace with:
   ```python
   valid_lanes = [
       "planned", "claimed", "in_progress", "for_review",
       "done", "blocked", "canceled",
       "doing",  # Accepted alias for in_progress (backward compatibility)
   ]
   ```
5. The validation should accept `doing` as input (for backward compatibility with existing frontmatter files) but the system should resolve it to `in_progress` when processing.

**Files**: `src/specify_cli/frontmatter.py` (modify existing)

**Validation**:
- Frontmatter with `lane: claimed` passes validation
- Frontmatter with `lane: in_progress` passes validation
- Frontmatter with `lane: doing` passes validation (accepted alias)
- Frontmatter with `lane: blocked` passes validation
- Frontmatter with `lane: invalid_lane` fails validation

**Edge Cases**:
- Existing frontmatter files with `lane: doing` must not break -- they are valid input
- New frontmatter files should use canonical values, but the validator accepts both
- Case sensitivity: validation should be case-sensitive (lanes are lowercase)
- The `validate()` method may be called in multiple contexts -- check all call sites

---

### Subtask T024 -- Update `ensure_lane()` in tasks_support.py

**Purpose**: Make `ensure_lane()` resolve aliases before validating against the canonical LANES tuple.

**Steps**:
1. Find the `ensure_lane()` function in `tasks_support.py`. It likely validates that a lane value is in LANES.
2. Add alias resolution at the start:
   ```python
   def ensure_lane(lane: str) -> str:
       """Validate and normalize a lane value.

       Resolves aliases (e.g., 'doing' -> 'in_progress') before validation.
       Returns the canonical lane name.
       Raises TaskCliError if the lane is not valid.
       """
       normalized = lane.strip().lower()
       # Resolve alias
       resolved = LANE_ALIASES.get(normalized, normalized)
       if resolved not in LANES:
           raise TaskCliError(
               f"Invalid lane '{lane}'. Valid lanes: {', '.join(LANES)}"
           )
       return resolved
   ```
3. The return value is the canonical lane name (never the alias)
4. Update all callers of `ensure_lane()` to use the returned value (not the original input)

**Files**: `src/specify_cli/tasks_support.py` (modify existing)

**Validation**:
- `ensure_lane("doing")` returns `"in_progress"`
- `ensure_lane("claimed")` returns `"claimed"`
- `ensure_lane("in_progress")` returns `"in_progress"`
- `ensure_lane("DOING")` returns `"in_progress"` (case insensitive)
- `ensure_lane("invalid")` raises `TaskCliError`
- `ensure_lane("  doing  ")` returns `"in_progress"` (whitespace stripped)

**Edge Cases**:
- `ensure_lane("")` should raise TaskCliError (empty string is not a valid lane)
- `ensure_lane("Planned")` should return `"planned"` (case normalization)
- If `ensure_lane` currently does not return the lane value, add a return statement

---

### Subtask T025 -- Audit codebase for hardcoded lane references

**Purpose**: Find and update every hardcoded reference to the old 4-lane set throughout the codebase.

**Steps**:
1. Search for the old LANES tuple pattern:
   ```
   grep -rn '"doing"' src/specify_cli/
   grep -rn "'doing'" src/specify_cli/
   grep -rn "planned.*doing.*for_review.*done" src/specify_cli/
   grep -rn "LANE_PRIORITY" src/specify_cli/
   ```

2. Key files to check and update:

   **`src/specify_cli/agent_utils/status.py`**:
   - Find lane references in status display functions
   - Update any hardcoded lane lists to use the 7-lane set
   - Ensure display functions handle new lanes (`claimed`, `blocked`, `canceled`)
   - Update kanban board column definitions if they reference 4 lanes

   **`src/specify_cli/merge/status_resolver.py`**:
   - Find `LANE_PRIORITY` dict
   - Current: `{"done": 4, "for_review": 3, "doing": 2, "planned": 1}`
   - Update to include all 7 lanes:
     ```python
     LANE_PRIORITY: Dict[str, int] = {
         "canceled": 0,
         "blocked": 1,
         "planned": 2,
         "claimed": 3,
         "in_progress": 4,
         "for_review": 5,
         "done": 6,
     }
     ```
   - Note: The priority values may need adjustment based on rollback-aware logic (WP10 will further refine this). For now, establish the 7-lane mapping.
   - Add `"doing"` alias handling in the resolver if it reads lane values from frontmatter

   **`src/specify_cli/cli/commands/agent/tasks.py`**:
   - Check `move_task()` for hardcoded lane references
   - Verify `ensure_lane()` calls use the return value

   **Other files to scan**:
   - `src/specify_cli/cli/commands/agent/workflow.py`
   - `src/specify_cli/core/worktree_topology.py`
   - Any file importing `LANES` from `tasks_support`

3. For each hardcoded reference found:
   - If it is a validation check: update to include 7 lanes + alias
   - If it is a display/formatting: add new lanes to the display
   - If it is a priority/ordering: establish 7-lane ordering
   - If it references `"doing"` as a canonical value: change to `"in_progress"` and add alias handling where needed

**Files**: Multiple existing files (see list above)

**Validation**:
- `grep -rn '"doing"' src/specify_cli/` should show only alias-handling code, not usage as a canonical lane value
- All modified files still pass their existing tests (after test updates in T026)

**Edge Cases**:
- Template files (`.md`) may contain `doing` as documentation -- these may or may not need updating
- Migration files may reference old lane values for backward compatibility -- leave these as-is
- Test files will be updated in T026

---

### Subtask T026 -- Tests for expanded lane validation

**Purpose**: Update existing tests that assert on the 4-lane set, and add new tests for the expanded 7-lane model.

**Steps**:
1. Find existing tests that reference the old LANES tuple:
   ```
   grep -rn "LANES" tests/
   grep -rn '"doing"' tests/
   grep -rn "'doing'" tests/
   ```

2. Update tests that assert `LANES == ("planned", "doing", "for_review", "done")` to expect the new 7-lane tuple

3. Add new tests (can go in existing test files or a new file `tests/specify_cli/status/test_lane_expansion.py`):

   - `test_lanes_tuple_has_seven_values` -- `len(LANES) == 7`
   - `test_lanes_tuple_values` -- exact match on all 7 values
   - `test_doing_not_in_lanes` -- `"doing" not in LANES`
   - `test_doing_in_aliases` -- `"doing" in LANE_ALIASES`
   - `test_ensure_lane_doing_resolves` -- `ensure_lane("doing") == "in_progress"`
   - `test_ensure_lane_claimed_valid` -- `ensure_lane("claimed") == "claimed"`
   - `test_ensure_lane_blocked_valid` -- `ensure_lane("blocked") == "blocked"`
   - `test_ensure_lane_canceled_valid` -- `ensure_lane("canceled") == "canceled"`
   - `test_ensure_lane_invalid_raises` -- `ensure_lane("nonexistent")` raises `TaskCliError`
   - `test_ensure_lane_case_insensitive` -- `ensure_lane("DOING") == "in_progress"`
   - `test_frontmatter_validates_all_seven_lanes` -- each canonical lane passes validation
   - `test_frontmatter_validates_doing_alias` -- `doing` passes validation
   - `test_frontmatter_rejects_invalid_lane` -- `invalid_lane` fails validation
   - `test_lane_priority_has_seven_entries` -- `len(LANE_PRIORITY) == 7`
   - `test_lane_priority_includes_new_lanes` -- `claimed`, `blocked`, `canceled` all present

4. Update existing tests that may break due to lane changes:
   - Tests using `"doing"` as a lane value may need updating to `"in_progress"` where they test canonical behavior
   - Tests verifying display output may need updating to include new lanes
   - Tests for move_task that use `--to doing` should still work (alias resolution)

**Files**: Various test files (new and existing)

**Validation**: `python -m pytest tests/ -x -q` -- all tests pass (no regressions)

**Edge Cases**:
- Parametrized tests over lanes: add new lanes to parameter lists
- Snapshot tests (if any) that capture lane output: update expected output
- Integration tests that create WPs with specific lanes: verify new lanes work end-to-end

---

## Test Strategy

**Required per user requirements**: Tests verifying lane expansion and backward compatibility.

- **Coverage target**: All modified functions in tasks_support.py, frontmatter.py, and agent_utils/status.py
- **Test runner**: `python -m pytest tests/ -x -q` (full suite to catch regressions)
- **Backward compatibility**: `doing` alias must work everywhere it worked before
- **Regression testing**: Run the full test suite after changes to catch unexpected breakage
- **Audit verification**: After T025, re-grep for hardcoded lane references to confirm none remain

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing tests | CI failure | Update all tests that assert on 4-lane set; run full suite |
| Hardcoded `"doing"` in agent templates | Slash commands break | Templates accept `doing` as alias; audit all `.md` templates in command-templates/ |
| LANE_PRIORITY values wrong | Merge behavior changes | Initial 7-lane priority is placeholder; WP10 refines with rollback-aware logic |
| Missing a hardcoded reference | Silent bug | Thorough grep + manual audit of key files |
| `ensure_lane()` callers ignoring return value | Alias not resolved | Check all call sites use the returned canonical value |

---

## Review Guidance

- **Check LANES tuple**: Exactly 7 values, `doing` NOT included (it is in LANE_ALIASES)
- **Check ensure_lane()**: Returns canonical value, resolves aliases, handles case/whitespace
- **Check frontmatter.py**: valid_lanes includes all 7 canonical lanes PLUS `doing` as accepted alias
- **Check LANE_PRIORITY**: All 7 lanes present with reasonable ordering
- **Check codebase audit completeness**: Run `grep -rn '"doing"' src/specify_cli/` and verify only alias-handling code remains
- **Check test updates**: All tests that previously asserted 4-lane behavior now assert 7-lane behavior
- **No fallback mechanisms**: Invalid lane values cause errors, not silent defaults
- **Backward compatibility**: `doing` accepted everywhere as input, resolved to `in_progress` as output

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T14:31:50Z – claude-wp05 – shell_pid=42857 – lane=doing – Assigned agent via workflow command
