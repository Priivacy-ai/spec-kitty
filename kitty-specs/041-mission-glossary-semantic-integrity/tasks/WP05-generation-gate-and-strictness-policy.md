---
work_package_id: WP05
title: Generation Gate & Strictness Policy
lane: planned
dependencies: []
subtasks: [T021, T022, T023, T024]
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Generation Gate & Strictness Policy

**ID**: WP05 **Priority**: P1 (MVP blocker) **Estimated Effort**: 1-2 days

## Objective

Implement generation gate that blocks LLM generation on unresolved high-severity conflicts, with configurable strictness policy (off/medium/max) and precedence resolution.

## Context

Generation gate is the enforcement point. It evaluates conflicts and strictness mode to decide: pass, warn, or block generation.

**Strictness modes**:
- off: No blocking
- medium (default): Block only high-severity
- max: Block any unresolved conflict

**Precedence**: global → mission → step → runtime override

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

---

## Subtasks

### T021: StrictnessPolicy

Implement precedence resolution (global → mission → step → runtime).

**Implementation** (strictness.py):
```python
class Strictness(Enum):
    OFF = "off"
    MEDIUM = "medium"
    MAX = "max"

def resolve_strictness(
    global_default: Strictness,
    mission_override: Optional[Strictness],
    step_override: Optional[Strictness],
    runtime_override: Optional[Strictness],
) -> Strictness:
    """Resolve strictness with precedence."""
    return (runtime_override or step_override or mission_override or global_default)
```

**Tests**: Precedence works correctly.

---

### T022: Gate decision logic

Implement should_block() based on strictness + conflicts.

**Logic**:
```python
def should_block(strictness: Strictness, conflicts: List[SemanticConflict]) -> bool:
    if strictness == Strictness.OFF:
        return False
    elif strictness == Strictness.MEDIUM:
        return any(c.severity == Severity.HIGH for c in conflicts)
    elif strictness == Strictness.MAX:
        return len(conflicts) > 0
```

**Tests**: All combinations of strictness + severity.

---

### T023: GenerationGateMiddleware

Middleware that blocks generation by raising BlockedByConflict.

**Implementation**:
```python
class GenerationGateMiddleware:
    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        strictness = resolve_strictness(...)
        if should_block(strictness, context.conflicts):
            # Emit GenerationBlockedBySemanticConflict
            raise BlockedByConflict(context.conflicts)
        return context
```

---

### T024: Gate tests

Test all strictness modes, precedence, blocking behavior.

---

## Definition of Done

- [ ] 4 subtasks complete
- [ ] strictness.py: ~50 lines
- [ ] middleware.py: GenerationGateMiddleware ~40 lines
- [ ] Tests >90% coverage
- [ ] All strictness modes work correctly

---

## Testing

```bash
pytest tests/specify_cli/glossary/test_strictness.py -v
pytest tests/specify_cli/glossary/test_middleware.py::test_generation_gate -v
```

---

## Reviewer Guidance

**Focus**: Precedence correctness, blocking behavior

**Acceptance**:
- [ ] medium blocks only high-severity
- [ ] off never blocks
- [ ] Precedence works
