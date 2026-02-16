---
work_package_id: WP08
title: Event Integration
lane: planned
dependencies: []
subtasks: [T036, T037, T038, T039]
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Event Integration

**ID**: WP08 **Priority**: P2 **Estimated Effort**: 2 days

## Objective

Implement event emission adapters that import Feature 007 canonical contracts and emit at middleware boundaries.

## Context

All state changes emit events. Import canonical events from spec_kitty_events.glossary.events (Feature 007).

**Events**: GlossaryScopeActivated, TermCandidateObserved, SemanticCheckEvaluated, GlossaryClarificationRequested, GlossaryClarificationResolved, GlossarySenseUpdated, GenerationBlockedBySemanticConflict, StepCheckpointed

**Design ref**: [contracts/events.md](../contracts/events.md)

## Implementation Command

```bash
spec-kitty implement WP08 --base WP07
```

---

## Subtasks

### T036: Event emission adapters

**Implementation** (events.py):
```python
try:
    from spec_kitty_events.glossary.events import (
        GlossaryScopeActivated,
        TermCandidateObserved,
        SemanticCheckEvaluated,
        # ... etc
    )
except ImportError:
    # Stub if package not available
    class GlossaryScopeActivated:
        pass
    # ...
```

---

### T037: Emit at middleware boundaries

Update all middleware to emit events:
- Extraction → TermCandidateObserved
- Semantic check → SemanticCheckEvaluated
- Gate → GenerationBlockedBySemanticConflict
- Clarification → GlossaryClarificationRequested/Resolved
- Checkpoint → StepCheckpointed

---

### T038: Event log persistence

Write events to `.kittify/events/glossary/{mission_id}.events.jsonl`.

---

### T039: Event emission tests

Verify payloads match Feature 007 schemas, ordering correct.

---

## Definition of Done

- [ ] 4 subtasks complete
- [ ] events.py: ~80 lines
- [ ] All 7 events emit correctly
- [ ] Tests >90% coverage

---

## Reviewer Guidance

**Focus**: Event payload correctness, persistence

**Acceptance**:
- [ ] Events match Feature 007 schemas
- [ ] JSONL persistence works
