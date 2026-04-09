# Quickstart: WPState/Lane Consumer Migration

**Mission**: 080-wpstate-lane-consumer-strangler-fig-phase-2  
**Date**: 2026-04-09 (Amended)

---

## Quick Reference: Before & After

Use this section to quickly understand how to migrate a consumer.

---

## Pattern 1: Progress Bucketing

### Before: Manual Lane Bucketing

```python
# agent_utils/status.py: manual bucketing for display
lane_str = wp_snapshot.get("lane", "planned")

if lane_str in ("planned",):
    progress = "Not Started"
elif lane_str in ("claimed", "in_progress", "blocked"):
    progress = "In Progress"
elif lane_str in ("for_review", "in_review", "approved"):
    progress = "Review"
elif lane_str in ("done", "canceled"):
    progress = "Complete"
```

### After: Use State Properties

```python
from specify_cli.status.wp_state import wp_state_for

state = wp_state_for(lane_str)
bucket = state.progress_bucket()  # "not_started", "in_flight", "review", "terminal"

progress_map = {
    "not_started": "Not Started",
    "in_flight": "In Progress",
    "review": "Review",
    "terminal": "Complete",
}
progress = progress_map[bucket]
```

**Key Change**: Delegate bucketing to `state.progress_bucket()` instead of duplicating lane logic.

---

## Pattern 2: Routing Decisions (Run-Affecting Check)

### Before: Raw Lane Tuple Membership

```python
# next/runtime_bridge.py: manual tuple for active WPs
RUN_AFFECTING_LANES = (
    Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.APPROVED, 
    Lane.PLANNED, Lane.CLAIMED
)

if lane in RUN_AFFECTING_LANES:
    action = "route_to_implementation"
elif lane in (Lane.DONE, Lane.CANCELED):
    action = "accept"
```

### After: Use State Property

```python
from specify_cli.status.wp_state import wp_state_for

state = wp_state_for(lane)

if state.is_run_affecting:
    action = "route_to_implementation"
elif state.lane in (Lane.DONE, Lane.CANCELED):
    action = "accept"
```

**Key Change**: Use `state.is_run_affecting` instead of custom lane tuples.

---

## Pattern 3: Agent Assignment Resolution

### Before: Manual String/Dict Coercion + Fallback

```python
# cli/commands/agent/workflow.py: complex logic scattered
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

### After: Use Resolved Agent

```python
from specify_cli.status.wp_metadata import WPMetadata

assignment = wp_metadata.resolved_agent()  # returns AgentAssignment

tool = assignment.tool
model = assignment.model
profile_id = assignment.profile_id
role = assignment.role
```

**Key Change**: Use `WPMetadata.resolved_agent()` (defined in `specify_cli.status.wp_metadata`) for unified agent resolution with fallback.

---

## Pattern 4: Arbiter Review Checks

### Before: Manual Lane Enum Matching

```python
# review/arbiter.py: direct enum comparison
latest = wp_events[-1]
if latest.from_lane == Lane.FOR_REVIEW and latest.to_lane == Lane.PLANNED:
    return True  # WP was in for_review, now moved back
```

### After: Typed Lane Comparison

```python
from specify_cli.status.models import Lane

latest = wp_events[-1]
if Lane(latest.from_lane) == Lane.FOR_REVIEW and Lane(latest.to_lane) == Lane.PLANNED:
    return True
```

**Key Change**: Use typed Lane enum instead of string comparisons.

---

## Pattern 5: Task Script Lane Access

### Before: Manual Lane Bucketing for Display

```python
# scripts/tasks/tasks_cli.py: hardcoded lane → display
lane = get_lane_from_frontmatter(wp_path)

if lane in ("planned", "claimed"):
    display = "Planned"
elif lane in ("in_progress",):
    display = "In Progress"
elif lane in ("for_review", "in_review"):
    display = "In Review"
```

### After: Use progress_bucket()

```python
from specify_cli.status.wp_state import wp_state_for
from specify_cli.status.lane_reader import get_wp_lane

lane_str = str(get_wp_lane(feature_dir, wp_id))
state = wp_state_for(lane_str)
bucket = state.progress_bucket()

display_map = {
    "not_started": "Planned",
    "in_flight": "In Progress",
    "review": "In Review",
    "terminal": "Complete",
}
display = display_map[bucket]
```

**Key Change**: Delegate lane bucketing to `state.progress_bucket()`.

---

## Pattern 6: Merge Validation (Approved|Done Check)

### Before: Manual Lane String Check

```python
# cli/commands/merge.py: explicit string check for merge-ready
lane_str = str(get_wp_lane(feature_dir, wp_id))
if lane_str not in ("done", "approved"):
    incomplete.append(f"{wp_id}={lane_str}")
```

### After: Typed Lane Enum Check

```python
from specify_cli.status.models import Lane

lane = Lane(str(get_wp_lane(feature_dir, wp_id)))
if lane not in (Lane.DONE, Lane.APPROVED):
    incomplete.append(f"{wp_id}={lane.value}")
```

**Key Change**: Use typed Lane enum; preserve approved|done distinction explicitly (NOT is_terminal).

---

## Pattern 7: Recovery Mode Transitions

### Before: Hardcoded Transition Tuples

```python
# lanes/recovery.py: hardcoded recovery transitions
_RECOVERY_TRANSITIONS = {
    Lane.PLANNED: [Lane.CLAIMED, Lane.IN_PROGRESS],
    Lane.CLAIMED: [Lane.IN_PROGRESS],
}

if current_lane not in _RECOVERY_TRANSITIONS:
    raise RecoveryError(f"Cannot recover from {current_lane}")
```

### After: Delegate to Status Module

```python
from specify_cli.status.transitions import validate_transition

if not validate_transition(current_lane, target_lane):
    raise RecoveryError(f"Invalid: {current_lane} → {target_lane}")
```

**Key Change**: Use `validate_transition()` from status module instead of hardcoding rules.

---

## Common Pitfalls & Solutions

### Pitfall 1: Using is_terminal for Merge Validation

❌ **Wrong**:
```python
if state.is_terminal:
    # WP is ready to merge
```

✓ **Right**:
```python
from specify_cli.status.models import Lane

if lane in (Lane.DONE, Lane.APPROVED):
    # WP is ready to merge
```

**Why**: `is_terminal` is only done/canceled (cleanup logic). Merge-ready is approved|done (must be explicit).

---

### Pitfall 2: Reimplementing Lane Buckets Instead of Using progress_bucket()

❌ **Wrong**:
```python
if lane in ("for_review", "in_review", "approved"):
    category = "review"
```

✓ **Right**:
```python
state = wp_state_for(lane)
category = state.progress_bucket()  # Returns "review" for for_review/in_review/approved
```

**Why**: `progress_bucket()` is the authoritative bucketing; duplication risks divergence.

---

### Pitfall 3: Not Using Resolved Agent

❌ **Wrong**:
```python
tool = wp.agent  # May be string, dict, or None
```

✓ **Right**:
```python
assignment = wp_metadata.resolved_agent()
tool = assignment.tool  # Always valid string
```

**Why**: `resolved_agent()` unifies all legacy formats; consumer doesn't need to handle variations.

---

### Pitfall 4: Using String Lane Comparisons in New Code

❌ **Wrong**:
```python
if state_dict.get("lane") == "for_review":
    # ...
```

✓ **Right**:
```python
state = wp_state_for(state_dict.get("lane", "planned"))
if state.progress_bucket() == "review":
    # ...
```

**Why**: Typed state prevents typos and ensures consistency.

---

## Testing Your Migration

### Quick Test: is_run_affecting

```python
from specify_cli.status.models import Lane
from specify_cli.status.wp_state import wp_state_for

# Test is_run_affecting
state_planned = wp_state_for(Lane.PLANNED)
assert state_planned.is_run_affecting is True

state_done = wp_state_for(Lane.DONE)
assert state_done.is_run_affecting is False
```

### Quick Test: Agent Assignment

```python
from specify_cli.status.models import AgentAssignment

assignment = wp_metadata.resolved_agent()
assert isinstance(assignment, AgentAssignment)
assert isinstance(assignment.tool, str) and assignment.tool != ""
assert isinstance(assignment.model, str) and assignment.model != ""
```

### Quick Test: progress_bucket()

```python
from specify_cli.status.wp_state import wp_state_for

assert wp_state_for("for_review").progress_bucket() == "review"
assert wp_state_for("in_review").progress_bucket() == "review"
assert wp_state_for("approved").progress_bucket() == "review"
assert wp_state_for("done").progress_bucket() == "terminal"
assert wp_state_for("in_progress").progress_bucket() == "in_flight"
assert wp_state_for("planned").progress_bucket() == "not_started"
```

### Quick Test: Regression

```python
# Old code
old_category = "review" if lane in ("for_review", "in_review", "approved") else "other"

# New code
new_category = wp_state_for(lane).progress_bucket()

# Verify mapping unchanged
assert (old_category == "review") == (new_category == "review")
```

---

## When to Use Each Interface

| Interface | Use When | Consumer |
|-----------|----------|----------|
| `state.is_run_affecting` | Checking if WP is active (not terminal, not blocked) | runtime_bridge.py |
| `state.progress_bucket()` | Bucketing lanes for display/logic | status.py, tasks_cli.py |
| `wp_metadata.resolved_agent()` | Getting agent assignment with fallback | workflow.py |
| `Lane(str)` enum | Type-safe lane membership checks | arbiter.py, merge.py, recovery.py |
| `validate_transition()` | Checking allowed lane transitions | recovery.py |

---

## Workflow: Migrating a Consumer

1. **Identify raw lane usage**: `grep -n "get.*lane\|\.lane\|Lane\." file.py`
2. **Construct state object** (if needed): `state = wp_state_for(wp_snapshot)` at the beginning
3. **Replace tuple checks**: `if lane in (A, B):` → `if state.is_run_affecting:`
4. **Replace hardcoded buckets**: Custom grouping → `state.progress_bucket()`
5. **Replace agent coercion**: Manual string/dict logic → `wp_metadata.resolved_agent()`
6. **Add tests**: Regression tests comparing old vs new output
7. **Verify**: Run existing test suite; all pass with same behavior

---

## Useful Function Signatures

```python
# Import these at the top of your consumer
from specify_cli.status.models import Lane, AgentAssignment
from specify_cli.status.wp_state import wp_state_for
from specify_cli.status.wp_metadata import WPMetadata
from specify_cli.status.lane_reader import get_wp_lane
from specify_cli.status.transitions import validate_transition

# Create state from a lane value (enum or string)
state = wp_state_for(lane)  # accepts Lane or str

# Use state properties/methods
is_active = state.is_run_affecting  # bool: True for active lanes
bucket = state.progress_bucket()  # str: "not_started", "in_flight", "review", "terminal"
lane_enum = state.lane  # Lane enum for type-safe comparisons

# Resolve agent assignment (typed AgentAssignment boundary)
assignment = wp_metadata.resolved_agent()  # AgentAssignment
tool = assignment.tool  # str
model = assignment.model  # str
profile_id = assignment.profile_id  # Optional[str]
role = assignment.role  # Optional[str]

# Validate transitions (recovery mode, etc.)
ok, error = validate_transition(from_lane, to_lane)  # (bool, Optional[str])

# Get lane from event log
lane_str = str(get_wp_lane(feature_dir, wp_id))  # str: one of 9 lane values
```

---

## 7 Verified Consumers in This Mission

1. **agent_utils/status.py** — Progress bucketing (Slice 1)
2. **next/runtime_bridge.py** — Routing with is_run_affecting (Slice 2)
3. **cli/commands/agent/workflow.py** — Agent resolution (Slice 2)
4. **review/arbiter.py** — Review checks with typed Lane (Slice 3)
5. **scripts/tasks/tasks_cli.py** — Task script display (Slice 3)
6. **cli/commands/merge.py** — Merge validation (approved|done) (Slice 4)
7. **lanes/recovery.py** — Recovery transitions (Slice 4)

---

## Change Log

- **2026-04-09 (Initial)**: Quickstart for 15 consumers, 8 patterns
- **2026-04-09 (Amendment)**: Trimmed to 7 consumers, 7 patterns. Removed patterns for broadened consumers. Emphasized approved|done vs is_terminal distinction.
