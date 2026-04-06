---
work_package_id: WP03
title: Agent Module Rename + Alias Removal (Non-Orchestrator)
dependencies: [WP02]
requirement_refs:
- FR-003
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts were generated on main; completed changes must merge back into main.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase B - Agent Layer
assignee: ''
agent: ''
shell_pid: ''
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/mission.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/feature.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/status.py
- src/specify_cli/cli/commands/materialize.py
- src/specify_cli/status/models.py
- src/specify_cli/status/progress.py
- src/specify_cli/status/views.py
- src/specify_cli/next/decision.py
- tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py
- tests/specify_cli/test_cli/test_map_requirements.py
- tests/tasks/test_finalize_tasks_json_output_unit.py
- tests/missions/test_feature_lifecycle_unit.py
- tests/agent/**
---

# Work Package Prompt: WP03 – Agent Module Rename + Alias Removal (Non-Orchestrator)

## Objective

Rename `cli/commands/agent/feature.py` → `agent/mission.py` and remove `identity_aliases` usage from 6 non-orchestrator production files. After this WP, the `with_tracked_mission_slug_aliases()` function is no longer called by status, progress, views, materialize, next/decision, or agent/status modules.

**Scope boundary**: This WP does NOT touch `orchestrator_api/commands.py` — that file has 8 alias calls and is WP04's exclusive scope. This WP also does NOT delete `identity_aliases.py` — WP04 deletes it after removing the last 8 calls.

## Context

`identity_aliases.py` contains `with_tracked_mission_slug_aliases()`, a bidirectional alias function that injects `feature_slug` alongside `mission_slug` in all live outputs. It is imported by 7 production files with 27 total call sites. This WP handles 6 of those files (19 call sites). WP04 handles the remaining file (`orchestrator_api/commands.py`, 8 calls) and deletes the module.

At each call site, the function wraps a dict that already contains `mission_slug`. The alias function adds `feature_slug` as a copy. To remove: replace `with_tracked_mission_slug_aliases(data)` with just `data`.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`

## Implementation

### T013: Rename agent/feature.py → agent/mission.py

**Purpose**: Last feature-era module name in the agent command layer.

**Steps**:
1. `git mv src/specify_cli/cli/commands/agent/feature.py src/specify_cli/cli/commands/agent/mission.py`
2. Update import in `src/specify_cli/cli/commands/agent/tasks.py` (line ~1958): change `from specify_cli.cli.commands.agent.feature import` to `from specify_cli.cli.commands.agent.mission import`
3. Search: `grep -r "from specify_cli.cli.commands.agent.feature" src/` — verify only tasks.py had the import
4. Run a quick smoke test to verify the CLI still loads

### T014: Update 35+ Test Imports

**Purpose**: Fix all test files that import from the old module path.

**Steps**:
Update imports in all these files (change `agent.feature` → `agent.mission` in import paths):
1. `tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py` (5 import sites)
2. `tests/specify_cli/test_cli/test_map_requirements.py` (line 11)
3. `tests/tasks/test_finalize_tasks_json_output_unit.py` (line 22)
4. `tests/missions/test_feature_lifecycle_unit.py` (12+ import sites)
5. `tests/agent/test_agent_feature.py` (6 import sites)
6. `tests/agent/cli/commands/test_feature_slug_validation.py` (line 6)
7. `tests/agent/test_create_feature_branch_unit.py` (line 13)
8. `tests/agent/test_create_feature_branch.py` (9 import sites)

**Strategy**: Use `grep -r "from specify_cli.cli.commands.agent.feature" tests/` to find ALL sites. Update each one. Run `pytest` on each updated file.

### T015: Remove Alias Injection from Status Modules

**Purpose**: Status outputs must emit `mission_slug` only, not both `mission_slug` and `feature_slug`.

**Steps**:
1. **`src/specify_cli/status/models.py`** (line 15, 217):
   - Remove `from specify_cli.core.identity_aliases import with_tracked_mission_slug_aliases`
   - In `StatusSnapshot.to_dict()` (line ~217): replace `with_tracked_mission_slug_aliases(result)` with `result`
2. **`src/specify_cli/status/progress.py`** (line 19, 73):
   - Remove import
   - Replace call at line ~73 with direct dict usage
3. **`src/specify_cli/status/views.py`** (line 18, 106):
   - Remove import
   - Replace call at line ~106 with direct dict usage

**Verification**: After each change, the module's output should still contain `mission_slug` but NOT `feature_slug`.

### T016: Remove Alias Injection from Next/Decision and Materialize

**Purpose**: These modules output machine-facing JSON that must not contain `feature_slug`.

**Steps**:
1. **`src/specify_cli/next/decision.py`** (line 24, 67):
   - Remove import
   - Replace `with_tracked_mission_slug_aliases(data)` with `data` at line ~67
2. **`src/specify_cli/cli/commands/materialize.py`** (line 18, 86):
   - Remove import
   - Replace call at line ~86

### T017: Remove Alias Injection from Agent/Status

**Purpose**: Agent status commands output JSON that must not contain `feature_slug`.

**Steps**:
1. **`src/specify_cli/cli/commands/agent/status.py`** (line 20, calls at 380, 437, 617, 648):
   - Remove import at line 20
   - Replace all 4 call sites with direct dict usage

### T018: Verify Outputs Still Contain mission_slug

**Purpose**: Confirm alias removal didn't accidentally remove `mission_slug` (only `feature_slug` should be gone).

**Steps**:
1. Run the full test suite: `pytest tests/`
2. Spot-check: invoke a status/materialize command on a test feature and verify `mission_slug` appears in JSON output
3. Verify `feature_slug` does NOT appear in any of the modified modules' outputs

## Definition of Done

- [ ] `agent/feature.py` no longer exists; `agent/mission.py` does
- [ ] All 35+ test imports updated
- [ ] `with_tracked_mission_slug_aliases()` has zero calls in status/, next/, materialize, agent/status
- [ ] All affected modules still emit `mission_slug` in their outputs
- [ ] No `feature_slug` appears in outputs from modified modules
- [ ] Full test suite passes
- [ ] `identity_aliases.py` still exists (WP04 deletes it)

## Risks

- Missing a call site: use `grep -r "with_tracked_mission_slug_aliases" src/` to verify only `orchestrator_api/commands.py` remains
- Accidentally removing `mission_slug` from output: the data dict already contains it; the alias function only adds `feature_slug`
