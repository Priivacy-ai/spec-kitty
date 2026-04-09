# Data Model: WPState/Lane Consumer Migration

**Mission**: 080-wpstate-lane-consumer-strangler-fig-phase-2  
**Date**: 2026-04-09 (Amended)

---

## Overview

Two primary data structures define the migration:

1. **WPState.is_run_affecting** (new property) — Encapsulates active WP state query
2. **AgentAssignment** (new value object) — Represents resolved agent assignment
3. **WPMetadata.resolved_agent()** (new method) — Unifies legacy agent coercion

---

## WPState.is_run_affecting

### Location

`src/specify_cli/status/wp_state.py`

### Definition

```python
@property
def is_run_affecting(self) -> bool:
    """Return True if WP affects execution progress.
    
    A WP is "run-affecting" if it is active (planned through approved).
    Does not include terminal or blocked lanes.
    
    Returns:
        True if lane in {planned, claimed, in_progress, for_review, in_review, approved}
        False if lane in {done, blocked, canceled}
    
    Usage:
        if state.is_run_affecting:
            # Route to implementation or review
    """
    return self.lane in {
        Lane.PLANNED,
        Lane.CLAIMED,
        Lane.IN_PROGRESS,
        Lane.FOR_REVIEW,
        Lane.IN_REVIEW,
        Lane.APPROVED,
    }
```

### Rationale

Consumers previously used ad-hoc lane tuples `(Lane.IN_PROGRESS, Lane.FOR_REVIEW, ...)` to determine if a WP affects execution. This property centralizes that logic and provides a single point of truth.

### Test Coverage

- Behavior test: 9 lanes → verify correct True/False for each
- Examples:
  - `is_run_affecting("planned")` → True
  - `is_run_affecting("approved")` → True
  - `is_run_affecting("done")` → False
  - `is_run_affecting("blocked")` → False
  - `is_run_affecting("canceled")` → False

---

## AgentAssignment

### Location

`src/specify_cli/status/models.py`

### Definition

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class AgentAssignment:
    """Resolved agent assignment with complete context.
    
    Represents the fully-resolved agent assigned to a work package,
    including the tool (AI agent type), model, optional profile ID, and role.
    
    This value object is the output of legacy coercion and fallback resolution
    from WPMetadata.resolved_agent(). It provides a clean, typed interface for
    consumers to access agent assignment context.
    
    Attributes:
        tool: AI agent identifier (e.g., 'claude', 'copilot', 'gemini', 'cursor').
        model: Model identifier (e.g., 'claude-opus-4-6', 'gpt-4-turbo').
        profile_id: Optional profile identifier for agent configuration override.
        role: Optional role for this assignment (e.g., 'reviewer', 'implementer').
    
    Example:
        >>> assignment = wp_metadata.resolved_agent()
        >>> print(assignment.tool)  # 'claude'
        >>> print(assignment.model)  # 'claude-opus-4-6'
        >>> print(assignment.profile_id)  # None or 'profile-123'
        >>> print(assignment.role)  # 'reviewer' or None
    """
    tool: str
    model: str
    profile_id: Optional[str] = None
    role: Optional[str] = None
```

### Properties

| Property | Type | Required | Example |
|----------|------|----------|---------|
| `tool` | str | Yes | "claude", "copilot", "gemini" |
| `model` | str | Yes | "claude-opus-4-6", "gpt-4-turbo" |
| `profile_id` | Optional[str] | No | "profile-ai-reviewer", None |
| `role` | Optional[str] | No | "reviewer", "implementer", None |

### Immutability

Frozen dataclass ensures:
- No field mutations after creation
- Safe to share between functions
- Hashable (can be used as dict key)

### Test Coverage

**Legacy Coercion Scenarios** (tested in WP02):
1. String agent → AgentAssignment with tool=string, model=fallback
2. Dict agent → AgentAssignment with tool/model/profile_id/role from dict
3. None agent → AgentAssignment with tool=default, model=fallback
4. Model field fallback → AgentAssignment with model from model field
5. Agent profile field fallback → AgentAssignment with profile_id from agent_profile field
6. Role field fallback → AgentAssignment with role from role field

---

## WPMetadata.resolved_agent()

### Location

`src/specify_cli/tasks_support.py` and related frontmatter handling

### Definition

```python
def resolved_agent(self) -> AgentAssignment:
    """Resolve agent assignment with legacy coercion and fallback.
    
    Unifies agent metadata resolution across all legacy formats and fallback fields.
    Handles string agents, dict agents, None, and falls back to model, agent_profile,
    and role fields when the primary agent field is incomplete.
    
    Fallback Order:
    1. Direct AgentAssignment from agent field (if already an AgentAssignment)
    2. String agent field → tool=value, model=self.model (fallback to default)
    3. Dict agent field → tool/model/profile_id/role from dict, fallback to other fields
    4. None/missing agent → tool=default, model=self.model (fallback to default)
    5. Fallback to agent_profile field for profile_id
    6. Fallback to role field for role
    7. Return sensible defaults for missing values
    
    Returns:
        AgentAssignment with all resolved values (no None fields except optional ones)
    
    Examples:
        >>> metadata = WPMetadata(agent="claude", model="claude-opus-4-6")
        >>> assignment = metadata.resolved_agent()
        >>> assignment.tool  # "claude"
        >>> assignment.model  # "claude-opus-4-6"
        
        >>> metadata = WPMetadata(agent={"tool": "copilot", "model": "gpt-4"})
        >>> assignment = metadata.resolved_agent()
        >>> assignment.tool  # "copilot"
        >>> assignment.model  # "gpt-4"
        
        >>> metadata = WPMetadata(agent=None, model="default-model", role="reviewer")
        >>> assignment = metadata.resolved_agent()
        >>> assignment.tool  # "unknown" (default)
        >>> assignment.model  # "default-model"
        >>> assignment.role  # "reviewer"
    """
```

### Implementation Algorithm

```python
def resolved_agent(self) -> AgentAssignment:
    # Step 1: If already AgentAssignment, return it
    if isinstance(self.agent, AgentAssignment):
        return self.agent
    
    # Step 2-4: Extract from string/dict/None
    tool = None
    model = None
    profile_id = None
    role = None
    
    if isinstance(self.agent, str):
        tool = self.agent
        model = self.model or "unknown-model"
    elif isinstance(self.agent, dict):
        tool = self.agent.get("tool")
        model = self.agent.get("model")
        profile_id = self.agent.get("profile_id")
        role = self.agent.get("role")
    else:
        tool = "unknown"
        model = self.model or "unknown-model"
    
    # Step 5-7: Fallback and normalize
    if not profile_id:
        profile_id = self.agent_profile
    if not role:
        role = self.role
    
    if not tool:
        tool = "unknown"
    if not model:
        model = "unknown-model"
    
    return AgentAssignment(
        tool=tool,
        model=model,
        profile_id=profile_id,
        role=role,
    )
```

### Test Coverage

All legacy input scenarios:
- String agent with/without model field
- Dict agent with various field combinations
- None/missing agent with fallback fields
- Edge cases: empty strings, None values, conflicting fields
- Verify no exceptions raised for any input combination
- Verify sensible defaults for all missing fields

---

## Note: WPState.is_terminal

`WPState.is_terminal` already exists in the current tree. This mission does **not** introduce it. It is used internally in status module but **not** exposed as a consumer replacement for merge validation.

Merge validation explicitly checks `approved | done` using typed Lane enum, not delegated to `is_terminal` (which is cleanup logic: done/canceled only).

---

## Type Safety & Validation

### Lane Enum Boundaries

Lane is defined as a string enum with 9 valid values:

```python
class Lane(str, Enum):
    PLANNED = "planned"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    FOR_REVIEW = "for_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELED = "canceled"
```

**Guarantee**: WPState.lane is always one of these 9 values.

### AgentAssignment Immutability

`frozen=True` ensures:
- No mutations after creation
- Safe for concurrent access
- Can be cached or memoized

---

## Integration Points

### Consumer Access Patterns

**Before** (raw lane-string):
```python
if snapshot.get("lane") in ("done", "approved"):
    # ...

# Or manual agent extraction
tool = wp.agent
model = wp.model or "default"
```

**After** (typed state):
```python
state = wp_state_for(snapshot)
if state.is_run_affecting:  # True for all active lanes
    # ...

# Or unified agent resolution
assignment = wp_metadata.resolved_agent()
tool = assignment.tool
model = assignment.model
```

### Data Flow

```
Event Log (status.events.jsonl)
    ↓
reduce() function
    ↓
WPSnapshot (dict with lane string)
    ↓
wp_state_for() constructor
    ↓
WPState (typed object with is_run_affecting property)
    ↓
Consumer queries via is_run_affecting
```

---

## Backward Compatibility

### During Migration (Slices 1-4)

- New consumers call state properties
- Old code paths may coexist temporarily
- Both work safely without conflicts

### After Final Slice (WP07)

- All consumers use WPState properties
- No raw lane strings in consumer code
- Full encapsulation achieved

---

## Change Log

- **2026-04-09 (Initial)**: Full data model for 15 consumers, 3 new interfaces
- **2026-04-09 (Amendment)**: Trimmed to 7 consumers, 2 new interfaces. Removed is_terminal (already exists). Focused on is_run_affecting + AgentAssignment only.
