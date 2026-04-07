---
work_package_id: WP08
title: Dashboard API TypedDict Contracts (#361 Phase 1)
dependencies: [WP04, WP06]
requirement_refs:
- FR-015
- FR-016
- NFR-006
- NFR-007
planning_base_branch: feature/metadata-state-type-hardening
merge_target_branch: feature/metadata-state-type-hardening
branch_strategy: Planning artifacts for this feature were generated on feature/metadata-state-type-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/metadata-state-type-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
- T042
- T043
- T044
phase: Phase 4 - Infrastructure & Cross-Cutting
assignee: ''
agent: "opencode"
shell_pid: "152804"
history:
- at: '2026-04-06T06:15:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/dashboard/api_types.py
execution_mode: code_change
lane: planned
agent_profile: python-implementer
owned_files:
- src/specify_cli/dashboard/api_types.py
- src/specify_cli/dashboard/handlers/features.py
- src/specify_cli/dashboard/handlers/api.py
- src/specify_cli/dashboard/static/dashboard/dashboard.js
- tests/test_dashboard/test_api_contract.py
task_type: implement
---

# Work Package Prompt: WP08 – Dashboard API TypedDict Contracts (#361 Phase 1)

## IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- **Objective**: Define `TypedDict` response shapes for all JSON dashboard endpoints. Migrate handler methods to construct responses through these types. Write a JS-to-Python contract test. Apply Boy Scout fixes to `dashboard.js` and handler files.
- **Feedback display addendum**: Own the human-facing display of persisted review feedback references and content once canonical state surfaces provide them. WP08 is responsible for rendering rejected-review feedback discoverably in dashboard/API-facing outputs; canonical state propagation of `review_ref` is owned by WP05.
- **SC-008**: A dashboard API contract test validates that all JSON endpoint response shapes match their `TypedDict` definitions and that the JS frontend references the same keys.
- **FR-015**: `TypedDict` response shapes defined in `dashboard/api_types.py` for all JSON endpoints.
- **FR-016**: Contract test validates JS frontend key alignment with Python types.
- **NFR-006**: Dashboard API responses produce identical structure and values before and after.
- **NFR-007**: `mypy` passes on handler files; new code does not increase error count.
- **NFR-007a**: Rejected-review feedback display must not invent or mutate review state; it renders canonically sourced `review_ref`/feedback only.

## Context & Constraints

- **Upstream issue**: #361 — dashboard API type safety (Phase 1 only)
- **Data model**: `kitty-specs/065-wp-metadata-state-type-hardening/data-model.md` (Dashboard API Response Types section)
- **Plan**: `kitty-specs/065-wp-metadata-state-type-hardening/plan.md` (WP08 section)
- **Prerequisites**: WP04 (WPMetadata migration in `scanner.py`) and WP06 (WPState migration in `scanner.py`). Both must complete before dashboard TypedDict work can safely assess final response shapes.
- **Rebased baseline note**: Review-feedback evidence and handoff semantics are already part of the current baseline. WP08 is limited to typed response contracts and human-facing rendering of canonically sourced review feedback; it must not invent new persistence or transition semantics for `review_ref`.

**TypedDict definitions** (from data-model.md):
```python
class ArtifactInfo(TypedDict):
    exists: bool
    mtime: float | None
    size: int | None

class KanbanStats(TypedDict):
    total: int
    planned: int
    doing: int
    for_review: int
    in_review: int   # Added: FR-012a promotes in_review to first-class lane
    approved: int
    done: int

class KanbanTaskData(TypedDict):
    id: str
    title: str
    lane: str
    subtasks: list[Any]
    agent: str
    phase: str
    prompt_path: str

class KanbanResponse(TypedDict):
    lanes: dict[str, list[KanbanTaskData]]
    is_legacy: bool
    upgrade_needed: bool

class HealthResponse(TypedDict):
    status: str
    project_path: str
    sync: dict[str, Any]

class ResearchResponse(TypedDict):
    main_file: str | None
    artifacts: list[dict[str, str]]

class ArtifactDirectoryResponse(TypedDict):
    files: list[dict[str, str]]
```

**Note**: `FeaturesListResponse` is the largest shape (~15 keys with nested objects). Its definition will be finalized during implementation based on post-migration handler output.

**Doctrine**:
- `030-test-and-typecheck-quality-gate.directive.yaml` — mypy on handlers
- `025-boy-scout-rule.directive.yaml` — JS cleanup
- `change-apply-smallest-viable-diff.tactic.yaml`

**Cross-cutting**:
- **Boy Scout** (DIRECTIVE_025): All JS fixes from Tier 1 and Tier 2 SonarCloud items assigned to WP08. Also `dashboard/handlers/api.py` path variable shadowing.
- **Scope split**: WP08 owns review feedback display/rendering. WP05 owns canonical `review_ref` propagation into runtime state surfaces.
- **Self Observation Protocol** (NFR-009): Write observation log at session end.
- **Quality Gate** (DIRECTIVE_030): Tests + type checks must pass before `for_review`.

## Branch Strategy

- **Implementation command**: `spec-kitty implement WP08 --base WP04 --base WP06`
- **Planning base branch**: `feature/metadata-state-type-hardening`
- **Merge target branch**: `feature/metadata-state-type-hardening`

> **Note**: WP08 depends on both WP04 and WP06. The `--base` flags may need to reference the merged state of both. Verify the branch topology before starting.

## Subtasks & Detailed Guidance

### Subtask T038 – Create dashboard/api_types.py with TypedDict definitions

- **Purpose**: Define typed response shapes for all JSON dashboard endpoints in a single module.
- **Steps**:
  1. Create `src/specify_cli/dashboard/api_types.py`:
     ```python
     """TypedDict response shapes for dashboard JSON endpoints."""
     from __future__ import annotations
     from typing import Any, TypedDict
     ```
  2. Implement the TypedDict classes from data-model.md (listed in Context above).
  3. For `FeaturesListResponse`, examine the actual handler output to determine the full shape:
     ```bash
     rg "def.*features|return.*dict\(|return.*{" src/specify_cli/dashboard/handlers/features.py | head -20
     ```
     Build the TypedDict to match the actual response structure. This is the largest type (~15 keys) and may require nested TypedDicts.
  4. Quick import check:
     ```bash
     python -c "from specify_cli.dashboard.api_types import KanbanResponse, HealthResponse; print('OK')"
     ```
- **Files**: `src/specify_cli/dashboard/api_types.py` (NEW)
- **Validation**:
  - [ ] All TypedDict classes from data-model.md present
  - [ ] `FeaturesListResponse` added based on actual handler output
  - [ ] Import succeeds

### Subtask T039 – Migrate handlers/features.py to TypedDict types

- **Purpose**: Annotate the features handler methods to construct responses through TypedDict types.
- **Steps**:
  1. Find response construction patterns:
     ```bash
     rg "return.*{|return.*dict\(" src/specify_cli/dashboard/handlers/features.py | head -20
     ```
  2. For each handler method that returns a JSON response:
     - Add return type annotation using the appropriate TypedDict
     - Ensure the response dict matches the TypedDict keys exactly
     - If any key is missing or extra, update either the TypedDict (T038) or the handler
  3. **Important**: This is type annotation only — no behavioral change. The response structure must be byte-for-byte identical.
  4. Run tests:
     ```bash
     pytest tests/ -x -v -k "features or dashboard"
     ```
- **Files**: `src/specify_cli/dashboard/handlers/features.py`
- **Validation**:
  - [ ] All handler methods annotated with TypedDict return types
  - [ ] No behavioral change — response structure identical
  - [ ] Tests pass

### Subtask T040 – Migrate handlers/api.py + Boy Scout path rename

- **Purpose**: Annotate the API handler methods with TypedDict return types. Apply Boy Scout fix for variable shadowing.
- **Steps**:
  1. Find response construction patterns:
     ```bash
     rg "return.*{|return.*dict\(" src/specify_cli/dashboard/handlers/api.py | head -20
     ```
  2. Annotate each handler method with the appropriate TypedDict return type.
  3. **Boy Scout** (DIRECTIVE_025): Fix the reassigned `path` variable at line ~159:
     ```bash
     rg "path" src/specify_cli/dashboard/handlers/api.py | head -20
     ```
     Rename the reassigned variable to avoid shadowing (e.g., `path` → `file_path` or `resolved_path`).
  4. Run tests:
     ```bash
     pytest tests/ -x -v -k "api or dashboard"
     ```
  5. **Commit separately** (handler migration + Boy Scout fix together, since they touch the same file).
- **Files**: `src/specify_cli/dashboard/handlers/api.py`
- **Validation**:
  - [ ] All handler methods annotated with TypedDict return types
  - [ ] Boy Scout: `path` variable shadowing fixed
  - [ ] No behavioral change
  - [ ] Tests pass

### Subtask T041 – Write JS-to-Python contract test

- **Purpose**: Create a pytest test that validates the JS frontend references the same response keys that the Python TypedDict definitions declare.
- **Steps**:
  1. Create `tests/test_dashboard/test_api_contract.py`:
     ```python
     """Contract test: JS frontend ↔ Python TypedDict key alignment."""
     import ast
     import re
     from pathlib import Path
     from typing import get_type_hints

     from specify_cli.dashboard.api_types import (
         KanbanResponse,
         KanbanTaskData,
         HealthResponse,
         # ... all TypedDicts
     )
     ```
  2. Parse `dashboard.js` for property accesses on fetch responses:
     ```python
     def _extract_js_property_accesses(js_path: Path) -> set[str]:
         """Extract .property and ["property"] accesses from JS fetch handlers."""
         content = js_path.read_text()
         dot_access = set(re.findall(r'\.(\w+)', content))
         bracket_access = set(re.findall(r'\["(\w+)"\]', content))
         return dot_access | bracket_access
     ```
  3. Compare against TypedDict keys:
     ```python
     def test_kanban_response_keys_in_js():
         js_keys = _extract_js_property_accesses(JS_PATH)
         python_keys = set(KanbanResponse.__annotations__.keys())
         # Every Python key should be referenced in JS
         missing = python_keys - js_keys
         assert not missing, f"Python keys not found in JS: {missing}"
     ```
  4. **Note**: This test may produce false negatives if JS uses dynamic property access. Scope the test to statically analyzable accesses. Accept that some keys may be accessed dynamically and document those as known exceptions.
  5. Run tests:
     ```bash
     pytest tests/test_dashboard/test_api_contract.py -x -v
     ```
- **Files**: `tests/test_dashboard/test_api_contract.py` (NEW)
- **Notes**: The regex-based JS parsing is intentionally simple. A more sophisticated AST parser could be added later but is out of scope for Phase 1.
- **Validation**:
  - [ ] Contract test exists and runs
  - [ ] Test validates key alignment for major response types
  - [ ] Known dynamic-access exceptions are documented

### Subtask T042 – Boy Scout JS: unused vars, isNaN, RegExp

- **Purpose**: Apply Tier 1 SonarCloud fixes to `dashboard.js` (quick wins).
- **Steps**:
  1. **Remove unused `artifactKey` variable** at line ~629:
     ```bash
     rg "artifactKey" src/specify_cli/dashboard/static/dashboard/dashboard.js
     ```
     Remove the variable declaration if it's not referenced elsewhere.
  2. **`.find()` → `.some()`** at line ~1151:
     ```bash
     rg "\.find\(" src/specify_cli/dashboard/static/dashboard/dashboard.js
     ```
     If `.find()` is used in a boolean context (e.g., `if (arr.find(...))`), replace with `.some()`.
  3. **`isNaN()` → `Number.isNaN()`** at line ~307:
     ```bash
     rg "isNaN\(" src/specify_cli/dashboard/static/dashboard/dashboard.js
     ```
     Replace global `isNaN()` with `Number.isNaN()` for type-safe NaN checking.
  4. **Use `RegExp.exec()`** instead of `String.match()` at line ~132:
     ```bash
     rg "\.match\(" src/specify_cli/dashboard/static/dashboard/dashboard.js | head -5
     ```
     Replace `str.match(regex)` with `regex.exec(str)` where appropriate.
  5. Run any JS tests if available, or verify no syntax errors:
     ```bash
     node --check src/specify_cli/dashboard/static/dashboard/dashboard.js
     ```
- **Files**: `src/specify_cli/dashboard/static/dashboard/dashboard.js`
- **Parallel?**: Yes — independent of T038-T041 (Python work).
- **Validation**:
  - [ ] Unused `artifactKey` removed
  - [ ] `.find()` → `.some()` where boolean context
  - [ ] `isNaN()` → `Number.isNaN()`
  - [ ] `RegExp.exec()` used instead of `.match()`
  - [ ] No JS syntax errors

### Subtask T043 – Boy Scout JS: optional chaining, Promise rejection

- **Purpose**: Apply Tier 2 SonarCloud fixes to `dashboard.js` (moderate wins).
- **Steps**:
  1. **Optional chaining** (9 sites): Find property access chains that could use `?.`:
     ```bash
     rg "\w+\.\w+\.\w+" src/specify_cli/dashboard/static/dashboard/dashboard.js | head -15
     ```
     Add optional chaining where null/undefined checks are missing:
     ```javascript
     // BEFORE:
     if (data && data.items && data.items.length) { ... }
     // AFTER:
     if (data?.items?.length) { ... }
     ```
  2. **Promise rejection with Error** (8 sites): Find `.catch` handlers and `Promise.reject()` calls:
     ```bash
     rg "reject\(|\.catch\(" src/specify_cli/dashboard/static/dashboard/dashboard.js | head -15
     ```
     Ensure rejections use `Error` objects:
     ```javascript
     // BEFORE:
     Promise.reject("something went wrong")
     // AFTER:
     Promise.reject(new Error("something went wrong"))
     ```
  3. Verify no syntax errors:
     ```bash
     node --check src/specify_cli/dashboard/static/dashboard/dashboard.js
     ```
- **Files**: `src/specify_cli/dashboard/static/dashboard/dashboard.js`
- **Parallel?**: Yes — independent of T038-T041 (Python work). Can be combined with T042 in one commit since both touch the same file.
- **Validation**:
  - [ ] 9 optional chaining fixes applied
  - [ ] 8 Promise rejection fixes applied (use `Error` objects)
  - [ ] No JS syntax errors
  - [ ] Dashboard still functional (manual verify if possible)

### Subtask T044 – Run mypy on handler files

- **Purpose**: Verify type correctness of the migrated handler files with mypy.
- **Steps**:
  1. Run mypy on the handler files:
     ```bash
     mypy src/specify_cli/dashboard/handlers/features.py src/specify_cli/dashboard/handlers/api.py src/specify_cli/dashboard/api_types.py --ignore-missing-imports
     ```
  2. Fix any type errors:
     - Missing return type annotations → add them
     - Incompatible types → adjust TypedDicts or add `cast()` where needed
     - Import errors → verify import paths
  3. Run the full project mypy check to ensure no regressions:
     ```bash
     mypy src/specify_cli/ --ignore-missing-imports 2>/dev/null | tail -5
     ```
  4. Verify the error count does not increase for touched files (NFR-007).
- **Files**: No new files — verification and fixes to existing handler files.
- **Validation**:
  - [ ] `mypy` passes on handler files with zero errors
  - [ ] No regressions in mypy error count for the project
  - [ ] TypedDict annotations are correctly applied

## Definition of Done

- [ ] `api_types.py` with all TypedDict definitions (T038)
- [ ] `handlers/features.py` annotated with TypedDict return types (T039)
- [ ] `handlers/api.py` annotated + Boy Scout path rename (T040)
- [ ] JS-to-Python contract test passes (T041)
- [ ] Boy Scout JS Tier 1 fixes applied (T042)
- [ ] Boy Scout JS Tier 2 fixes applied (T043)
- [ ] `mypy` passes on handler files (T044)
- [ ] Dashboard API responses identical before/after (NFR-006)
- [ ] Full test suite passes with zero regressions
- [ ] Type checks pass

## Risks & Mitigations

- **Risk**: JS-to-Python contract test may be fragile if JS uses dynamic property access. **Mitigation**: Limit test scope to statically analyzable accesses; document known exceptions.
- **Risk**: `FeaturesListResponse` TypedDict may be more complex than data-model.md estimates (~15 keys with nested objects). **Mitigation**: Build the type from actual handler output during implementation; accept that Phase 1 may not capture every edge case.
- **Risk**: Boy Scout JS fixes may introduce subtle behavior changes. **Mitigation**: Use `node --check` for syntax validation; test dashboard manually if possible; optional chaining and Error rejection are semantically equivalent changes.

## Review Guidance

- Verify TypedDict definitions match the actual handler response structure (not just data-model.md — those are estimates)
- Check that handler annotations are return-type only — no behavioral changes
- Confirm the contract test covers the major response types (Kanban, Health, Features)
- Verify Boy Scout JS fixes are correct (optional chaining preserves semantics, Error rejection wraps strings)
- Check `mypy` output — zero errors on handler files

## Activity Log

- 2026-04-06T06:15:00Z – system – Prompt created.
- 2026-04-06T21:27:39Z – opencode – shell_pid=152804 – Started implementation via action command
- 2026-04-06T21:48:56Z – opencode – shell_pid=152804 – All 7 subtasks (T038-T044) complete. 26 TypedDict response shapes in api_types.py. 32 JS-to-Python contract tests pass. mypy error count reduced from 11 to 5 (all remaining are pre-existing). Full test suite: 8880 passed, 0 failures. Boy Scout JS fixes: 4 Tier 1 + 20 Tier 2 fixes in dashboard.js.
- 2026-04-07T04:33:20Z – opencode – shell_pid=152804 – Started review via action command
- 2026-04-07T04:35:24Z – opencode – shell_pid=152804 – Review passed: All 7 subtasks meet acceptance criteria. 26 TypedDict classes correctly model actual handler output. 32 contract tests pass. Handler annotations are type-only with no behavioral changes. Boy Scout JS fixes (12 optional chaining, 8 Promise.reject, unused var, .some(), Number.isNaN, RegExp.exec) are all semantically correct. mypy: zero new errors, pre-existing count reduced 11→5. Full dashboard test suite (76 tests) passes.
