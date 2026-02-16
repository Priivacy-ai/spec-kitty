---
work_package_id: WP07
title: Checkpoint/Resume Mechanism
lane: planned
dependencies: []
subtasks: [T030, T031, T032, T033, T034, T035]
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Checkpoint/Resume Mechanism

**ID**: WP07 **Priority**: P2 **Estimated Effort**: 2-3 days

## Objective

Implement event-sourced checkpoint/resume with input hash verification for cross-session recovery.

## Context

Checkpoint/resume enables async conflict resolution. Before blocking, emit StepCheckpointed event with minimal payload. On resume, load checkpoint, verify input hash, restore context.

**Design ref**: [research.md](../research.md) Finding 4

## Implementation Command

```bash
spec-kitty implement WP07 --base WP05
```

Can run in parallel with WP06.

---

## Subtasks

### T030: StepCheckpoint data model

**Implementation** (checkpoint.py):
```python
@dataclass
class StepCheckpoint:
    mission_id: str
    run_id: str
    step_id: str
    strictness: Strictness
    scope_refs: List[ScopeRef]
    input_hash: str  # SHA256 of sorted JSON inputs
    cursor: str  # e.g., "pre_generation_gate"
    retry_token: str  # UUID
    timestamp: datetime
```

---

### T031: Checkpoint emission

Emit StepCheckpointed event before generation gate.

---

### T032: Checkpoint loading

Load latest StepCheckpointed for step_id from event log.

---

### T033: Input hash verification

Compute SHA256 of current inputs, compare with checkpoint.input_hash. If mismatch, prompt for confirmation.

**Implementation**:
```python
import hashlib
import json

def compute_input_hash(inputs: dict) -> str:
    canonical = json.dumps(inputs, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()

def verify_input_hash(checkpoint: StepCheckpoint, current_inputs: dict) -> bool:
    current_hash = compute_input_hash(current_inputs)
    return current_hash == checkpoint.input_hash
```

---

### T034: ResumeMiddleware

Load checkpoint, verify hash, restore context, resume from cursor.

---

### T035: Checkpoint/resume tests

Test emission, loading, verification, resume flow.

---

## Definition of Done

- [ ] 6 subtasks complete
- [ ] checkpoint.py: ~100 lines
- [ ] Tests >90% coverage

---

## Reviewer Guidance

**Focus**: Hash verification, cross-session recovery

**Acceptance**:
- [ ] Checkpoint emitted correctly
- [ ] Resume restores state
- [ ] Hash mismatch prompts user
