# Tasks: Task Workflow Bug Fixes: Spec Path and Error Hint

**Mission**: `task-workflow-bug-fixes-01KV69BZ`
**Branch**: `fix/task-workflow-bug-fixes` → merge target: `fix/task-workflow-bug-fixes`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T003 | Regression test: coord worktree present → spec.md resolves from primary checkout (**ATDD-first**) | WP01 | — |
| T001 | Add `primary_feature_dir_for_mission` late import inside `map_requirements` | WP01 | — |
| T002 | Replace `spec_md = feature_dir / SPEC_MD_FILENAME` with primary-checkout path | WP01 | — |
| T005 | Regression test: literal zero-match error contains YAML `create_intent` snippet (**ATDD-first**) | WP02 | [P] |
| T004 | Replace `validate_glob_matches` error tail with ready-to-paste YAML fragment | WP02 | [P] |

---

## Work Package WP01 — Fix map-requirements spec.md Path Resolution (P1)

**Goal**: Eliminate the "spec.md not found" failure that blocks `map-requirements` after `setup-plan` has created a coordination worktree. Swap the topology-aware resolver for the topology-blind `primary_feature_dir_for_mission` specifically for `spec.md` access.

**Priority**: P1 (blocks standard task workflow)
**Estimated prompt size**: ~280 lines
**Prompt file**: [tasks/WP01-map-requirements-spec-path-fix.md](tasks/WP01-map-requirements-spec-path-fix.md)
**Dependencies**: none
**Execution mode**: `code_change`

**Included subtasks**:

- [x] T003 Regression test: coord worktree present → spec.md resolves from primary checkout (WP01) **[ATDD-first — commit before T001/T002]**
- [x] T001 Add `primary_feature_dir_for_mission` late import inside `map_requirements` (WP01)
- [x] T002 Replace `spec_md = feature_dir / SPEC_MD_FILENAME` with primary-checkout-anchored path (WP01)

**Implementation sketch**:
1. Locate the `map_requirements` function in `src/specify_cli/cli/commands/agent/tasks.py`.
2. After the existing `from specify_cli.missions.feature_dir_resolver import resolve_feature_dir_for_slug` late import (~line 3533), add a parallel late import of `primary_feature_dir_for_mission`.
3. Derive `primary_dir` from the new import and use it for `spec_md`.
4. `feature_dir` (topology-aware) remains for WP file access — do not change downstream usage.
5. Add a unit/integration test in `tests/specify_cli/` that mocks or stubs the coord worktree path to exist, then asserts `spec_md` is rooted in the primary checkout.

**Risks**: `test_no_raw_mission_spec_paths.py` architectural test must stay green — use `primary_feature_dir_for_mission` from the sanctioned module, not inline path construction.

---

## Work Package WP02 — Enhance validate_glob_matches create_intent Error Hint (P2)

**Goal**: Change the zero-match literal-path error in `validate_glob_matches` to include a ready-to-paste YAML fragment, enabling agents and developers to self-recover from a planned-new-file error without consulting documentation. Add a regression test to lock in the hint text.

**Priority**: P2
**Estimated prompt size**: ~220 lines
**Prompt file**: [tasks/WP02-validate-glob-matches-create-intent-hint.md](tasks/WP02-validate-glob-matches-create-intent-hint.md)
**Dependencies**: none (independent of WP01)
**Execution mode**: `code_change`

**Included subtasks**:

- [x] T005 Regression test: literal zero-match error contains YAML `create_intent` snippet (WP02) **[ATDD-first — commit before T004; assert `"  create_intent:\n    -"` in error]**
- [x] T004 Replace `validate_glob_matches` error tail with ready-to-paste YAML fragment (WP02)

**Implementation sketch**:
1. Locate the `else` branch in `validate_glob_matches` in `src/specify_cli/ownership/validation.py` (~line 370).
2. Replace the trailing `msg +=` that currently says "add it to 'create_intent' in the WP frontmatter." with the YAML fragment version.
3. Add a test method to `tests/specify_cli/ownership/test_validation.py` in the existing `validate_glob_matches` test class. Call the function with a manifest whose `owned_files` contains a literal path absent from the tmp repo; assert `result.passed is False`, `"create_intent"` in `result.errors[0]`, and the offending path in `result.errors[0]`.

**Parallel opportunities**: WP01 and WP02 touch different modules with no shared code and can be implemented in parallel lanes.

**Risks**: NFR-003 (≤300 chars per error): verify the final message length with the longest realistic path. The `_nearest_match_suggestion` prefix (when present) must not be accidentally removed.
