---
work_package_id: WP03
title: Profile Inheritance — Merge-by-Default with Excluding
lane: done
dependencies: [WP02]
requirement_refs:
- FR-016
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase B - Core Profile Infrastructure
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-22T11:50:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
---

# Work Package Prompt: WP03 – Profile Inheritance — Merge-by-Default with Excluding

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address the Review Feedback section first.

---

## Review Feedback

*[Empty — populated by `/spec-kitty.review` if work is returned.]*

---

## Dependency Rebase Guidance

Depends on **WP02** (Phase A gate). Phase A must be fully merged before starting this WP.

```bash
spec-kitty implement WP03 --base WP02
```

---

## Objectives & Success Criteria

- `resolve_profile()` merges list-type fields (`directive-references`, `capabilities`, `canonical-verbs`, `mode-defaults`) by union (no duplicates) rather than child-replaces-parent.
- `AgentProfile` model has an `excluding` field supporting field-level (`excluding: [directive-references]`) and value-level (`excluding: {directive-references: [DIRECTIVE_010]}`) forms.
- `resolve_profile()` applies `excluding` removals after union merge.
- Missing parent raises `KeyError` with a clear message (not warn-and-return).
- All 6 US-6 acceptance scenarios pass.
- Existing profile tests continue to pass.
- Requirements FR-016, C-006, SC-006 satisfied.

## Context & Constraints

- **Plan**: `kitty-specs/057-doctrine-stack-init-and-profile-integration/plan.md` → WP-B1
- **Spec**: US-6, FR-016, C-006, SC-006
- **Primary files**: `src/doctrine/agent_profiles/profile.py`, `src/doctrine/agent_profiles/repository.py`
- **Test file**: `tests/doctrine/test_profile_inheritance.py` (new)
- **ATDD constraint**: Write tests first (T009); they MUST fail before T010-T013 begin.
- **Start command**: `spec-kitty implement WP03 --base WP02`

## Subtasks & Detailed Guidance

### Subtask T009 – Write ATDD acceptance tests (tests first)

- **Purpose**: The 6 US-6 scenarios are the acceptance gate. Tests must be red before implementation.
- **Files**: Create `tests/doctrine/test_profile_inheritance.py`.
- **Steps**:
  1. Read `tests/doctrine/` for existing test patterns (fixtures, `AgentProfileRepository` setup).
  2. Write 6 test functions covering US-6 scenarios:
     - `test_unspecified_fields_inherited` — child with `specializes-from: implementer`, unspecified fields come from parent.
     - `test_child_overrides_scalar_field` — child's `primary_focus` overrides parent's.
     - `test_list_fields_merged_by_union` — child adding one directive → resolved profile has parent + child directives, no duplicates.
     - `test_excluding_value_removed` — `excluding: {directive-references: [DIRECTIVE_010]}` → resolved profile omits DIRECTIVE_010 from merged directives.
     - `test_multi_level_chain` — grandchild → child → parent; inheritance cascades correctly at each level.
     - `test_missing_parent_raises_key_error` — profile with `specializes-from: nonexistent` → `resolve_profile()` raises `KeyError`.
  3. Run `pytest tests/doctrine/test_profile_inheritance.py -v` — all must FAIL (red). If any pass, that behavior already exists; note it.
- **ZOMBIES reference**: Zero (no parent) = grandchild with 0 ancestors; One = single-level inherit; Many = multi-level chain; Boundary = excluding nonexistent value (silent); Interface = resolve_profile return type is AgentProfile; Exceptions = cycle → ValueError, missing parent → KeyError; Simple = basic override.

### Subtask T010 – Add `excluding` field to `AgentProfile` model

- **Purpose**: Without this field on the Pydantic model, the YAML `excluding` key cannot be loaded and applied.
- **Files**: `src/doctrine/agent_profiles/profile.py`
- **Steps**:
  1. Read `profile.py` lines 126-180 (AgentProfile class). Note the existing field definitions and their aliases.
  2. Add the `excluding` field after `specializes_from`:
     ```python
     # Supports both forms:
     #   excluding: [field_name]           → removes entire field from resolved result
     #   excluding: {field_name: [value]}  → removes specific values from list field
     excluding: list[str] | dict[str, list[str]] | None = Field(default=None, alias="excluding")
     ```
  3. Run `mypy src/doctrine/agent_profiles/profile.py` and fix any type errors.
  4. Run `pytest tests/doctrine/ -x` — existing tests must still pass.

### Subtask T011 – Update `resolve_profile()` to use union merge for list fields

- **Purpose**: Currently list fields use child-replaces-parent (via `shallow_merge()`). Change to union merge for the list-type profile fields.
- **Files**: `src/doctrine/agent_profiles/repository.py`
- **Steps**:
  1. Read `resolve_profile()` in its entirety (lines 432-494 approx).
  2. The current `shallow_merge()` function replaces lists. Introduce `union_merge()` that merges list fields by union:
     ```python
     LIST_FIELDS = frozenset({
         "capabilities", "directive-references", "canonical-verbs", "mode-defaults",
     })

     def union_merge(parent_data: dict, child_data: dict) -> dict:
         merged = parent_data.copy()
         for key, child_value in child_data.items():
             parent_value = merged.get(key)
             if key in LIST_FIELDS and isinstance(parent_value, list) and isinstance(child_value, list):
                 # Union: parent items + child items not already in parent
                 seen = {str(item) for item in parent_value}
                 merged[key] = parent_value + [item for item in child_value if str(item) not in seen]
             elif isinstance(parent_value, dict) and isinstance(child_value, dict):
                 nested = parent_value.copy()
                 nested.update(child_value)
                 merged[key] = nested
             else:
                 merged[key] = child_value
         return merged
     ```
  3. Replace `shallow_merge` call in the chain-building loop with `union_merge`.
  4. Run `pytest tests/doctrine/test_profile_inheritance.py::test_list_fields_merged_by_union -v` — should now pass. The other 5 tests may still fail (missing T010/T012/T013 changes).
  5. Run `pytest tests/doctrine/ -x` to catch regressions in existing tests.

### Subtask T012 – Apply `excluding` removals post-merge

- **Purpose**: After union merge, apply the child profile's `excluding` declarations to strip unwanted inherited values.
- **Files**: `src/doctrine/agent_profiles/repository.py`
- **Steps**:
  1. In `resolve_profile()`, after the chain-building loop produces the `merged` dict, add an exclusion pass:
     ```python
     # Apply excluding from the original (child) profile
     excluding = profile.excluding
     if excluding is not None:
         if isinstance(excluding, list):
             # Field-level: remove entire fields
             for field_name in excluding:
                 merged.pop(field_name, None)
         elif isinstance(excluding, dict):
             # Value-level: remove specific values from list fields
             for field_name, values_to_remove in excluding.items():
                 if field_name in merged and isinstance(merged[field_name], list):
                     remove_set = {str(v) for v in values_to_remove}
                     merged[field_name] = [
                         item for item in merged[field_name]
                         if str(item) not in remove_set
                     ]
     ```
  2. For multi-level chains, exclusion is applied from the **resolving profile's** `excluding` field (not each ancestor's). This is the simplest semantics. Clarify in a comment if needed.
  3. Run `pytest tests/doctrine/test_profile_inheritance.py::test_excluding_value_removed -v` — should pass.
  4. Run `pytest tests/doctrine/test_profile_inheritance.py::test_multi_level_chain -v` — may or may not pass depending on test fixture.

### Subtask T013 – Fix missing-parent handling to raise `KeyError`

- **Purpose**: The current warn-and-return is a silent failure. Per spec (US-6 Scenario 6), missing parent must raise a clear error.
- **Files**: `src/doctrine/agent_profiles/repository.py`
- **Steps**:
  1. Find the missing-parent block in `resolve_profile()` (lines ~455-464 approx):
     ```python
     parent = self.get(parent_id)
     if parent is None:
         warnings.warn(...)
         return profile  # ← change this
     ```
  2. Replace warn-and-return with:
     ```python
     parent = self.get(parent_id)
     if parent is None:
         raise KeyError(
             f"Profile '{profile_id}' references missing parent '{parent_id}'. "
             "Ensure the parent profile exists in shipped/ or _proposed/ before resolving."
         )
     ```
  3. Remove the `warnings` import if it is no longer used elsewhere in the file.
  4. Run the full ATDD suite: `pytest tests/doctrine/test_profile_inheritance.py -v` — all 6 tests should now pass (green).
  5. Run `pytest tests/doctrine/ -x` — all existing tests must pass.

## Test Strategy

```bash
# ATDD acceptance tests (must be green after all subtasks)
rtk test pytest tests/doctrine/test_profile_inheritance.py -v

# Full doctrine test suite (regression)
rtk test pytest tests/doctrine/ -x

# Type check
mypy --strict src/doctrine/agent_profiles/profile.py src/doctrine/agent_profiles/repository.py

# Lint
rtk ruff check src/doctrine/agent_profiles/
```

## Risks & Mitigations

- **Existing tests break**: Some tests may rely on child-replaces-parent list semantics. After T011, run `pytest tests/doctrine/ -x` and fix any regressions before marking WP complete.
- **Excluding nonexistent value**: Must be silently ignored (not raise). Test this with T009 boundary case.
- **Multi-level excluding semantics**: If ambiguous, implement "leaf profile's `excluding` applies to the final merged result" and document in a code comment.

## Review Guidance

- Reviewer should create a temporary test child profile in `_proposed/` with `specializes-from: implementer` and `excluding: {directive-references: [<some_directive>]}` and verify resolution works end-to-end via `AgentProfileRepository`.
- Confirm `KeyError` is raised for missing parent (run `repo.resolve_profile("orphan-profile")` where `orphan-profile` has `specializes-from: nonexistent`).
- Check that cycle detection still raises `ValueError` (not changed by this WP).

## Activity Log

- 2026-03-22T11:50:00Z – system – lane=planned – Prompt created.
