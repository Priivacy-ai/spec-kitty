---
work_package_id: WP03
title: Deterministic Reducer
lane: "done"
dependencies:
- WP01
base_branch: 2.x
base_commit: 1b37d3a7c2a626005000cff7b1dd2e76a87de203
created_at: '2026-02-08T14:31:42.584209+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-wp03"
shell_pid: "42678"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-08T14:07:18Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 -- Deterministic Reducer

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
spec-kitty implement WP03 --base WP02
```

This WP depends on WP01 (models) and WP02 (store read). Branch from WP02's branch since WP02 already includes WP01.

---

## Objectives & Success Criteria

Create the deterministic reducer -- the heart of the canonical status model. Given a list of StatusEvents, the reducer produces a StatusSnapshot representing the current state of all work packages. This WP delivers:

1. `reduce()` function: deduplicates, sorts, and reduces events to a StatusSnapshot
2. Rollback-aware precedence logic for concurrent event conflict resolution
3. Byte-identical output guarantee via deterministic JSON serialization
4. `materialize()` function: reads events from store, reduces, writes `status.json` atomically
5. Comprehensive unit tests for determinism, idempotency, and conflict resolution

**Success**: Same event log always produces byte-identical `status.json`. Reviewer rollback beats concurrent forward progression. Duplicate event_ids are deduplicated. Out-of-order events are sorted correctly.

---

## Context & Constraints

- **Spec**: `kitty-specs/034-feature-status-state-model-remediation/spec.md` -- FR-005 (deterministic reducer), FR-006 (byte-identical output), FR-014 (merge deduplication), FR-015 (rollback precedence)
- **Plan**: `kitty-specs/034-feature-status-state-model-remediation/plan.md` -- AD-2 (Reducer Algorithm), AD-4 (Rollback-Aware Conflict Resolution)
- **Data Model**: `kitty-specs/034-feature-status-state-model-remediation/data-model.md` -- StatusSnapshot entity, Determinism contract
- **Contracts**: `kitty-specs/034-feature-status-state-model-remediation/contracts/snapshot-schema.json` -- output format

**Key constraints**:
- Sorting key: primary = `event.at` (ISO 8601 timestamp string), secondary = `event.event_id` (ULID string). Both sort lexicographically
- Deduplication: keep first occurrence by `event_id`
- Byte-identical output: `json.dumps(snapshot.to_dict(), sort_keys=True, indent=2, ensure_ascii=False) + "\n"`
- Atomic write: write to temporary file, then `os.replace()` to target
- Rollback-aware: reviewer rollback (`for_review -> in_progress` with `review_ref`) beats concurrent forward progression for the same WP
- No fallback mechanisms: corruption in the event log causes the reducer to fail, not produce partial results

---

## Subtasks & Detailed Guidance

### Subtask T011 -- Create `src/specify_cli/status/reducer.py`

**Purpose**: Core reducer implementing the dedupe/sort/reduce algorithm per AD-2 in the plan.

**Steps**:
1. Create `src/specify_cli/status/reducer.py` with imports:
   ```python
   from __future__ import annotations

   import json
   import os
   from datetime import datetime, timezone
   from pathlib import Path
   from typing import Any

   from specify_cli.status.models import Lane, StatusEvent, StatusSnapshot
   from specify_cli.status.store import read_events
   ```

2. Implement `reduce()`:
   ```python
   def reduce(events: list[StatusEvent]) -> StatusSnapshot:
       """Reduce a list of StatusEvents to a StatusSnapshot.

       Algorithm:
       1. Deduplicate by event_id (keep first occurrence)
       2. Sort by (at, event_id) ascending
       3. Iterate and track current lane per WP
       4. Apply rollback-aware precedence for concurrent events
       5. Build summary counts
       """
       if not events:
           return StatusSnapshot(
               feature_slug="",
               materialized_at=_now_utc(),
               event_count=0,
               last_event_id=None,
               work_packages={},
               summary={lane.value: 0 for lane in Lane},
           )

       # Step 1: Deduplicate by event_id (keep first occurrence)
       seen_ids: set[str] = set()
       unique_events: list[StatusEvent] = []
       for event in events:
           if event.event_id not in seen_ids:
               seen_ids.add(event.event_id)
               unique_events.append(event)

       # Step 2: Sort by (at, event_id)
       sorted_events = sorted(unique_events, key=lambda e: (e.at, e.event_id))

       # Step 3: Reduce to current state per WP
       wp_states: dict[str, dict[str, Any]] = {}
       feature_slug = sorted_events[0].feature_slug

       for event in sorted_events:
           wp_id = event.wp_id
           current = wp_states.get(wp_id)

           if current is not None:
               # Check for concurrent events (rollback-aware precedence)
               if _should_apply_event(current, event, sorted_events):
                   wp_states[wp_id] = _wp_state_from_event(event, current)
           else:
               wp_states[wp_id] = _wp_state_from_event(event, None)

       # Step 4: Build summary
       summary = {lane.value: 0 for lane in Lane}
       for wp_state in wp_states.values():
           lane_val = wp_state["lane"]
           if lane_val in summary:
               summary[lane_val] += 1

       last_event = sorted_events[-1]
       return StatusSnapshot(
           feature_slug=feature_slug,
           materialized_at=_now_utc(),
           event_count=len(sorted_events),
           last_event_id=last_event.event_id,
           work_packages=wp_states,
           summary=summary,
       )
   ```

3. Implement helper functions:
   ```python
   def _now_utc() -> str:
       return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

   def _wp_state_from_event(
       event: StatusEvent,
       previous: dict[str, Any] | None,
   ) -> dict[str, Any]:
       force_count = 0
       if previous is not None:
           force_count = previous.get("force_count", 0)
       if event.force:
           force_count += 1
       return {
           "lane": event.to_lane if isinstance(event.to_lane, str) else event.to_lane.value,
           "actor": event.actor,
           "last_transition_at": event.at,
           "last_event_id": event.event_id,
           "force_count": force_count,
       }
   ```

**Files**: `src/specify_cli/status/reducer.py` (new file)

**Validation**:
- `reduce([])` returns an empty snapshot with zero counts
- `reduce([event1, event2])` where event2 is chronologically later produces WP state matching event2
- `reduce([event2, event1])` (out of order) produces identical result to above (sorted by timestamp)

**Edge Cases**:
- Empty event list: returns snapshot with no WPs, all summary counts zero, feature_slug empty, last_event_id None
- Single event: snapshot has one WP in the target lane
- Multiple WPs: each WP tracks its own state independently
- Events for unknown/new WPs: created in snapshot on first encounter

---

### Subtask T012 -- Rollback-aware precedence in reduce()

**Purpose**: When two events for the same WP are concurrent (originate from the same `from_lane`), a reviewer rollback (`for_review -> in_progress` with `review_ref`) takes precedence over concurrent forward progression.

**Steps**:
1. Implement `_is_rollback_event()`:
   ```python
   def _is_rollback_event(event: StatusEvent) -> bool:
       """Check if an event represents a reviewer rollback."""
       return (
           event.from_lane in (Lane.FOR_REVIEW, "for_review")
           and event.to_lane in (Lane.IN_PROGRESS, "in_progress")
           and event.review_ref is not None
       )
   ```

2. Implement `_should_apply_event()`:
   ```python
   def _should_apply_event(
       current_state: dict[str, Any],
       new_event: StatusEvent,
       all_events: list[StatusEvent],
   ) -> bool:
       """Determine if a new event should override the current WP state.

       Rollback-aware precedence:
       - If the new event is a rollback (for_review -> in_progress with review_ref),
         it wins over any concurrent forward event from the same from_lane.
       - If the current state was set by a rollback and the new event is NOT a rollback
         from the same from_lane, the rollback wins (keep current).
       - Otherwise, later event wins (standard timestamp ordering -- events are pre-sorted).
       """
       current_event_id = current_state.get("last_event_id")
       from_lane_str = new_event.from_lane if isinstance(new_event.from_lane, str) else new_event.from_lane.value
       current_lane = current_state.get("lane")

       # If new event's from_lane does not match current WP lane, this is not
       # a concurrent conflict -- it is a sequential transition. Always apply.
       if from_lane_str != current_lane:
           # Check if the from_lane matches what the WP was in before the
           # current event (concurrent scenario). For simplicity in the sorted
           # stream, if from_lane does not match current lane, the event may
           # be stale or the WP was already moved. Apply only if from_lane
           # matches current lane (standard sequential application).
           # In the sorted stream, the latest event for a WP always wins
           # unless rollback precedence applies.
           pass

       # Always apply: events are sorted, so later events naturally win.
       # The exception is when a rollback should take precedence.

       # Find the event that set the current state
       if current_event_id:
           current_setter = None
           for e in all_events:
               if e.event_id == current_event_id:
                   current_setter = e
                   break

           if current_setter is not None:
               # Concurrent check: both events from same from_lane for same WP
               current_from = current_setter.from_lane if isinstance(current_setter.from_lane, str) else current_setter.from_lane.value

               if current_from == from_lane_str:
                   # Concurrent events detected
                   if _is_rollback_event(current_setter) and not _is_rollback_event(new_event):
                       # Current is rollback, new is forward -- rollback wins
                       return False
                   if _is_rollback_event(new_event) and not _is_rollback_event(current_setter):
                       # New is rollback, current is forward -- rollback wins
                       return True

       # Default: later event wins (events are sorted by timestamp)
       return True
   ```

**Files**: `src/specify_cli/status/reducer.py` (same file)

**Validation**:
- Branch A: `for_review -> done` (forward). Branch B: `for_review -> in_progress` with review_ref (rollback). After merge and reduce, WP state is `in_progress` (rollback wins).
- Two non-conflicting events for different WPs: both applied correctly.
- Two concurrent forward events (no rollback): later timestamp wins.

**Edge Cases**:
- Both events are rollbacks: later timestamp wins (both have review_ref)
- Rollback event has earlier timestamp but still wins over forward event
- Events from different from_lanes are not concurrent -- standard ordering applies

---

### Subtask T013 -- Byte-identical output serialization

**Purpose**: Guarantee that running the reducer on the same event log always produces the exact same bytes in `status.json`.

**Steps**:
1. Implement `materialize_to_json()`:
   ```python
   def materialize_to_json(snapshot: StatusSnapshot) -> str:
       """Serialize a StatusSnapshot to deterministic JSON string.

       This function MUST produce byte-identical output for identical input.
       The exact string format is: json.dumps with sort_keys, indent=2,
       ensure_ascii=False, followed by a trailing newline.
       """
       return json.dumps(
           snapshot.to_dict(),
           sort_keys=True,
           indent=2,
           ensure_ascii=False,
       ) + "\n"
   ```

2. The `materialized_at` field in the snapshot is set at reduce time. For byte-identical output on re-materialization, the caller must use the same snapshot object. The `materialize()` function (T014) re-reduces from the log each time, so `materialized_at` will differ -- this is expected. The determinism contract means: same events + same materialized_at = same bytes.

3. For testing byte-identical output, create a snapshot with a fixed `materialized_at` and verify the JSON output matches exactly.

**Files**: `src/specify_cli/status/reducer.py` (same file)

**Validation**:
- Create a StatusSnapshot with fixed `materialized_at`, call `materialize_to_json()` twice, compare bytes -- must be identical
- Output must have trailing newline
- Keys in output must be alphabetically sorted at every nesting level

**Edge Cases**:
- Unicode characters in actor names: `ensure_ascii=False` preserves them as-is
- Numeric values (event_count, force_count): serialized as integers, not strings
- Null values: serialized as JSON `null`

---

### Subtask T014 -- `materialize()` function

**Purpose**: High-level function that reads events from the store, reduces them, and writes `status.json` atomically.

**Steps**:
1. Define output filename constant:
   ```python
   SNAPSHOT_FILENAME = "status.json"
   ```

2. Implement `materialize()`:
   ```python
   def materialize(feature_dir: Path) -> StatusSnapshot:
       """Read events, reduce to snapshot, write status.json atomically.

       Uses write-to-temp-then-rename pattern for atomic file replacement.
       Returns the materialized StatusSnapshot.
       """
       events = read_events(feature_dir)
       snapshot = reduce(events)

       # Atomic write: write to temp file, then os.replace()
       snapshot_path = feature_dir / SNAPSHOT_FILENAME
       tmp_path = snapshot_path.with_suffix(".json.tmp")

       json_str = materialize_to_json(snapshot)
       tmp_path.write_text(json_str, encoding="utf-8")
       os.replace(str(tmp_path), str(snapshot_path))

       return snapshot
   ```

3. The `os.replace()` call is atomic on POSIX systems and mostly-atomic on Windows.

**Files**: `src/specify_cli/status/reducer.py` (same file)

**Validation**:
- Append 3 events via store, call `materialize()`, verify `status.json` exists and contains correct WP states
- Call `materialize()` again (no new events), verify `status.json` is updated (new `materialized_at` timestamp)
- Verify no `.json.tmp` file remains after successful materialization

**Edge Cases**:
- Empty event log: produces snapshot with empty work_packages, status.json still written
- Feature directory does not exist: `read_events()` returns empty list (from store.py), snapshot is empty
- Interrupted write: if crash occurs between tmp write and replace, `.json.tmp` file may remain -- next materialize overwrites it
- `os.replace` target does not exist: creates the file (first materialization)

---

### Subtask T015 -- Unit tests for reducer determinism and idempotency

**Purpose**: Verify the core determinism contract: same input always produces same output.

**Steps**:
1. Create `tests/specify_cli/status/test_reducer.py`
2. Test cases:

   - `test_reduce_empty_events` -- empty list produces snapshot with no WPs, all summary counts zero
   - `test_reduce_single_event` -- one event, WP in target lane, summary has one count in that lane
   - `test_reduce_ordered_events` -- events in chronological order, WP reflects final state
   - `test_reduce_out_of_order_events` -- events in reverse chronological order, reducer sorts them, same result as ordered
   - `test_reduce_deduplication` -- same event_id twice, only counted once, result same as single event
   - `test_byte_identical_output` -- create snapshot with fixed materialized_at, call materialize_to_json twice, compare exact strings
   - `test_materialize_creates_status_json` -- use tmp_path, append events, materialize, verify file exists and parses
   - `test_materialize_atomic_write` -- verify no `.json.tmp` remains after successful materialize
   - `test_reduce_multiple_wps` -- events for WP01 and WP02, both tracked independently in snapshot
   - `test_reduce_force_count_tracked` -- event with force=True increments force_count
   - `test_summary_counts_match_wp_states` -- summary dict reflects actual lane distribution

3. Use factory functions for creating StatusEvent instances with controlled timestamps and event_ids

**Files**: `tests/specify_cli/status/test_reducer.py` (new file)

**Validation**: `python -m pytest tests/specify_cli/status/test_reducer.py -v` -- all pass

---

### Subtask T016 -- Unit tests for rollback-aware conflict resolution

**Purpose**: Verify the rollback precedence rule in concurrent event scenarios.

**Steps**:
1. Create `tests/specify_cli/status/test_conflict_resolution.py`
2. Test cases:

   - `test_rollback_beats_forward` -- Branch A: `for_review -> done` at T1. Branch B: `for_review -> in_progress` with review_ref at T2. After merge (both events in list), reduce produces WP in `in_progress` (rollback wins regardless of timestamp ordering)
   - `test_rollback_beats_forward_earlier_timestamp` -- Same as above but rollback event has EARLIER timestamp than forward event. Rollback still wins.
   - `test_non_conflicting_different_wps` -- WP01 forward event + WP02 rollback event. Both applied correctly to their respective WPs (no interference).
   - `test_concurrent_forward_events_timestamp_wins` -- Two forward events from same from_lane (no review_ref on either). Later timestamp wins.
   - `test_concurrent_rollbacks_timestamp_wins` -- Two rollback events (both have review_ref). Later timestamp wins.
   - `test_sequential_events_not_concurrent` -- Events from different from_lanes for same WP. Standard sequential ordering (later event wins).
   - `test_deduplication_before_conflict_resolution` -- Duplicate event_ids with different content. First occurrence kept, second discarded.

3. Create specific test fixtures simulating merge scenarios:
   - Two separate event lists (branch A and branch B)
   - Concatenate them (simulating git merge of JSONL files)
   - Feed combined list to `reduce()`

**Files**: `tests/specify_cli/status/test_conflict_resolution.py` (new file)

**Validation**: `python -m pytest tests/specify_cli/status/test_conflict_resolution.py -v` -- all pass

**Edge Cases**:
- Both branches produce events with same timestamp but different event_ids: ULID secondary sort resolves deterministically
- One branch has no events for a WP while the other does: non-conflicting, both applied

---

## Test Strategy

**Required per user requirements**: Unit tests for reducer determinism and conflict resolution.

- **Coverage target**: 100% of reducer.py
- **Test runner**: `python -m pytest tests/specify_cli/status/test_reducer.py tests/specify_cli/status/test_conflict_resolution.py -v`
- **Determinism testing**: Use fixed timestamps and event_ids in factory functions, then verify JSON output byte-for-byte
- **Conflict testing**: Simulate branch merges by concatenating event lists
- **Fixtures**: Factory functions that create StatusEvent with controllable `at`, `event_id`, `from_lane`, `to_lane`, `review_ref` fields
- **Idempotency testing**: Call `materialize()` twice, verify both produce valid status.json (timestamps will differ but structure is identical)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Non-deterministic JSON serialization | Different bytes from same input | Enforce `sort_keys=True` at every level; use `indent=2` consistently |
| Floating-point timestamps | Non-deterministic sorting | Use ISO 8601 strings exclusively, never convert to float |
| os.replace not fully atomic on Windows | Corrupt status.json on crash | Write to .tmp first; on next run, materialize regenerates from log |
| Rollback detection false positives | Wrong WP state after merge | Rollback requires both `for_review -> in_progress` AND `review_ref` set -- two conditions reduce false positives |
| materialized_at varies per run | Tests expecting exact byte match fail | In byte-identical tests, use a snapshot with a fixed materialized_at, not the materialize() function |

---

## Review Guidance

- **Check reduce() algorithm**: Follows AD-2 exactly: deduplicate, sort, iterate, track state per WP
- **Check rollback precedence**: `_is_rollback_event()` checks all three conditions (from_lane=for_review, to_lane=in_progress, review_ref not None)
- **Check byte-identical output**: `materialize_to_json()` uses `sort_keys=True, indent=2, ensure_ascii=False` + trailing newline
- **Check atomic write**: `materialize()` writes to `.tmp` then `os.replace()`
- **Check deduplication**: First occurrence by event_id kept, not last
- **Check sorting key**: `(event.at, event.event_id)` -- both strings, both sort lexicographically
- **No fallback mechanisms**: Corrupted event log causes StoreError propagation, not partial snapshot

---

## Activity Log

- 2026-02-08T14:07:18Z -- system -- lane=planned -- Prompt created.
- 2026-02-08T14:31:43Z – claude-wp03 – shell_pid=42678 – lane=doing – Assigned agent via workflow command
- 2026-02-08T14:46:40Z – claude-wp03 – shell_pid=42678 – lane=for_review – Moved to for_review
- 2026-02-08T14:46:55Z – claude-wp03 – shell_pid=42678 – lane=done – Moved to done
