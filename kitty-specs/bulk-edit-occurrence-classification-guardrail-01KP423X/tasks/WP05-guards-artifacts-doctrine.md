---
work_package_id: WP05
title: Guard Registration, Expected Artifacts & Doctrine
dependencies:
- WP02
requirement_refs:
- FR-002
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
agent: "claude:opus:implementer:implementer"
shell_pid: "77246"
history:
- date: '2026-04-13'
  author: claude
  action: created
authoritative_surface: src/
execution_mode: code_change
owned_files:
- src/specify_cli/mission_v1/guards.py
- src/specify_cli/missions/software-dev/expected-artifacts.yaml
- src/doctrine/directives/shipped/035-bulk-edit-occurrence-classification.directive.yaml
- src/doctrine/tactics/shipped/occurrence-classification-workflow.tactic.yaml
- tests/specify_cli/mission_v1/test_guards_bulk_edit.py
tags: []
---

# WP05 — Guard Registration, Expected Artifacts & Doctrine

## Objective

Register the `occurrence_map_complete` guard in the state machine guard system, add `occurrence_map.yaml` as a conditionally-required expected artifact, and create the doctrine directive and tactic that codify the governance rule.

## Context

- **Spec**: FR-002 (workflow step), FR-011 (doctrine update)
- **Plan**: Integration Points 5, 6, 7 — Guard System, Expected Artifacts, Doctrine
- **Data model**: Directive 035, tactic occurrence-classification-workflow
- Existing guard system: `src/specify_cli/mission_v1/guards.py` has 6 built-in primitives (`artifact_exists`, `gate_passed`, `all_wp_status`, `any_wp_status`, `input_provided`, `event_count`) registered in `GUARD_REGISTRY`
- Existing expected artifacts: `src/specify_cli/missions/software-dev/expected-artifacts.yaml`
- Existing directives: `src/doctrine/directives/shipped/` (001 through 034)
- Existing tactics: `src/doctrine/tactics/shipped/` (45 tactics)

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

---

### Subtask T013: Register occurrence_map_complete Guard Primitive

**Purpose**: Add a new guard to the state machine that checks occurrence map validity when `change_mode` is `bulk_edit`.

**Steps**:

1. Open `src/specify_cli/mission_v1/guards.py`

2. Study the existing guard factory pattern. Each guard is:
   - A factory function that receives args from the guard expression
   - Returns a callable `(EventData) -> bool`
   - Registered in `GUARD_REGISTRY` dict

3. Add the new guard factory:
   ```python
   def _occurrence_map_complete_factory() -> Callable[[Any], bool]:
       """Guard: bulk_edit missions must have a valid occurrence map."""
       def check(event_data: Any) -> bool:
           feature_dir = _resolve_feature_dir(event_data)
           if feature_dir is None:
               return True  # Can't check — don't block
           from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready
           result = ensure_occurrence_classification_ready(feature_dir)
           return result.passed
       return check
   ```

4. Register in `GUARD_REGISTRY`:
   ```python
   GUARD_REGISTRY["occurrence_map_complete"] = _occurrence_map_complete_factory
   ```

5. Create test at `tests/specify_cli/mission_v1/test_guards_bulk_edit.py`:
   - `test_guard_passes_non_bulk_edit`: Mission without change_mode returns True
   - `test_guard_fails_bulk_edit_no_map`: Mission with bulk_edit and no map returns False
   - `test_guard_passes_bulk_edit_valid_map`: Mission with bulk_edit and valid map returns True

**Files**: `src/specify_cli/mission_v1/guards.py`, `tests/specify_cli/mission_v1/test_guards_bulk_edit.py`

**Validation**:
- [ ] Guard registered and callable via expression `occurrence_map_complete()`
- [ ] Guard follows existing factory pattern
- [ ] Tests pass

---

### Subtask T014: Update Expected Artifacts YAML

**Purpose**: Declare `occurrence_map.yaml` as a conditionally-required artifact for software-dev missions.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/expected-artifacts.yaml`

2. Study the existing structure (artifacts listed by step with blocking flags)

3. Add `occurrence_map.yaml` entry under the appropriate section:
   ```yaml
   # Conditionally required when change_mode is bulk_edit
   - name: "occurrence_map.yaml"
     artifact_class: "input"
     path_pattern: "occurrence_map.yaml"
     blocking: true
     condition: "change_mode == 'bulk_edit'"
     description: "Classification of target string occurrences by semantic category with per-category change actions"
   ```

4. If the expected-artifacts system doesn't support conditional blocking, add the entry as `blocking: false` with a note that runtime enforcement is via the gate function (WP04).

**Files**: `src/specify_cli/missions/software-dev/expected-artifacts.yaml`

**Validation**:
- [ ] YAML parses correctly
- [ ] Artifact is listed in expected artifacts

---

### Subtask T015: Create Doctrine Directive 035

**Purpose**: Codify the bulk edit classification rule as a formal governance directive.

**Steps**:

1. Create `src/doctrine/directives/shipped/035-bulk-edit-occurrence-classification.directive.yaml`

2. Follow the existing directive schema (see `001-architectural-integrity-standard.directive.yaml` for reference):
   ```yaml
   schema_version: "1.0"
   id: DIRECTIVE_035
   title: Bulk Edit Occurrence Classification
   intent: >
     Codebase-wide renames, terminology migrations, and bulk string changes
     must classify string occurrences by semantic context before edits begin.
     Different contexts (code symbols, imports, filesystem paths, serialized keys,
     CLI commands, docs, tests, logs) may have different change rules. Mechanical
     find-and-replace that treats all occurrences identically produces silent
     runtime breakage.
   tactic_refs:
     - occurrence-classification-workflow
   enforcement: required
   scope: >
     Applies to any mission marked with change_mode: bulk_edit, or any mission
     where the specification describes codebase-wide renames, terminology
     migrations, or bulk string replacement operations.
   procedures:
     - Declare the mission as occurrence-sensitive by setting change_mode to bulk_edit in mission metadata.
     - Before implementation, produce an occurrence_map.yaml classifying the target term by semantic category.
     - For each category, assign an explicit action (rename, manual_review, do_not_change, rename_if_user_visible).
     - Document exceptions for specific files or patterns that override category-level rules.
     - Implementation must not begin until the occurrence map exists and passes validation.
     - Review must reference the occurrence map as the governing artifact for evaluating changes.
   integrity_rules:
     - Every occurrence category in the map must have an explicit action assignment.
     - Categories marked do_not_change must not be modified without updating the map and obtaining re-approval.
     - The occurrence map is the sole authority for what categories may change; no ad-hoc changes without classification.
   validation_criteria:
     - Implementation is blocked when change_mode is bulk_edit and occurrence_map.yaml is missing or invalid.
     - Review rejects work that lacks an admissible occurrence map.
     - The occurrence map covers at least 3 distinct categories.
   ```

**Files**: `src/doctrine/directives/shipped/035-bulk-edit-occurrence-classification.directive.yaml`

**Validation**:
- [ ] YAML is valid
- [ ] Schema matches existing directive structure
- [ ] Doctrine catalog loads without errors: `spec-kitty charter sync` (if applicable)

---

### Subtask T016: Create Occurrence Classification Workflow Tactic

**Purpose**: Create the procedural tactic referenced by the directive.

**Steps**:

1. Create `src/doctrine/tactics/shipped/occurrence-classification-workflow.tactic.yaml`

2. Follow existing tactic schema (see `tdd-red-green-refactor.tactic.yaml` for reference):
   ```yaml
   schema_version: "1.0"
   id: occurrence-classification-workflow
   name: Occurrence Classification Workflow
   purpose: >
     Guide mission authors through classifying string occurrences by semantic
     context before performing bulk edits. Ensures each category receives an
     explicit action assignment and the resulting map is machine-readable and
     reviewable.
   steps:
     - title: Identify the target
       description: >
         Name the primary term or pattern being changed and its intended
         replacement. Specify the operation type: rename, remove, or deprecate.
       examples:
         - "target: constitution → charter (rename)"
         - "target: legacy_api_v1 (remove)"

     - title: Enumerate occurrence categories
       description: >
         List every semantic context where the target string appears. Start
         with the standard categories: code symbols, import paths, filesystem
         paths, serialized keys, CLI commands, user-facing strings, tests/fixtures,
         and logs/telemetry. Add project-specific categories as needed.
       examples:
         - "code_symbols: CompiledConstitution, sync_constitution()"
         - "serialized_keys: constitution_hash in meta.json"

     - title: Assign per-category actions
       description: >
         For each category, choose an action: rename (safe to change),
         manual_review (needs case-by-case judgment), do_not_change (must
         not be modified), or rename_if_user_visible (change only in
         user-facing contexts).
       examples:
         - "code_symbols: rename, serialized_keys: do_not_change"

     - title: Document exceptions
       description: >
         List specific files or patterns that override the category-level
         rules. Common exceptions include migration files, changelog entries,
         and third-party vendored code.
       examples:
         - "migrations/*.py: do_not_change (historical records)"

     - title: Write and validate the occurrence map
       description: >
         Write the classification to occurrence_map.yaml in the mission's
         kitty-specs directory. Run validation to confirm structural
         completeness and admissibility before proceeding to implementation.
   ```

**Files**: `src/doctrine/tactics/shipped/occurrence-classification-workflow.tactic.yaml`

**Validation**:
- [ ] YAML is valid
- [ ] Schema matches existing tactic structure
- [ ] tactic_ref in directive 035 matches this tactic's id

## Definition of Done

- [ ] `occurrence_map_complete` guard registered and testable
- [ ] Expected artifacts updated for software-dev mission
- [ ] Directive 035 created with correct schema
- [ ] Tactic created and referenced by directive
- [ ] All tests pass
- [ ] mypy --strict passes on modified guards.py

## Risks

- **Low**: Guard registration could conflict with existing guards. Mitigate by using a unique name and following the established factory pattern.
- **Low**: Expected artifacts conditional support may not exist. Fall back to non-blocking entry with documentation.

## Reviewer Guidance

- Verify directive 035 schema matches existing directives (compare with 001 or 010)
- Verify tactic schema matches existing tactics
- Confirm guard factory follows the pattern of existing guards in `GUARD_REGISTRY`
- Check that expected-artifacts YAML remains valid after addition

## Activity Log

- 2026-04-13T19:19:17Z – claude:opus:implementer:implementer – shell_pid=77246 – Started implementation via action command
- 2026-04-13T19:25:09Z – claude:opus:implementer:implementer – shell_pid=77246 – Ready for review
- 2026-04-13T19:25:36Z – claude:opus:implementer:implementer – shell_pid=77246 – Review passed: guard registered, expected artifacts updated, directive 035 and tactic created. 7 tests.
- 2026-04-13T19:32:11Z – claude:opus:implementer:implementer – shell_pid=77246 – Done override: Feature merged to main
