---
work_package_id: WP03
title: Term Extraction Implementation
lane: "doing"
dependencies: []
base_branch: 2.x
base_commit: 28a2fdf773a7b7aae3371a4aec50602bdb6dbf23
created_at: '2026-02-16T14:05:12.902282+00:00'
subtasks: [T010, T011, T012, T013, T014, T015]
agent: "codex"
shell_pid: "80719"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Term Extraction Implementation

**ID**: WP03  
**Priority**: P1  
**Estimated Effort**: 3-4 days

## Objective

Implement term extraction using metadata hints + deterministic heuristics, with scope-aware normalization and confidence scoring. No LLM in hot path (<100ms target).

## Context

Extraction middleware is the first stage of the pipeline. It scans step inputs/outputs for domain terms using:
- Metadata hints (glossary_watch_terms - highest confidence)
- Deterministic heuristics (quoted phrases, acronyms, casing patterns)
- Scope-aware normalization (lowercase, trim, stem-light)
- Confidence scoring (metadata > pattern > weak heuristic)

**Design ref**: [research.md](../research.md) Finding 3

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

Can run in parallel with WP02 after WP01 completes.

---

## Subtask Breakdown

### T010: Metadata hints extraction

Extract terms from `glossary_watch_terms`, `glossary_aliases`, `glossary_exclude_terms`, `glossary_fields` metadata.

**Implementation** (extraction.py):
```python
def extract_metadata_hints(metadata: dict) -> List[str]:
    """Extract terms from metadata hints (highest confidence)."""
    terms = set()
    
    # Explicit watch terms
    if "glossary_watch_terms" in metadata:
        terms.update(metadata["glossary_watch_terms"])
    
    # Aliases (map to canonical)
    if "glossary_aliases" in metadata:
        for alias, canonical in metadata["glossary_aliases"].items():
            terms.add(canonical)
    
    return list(terms)
```

**Tests**: Verify watch terms extracted, aliases mapped, exclude terms filtered.

---

### T011: Deterministic heuristics

Implement pattern matching for quoted phrases, acronyms, snake_case, camelCase, repeated nouns.

**Patterns**:
- Quoted: `r'"([^"]+)"'`
- Acronyms: `r'\b[A-Z]{2,5}\b'`
- Snake_case: `r'\b[a-z]+_[a-z_]+\b'`
- camelCase: `r'\b[a-z]+[A-Z][a-zA-Z]+\b'`
- Repeated: Count noun phrases appearing 3+ times

**Tests**: Each pattern extracts correctly, no false positives on common words.

---

### T012: Scope-aware normalization

Normalize extracted terms: lowercase, trim, stem-light (plural → singular).

**Implementation**:
```python
def normalize_term(surface: str) -> str:
    """Normalize term surface."""
    # Lowercase + trim
    normalized = surface.lower().strip()
    
    # Stem-light: simple plural removal
    if normalized.endswith('s') and len(normalized) > 3:
        # workspaces -> workspace
        singular = normalized[:-1]
        if is_likely_word(singular):  # Heuristic check
            return singular
    
    return normalized
```

**Tests**: Normalization is idempotent, plurals convert correctly.

---

### T013: Confidence scoring

Score confidence: metadata (1.0) > explicit pattern (0.8) > weak heuristic (0.5).

**Implementation**:
```python
def score_confidence(term: str, source: str) -> float:
    """Score extraction confidence."""
    if source == "metadata_hint":
        return 1.0
    elif source in ["quoted_phrase", "acronym", "casing_pattern"]:
        return 0.8
    elif source == "repeated_noun":
        return 0.5
    else:
        return 0.3  # Default low
```

**Tests**: Scores match expected values, metadata always highest.

---

### T014: GlossaryCandidateExtractionMiddleware

Middleware that orchestrates extraction logic and emits TermCandidateObserved events.

**Implementation** (middleware.py):
```python
class GlossaryCandidateExtractionMiddleware:
    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        # 1. Extract from metadata hints
        # 2. Extract from heuristics (scan glossary_fields)
        # 3. Normalize all terms
        # 4. Score confidence
        # 5. Emit TermCandidateObserved for each
        # 6. Add to context.extracted_terms
        return context
```

**Tests**: Full pipeline extracts terms, emits events, adds to context.

---

### T015: Extraction tests

Unit tests for each extractor + integration test for middleware.

**Test coverage**:
- Metadata extraction
- Each heuristic pattern
- Normalization edge cases (acronyms, single-letter words)
- Confidence scoring
- Middleware integration (mocked context)

---

## Definition of Done

- [ ] 6 subtasks complete
- [ ] extraction.py: 4 extractors + normalization + scoring (~150 lines)
- [ ] middleware.py: GlossaryCandidateExtractionMiddleware (~80 lines)
- [ ] Tests: >90% coverage, all edge cases tested
- [ ] Performance: <100ms for typical step input (100-500 words)
- [ ] mypy --strict passes

---

## Testing Strategy

```bash
pytest tests/specify_cli/glossary/test_extraction.py -v
pytest tests/specify_cli/glossary/test_middleware.py::test_extraction -v
pytest --cov=src/specify_cli/glossary/extraction --cov-report=term-missing
```

**Benchmark**: `pytest tests/specify_cli/glossary/test_extraction.py::test_extraction_performance -v`

---

## Risks & Mitigations

**Risk**: False positives from heuristics  
**Mitigation**: Confidence scoring, low-confidence terms auto-add as draft (not blocking)

**Risk**: Performance on large inputs  
**Mitigation**: Limit scan to first 1000 words, cache regex patterns

---

## Reviewer Guidance

**Focus**:
1. Heuristic precision (check false positive rate)
2. Performance (<100ms)
3. Confidence scores align with accuracy

**Acceptance**:
- [ ] Extracts known terms correctly
- [ ] No false positives on common words ("the", "and")
- [ ] Performance <100ms

## Activity Log

- 2026-02-16T13:29:13Z – claude-sonnet – shell_pid=27938 – lane=doing – Assigned agent via workflow command
- 2026-02-16T13:57:27Z – claude-sonnet – shell_pid=27938 – lane=planned – Reclaimed: stale workspace, no implementation
- 2026-02-16T14:14:14Z – claude-sonnet – shell_pid=51478 – lane=for_review – Ready for review: term extraction implementation complete with tests (99% coverage, <100ms performance, mypy strict)
- 2026-02-16T14:15:08Z – codex – shell_pid=57393 – lane=doing – Started review via workflow command
- 2026-02-16T14:17:21Z – codex – shell_pid=57393 – lane=planned – Moved to planned
- 2026-02-16T14:28:55Z – coordinator – shell_pid=64243 – lane=doing – Started implementation via workflow command
- 2026-02-16T14:32:07Z – coordinator – shell_pid=64243 – lane=for_review – Fixed: added comprehensive type validation for all metadata fields (glossary_watch_terms, glossary_aliases, glossary_exclude_terms) with 12 regression tests. Graceful degradation on malformed metadata.
- 2026-02-16T14:32:47Z – codex – shell_pid=66189 – lane=doing – Started review via workflow command
- 2026-02-16T14:35:41Z – codex – shell_pid=66189 – lane=planned – Moved to planned
- 2026-02-16T14:36:31Z – coordinator – shell_pid=69040 – lane=doing – Started implementation via workflow command
- 2026-02-16T14:40:27Z – coordinator – shell_pid=69040 – lane=for_review – Fixed: metadata.glossary_fields now implemented with regression tests (cycle 3/3)
- 2026-02-16T14:41:05Z – codex – shell_pid=71204 – lane=doing – Started review via workflow command
- 2026-02-16T14:43:34Z – codex – shell_pid=71204 – lane=planned – Moved to planned
- 2026-02-16T14:45:43Z – coordinator – shell_pid=73336 – lane=doing – Started implementation via workflow command
- 2026-02-16T14:46:47Z – coordinator – shell_pid=73336 – lane=doing – Acknowledged review feedback - fixing stemming corruption and event emission (cycle 4)
- 2026-02-16T14:50:05Z – coordinator – shell_pid=73336 – lane=for_review – Fixed: stemming bug resolved (class/glass/address/status preserved), event emission implemented with proper stub interface, 101 tests passing, mypy strict clean (cycle 4 arbiter override - final attempt)
- 2026-02-16T14:50:48Z – codex – shell_pid=77135 – lane=doing – Started review via workflow command
- 2026-02-16T14:52:47Z – codex – shell_pid=77135 – lane=planned – Moved to planned
- 2026-02-16T14:53:40Z – coordinator – shell_pid=79292 – lane=doing – Started implementation via workflow command
- 2026-02-16T14:56:07Z – coordinator – shell_pid=79292 – lane=for_review – Fixed: acronym extraction now filters common words (AND, THE, etc.) with 2 regression tests. All 103 tests passing (cycle 5 trivial fix).
- 2026-02-16T14:56:33Z – codex – shell_pid=80719 – lane=doing – Started review via workflow command
