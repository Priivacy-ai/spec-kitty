---
work_package_id: WP05
title: Directive Schema Extension
lane: "done"
dependencies: [WP01]
base_branch: feature/agent-profile-implementation
base_commit: 319c155f7f3874a58a122a1c06dee35dea7f56c2
created_at: '2026-02-28T08:23:55.607022+00:00'
subtasks:
- T025
- T026
- T027
- T028
phase: Phase 1 - Foundation
assignee: ''
agent: codex
shell_pid: '112867'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-26T04:36:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Directive Schema Extension

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Extend `directive.schema.yaml` with 4 optional enrichment fields: `scope`, `procedures`, `integrity-rules`, `validation-criteria`
- Update `Directive` model to include these fields (if not already done in WP01)
- Existing minimal directives (stub format) MUST continue to validate unchanged
- Enriched directives (with new fields) MUST also validate
- Backward compatibility is mandatory

## Context & Constraints

- **Depends on WP01**: The `Directive` model and `DirectiveRepository` must already exist
- **Schema**: `src/doctrine/schemas/directive.schema.yaml` — currently has `additionalProperties: false`
- **Research decision R-002**: 4 fields cover most common doctrine_ref sections without over-engineering
- **DD-002**: Pure YAML with multiline string fields for enriched directives

## Subtasks & Detailed Guidance

### Subtask T025 – Update `directive.schema.yaml`

- **Purpose**: Add optional enrichment fields to the directive JSON Schema.
- **Steps**:
  1. Open `src/doctrine/schemas/directive.schema.yaml`
  2. Add these optional properties:
     ```yaml
     scope:
       type: string
       description: "When the directive applies and exceptions"
     procedures:
       type: array
       items:
         type: string
       description: "Ordered steps to follow"
     integrity-rules:
       type: array
       items:
         type: string
       description: "Hard constraints that must not be violated"
     validation-criteria:
       type: array
       items:
         type: string
       description: "How to verify compliance"
     ```
  3. Do NOT add these to the `required` list — they must be optional
  4. The `additionalProperties: false` constraint must still work (add the new properties to the `properties` block)
  5. Validate that existing directive files still pass schema validation
- **Files**: `src/doctrine/schemas/directive.schema.yaml` (update, ~10 lines added)
- **Notes**: Use YAML keys with hyphens (`integrity-rules`, `validation-criteria`) to match the existing `tactic-refs` convention. The Pydantic model aliases handle the Python-to-YAML mapping.

### Subtask T026 – Update Directive model with enrichment fields

- **Purpose**: Ensure the `Directive` Pydantic model has all enrichment fields.
- **Steps**:
  1. Open `src/doctrine/directives/models.py`
  2. Verify these fields exist (they should have been added in WP01 T002):
     - `scope: str | None = None`
     - `procedures: list[str] = Field(default_factory=list)`
     - `integrity_rules: list[str] = Field(default_factory=list, alias="integrity-rules")`
     - `validation_criteria: list[str] = Field(default_factory=list, alias="validation-criteria")`
  3. If WP01 already added these fields, this subtask is a verification step
  4. If any fields are missing, add them now
- **Files**: `src/doctrine/directives/models.py` (update if needed)
- **Notes**: This subtask may be a no-op if WP01 was thorough. The key value is explicit verification.

### Subtask T027 – Write backward-compatibility tests

- **Purpose**: Ensure existing minimal directives still validate after schema change.
- **Steps**:
  1. Create test that loads every existing shipped directive (minimal format)
  2. Validate each against the updated schema
  3. Assert zero validation errors for all existing directives
  4. Create a test with a deliberately minimal directive (only required fields) and verify it validates
- **Files**: `tests/doctrine/directives/test_schema_compatibility.py` (new, ~40 lines)
- **Notes**: This is the critical safety test — if existing directives break, the schema change is wrong.

### Subtask T028 – Write enriched-format tests

- **Purpose**: Verify new enrichment fields work correctly in schema and model.
- **Steps**:
  1. Create a test directive YAML with all enrichment fields populated:
     ```yaml
     schema-version: "1.0"
     id: DIRECTIVE_TEST
     title: Test Enriched Directive
     intent: "Test intent for enriched directive."
     enforcement: required
     scope: "Applies to all test code."
     procedures:
       - "Step 1: Write test"
       - "Step 2: Run test"
     integrity-rules:
       - "Tests must pass before merge"
     validation-criteria:
       - "All tests green in CI"
     ```
  2. Validate against schema — must pass
  3. Parse with `Directive` model — all fields must be populated
  4. Verify `scope` is a string, `procedures` is a list, etc.
  5. Test round-trip: create `Directive`, save via repository, reload, compare
- **Files**: `tests/doctrine/directives/test_schema_compatibility.py` (extend, ~40 lines added)

## Test Strategy

```bash
pytest tests/doctrine/directives/test_schema_compatibility.py -v
```

**Key test matrix**:

| Directive format | Schema valid? | Model loads? |
|-----------------|:---:|:---:|
| Minimal (existing) | Yes | Yes |
| Enriched (all fields) | Yes | Yes |
| Partial enrichment (some fields) | Yes | Yes |
| Invalid enrichment field type | No | No |

## Risks & Mitigations

- **Breaking existing directives**: Mitigated by T027 backward-compatibility tests run before any enrichment
- **YAML key naming**: Use hyphens in schema (`integrity-rules`) matching `tactic-refs` convention; Pydantic alias handles mapping

## Review Guidance

- Verify existing shipped directives still validate (run T027 tests)
- Verify `additionalProperties: false` still works after adding new properties
- Verify YAML key convention is consistent (`integrity-rules` not `integrity_rules` in YAML)

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

Depends on WP01:
```bash
spec-kitty implement WP05 --base WP01
```
- 2026-02-28T08:23:55Z – codex – shell_pid=112867 – lane=doing – Assigned agent via workflow command
- 2026-02-28T08:30:02Z – codex – shell_pid=112867 – lane=for_review – Ready for review: doctrine service + directive schema compatibility tests
- 2026-03-04T04:46:48Z – codex – shell_pid=112867 – lane=done – Reviewed and approved: Directive schema extension complete, 48 tests passing. DoctrineService also implemented here.
