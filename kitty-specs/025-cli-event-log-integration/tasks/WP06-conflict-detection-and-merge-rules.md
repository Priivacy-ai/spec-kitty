---
work_package_id: "WP06"
title: "Conflict Detection & Merge Rules"
phase: "Phase 2 - Advanced Features & Edge Cases"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP05"]
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
history:
  - timestamp: "2026-01-27T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Conflict Detection & Merge Rules

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you start.
- **Report progress**: Update Activity Log as you address feedback items.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate if work needs changes.]*

---

## Objectives & Success Criteria

**Primary Goal**: Implement concurrent operation detection and deterministic conflict resolution using Last-Write-Wins merge rule.

**Success Criteria**:
- ✅ Conflict detection identifies events with same Lamport clock (concurrent operations)
- ✅ Last-Write-Wins merge rule implemented (lexicographic ULID sorting)
- ✅ Conflict detection integrated into state reconstruction (EventReader enhancement)
- ✅ Conflict warnings displayed in `spec-kitty status` output
- ✅ Conflict resolutions logged to stderr with explanation
- ✅ 100% deterministic resolution (no user prompts required)

**Priority**: P2 (US4)

**User Story**: US4 - Conflict Detection for Concurrent Operations

**Independent Test**:
```python
# Simulate concurrent events (same clock)
from specify_cli.events.store import EventStore
from specify_cli.events.types import Event
from pathlib import Path

events_dir = Path("/tmp/test-conflict/.kittify/events")
events_dir.mkdir(parents=True)

# Manually create JSONL with concurrent events
import json
from datetime import datetime, timezone

event_a = {
    "event_id": "01AAAAAAAAAAAAAAAAAAAAAAA1",  # Lower ULID
    "event_type": "WPStatusChanged",
    "event_version": 1,
    "lamport_clock": 5,  # Same clock!
    "entity_id": "WP01",
    "entity_type": "WorkPackage",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "actor": "agent-a",
    "causation_id": None,
    "correlation_id": None,
    "payload": {"old_status": "doing", "new_status": "for_review"}
}

event_b = {
    "event_id": "01ZZZZZZZZZZZZZZZZZZZZZZZZ",  # Higher ULID
    "event_type": "WPStatusChanged",
    "event_version": 1,
    "lamport_clock": 5,  # Same clock!
    "entity_id": "WP01",
    "entity_type": "WorkPackage",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "actor": "agent-b",
    "causation_id": None,
    "correlation_id": None,
    "payload": {"old_status": "doing", "new_status": "rejected"}
}

# Write to JSONL
jsonl_file = events_dir / "2026-01-27.jsonl"
with open(jsonl_file, "w") as f:
    f.write(json.dumps(event_a) + "\n")
    f.write(json.dumps(event_b) + "\n")

# Read with conflict detection
store = EventStore(Path("/tmp/test-conflict"))
reader = EventReader(store)
status = reader.reconstruct_wp_status("WP01")

# Verify LWW applied (event_b wins due to higher ULID)
assert status == "rejected", f"Expected 'rejected', got {status}"
print("✓ Conflict detected and resolved via LWW")
```

---

## Context & Constraints

### ⚠️ CRITICAL: Target Branch

**This work package MUST be implemented on the `2.x` branch (NOT main).**

Verify you're on 2.x:
```bash
git branch --show-current  # Must output: 2.x
```

### Prerequisites

- **WP05 complete**: EventReader.reconstruct_wp_status() exists
- **Spec**: US4 acceptance scenarios (lines 86-90)
- **Data model**: Conflict resolution logic (lines 327-371)
- **Research**: sync-protocols.md (Last-Write-Wins pattern, lines 295-319)

### Architectural Constraints

**From spec.md (US4)**:
- Use `is_concurrent()` from spec-kitty-events library OR implement LWW locally
- State-machine merge rule for workflow transitions (later event_id wins)
- CRDT set merge for tag additions (future - not implemented in this WP)
- Deterministic resolution (no user prompts)

**From data-model.md (Conflict Resolution)**:
- Group events by Lamport clock
- Detect conflicts: len(events_at_clock) > 1
- Apply LWW: Sort by event_id (lexicographic), take last event

**From plan decision** (Planning Q2):
- Last-Write-Wins sufficient for workflow state (research-validated)
- Conflicts rare in CLI use case (single user per project)

### Key Technical Decisions

1. **LWW Merge Rule** (Research): Lexicographic ULID sorting determines winner
2. **Conflict Warning** (FR-024): Surface conflict info in status output
3. **Deterministic** (FR-022): No user interaction required for resolution

---

## Subtasks & Detailed Guidance

### Subtask T031 – Implement conflict detection (group events by Lamport clock, find duplicates)

**Purpose**: Identify concurrent events (same Lamport clock value) that require conflict resolution.

**Steps**:

1. **Add conflict detection to reader module**:
   ```python
   # In src/specify_cli/events/reader.py (add new class)

   from typing import Any
   from collections import defaultdict


   @dataclass
   class ConflictInfo:
       """Information about a detected conflict."""
       lamport_clock: int
       entity_id: str
       event_type: str
       conflicting_events: list[Event]  # Events with same clock
       winning_event: Event  # Event selected by merge rule
       merge_rule: str  # "LWW" (Last-Write-Wins)


   class ConflictDetector:
       """Detect and track conflicts in event log."""

       def detect_conflicts(self, events: list[Event]) -> list[ConflictInfo]:
           """
           Detect concurrent events (same Lamport clock).

           Args:
               events: List of events to check (should be for same entity)

           Returns:
               List of ConflictInfo for each detected conflict
           """
           # Group events by Lamport clock
           events_by_clock: dict[int, list[Event]] = defaultdict(list)
           for event in events:
               events_by_clock[event.lamport_clock].append(event)

           # Find conflicts (clocks with >1 event)
           conflicts = []
           for clock, clock_events in events_by_clock.items():
               if len(clock_events) > 1:
                   # Conflict detected!
                   # Sort by event_id (lexicographic) for LWW
                   sorted_events = sorted(clock_events, key=lambda e: e.event_id)
                   winning_event = sorted_events[-1]  # Last event wins

                   conflicts.append(ConflictInfo(
                       lamport_clock=clock,
                       entity_id=clock_events[0].entity_id,
                       event_type=clock_events[0].event_type,
                       conflicting_events=clock_events,
                       winning_event=winning_event,
                       merge_rule="LWW",
                   ))

           return conflicts

       def is_concurrent(self, event1: Event, event2: Event) -> bool:
           """
           Check if two events are concurrent (same Lamport clock).

           Args:
               event1, event2: Events to compare

           Returns:
               True if concurrent (same lamport_clock)
           """
           return event1.lamport_clock == event2.lamport_clock
   ```

**Files**:
- `src/specify_cli/events/reader.py` (modify: add ConflictDetector class and ConflictInfo dataclass)

**Validation**:
- [ ] `detect_conflicts()` groups events by lamport_clock
- [ ] Identifies conflicts where len(events_at_clock) > 1
- [ ] Returns ConflictInfo with conflicting_events and winning_event
- [ ] `is_concurrent()` checks if two events have same clock

**Edge Cases**:
- No conflicts (all unique clocks): Returns empty list
- Multiple conflicts at different clocks: All detected and returned
- Conflict with 3+ concurrent events: LWW still works (lexicographic sort, last wins)

**Parallel?**: Yes - Can implement in parallel with T032-T033 (separate class)

---

### Subtask T032 – Implement Last-Write-Wins merge rule (lexicographic ULID sorting)

**Purpose**: Provide deterministic conflict resolution using ULID lexicographic ordering.

**Steps**:

1. **Add merge rule to ConflictDetector**:
   ```python
   # In src/specify_cli/events/reader.py (add to ConflictDetector class)

   def apply_lww_merge(self, conflicting_events: list[Event]) -> Event:
       """
       Apply Last-Write-Wins merge rule.

       ULIDs are lexicographically sortable (timestamp-embedded).
       Later ULID = later creation time = wins.

       Args:
           conflicting_events: Events with same Lamport clock

       Returns:
           Winning event (event with highest ULID)
       """
       if not conflicting_events:
           raise ValueError("Cannot apply merge rule to empty list")

       # Sort by event_id (ULIDs are lexicographically sortable)
       sorted_events = sorted(conflicting_events, key=lambda e: e.event_id)

       # Last event wins
       winning_event = sorted_events[-1]

       return winning_event

   def format_conflict_explanation(self, conflict: ConflictInfo) -> str:
       """
       Format conflict for display to user.

       Args:
           conflict: ConflictInfo object

       Returns:
           Human-readable explanation
       """
       event_ids = [e.event_id for e in conflict.conflicting_events]
       return (
           f"Conflict detected for {conflict.entity_id} at clock {conflict.lamport_clock}:\n"
           f"  - {len(conflict.conflicting_events)} concurrent {conflict.event_type} events\n"
           f"  - Event IDs: {', '.join(event_ids)}\n"
           f"  - Merge rule: {conflict.merge_rule}\n"
           f"  - Winner: {conflict.winning_event.event_id}\n"
       )
   ```

**Files**:
- `src/specify_cli/events/reader.py` (modify: add merge rule methods to ConflictDetector)

**Validation**:
- [ ] `apply_lww_merge()` sorts events by event_id
- [ ] Returns event with highest event_id (lexicographic order)
- [ ] Works with 2, 3, or more conflicting events
- [ ] `format_conflict_explanation()` produces human-readable output

**Edge Cases**:
- Single event (no conflict): Should not call this method (detected in detect_conflicts)
- Events with identical event_id: Impossible (ULID guarantees uniqueness)
- ULID format invalid: Would fail in Event validation (caught earlier)

**Parallel?**: Yes - Can implement in parallel with T031, T033

---

### Subtask T033 – Integrate conflict detection into state reconstruction (T028 enhancement)

**Purpose**: Enhance EventReader to detect and resolve conflicts during state reconstruction.

**Steps**:

1. **Modify reconstruct_wp_status() to detect conflicts**:
   ```python
   # In src/specify_cli/events/reader.py (modify reconstruct_wp_status method)

   def reconstruct_wp_status(
       self,
       wp_id: str,
       feature_slug: str | None = None,
       detect_conflicts: bool = True,  # NEW parameter
   ) -> tuple[str, list[ConflictInfo]]:  # NEW return type
       """
       Derive current WorkPackage status with optional conflict detection.

       Args:
           wp_id: Work package ID
           feature_slug: Optional feature filter
           detect_conflicts: If True, detect and resolve conflicts

       Returns:
           Tuple of (current_status, conflicts)
           - current_status: Derived status after conflict resolution
           - conflicts: List of ConflictInfo (empty if no conflicts)
       """
       # Read all WPStatusChanged events for this WP
       events = self.store.read(
           entity_id=wp_id,
           event_type="WPStatusChanged"
       )

       # Filter by feature if specified
       if feature_slug:
           events = [
               e for e in events
               if e.payload.get("feature_slug") == feature_slug
           ]

       # Detect conflicts
       conflicts = []
       if detect_conflicts:
           detector = ConflictDetector()
           conflicts = detector.detect_conflicts(events)

           # Log conflicts to stderr
           if conflicts:
               import sys
               for conflict in conflicts:
                   explanation = detector.format_conflict_explanation(conflict)
                   print(f"⚠️ {explanation}", file=sys.stderr)

       # Replay events in causal order
       # If conflicts exist, use winning events
       current_status = "planned"
       for event in events:
           # Skip non-winning events in conflicts
           if conflicts:
               # Check if this event is a winning event in any conflict
               is_winner = any(
                   event.event_id == c.winning_event.event_id
                   for c in conflicts
               )
               is_loser = any(
                   event in c.conflicting_events and event.event_id != c.winning_event.event_id
                   for c in conflicts
               )

               if is_loser:
                   # Skip this event (lost conflict)
                   continue

           # Apply transition
           new_status = event.payload.get("new_status")
           if new_status:
               current_status = new_status

       return current_status, conflicts

   def reconstruct_all_wp_statuses(
       self,
       feature_slug: str | None = None,
       detect_conflicts: bool = True,
   ) -> tuple[dict[str, str], dict[str, list[ConflictInfo]]]:
       """
       Derive current status for ALL work packages with conflict detection.

       Args:
           feature_slug: Optional feature filter
           detect_conflicts: If True, detect and resolve conflicts

       Returns:
           Tuple of (statuses, conflicts_by_wp)
           - statuses: Dict mapping WP ID → current status
           - conflicts_by_wp: Dict mapping WP ID → list of ConflictInfo
       """
       # Read all WPStatusChanged events
       events = self.store.read(event_type="WPStatusChanged")

       # Filter by feature if specified
       if feature_slug:
           events = [
               e for e in events
               if e.payload.get("feature_slug") == feature_slug
           ]

       # Group events by WP ID
       wp_events: dict[str, list[Event]] = defaultdict(list)
       for event in events:
           wp_id = event.entity_id
           wp_events[wp_id].append(event)

       # Reconstruct status for each WP (with conflict detection)
       statuses = {}
       conflicts_by_wp = {}

       for wp_id, wp_event_list in wp_events.items():
           status, conflicts = self.reconstruct_wp_status(
               wp_id,
               feature_slug=feature_slug,
               detect_conflicts=detect_conflicts,
           )
           statuses[wp_id] = status
           if conflicts:
               conflicts_by_wp[wp_id] = conflicts

       return statuses, conflicts_by_wp
   ```

**Files**:
- `src/specify_cli/events/reader.py` (modify: enhance reconstruct methods to return conflicts)

**Validation**:
- [ ] `reconstruct_wp_status()` detects conflicts via ConflictDetector
- [ ] Skips losing events during replay (only winning events applied)
- [ ] Returns tuple: (status, conflicts)
- [ ] Logs conflict explanations to stderr
- [ ] `reconstruct_all_wp_statuses()` detects conflicts for all WPs

**Edge Cases**:
- No conflicts: Returns (status, []) with empty conflicts list
- Multiple conflicts for same WP: All detected and resolved
- Conflict detection disabled: Returns (status, []) without detection overhead

**Parallel?**: No - Sequential after T031-T032 (needs ConflictDetector and merge rule)

---

### Subtask T034 – Add conflict warning output to `spec-kitty status` command

**Purpose**: Display conflict warnings in status command output so users are aware of concurrent operations.

**Steps**:

1. **Modify status command to show conflicts**:
   ```python
   # In src/specify_cli/cli/commands/status.py (modify)

   from specify_cli.events.reader import EventReader

   @with_event_store
   def status(
       feature: str | None,
       event_store: EventStore,
   ):
       """Display status with conflict warnings."""
       reader = EventReader(event_store)

       # Reconstruct with conflict detection
       wp_statuses, conflicts_by_wp = reader.reconstruct_all_wp_statuses(
           feature_slug=feature,
           detect_conflicts=True,
       )

       # Display kanban board (existing logic)
       lanes = group_by_status(wp_statuses)
       display_kanban_board(lanes, feature_filter=feature)

       # Display conflict warnings (NEW)
       if conflicts_by_wp:
           print("\n⚠️ Conflicts Detected:\n")
           for wp_id, conflicts in conflicts_by_wp.items():
               for conflict in conflicts:
                   print(f"  {wp_id}: {len(conflict.conflicting_events)} concurrent events at clock {conflict.lamport_clock}")
                   print(f"    Resolved via {conflict.merge_rule}: {conflict.winning_event.payload.get('new_status')}")
                   print()
   ```

**Files**:
- `src/specify_cli/cli/commands/status.py` (modify: add conflict warning display)

**Validation**:
- [ ] Conflicts displayed after kanban board
- [ ] Shows WP ID, clock value, number of conflicting events
- [ ] Shows merge rule applied (LWW)
- [ ] Shows winning event's resulting status
- [ ] Test: Create concurrent events, run status, verify warning shown

**Edge Cases**:
- No conflicts: No warning section shown
- Multiple conflicts: All displayed in list
- Conflict without clear winner: Should not happen (LWW always produces winner)

**Parallel?**: Yes - Can implement in parallel with T033, T035 (different files)

---

### Subtask T035 – Log conflict resolutions to stderr with explanation

**Purpose**: Provide detailed conflict resolution logs for debugging and auditing.

**Steps**:

1. **Verify logging in reconstruct_wp_status()**:
   ```python
   # In src/specify_cli/events/reader.py
   # Should already log conflicts from T033

   def reconstruct_wp_status(...):
       # ... existing logic

       # Detect conflicts
       if detect_conflicts:
           detector = ConflictDetector()
           conflicts = detector.detect_conflicts(events)

           # Log conflicts to stderr (already implemented in T033)
           if conflicts:
               import sys
               for conflict in conflicts:
                   explanation = detector.format_conflict_explanation(conflict)
                   print(f"⚠️ {explanation}", file=sys.stderr)
   ```

2. **Enhance logging with merge rule details**:
   ```python
   # In src/specify_cli/events/reader.py (modify format_conflict_explanation)

   def format_conflict_explanation(self, conflict: ConflictInfo) -> str:
       """Format conflict with detailed merge rule explanation."""
       event_ids = [e.event_id for e in conflict.conflicting_events]
       event_details = [
           f"    - {e.event_id}: {e.payload.get('new_status')} (actor: {e.actor})"
           for e in conflict.conflicting_events
       ]

       return (
           f"Conflict detected for {conflict.entity_id} at clock {conflict.lamport_clock}:\n"
           f"  Concurrent events:\n"
           + "\n".join(event_details) + "\n"
           f"  Merge rule: {conflict.merge_rule} (Last-Write-Wins)\n"
           f"  Winner: {conflict.winning_event.event_id}\n"
           f"  Result: {conflict.entity_id} status = {conflict.winning_event.payload.get('new_status')}\n"
       )
   ```

**Files**:
- `src/specify_cli/events/reader.py` (modify: enhance conflict explanation)

**Validation**:
- [ ] Conflict logged to stderr (not stdout)
- [ ] Explanation includes: clock value, conflicting event IDs, merge rule, winner
- [ ] Shows payload details (e.g., new_status) for each conflicting event
- [ ] Test: Trigger conflict, verify detailed log output

**Edge Cases**:
- Conflict with identical payloads: Still logged (conflict exists even if outcome same)
- Missing payload fields: Uses .get() with defaults (no KeyError)

**Parallel?**: Yes - Enhancement of T032 (can proceed in parallel)

---

## Test Strategy

**No separate test files** (constitution: tests not explicitly requested).

**Validation approach**:
1. **T031**: Unit test - Group events by clock, identify duplicates
2. **T032**: Unit test - Sort by event_id, verify last event wins
3. **T033**: Integration test - Reconstruct status with conflicts, verify winning event used
4. **T034**: UI test - Run status with conflicts, verify warning shown
5. **T035**: Log test - Verify conflict explanation logged to stderr

**Conflict simulation test**:
```python
from specify_cli.events.store import EventStore
from specify_cli.events.reader import EventReader, ConflictDetector
from pathlib import Path
import json

# Setup
events_dir = Path("/tmp/test-lww/.kittify/events")
events_dir.mkdir(parents=True, exist_ok=True)

# Create JSONL with concurrent events
events_data = [
    {
        "event_id": "01AAAA000000000000000000AA",  # Earlier ULID
        "event_type": "WPStatusChanged",
        "event_version": 1,
        "lamport_clock": 10,
        "entity_id": "WP05",
        "entity_type": "WorkPackage",
        "timestamp": "2026-01-27T10:00:00Z",
        "actor": "agent-a",
        "causation_id": None,
        "correlation_id": None,
        "payload": {"feature_slug": "test", "old_status": "doing", "new_status": "for_review"}
    },
    {
        "event_id": "01ZZZZ999999999999999999ZZ",  # Later ULID (wins)
        "event_type": "WPStatusChanged",
        "event_version": 1,
        "lamport_clock": 10,  # Same clock!
        "entity_id": "WP05",
        "entity_type": "WorkPackage",
        "timestamp": "2026-01-27T10:00:01Z",
        "actor": "agent-b",
        "causation_id": None,
        "correlation_id": None,
        "payload": {"feature_slug": "test", "old_status": "doing", "new_status": "rejected"}
    }
]

# Write to JSONL
jsonl_file = events_dir / "2026-01-27.jsonl"
with open(jsonl_file, "w") as f:
    for event_data in events_data:
        f.write(json.dumps(event_data) + "\n")

# Reconstruct status
store = EventStore(Path("/tmp/test-lww"))
reader = EventReader(store)
status, conflicts = reader.reconstruct_wp_status("WP05", detect_conflicts=True)

# Verify LWW applied
assert status == "rejected", f"Expected 'rejected', got {status}"
assert len(conflicts) == 1, f"Expected 1 conflict, got {len(conflicts)}"
assert conflicts[0].winning_event.event_id == "01ZZZZ999999999999999999ZZ"

print("✓ LWW merge rule test passed")
```

---

## Risks & Mitigations

### Risk 1: LWW rule loses important state changes

**Impact**: User expects agent-a's transition to win, but agent-b wins due to later ULID

**Mitigation**:
- Both events preserved in event log (audit trail complete)
- Conflict warning shown to user (T034)
- Logged explanation shows which event won and why (T035)
- Users can manually inspect event log if needed

### Risk 2: Conflicts are common in practice (performance hit)

**Impact**: Conflict detection adds latency to every state reconstruction

**Mitigation**:
- Conflicts rare in CLI (single user per project, validated by research)
- Detection is O(n) pass (grouping by clock, lightweight)
- Can disable detection via parameter if needed (detect_conflicts=False)

### Risk 3: Merge rule is non-deterministic

**Impact**: Different agents reconstruct different state (violates determinism requirement)

**Mitigation**:
- ULID lexicographic sort is deterministic (same input → same output)
- No random tie-breaking (ULIDs are globally unique)
- Test validates determinism (run reconstruction twice, same result)

---

## Definition of Done Checklist

- [ ] T031: ConflictDetector.detect_conflicts() groups by clock, finds duplicates
- [ ] T031: ConflictInfo dataclass with conflicting_events and winning_event
- [ ] T031: `is_concurrent()` checks if events have same clock
- [ ] T032: `apply_lww_merge()` sorts by event_id (lexicographic)
- [ ] T032: Returns event with highest event_id
- [ ] T032: `format_conflict_explanation()` produces readable output
- [ ] T033: `reconstruct_wp_status()` enhanced to detect conflicts
- [ ] T033: Returns tuple: (status, conflicts)
- [ ] T033: Skips losing events during replay
- [ ] T033: Logs conflict explanations to stderr
- [ ] T034: `spec-kitty status` displays conflict warnings
- [ ] T034: Warning shows WP ID, clock, merge rule, result
- [ ] T035: Conflict resolutions logged with detailed explanation
- [ ] Conflict simulation test passes (LWW correctly applied)
- [ ] Determinism test passes (multiple runs produce same result)

---

## Review Guidance

**Key Acceptance Checkpoints**:

1. **T031 - Conflict Detection**:
   - ✓ Groups events by lamport_clock
   - ✓ Identifies clocks with >1 event
   - ✓ Returns ConflictInfo with all metadata

2. **T032 - LWW Merge Rule**:
   - ✓ Lexicographic ULID sorting
   - ✓ Last event wins (deterministic)
   - ✓ Works with 2, 3, or more concurrent events

3. **T033 - Integration**:
   - ✓ reconstruct_wp_status() returns (status, conflicts)
   - ✓ Skips losing events during replay
   - ✓ Logs conflicts to stderr

4. **T034 - UI Warning**:
   - ✓ Conflict warning shown in status output
   - ✓ Clear, actionable information

5. **T035 - Detailed Logging**:
   - ✓ Explanation includes all conflicting events
   - ✓ Shows merge rule applied
   - ✓ Shows winning event and result

**Reviewers should**:
- Run conflict simulation test (verify LWW applied)
- Check stderr output (verify detailed logging)
- Run status command with conflicts (verify warning shown)
- Test determinism (run twice, same result)

---

## Activity Log

- 2026-01-27T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

## Implementation Command

This WP depends on WP05. Implement from WP05's branch:

```bash
spec-kitty implement WP06 --base WP05
```

This will create workspace: `.worktrees/025-cli-event-log-integration-WP06/` branched from WP05.
