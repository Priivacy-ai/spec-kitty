---
work_package_id: WP02
title: Rename Core Modules + Canonical meta.json Writes
dependencies: []
requirement_refs:
- FR-016
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase A - Foundation
assignee: ''
agent: "opencode:gpt-5.4:python-implementer:implementer"
shell_pid: "48516"
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/core/mission_creation.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/feature_creation.py
- src/specify_cli/core/mission_creation.py
- src/specify_cli/feature_metadata.py
- src/specify_cli/mission_metadata.py
- src/specify_cli/upgrade/feature_meta.py
- src/specify_cli/acceptance.py
- src/specify_cli/doc_state.py
- src/specify_cli/dashboard/diagnostics.py
- src/specify_cli/scripts/tasks/tasks_cli.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/status/emit.py
- src/specify_cli/tracker/origin.py
- tests/specify_cli/core/test_feature_creation.py
- tests/specify_cli/test_feature_metadata*.py
---

# Work Package Prompt: WP02 – Rename Core Modules + Canonical meta.json Writes

## Objective

Rename `feature_creation.py` → `mission_creation.py` and `feature_metadata.py` → `mission_metadata.py`. Update all imports across the codebase. Fix meta.json scaffolding to write canonical field names (`mission_slug`, `mission_number`, `mission_type`).

## Context

These two modules are the most-imported feature-era modules in the codebase:
- `feature_creation.py`: 2 production imports (`tracker/origin.py`, `cli/commands/agent/feature.py`)
- `feature_metadata.py`: 10 production imports across tracker, status, CLI, dashboard, scripts, and upgrade modules

The meta.json scaffolding in `feature_creation.py` currently writes legacy field names (`feature_slug`, `feature_number`, `mission`). FR-019 requires new writes to use canonical terms.

**Important**: `cli/commands/agent/feature.py` imports from `feature_creation.py`, but that file is renamed in WP03. For this WP, update the import in the file at its CURRENT location (`agent/feature.py`). WP03 will rename it afterward.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`

## Implementation

### T006: Rename feature_creation.py → mission_creation.py

**Purpose**: Rename the module and update production imports.

**Steps**:
1. `git mv src/specify_cli/core/feature_creation.py src/specify_cli/core/mission_creation.py`
2. Update import in `src/specify_cli/tracker/origin.py` (line ~335): `from specify_cli.core.feature_creation import ...` → `from specify_cli.core.mission_creation import ...`
3. Update import in `src/specify_cli/cli/commands/agent/feature.py` (line ~548): same pattern
4. Search for any other imports: `grep -r "from specify_cli.core.feature_creation" src/`
5. Run `pytest tests/specify_cli/core/test_feature_creation.py` to verify the rename doesn't break basic functionality

**Files**: `src/specify_cli/core/mission_creation.py`, `src/specify_cli/tracker/origin.py`, `src/specify_cli/cli/commands/agent/feature.py`

### T007: Update meta.json Scaffolding

**Purpose**: New mission metadata must use canonical field names (FR-019).

**Steps**:
1. In `mission_creation.py`, find the code that writes `meta.json` (look for dict construction with `feature_slug`, `feature_number`, `mission` keys)
2. Change field names:
   - `"feature_number"` → `"mission_number"`
   - `"feature_slug"` → `"mission_slug"`
   - `"mission"` → `"mission_type"`
3. Keep unchanged: `slug`, `friendly_name`, `target_branch`, `created_at`, `vcs`
4. Also update the `TASKS_README_CONTENT` template if it references feature_slug in YAML examples (known bug #418)
5. Verify the JSON output structure matches the canonical schema from data-model.md

**Files**: `src/specify_cli/core/mission_creation.py`

### T008: Update Test Files for mission_creation

**Purpose**: Fix test imports after rename.

**Steps**:
1. Update `tests/specify_cli/core/test_feature_creation.py`: change all `from specify_cli.core.feature_creation import` to `from specify_cli.core.mission_creation import`
2. Update `tests/sync/tracker/test_origin.py` (line ~534): same pattern
3. Update `tests/sync/tracker/test_origin_integration.py` (line ~433): same pattern
4. Run all updated test files

**Files**: `tests/specify_cli/core/test_feature_creation.py`, `tests/sync/tracker/test_origin.py`, `tests/sync/tracker/test_origin_integration.py`

### T009: Rename feature_metadata.py → mission_metadata.py

**Purpose**: Rename the most-imported feature-era module.

**Steps**:
1. `git mv src/specify_cli/feature_metadata.py src/specify_cli/mission_metadata.py`
2. Update 10 production imports — each file has `from specify_cli.feature_metadata import ...`:
   - `src/specify_cli/upgrade/feature_meta.py` (line 18)
   - `src/specify_cli/core/mission_creation.py` (was feature_creation, line ~303)
   - `src/specify_cli/orchestrator_api/commands.py` (line 956) — note: WP04 also modifies this file for command renames, but this import update is WP02's scope
   - `src/specify_cli/acceptance.py` (line 29)
   - `src/specify_cli/tracker/origin.py` (line 20)
   - `src/specify_cli/status/emit.py` (line 34)
   - `src/specify_cli/cli/commands/implement.py` (line 19)
   - `src/specify_cli/dashboard/diagnostics.py` (line 24)
   - `src/specify_cli/scripts/tasks/tasks_cli.py` (line 70)
   - `src/specify_cli/doc_state.py` (line 46)
3. Search for any missed imports: `grep -r "from specify_cli.feature_metadata" src/`

**Files**: `src/specify_cli/mission_metadata.py` + 10 files listed above

### T010: Update Test Files for mission_metadata

**Purpose**: Fix test imports after rename.

**Steps**:
1. `tests/specify_cli/test_canonical_acceptance.py` (line 20)
2. `tests/specify_cli/test_feature_metadata_origin.py` (line 11)
3. `tests/specify_cli/test_feature_metadata.py` (line 13)
4. Search: `grep -r "from specify_cli.feature_metadata" tests/`

**Files**: 3 test files

### T011: Update Other meta.json Write Paths

**Purpose**: Ensure ALL code paths that write meta.json use canonical fields.

**Steps**:
1. Check `src/specify_cli/upgrade/feature_meta.py` — does it write meta.json? If so, update field names
2. Search for any other code that writes to `meta.json`: `grep -r "meta\.json" src/ | grep -i write`
3. Check status modules, acceptance, and doc_state for meta.json writes
4. Each write path must produce `mission_slug`, `mission_number`, `mission_type` — not legacy names

**Files**: `src/specify_cli/upgrade/feature_meta.py` + any others found

### T012: Test Canonical meta.json Writes

**Purpose**: Verify no legacy field names appear in new meta.json output.

**Steps**:
1. Write a test that invokes the create-mission scaffolding and asserts the resulting meta.json contains:
   - `mission_number` (not `feature_number`)
   - `mission_slug` (not `feature_slug`)
   - `mission_type` (not `mission` as a bare field name)
2. Assert `feature_slug`, `feature_number` are NOT present in the output
3. Run full test suite: `pytest tests/`

**Files**: test files

## Definition of Done

- [ ] `feature_creation.py` no longer exists; `mission_creation.py` does
- [ ] `feature_metadata.py` no longer exists; `mission_metadata.py` does
- [ ] All 12+ production imports updated and working
- [ ] All 6 test file imports updated
- [ ] New meta.json writes use `mission_slug`, `mission_number`, `mission_type`
- [ ] No `feature_slug` or `feature_number` in newly scaffolded meta.json
- [ ] Full test suite passes

## Risks

- Missed import: search comprehensively with grep, not just the known list
- `orchestrator_api/commands.py` import: update it here but don't modify the command logic (that's WP04)

## Activity Log

- 2026-04-06T06:04:23Z – opencode:gpt-5.4:python-implementer:implementer – shell_pid=39413 – Started implementation via action command
- 2026-04-06T06:04:49Z – opencode:gpt-5.4:python-implementer:implementer – shell_pid=39413 – Moved to planned
- 2026-04-06T06:18:22Z – opencode:gpt-5.4:python-implementer:implementer – shell_pid=48516 – Started implementation via action command
