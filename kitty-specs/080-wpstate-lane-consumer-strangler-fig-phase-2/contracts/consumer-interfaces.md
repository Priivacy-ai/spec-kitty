# Consumer Migration Contracts

**Mission**: 080-wpstate-lane-consumer-strangler-fig-phase-2  
**Date**: 2026-04-09 (Amended)

---

## Overview

This document defines the migration interface contract for each of the 4 slices targeting 7 verified WP lane consumers. Each contract specifies:

1. **Old Pattern**: Current raw lane-string logic in the consumer
2. **New Pattern**: Migrated code using typed/state semantics
3. **Backward Compatibility**: How compat is preserved during transition
4. **Test Verification**: How to verify the migration doesn't break existing behavior

---

## Universal Migration Pattern

All consumers follow a common refactoring pattern:

### Before (Raw Lane-String)

```python
from specify_cli.status.models import Lane

# Direct enum matching or raw string comparisons
if wp_snapshot.get("lane") in ("done", "approved"):
    # Action A
elif Lane(wp_snapshot.get("lane")) in (Lane.PLANNED, Lane.CLAIMED):
    # Action B
elif wp_snapshot.get("lane") == "for_review":
    # Action C
```

### After (Typed State)

```python
from specify_cli.status.models import wp_state_for, Lane

# Construct state object; delegate to state properties/methods
state = wp_state_for(wp_snapshot)

if state.is_run_affecting:  # True for planned...approved
    # Action B
elif state.progress_bucket() == "review":  # for_review, in_review
    # Action C
```

---

## Slice 1: Status Display

**File**: `src/specify_cli/agent_utils/status.py`

**Purpose**: Display kanban board with WPs grouped by progress bucket.

### Before Pattern

```python
# Manual lane bucketing for display categories
for wp_id, state_dict in snapshot.work_packages.items():
    lane_str = state_dict.get("lane", "planned")

    if lane_str in ("planned",):
        category = "not_started"
    elif lane_str in ("claimed", "in_progress", "blocked"):
        category = "in_flight"
    elif lane_str in ("for_review", "in_review", "approved"):
        category = "review"
    elif lane_str in ("done", "canceled"):
        category = "terminal"
```

### After Pattern

```python
# Delegate to state.progress_bucket()
from specify_cli.status.wp_state import wp_state_for

for wp_id, state_dict in snapshot.work_packages.items():
    state = wp_state_for(state_dict.get("lane", "planned"))
    category = state.progress_bucket()  # Returns: "not_started", "in_flight", "review", "terminal"
```

### Backward Compatibility

- `progress_bucket()` method already exists in WPState
- No changes to external API of show_kanban_status()
- Display behavior unchanged

### Test Verification

```python
def test_kanban_progress_bucket_unchanged():
    # Verify progress_bucket() maps lanes as shipped in WPState
    test_cases = [
        ("planned", "not_started"),
        ("claimed", "in_flight"),
        ("in_progress", "in_flight"),
        ("blocked", "in_flight"),
        ("for_review", "review"),
        ("in_review", "review"),
        ("approved", "review"),
        ("done", "terminal"),
        ("canceled", "terminal"),
    ]
    for lane_str, expected_bucket in test_cases:
        state = wp_state_for(lane_str)
        assert state.progress_bucket() == expected_bucket
```

---

## Slice 2: Runtime Routing & Agent Resolution

**Files**: `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/cli/commands/agent/workflow.py`

### runtime_bridge.py: Lane Membership Tests

**Purpose**: Decide if WP should be routed to implement or review.

#### Before Pattern

```python
# Raw lane tuple checks for "run-affecting" WPs
RUN_AFFECTING_LANES = (
    Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.APPROVED, 
    Lane.PLANNED, Lane.CLAIMED
)

if lane in RUN_AFFECTING_LANES:
    return "route_to_implementation"
elif lane in (Lane.DONE, Lane.CANCELED):
    return "accept"  # Terminal
```

#### After Pattern

```python
# Use state.is_run_affecting
state = wp_state_for(snapshot)

if state.is_run_affecting:
    return "route_to_implementation"
elif state.lane in (Lane.DONE, Lane.CANCELED):
    return "accept"
```

#### Backward Compatibility

- `is_run_affecting` property provides same information as old tuple check
- Lane enum unchanged
- No change to routing logic

#### Test Verification

```python
def test_is_run_affecting_matches_tuple_check():
    # Verify is_run_affecting == (lane in RUN_AFFECTING_LANES)
    RUN_AFFECTING = ("planned", "claimed", "in_progress", "for_review", 
                     "in_review", "approved")
    
    for lane_str in ["planned", "claimed", "in_progress", "for_review", 
                     "in_review", "approved", "done", "blocked", "canceled"]:
        state = wp_state_for({"lane": lane_str})
        expected = lane_str in RUN_AFFECTING
        assert state.is_run_affecting == expected
```

---

### workflow.py: Agent Assignment Resolution

**Purpose**: Resolve agent assignment and routing context for workflow.

#### Before Pattern

```python
# Manual string/dict coercion + fallback
if isinstance(wp.agent, str):
    tool = wp.agent
    model = wp.model or "unknown-model"
    profile_id = None
elif isinstance(wp.agent, dict):
    tool = wp.agent.get("tool", "unknown")
    model = wp.agent.get("model", wp.model or "unknown-model")
    profile_id = wp.agent.get("profile_id")
else:
    tool = "unknown"
    model = wp.model or "unknown-model"
    profile_id = None
```

#### After Pattern

```python
# Unified agent resolution via resolved_agent()
from specify_cli.status.models import AgentAssignment

assignment = wp_metadata.resolved_agent()

tool = assignment.tool
model = assignment.model
profile_id = assignment.profile_id
role = assignment.role
```

#### Backward Compatibility

- `resolved_agent()` handles all legacy formats
- Fallback order preserved
- No change to workflow API

#### Test Verification

```python
def test_resolved_agent_unifies_legacy_formats():
    # String agent
    metadata1 = WPMetadata(agent="claude", model="claude-opus-4-6")
    assert metadata1.resolved_agent().tool == "claude"
    
    # Dict agent
    metadata2 = WPMetadata(agent={"tool": "copilot", "model": "gpt-4"})
    assert metadata2.resolved_agent().tool == "copilot"
    
    # None agent
    metadata3 = WPMetadata(agent=None, model="default-model")
    assert metadata3.resolved_agent().model == "default-model"
```

---

## Slice 3: Review & Tasks

**Files**: `src/specify_cli/review/arbiter.py`, `src/specify_cli/scripts/tasks/tasks_cli.py`

### arbiter.py: Review Check

**Purpose**: Determine if WP was previously in for_review before being moved back.

#### Before Pattern

```python
# Direct Lane enum matching
latest = wp_events[-1]
if latest.from_lane == Lane.FOR_REVIEW and latest.to_lane == Lane.PLANNED:
    return True  # WP was in for_review, now moved back
```

#### After Pattern

```python
# Typed Lane comparison (same, but via WPState if needed)
from specify_cli.status.models import Lane

latest = wp_events[-1]
if Lane(latest.from_lane) == Lane.FOR_REVIEW and Lane(latest.to_lane) == Lane.PLANNED:
    return True
```

#### Backward Compatibility

- Lane enum values unchanged
- Same logic, just type-safe
- No API change

#### Test Verification

```python
def test_arbiter_review_check():
    event = {"from_lane": "for_review", "to_lane": "planned"}
    assert Lane(event["from_lane"]) == Lane.FOR_REVIEW
    assert Lane(event["to_lane"]) == Lane.PLANNED
```

---

### tasks_cli.py: Lane Access & Display

**Purpose**: Get current lane from event log and display task status.

#### Before Pattern

```python
# String lane from frontmatter/event log
lane = get_lane_from_frontmatter(wp_path)

if lane in ("planned", "claimed"):
    display = "Planned"
elif lane in ("in_progress",):
    display = "In Progress"
elif lane in ("for_review", "in_review"):
    display = "In Review"
```

#### After Pattern

```python
# Typed lane access
from specify_cli.status.lane_reader import get_wp_lane
from specify_cli.status.wp_state import wp_state_for

lane_str = str(get_wp_lane(feature_dir, wp_id))
state = wp_state_for(lane_str)

bucket = state.progress_bucket()
display_map = {
    "not_started": "Planned",
    "in_flight": "In Progress",
    "review": "In Review",
    "terminal": "Complete",
}
display = display_map.get(bucket, "Unknown")
```

#### Backward Compatibility

- `get_wp_lane()` still returns string
- `progress_bucket()` implements same mapping logic
- Display output unchanged

#### Test Verification

```python
def test_tasks_cli_lane_display():
    # Verify progress_bucket() maps to the shipped four-bucket vocabulary
    test_cases = [
        ("planned", "not_started"),
        ("in_progress", "in_flight"),
        ("for_review", "review"),
        ("done", "terminal"),
    ]
    for lane_str, expected_bucket in test_cases:
        state = wp_state_for(lane_str)
        assert state.progress_bucket() == expected_bucket
```

---

## Slice 4: Merge Validation & Recovery

**Files**: `src/specify_cli/cli/commands/merge.py`, `src/specify_cli/lanes/recovery.py`

### merge.py: Merge-Ready Check

**Purpose**: Verify WP is in approved or done lane before merging.

#### Before Pattern

```python
# Direct lane check for merge-ready
lane_str = str(get_wp_lane(feature_dir, wp_id))
if lane_str not in ("done", "approved"):
    incomplete.append(f"{wp_id}={lane_str}")
```

#### After Pattern

```python
# Typed Lane enum check (explicit approved|done distinction)
from specify_cli.status.models import Lane

lane = Lane(str(get_wp_lane(feature_dir, wp_id)))
if lane not in (Lane.DONE, Lane.APPROVED):
    incomplete.append(f"{wp_id}={lane.value}")
```

#### Backward Compatibility

- Merge validation logic unchanged
- Error messages identical
- `is_terminal` is NOT used here (it's only done/canceled for cleanup logic)

#### Test Verification

```python
def test_merge_ready_check_preserved():
    # Verify approved|done check is explicit and preserved
    from specify_cli.status.models import Lane
    
    ready_lanes = (Lane.DONE, Lane.APPROVED)
    
    test_cases = [
        ("done", True),
        ("approved", True),
        ("in_progress", False),
        ("for_review", False),
        ("claimed", False),
    ]
    for lane_str, should_be_ready in test_cases:
        lane = Lane(lane_str)
        is_ready = lane in ready_lanes
        assert is_ready == should_be_ready
```

---

### recovery.py: Lane Transitions

**Purpose**: Advance stalled WPs through allowed recovery transitions.

#### Before Pattern

```python
# Hardcoded recovery transition tuples
_RECOVERY_CEILING = Lane.IN_PROGRESS
_RECOVERY_TRANSITIONS = {
    Lane.PLANNED: [Lane.CLAIMED, Lane.IN_PROGRESS],
    Lane.CLAIMED: [Lane.IN_PROGRESS],
}

# Check if transition allowed
if current_lane not in _RECOVERY_TRANSITIONS:
    raise RecoveryError(f"Cannot recover from {current_lane}")
if target_lane not in _RECOVERY_TRANSITIONS[current_lane]:
    raise RecoveryError(f"Cannot transition {current_lane} → {target_lane}")
```

#### After Pattern

```python
# Use transition validation from status module
from specify_cli.status.transitions import validate_transition

if not validate_transition(current_lane, target_lane):
    raise RecoveryError(f"Invalid: {current_lane} → {target_lane}")
```

#### Backward Compatibility

- `validate_transition()` enforces same rules as hardcoded tuples
- Recovery behavior unchanged
- Transition logic centralized

#### Test Verification

```python
def test_recovery_transitions_preserved():
    from specify_cli.status.transitions import validate_transition
    from specify_cli.status.models import Lane
    
    # planned → claimed, in_progress allowed
    assert validate_transition(Lane.PLANNED, Lane.CLAIMED) == True
    assert validate_transition(Lane.PLANNED, Lane.IN_PROGRESS) == True
    
    # claimed → in_progress allowed
    assert validate_transition(Lane.CLAIMED, Lane.IN_PROGRESS) == True
    
    # planned → done NOT allowed (in recovery)
    assert validate_transition(Lane.PLANNED, Lane.DONE) == False
```

---

## General Testing Strategy

### Behavior Tests (New Code)

For WPState.is_run_affecting:
- Test all 9 lanes
- Verify correct True/False for each

For AgentAssignment + resolved_agent():
- String/dict/None inputs
- Fallback scenarios
- Edge cases

### Regression Tests (Each Consumer)

For each migrated consumer:
- Run existing test suite; verify all pass
- Compare old vs new output; verify identical

### Integration Tests (Per Slice)

After each slice:
- Run full test suite
- Test CLI commands end-to-end
- Verify no breakage

---

## Backward Compatibility Verification Checklist

- [ ] No new lane-string literals introduced
- [ ] All state property calls properly handled
- [ ] CLI output unchanged
- [ ] Event log format unchanged
- [ ] Frontmatter format unchanged
- [ ] API signatures unchanged (new methods only, no breaking changes)
- [ ] All 9 lanes properly handled

---

## Change Log

- **2026-04-09 (Initial)**: Contracts for 15 consumers, 6 slices
- **2026-04-09 (Amendment)**: Trimmed to 7 consumers, 4 slices. Removed dashboard/scanner.py, tasks.py, and other broadened files.
