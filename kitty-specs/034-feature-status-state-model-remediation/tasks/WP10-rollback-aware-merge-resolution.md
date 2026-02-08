---
work_package_id: WP10
title: Rollback-Aware Merge Resolution
lane: "for_review"
dependencies:
- WP01
base_branch: 2.x
base_commit: 7b0568bbf9fdff75ed719178c6c9251012b4d0c2
created_at: '2026-02-08T14:48:44.131410+00:00'
subtasks:
- T048
- T049
- T050
- T051
- T052
phase: Phase 1 - Canonical Log
assignee: ''
agent: ''
shell_pid: "50709"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP10 -- Rollback-Aware Merge Resolution

## Review Feedback Status

> **IMPORTANT**: Before starting implementation, check the `review_status` field in this file's frontmatter.
> - If `review_status` is empty or `""`, proceed with implementation as described below.
> - If `review_status` is `"has_feedback"`, read the **Review Feedback** section below FIRST and address all feedback items before continuing.
> - If `review_status` is `"approved"`, this WP has been accepted -- no further implementation needed.

## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Replace the current monotonic "most done wins" conflict resolver in `merge/status_resolver.py` with rollback-aware logic that correctly handles reviewer rejections, and add JSONL event log merge support for `status.events.jsonl` files.

**This WP fixes the core bug identified in the PRD**: when a reviewer sends a WP back from `for_review` to `in_progress` on one branch while another branch concurrently moves it to `done`, the current resolver incorrectly picks `done` (higher priority) instead of honoring the reviewer's rollback.

**Success Criteria**:
1. A reviewer rollback (`for_review -> in_progress` with review_ref) takes precedence over concurrent forward progression during merge.
2. Non-conflicting WPs from different branches merge correctly without interference.
3. The existing monotonic "most done wins" behavior is preserved as a FALLBACK when no rollback is detected.
4. JSONL event log files (`status.events.jsonl`) can be merged: concatenate, deduplicate by event_id, sort.
5. The expanded 7-lane LANE_PRIORITY map includes all canonical lanes.
6. All existing merge/status_resolver tests continue to pass for non-rollback scenarios.

## Context & Constraints

**Architecture References**:
- `plan.md` AD-4 defines the rollback-aware conflict resolution algorithm.
- `research.md` R-4 documents the current monotonic behavior and its failure modes.
- `data-model.md` Transition Matrix shows reviewer rollback: `for_review -> in_progress`.
- `contracts/transition-matrix.json` specifies `conflict_resolution.strategy: "rollback_aware"`.

**Current Code** (from `src/specify_cli/merge/status_resolver.py`):
```python
LANE_PRIORITY = {
    "done": 4,
    "for_review": 3,
    "doing": 2,
    "planned": 1,
}
```
This is used in `resolve_lane_conflict()` to pick the "most done" lane when two branches disagree. This is the bug.

**Dependency Artifacts Available**:
- WP01 provides `status/models.py` with Lane enum, CANONICAL_LANES, and StatusEvent.
- WP03 provides `status/reducer.py` with event deduplication and sorting logic.

**Constraints**:
- The existing `parse_conflict_markers()`, `resolve_status_conflicts()`, `get_conflicted_files()`, and `is_status_file()` functions must not be broken.
- The resolver operates on git merge conflict markers, not on the event log directly. For frontmatter lane conflicts, it reads the "ours" and "theirs" lane values from conflict markers.
- JSONL merge support is a NEW capability -- currently no auto-resolution exists for `.jsonl` files.

**Implementation Command**: `spec-kitty implement WP10 --base WP03` (merge WP01 branch manually)

## Subtasks & Detailed Guidance

### T048: Update LANE_PRIORITY

**Purpose**: Expand the lane priority map to include all 7 canonical lanes.

**Steps**:
1. Open `src/specify_cli/merge/status_resolver.py`.
2. Replace the current `LANE_PRIORITY` dict:
   ```python
   # OLD:
   LANE_PRIORITY = {
       "done": 4,
       "for_review": 3,
       "doing": 2,
       "planned": 1,
   }

   # NEW:
   LANE_PRIORITY = {
       "planned": 1,
       "claimed": 2,
       "in_progress": 3,
       "for_review": 4,
       "done": 5,
       "blocked": 0,   # Blocked is lowest priority (not "ahead" in workflow)
       "canceled": 6,   # Canceled is terminal, treated as highest monotonic priority
       # Legacy alias support:
       "doing": 3,      # Maps to same priority as in_progress
   }
   ```
3. The `"doing"` entry remains for backward compatibility with old frontmatter values that haven't been migrated yet.
4. Note: this LANE_PRIORITY is the FALLBACK for when no rollback is detected. The rollback-aware logic (T050) takes precedence.

**Files**: `src/specify_cli/merge/status_resolver.py`

**Validation**:
- Test: `LANE_PRIORITY["in_progress"] == 3`
- Test: `LANE_PRIORITY["doing"] == 3` (alias parity)
- Test: `LANE_PRIORITY["blocked"] == 0`
- Test: all 7 canonical lanes plus "doing" are in the map.

**Edge Cases**:
- A WP file with `lane: "doing"` from before migration: `LANE_PRIORITY["doing"]` resolves correctly.
- A WP file with `lane: "claimed"` (new lane): resolved correctly.

### T049: Implement Rollback Detection

**Purpose**: Detect whether a merge conflict involves a reviewer rollback signal.

**Steps**:
1. Create a function `_detect_rollback(content: str) -> bool` in `status_resolver.py`:
   ```python
   def _detect_rollback(content: str) -> bool:
       """Detect if content contains a reviewer rollback signal.

       A rollback is detected if ANY of:
       1. Frontmatter has review_status: "has_feedback"
       2. History entry contains "review" and the lane moves backward from for_review
       3. The lane value is in_progress AND there's a review reference
       """
   ```
2. Detection heuristics (check each in order):

   **Heuristic 1**: Parse frontmatter for `review_status: "has_feedback"`:
   ```python
   if re.search(r'review_status:\s*["\']?has_feedback["\']?', content):
       return True
   ```

   **Heuristic 2**: Parse history entries for review-related backward movement:
   ```python
   # Look for history entries mentioning "review" or "changes_requested"
   # combined with a lane that's "behind" for_review (e.g., in_progress, doing)
   if re.search(r'action:.*review.*', content, re.IGNORECASE):
       lane_match = LANE_PATTERN.search(content)
       if lane_match:
           lane_value = lane_match.group(3)
           if LANE_PRIORITY.get(lane_value, 0) < LANE_PRIORITY.get("for_review", 4):
               return True
   ```

   **Heuristic 3**: Look for `reviewed_by` being set while lane is going backward:
   ```python
   if re.search(r'reviewed_by:\s*\S+', content):
       lane_match = LANE_PATTERN.search(content)
       if lane_match:
           lane_value = lane_match.group(3)
           if lane_value in ("in_progress", "doing", "planned", "claimed"):
               return True
   ```

3. The function examines the CONTENT of one side of the conflict (typically "theirs") to determine if it represents a rollback.

**Files**: `src/specify_cli/merge/status_resolver.py`

**Validation**:
- Test: content with `review_status: "has_feedback"` and `lane: in_progress` -> True.
- Test: content with `lane: done` and no review signals -> False.
- Test: content with `reviewed_by: "alice"` and `lane: in_progress` -> True.
- Test: content with `lane: for_review` (forward progression) -> False.

**Edge Cases**:
- Both sides have rollback signals: pick the one with the lower (earlier) lane.
- History mentions "review" but in a non-rollback context (e.g., "moved to for_review"): avoid false positives by checking the lane value.

### T050: Replace resolve_lane_conflict()

**Purpose**: Implement the rollback-aware resolution logic.

**Steps**:
1. Locate `resolve_lane_conflict()` in `status_resolver.py` (or the equivalent function that picks the winning lane).
2. Create a new function or modify the existing one:
   ```python
   def resolve_lane_conflict_rollback_aware(
       ours_content: str,
       theirs_content: str,
       ours_lane: str,
       theirs_lane: str,
   ) -> str:
       """Resolve lane conflict with rollback awareness.

       Algorithm:
       1. If rollback detected in either side, prefer the rollback (lower lane).
       2. If no rollback, use LANE_PRIORITY (existing monotonic behavior).
       """
       ours_rollback = _detect_rollback(ours_content)
       theirs_rollback = _detect_rollback(theirs_content)

       if ours_rollback and not theirs_rollback:
           return ours_lane  # Our rollback wins over their forward
       if theirs_rollback and not ours_rollback:
           return theirs_lane  # Their rollback wins over our forward
       if ours_rollback and theirs_rollback:
           # Both are rollbacks: pick the lower (earlier) lane
           ours_priority = LANE_PRIORITY.get(ours_lane, 0)
           theirs_priority = LANE_PRIORITY.get(theirs_lane, 0)
           return ours_lane if ours_priority <= theirs_priority else theirs_lane

       # No rollback detected: fall back to monotonic "most done wins"
       ours_priority = LANE_PRIORITY.get(ours_lane, 0)
       theirs_priority = LANE_PRIORITY.get(theirs_lane, 0)
       return ours_lane if ours_priority >= theirs_priority else theirs_lane
   ```
3. Update the call sites in `resolve_status_conflicts()` to use the new function, passing the full content of each side (not just the lane value).
4. The existing `resolve_lane_conflict()` function may be kept as a deprecated alias or removed if all call sites are updated.

**Files**: `src/specify_cli/merge/status_resolver.py`

**Validation**:
- Test: ours=`done`, theirs=`in_progress` with rollback signal -> `in_progress` wins.
- Test: ours=`done`, theirs=`in_progress` without rollback signal -> `done` wins (monotonic fallback).
- Test: ours=`for_review`, theirs=`in_progress` both with rollback -> `in_progress` wins (lower priority).
- Test: ours=`in_progress`, theirs=`for_review` no rollback -> `for_review` wins (monotonic).

**Edge Cases**:
- Unknown lane value (not in LANE_PRIORITY): default to priority 0, log a warning.
- Same lane on both sides: no conflict, return either (they are equal).

### T051: JSONL Event Log Merge Support

**Purpose**: Add auto-resolution for `status.events.jsonl` files during git merge.

**Steps**:
1. Add `status.events.jsonl` pattern to `STATUS_FILE_PATTERNS`:
   ```python
   STATUS_FILE_PATTERNS = [
       "kitty-specs/*/tasks/*.md",
       "kitty-specs/*/tasks.md",
       "kitty-specs/*/*/tasks/*.md",
       "kitty-specs/*/*/tasks.md",
       "kitty-specs/*/status.events.jsonl",  # NEW
   ]
   ```
2. Create a JSONL merge function:
   ```python
   def resolve_jsonl_conflict(ours_content: str, theirs_content: str) -> str:
       """Merge two JSONL event log files.

       Algorithm:
       1. Parse both sides into event lists.
       2. Concatenate all events.
       3. Deduplicate by event_id (first occurrence wins).
       4. Sort by (at, event_id) ascending.
       5. Serialize back to JSONL.
       """
       import json

       events = {}  # event_id -> event_dict (dedup by first occurrence)

       for content in (ours_content, theirs_content):
           for line in content.strip().splitlines():
               line = line.strip()
               if not line:
                   continue
               try:
                   event = json.loads(line)
                   event_id = event.get("event_id")
                   if event_id and event_id not in events:
                       events[event_id] = event
               except json.JSONDecodeError:
                   # Skip corrupted lines during merge (log warning)
                   continue

       # Sort by (at, event_id) for deterministic ordering
       sorted_events = sorted(
           events.values(),
           key=lambda e: (e.get("at", ""), e.get("event_id", "")),
       )

       # Serialize back to JSONL
       lines = [json.dumps(e, sort_keys=True) for e in sorted_events]
       return "\n".join(lines) + "\n" if lines else ""
   ```
3. Integrate into `resolve_status_conflicts()`: when a conflicted file matches `*.jsonl`, use `resolve_jsonl_conflict()` instead of the frontmatter-based resolver.
4. Update `is_status_file()` to also match JSONL files.

**Files**: `src/specify_cli/merge/status_resolver.py`

**Validation**:
- Test: two JSONL files with non-overlapping events -> merged file has all events sorted.
- Test: two JSONL files with duplicate event_ids -> deduplicated (first wins).
- Test: one JSONL with corrupted line -> corrupted line skipped, valid events preserved.
- Test: empty JSONL on one side -> returns the other side's events.
- Test: both empty -> returns empty string.

**Edge Cases**:
- Rebase scenario: events may be re-ordered. Sort by (at, event_id) handles this.
- Corrupted JSONL during conflict: skip the bad line but merge the rest. Log a warning.
- Very large JSONL files: in-memory merge is acceptable for expected sizes (100s of events).

### T052: Tests

**Purpose**: Comprehensive test coverage for all rollback resolution and JSONL merge scenarios.

**Steps**:
1. Create or extend `tests/specify_cli/status/test_conflict_resolution.py` (as specified in plan.md project structure).
2. Test categories:

   **Rollback Detection Tests** (`test_detect_rollback_*`):
   - `test_detect_rollback_has_feedback`: content with `review_status: "has_feedback"` -> True.
   - `test_detect_rollback_review_history`: content with history mentioning review and backward lane -> True.
   - `test_detect_rollback_reviewed_by_backward`: content with `reviewed_by` set and lane in_progress -> True.
   - `test_detect_rollback_forward_progression`: content with lane=done, no review signals -> False.
   - `test_detect_rollback_for_review_not_rollback`: content with lane=for_review (this is forward, not rollback) -> False.

   **Rollback-Aware Resolution Tests** (`test_resolve_*`):
   - `test_rollback_beats_forward_progression`: theirs has rollback to in_progress, ours has forward to done -> theirs wins.
   - `test_no_rollback_uses_monotonic`: both sides have no rollback -> highest priority wins (existing behavior).
   - `test_both_rollback_picks_lower`: both sides have rollback -> lower priority lane wins.
   - `test_same_lane_no_conflict`: both sides have same lane -> return either.
   - `test_unknown_lane_defaults_to_zero`: lane not in LANE_PRIORITY -> treated as priority 0.

   **LANE_PRIORITY Tests** (`test_lane_priority_*`):
   - `test_all_canonical_lanes_present`: verify all 7 lanes in LANE_PRIORITY.
   - `test_doing_alias_has_same_priority`: `LANE_PRIORITY["doing"] == LANE_PRIORITY["in_progress"]`.
   - `test_priority_ordering`: planned < claimed < in_progress < for_review < done.
   - `test_blocked_lowest_priority`: `LANE_PRIORITY["blocked"] == 0`.

   **JSONL Merge Tests** (`test_resolve_jsonl_*`):
   - `test_merge_non_overlapping_events`: two files, no shared events -> all events in output, sorted.
   - `test_merge_duplicate_events`: shared event_ids -> deduplicated.
   - `test_merge_sort_order`: output sorted by (at, event_id).
   - `test_merge_corrupted_line`: one file has bad JSON -> bad line skipped, valid events kept.
   - `test_merge_empty_files`: both empty -> empty output.
   - `test_merge_one_empty`: one side empty -> other side preserved.

   **Backward Compatibility Tests** (`test_existing_behavior_*`):
   - `test_existing_four_lane_conflicts_still_work`: old planned/doing/for_review/done conflicts resolve correctly.
   - `test_doing_alias_in_conflict`: "doing" on one side, "in_progress" on other -> treated as same priority.

3. Use `pytest.mark.parametrize` for exhaustive transition pair testing.

**Files**: `tests/specify_cli/status/test_conflict_resolution.py`

**Validation**: All tests pass. Coverage of rollback detection and resolution logic reaches 95%+.

**Edge Cases**:
- Tests must create realistic frontmatter content (not just isolated values) to test the regex patterns.
- JSONL test events should have valid ULID event_ids and ISO timestamps.

## Test Strategy

**Unit Tests**:
- `tests/specify_cli/status/test_conflict_resolution.py` (T052) -- all rollback detection, resolution, and JSONL merge tests.

**Integration Tests**:
- Consider adding a test that creates an actual git merge conflict and runs the resolver. This would go in `tests/integration/`.

**Existing Test Preservation**:
- All tests in `tests/specify_cli/merge/` that test the existing status_resolver must continue to pass.
- The existing tests may need updates if they explicitly assert on the old 4-lane LANE_PRIORITY values.

**Running Tests**:
```bash
python -m pytest tests/specify_cli/status/test_conflict_resolution.py -x -q
python -m pytest tests/specify_cli/merge/ -x -q  # Verify existing tests still pass
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Rollback detection false positives | Non-rollback conflicts resolved incorrectly | Multiple heuristics with AND logic; require both review signal AND backward lane movement |
| Rollback detection false negatives | Real rollbacks overridden by "most done wins" | Comprehensive test coverage of all reviewer rollback scenarios |
| JSONL merge corrupts event log | Loss of status history | Skip corrupted lines with warning; original JSONL files preserved in git history |
| Changing LANE_PRIORITY breaks existing merges | In-flight merges resolve differently | Preserve "doing" alias at same priority as "in_progress"; existing 4-lane ordering unchanged |
| Regex patterns fail on edge-case frontmatter | Resolution falls back to monotonic | Frontmatter follows strict YAML format; test with real WP file content |

## Review Guidance

When reviewing this WP, verify:
1. **Rollback wins over forward**: The core bug fix. Create a scenario with reviewer rollback and concurrent done, verify rollback wins.
2. **Monotonic fallback preserved**: When no rollback is detected, the existing "most done wins" behavior is unchanged.
3. **LANE_PRIORITY includes all 7 lanes**: No missing entries. "doing" alias included.
4. **JSONL deduplication is by event_id**: Not by content. Two events with different event_ids but same content are both kept.
5. **JSONL sort order is deterministic**: (at, event_id) ascending. Same merge always produces same output.
6. **Existing tests pass**: Run the full merge test suite.
7. **No fallback mechanisms**: If a JSONL line is corrupted, it is SKIPPED with a warning, not silently accepted.
8. **Regex patterns are robust**: Test with real WP frontmatter content, including multi-line history entries.

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T15:00:39Z – unknown – shell_pid=50709 – lane=for_review – Moved to for_review
