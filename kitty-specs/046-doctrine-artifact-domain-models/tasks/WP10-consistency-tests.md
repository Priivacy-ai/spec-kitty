---
work_package_id: WP10
title: Consistency Tests & Existing Test Updates
lane: "done"
dependencies:
- WP01
- WP07
- WP08
- WP09
subtasks:
- T059
- T060
- T061
- T062
- T063
phase: Phase 2 - Content
assignee: ''
agent: ''
shell_pid: ''
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-26T04:36:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP10 – Consistency Tests & Existing Test Updates

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create cross-artifact reference integrity tests (every `tactic-ref` in every directive resolves to an existing tactic)
- Create enriched directive content validation tests (no stub directives remain)
- Update existing tests broken by file relocation (YAML files moved to `shipped/`)
- All existing doctrine tests pass with relocated files
- `pytest tests/doctrine/` passes with zero failures

## Context & Constraints

- **Depends on WP01-WP04**: File relocation must be complete
- **Depends on WP07-WP09**: Enriched and new directives must exist
- **Key files to update**: `tests/doctrine/test_schema_validation.py`, `tests/doctrine/test_artifact_compliance.py`
- **Existing test patterns**: Search for path references like `src/doctrine/directives/*.yaml`

## Subtasks & Detailed Guidance

### Subtask T059 – Create `tests/doctrine/test_consistency.py`

- **Purpose**: Cross-artifact reference integrity — verify tactic_refs resolve.
- **Steps**:
  1. Create `tests/doctrine/test_consistency.py`
  2. Test: Load all shipped directives via `DirectiveRepository`
  3. For each directive, extract `tactic_refs`
  4. For each tactic ref, verify `TacticRepository().get(ref)` returns non-None
  5. Test: Load all shipped tactics, extract references (TacticReference objects)
  6. For each reference, verify the referenced artifact exists in its repository
  7. Test: No duplicate IDs across all artifact types
  8. Test: All YAML files in `shipped/` directories validate against their schemas
- **Files**: `tests/doctrine/test_consistency.py` (new, ~80 lines)
- **Notes**: Use `DoctrineService` for convenient cross-repository access. Import all repository types.

### Subtask T060 – Create `tests/doctrine/test_enriched_directives.py`

- **Purpose**: Verify all shipped directives have substantive enriched content.
- **Steps**:
  1. Create `tests/doctrine/test_enriched_directives.py`
  2. Test: Every shipped directive has `intent` longer than one sentence (>50 chars)
  3. Test: Every shipped directive has non-empty `scope`
  4. Test: Every shipped directive has at least `procedures` or `validation-criteria` populated
  5. Test: No directive has placeholder text like "TODO", "TBD", "[NEEDS CLARIFICATION]"
  6. Test: Directive 004 specifically has `tactic-refs` containing `["acceptance-test-first", "tdd-red-green-refactor", "zombies-tdd"]`
- **Files**: `tests/doctrine/test_enriched_directives.py` (new, ~60 lines)

### Subtask T061 – Update `tests/doctrine/test_schema_validation.py`

- **Purpose**: Fix path references broken by file relocation.
- **Steps**:
  1. Read current `tests/doctrine/test_schema_validation.py`
  2. Identify all path references to YAML files (e.g., `src/doctrine/directives/*.yaml`)
  3. Update to new `shipped/` paths (e.g., `src/doctrine/directives/shipped/*.yaml`)
  4. Update for all artifact types: directives, tactics, styleguides, toolguides, paradigms
  5. Add paradigm schema validation (new schema from WP04)
  6. Run and verify all tests pass
- **Files**: `tests/doctrine/test_schema_validation.py` (update)
- **Notes**: This is the most critical update — existing CI relies on these tests

### Subtask T062 – Update `tests/doctrine/test_artifact_compliance.py`

- **Purpose**: Fix path references broken by file relocation.
- **Steps**:
  1. Read current `tests/doctrine/test_artifact_compliance.py`
  2. Update path references to `shipped/` subdirectories
  3. Run and verify all tests pass
- **Files**: `tests/doctrine/test_artifact_compliance.py` (update)

### Subtask T063 – Verify all existing doctrine tests pass

- **Purpose**: Full test suite regression check.
- **Steps**:
  1. Run `pytest tests/doctrine/ -v` — capture full output
  2. Identify any remaining failures from file relocation
  3. Fix any additional test files with stale path references
  4. Run `mypy src/doctrine/ --strict` — verify type safety
  5. Run `ruff check src/doctrine/` — verify linting
  6. All tests must pass before marking this WP complete
- **Files**: Various test files (fix as needed)
- **Notes**: This is the integration gate — nothing should be broken after all WPs

## Test Strategy

```bash
# Full regression
pytest tests/doctrine/ -v

# Just consistency and enrichment
pytest tests/doctrine/test_consistency.py tests/doctrine/test_enriched_directives.py -v

# Type safety
mypy src/doctrine/ --strict
```

## Risks & Mitigations

- **Undiscovered path references**: Grep entire test suite for old paths before declaring complete
  ```bash
  grep -r "doctrine/directives/" tests/ --include="*.py" | grep -v "shipped"
  ```
- **Tactic refs not yet resolved**: WP11 may create new tactics — consistency test may need to be conditional or WP10 must run after WP11

## Review Guidance

- Verify consistency test covers ALL cross-artifact reference types
- Verify enriched directive test catches stub/placeholder content
- Verify no old path references remain in test files
- Verify full `pytest tests/doctrine/` passes

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

Depends on WP01-04 and WP07-09:
```bash
spec-kitty implement WP10 --base WP07
```
Then merge other dependencies:
```bash
cd .worktrees/046-doctrine-artifact-domain-models-WP10/
git merge <WP08-branch>
git merge <WP09-branch>
```
- 2026-03-04T04:46:54Z – unknown – lane=done – Reviewed and approved: docs and zero-unresolved tactic-ref audit recorded.
