---
work_package_id: WP04
title: Semantic Check & Conflict Detection
lane: "doing"
dependencies: []
base_branch: 2.x
base_commit: 50240be10a0ea2da7e20c8406142f76249a3f8b7
created_at: '2026-02-16T15:04:11.047257+00:00'
subtasks: [T016, T017, T018, T019, T020]
shell_pid: "84395"
agent: "coordinator"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Semantic Check & Conflict Detection

**ID**: WP04  
**Priority**: P1  
**Estimated Effort**: 2-3 days

## Objective

Implement term resolution against scope hierarchy, conflict classification (4 types), and severity scoring.

## Context

Semantic check middleware resolves extracted terms against the 4-tier scope hierarchy (mission_local → team_domain → audience_domain → spec_kitty_core) and detects conflicts:
- **Unknown**: No match in any scope
- **Ambiguous**: 2+ active senses, unqualified usage
- **Inconsistent**: LLM output contradicts active glossary
- **Unresolved_critical**: Critical term, low confidence, no resolved sense

**Design ref**: [data-model.md](../data-model.md) SemanticConflict

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

**Dependencies**: WP02 (glossary store), WP03 (extracted terms)

---

## Subtask Breakdown

### T016: Term resolution against scope hierarchy

**Implementation** (resolution.py):
```python
def resolve_term(
    surface: str,
    scopes: List[GlossaryScope],
    store: GlossaryStore
) -> List[TermSense]:
    """Resolve term against scope hierarchy."""
    scope_values = tuple(s.value for s in scopes)
    return store.lookup(surface, scope_values)
```

**Tests**: Resolution follows order, returns all matches across scopes.

---

### T017: Conflict classification

Classify resolution results into 4 conflict types.

**Logic**:
```python
def classify_conflict(
    term: TermSurface,
    resolution_results: List[TermSense],
    confidence: float
) -> Optional[ConflictType]:
    """Classify conflict type."""
    if not resolution_results:
        return ConflictType.UNKNOWN
    elif len(resolution_results) > 1:
        return ConflictType.AMBIGUOUS
    # INCONSISTENT and UNRESOLVED_CRITICAL require additional context
    # (LLM output analysis, step criticality) - defer to WP06
    return None  # No conflict
```

**Tests**: All 4 types classify correctly.

---

### T018: Severity scoring

Score severity based on step criticality + confidence.

**Scoring matrix**:
- High: (critical step + low confidence) OR ambiguous
- Medium: (non-critical + ambiguous) OR (unknown + medium confidence)
- Low: (inconsistent) OR (unknown + high confidence)

**Tests**: Matrix coverage, edge cases.

---

### T019: SemanticCheckMiddleware

Middleware that orchestrates resolution, classification, scoring, and emits SemanticCheckEvaluated.

**Implementation**:
```python
class SemanticCheckMiddleware:
    def __init__(self, glossary_store: GlossaryStore):
        self.store = glossary_store
    
    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        conflicts = []
        for extracted_term in context.extracted_terms:
            # Resolve
            senses = resolve_term(extracted_term.surface, SCOPE_RESOLUTION_ORDER, self.store)
            # Classify
            conflict_type = classify_conflict(extracted_term.surface, senses, extracted_term.confidence)
            if conflict_type:
                # Score severity
                severity = score_severity(conflict_type, extracted_term.confidence, context.step_criticality)
                # Create conflict
                conflict = SemanticConflict(...)
                conflicts.append(conflict)
        
        context.conflicts = conflicts
        # Emit SemanticCheckEvaluated
        return context
```

---

### T020: Semantic check tests

Unit + integration tests for resolution, classification, scoring, middleware.

**Coverage**:
- All 4 conflict types
- Severity edge cases
- Multi-scope resolution
- Middleware integration

---

## Definition of Done

- [ ] 5 subtasks complete
- [ ] resolution.py: ~60 lines
- [ ] conflict.py: ~100 lines (classification + scoring)
- [ ] middleware.py: SemanticCheckMiddleware ~80 lines
- [ ] Tests >90% coverage
- [ ] mypy --strict passes

---

## Testing Strategy

```bash
pytest tests/specify_cli/glossary/test_resolution.py -v
pytest tests/specify_cli/glossary/test_conflict.py -v
pytest tests/specify_cli/glossary/test_middleware.py::test_semantic_check -v
```

---

## Reviewer Guidance

**Focus**:
1. Conflict classification accuracy
2. Severity scoring calibration
3. Scope resolution correctness

**Acceptance**:
- [ ] All 4 conflict types detected
- [ ] Severity scores align with risk

## Activity Log

- 2026-02-16T15:04:11Z – coordinator – shell_pid=84395 – lane=doing – Assigned agent via workflow command
