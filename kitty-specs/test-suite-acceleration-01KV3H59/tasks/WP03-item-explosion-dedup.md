---
work_package_id: WP03
title: Item-explosion and read-only de-duplication
dependencies:
- WP02
requirement_refs:
- FR-008
- FR-009
- NFR-007
tracker_refs: []
planning_base_branch: feat/test-suite-acceleration
merge_target_branch: feat/test-suite-acceleration
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-acceleration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-acceleration unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 2 - Redundancy removal
agent: claude
shell_pid: '9322'
history:
- at: '2026-06-14T17:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/status/test_transitions.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/status/test_transitions.py
- tests/specify_cli/integration/test_migration_e2e.py
- tests/doctrine/test_drg_relations.py
- tests/doctrine/conftest.py
- tests/architectural/conftest.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Item-explosion and read-only de-duplication

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile before parsing the rest of this prompt.

- **Profile**: `randy-reducer` (semantic compression)
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Remove collected-item explosion and per-test rebuilds of read-only state, with **every assertion path still executed**. Use the WP02 equivalence/mutation helpers to prove neutrality.

**Done when**: the FSM collapse passes a planted-mutation proof; shared/cached fixtures are read-only and exclude the carved-out tests; collected-node deltas are explicitly asserted (NFR-007).

## Context & Constraints

- Evidence: `architecture/test-suite-acceleration-plan.md` (R1/A5, R3/PP-04b, R7/B2/PP-04c-d). `contracts/behavioral-contracts.md` (C-READONLY). `data-model.md` (E6).
- **Depends on WP02** — import the equivalence/mutation helpers from `tests/_support/coverage_safety/`.
- Hard carve-outs (C-007): integrity, idempotency, file-existence, freshness tests must NOT use any shared/cached fixture.

## Branch Strategy

- **Planning base branch**: feat/test-suite-acceleration
- **Merge target branch**: feat/test-suite-acceleration

## Subtasks & Detailed Guidance

### Subtask T009 – Collapse the FSM parity matrix

- **Purpose**: `tests/status/test_transitions.py:510-541` parametrizes ~1701 parity rows (1700 of 2372 collected items). Collapse to one accumulate-all loop while keeping the exact coverage.
- **Steps**:
  1. Replace the parametrize with a single test that iterates `_PARITY_ROWS`, accumulating **all** mismatches (no early `break`/first-failure exit).
  2. Assert `checked == len(_PARITY_ROWS)` (anti-vacuity) and that the accumulated mismatch list is empty, reporting every offending row.
  3. Keep the exact-string `err == expected_err` comparison and keep `test_baseline_fixture_is_non_trivial` verbatim.
  4. Use the WP02 mutation helper: flip one baseline row, confirm the loop fails and **names** that row.
- **Files**: `tests/status/test_transitions.py`.

### Subtask T010 – Shared read-only migrated-project fixture

- **Purpose**: 3 `TestFullMigration` asserts (schema_version / gitignore / backup_cleaned) each rebuild the same migrated project (~50s on specify-cli-heavy).
- **Steps**:
  1. In `tests/specify_cli/integration/test_migration_e2e.py`, add a `tmp_path_factory`-scoped (module) fixture that runs the migration once, asserting `report.success` inside the fixture.
  2. Point ONLY the 3 truly-identical read-only tests at it.
  3. **Exclude** both counter tests (`features_migrated == 2`, `wps_backfilled == 2` — different inputs) and ALL rollback/dry-run/idempotency tests; those keep pristine per-test state.
- **Files**: `tests/specify_cli/integration/test_migration_e2e.py`.

### Subtask T011 – Cache whole-tree AST behind a fixture

- **Purpose**: Architectural boundary tests re-parse the whole source tree per test.
- **Steps**:
  1. Add a session/module-scoped fixture in `tests/architectural/conftest.py` that parses the tree once and exposes a read-only AST/module map.
  2. Route the boundary tests that only READ the tree through it.
  3. **Exclude** `test_idempotent`-style, file-existence, and freshness tests. Add a read-only guard so consumers can’t mutate the cached structure.
- **Files**: `tests/architectural/conftest.py` (fixture only; this WP does not edit `tests/architectural/test_real_home_isolation_guard.py`, which is WP02’s).
- **Notes**: Under CI `--dist loadfile` the architectural shard is per-worker so the cache win is mostly LOCAL — that is expected; the DRG cache (T012) is the real CI win.

### Subtask T012 – Cache DRG graph behind a fixture

- **Purpose**: Doctrine tests rebuild the DRG graph (~18s → ~2s) repeatedly.
- **Steps**:
  1. Add a session/module-scoped fixture in `tests/doctrine/conftest.py` that loads the DRG graph once.
  2. Route read-only DRG consumers (e.g. `tests/doctrine/test_drg_relations.py`) through it.
  3. **Exclude** `test_graph_file_exists`, `test_shipped_graph_yaml_is_fresh`, and any idempotency test.
- **Files**: `tests/doctrine/conftest.py`, `tests/doctrine/test_drg_relations.py`.

## Test Strategy

- `.venv/bin/pytest tests/status/test_transitions.py tests/specify_cli/integration/test_migration_e2e.py tests/doctrine -q` green.
- Run the planted-mutation proof for T009.
- Record before/after collected-node counts for each touched module and assert the intended delta (NFR-007).

## Risks & Mitigations

- **Risk**: a "read-only" consumer secretly mutates the cache → cross-test bleed. **Mitigation**: read-only guard + keep destructive tests function-scoped.
- **Risk**: collapsing the matrix hides which row failed. **Mitigation**: accumulate-all + name every offending row.

## Review Guidance

- Confirm the mutation proof actually fails on a planted bad row.
- Confirm every carve-out (counter/rollback/idempotency/freshness/existence) stays on pristine state.

## Activity Log

- 2026-06-14T17:10:00Z – system – Prompt created.
