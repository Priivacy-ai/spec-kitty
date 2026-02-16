---
work_package_id: WP09
title: Middleware Pipeline Integration
lane: planned
dependencies: []
subtasks: [T040, T041, T042, T043]
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Middleware Pipeline Integration

**ID**: WP09 **Priority**: P2 **Estimated Effort**: 2-3 days

## Objective

Integrate middleware pipeline into mission primitive execution, with metadata-driven attachment.

## Context

Connect all pieces: attach pipeline to primitive execution via `glossary_check` metadata.

## Implementation Command

```bash
spec-kitty implement WP09 --base WP08
```

---

## Subtasks

### T040: PrimitiveExecutionContext extension

Add glossary fields: extracted_terms, conflicts, strictness, checkpoint.

---

### T041: GlossaryMiddlewarePipeline class

Compose middleware in order, execute sequentially.

**Implementation**:
```python
class GlossaryMiddlewarePipeline:
    def __init__(self, middleware: List[GlossaryMiddleware]):
        self.middleware = middleware
    
    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        for mw in self.middleware:
            context = mw.process(context)
        return context
```

---

### T042: Metadata-driven attachment

Read `glossary_check` from mission.yaml, attach pipeline if enabled.

---

### T043: Full pipeline integration tests

End-to-end: extract → check → gate → clarify → resume.

---

## Definition of Done

- [ ] 4 subtasks complete
- [ ] Pipeline executes full flow
- [ ] Integration tests pass

---

## Reviewer Guidance

**Focus**: Pipeline composition, attachment correctness

**Acceptance**:
- [ ] Full flow works end-to-end
- [ ] Metadata controls attachment
