---
work_package_id: WP04
title: Orchestrator API Rename
dependencies: [WP01, WP03]
requirement_refs:
- FR-003
- FR-004
- FR-012
- FR-022
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase C - Contract Cleanup
assignee: ''
agent: ''
shell_pid: ''
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/orchestrator_api/
execution_mode: code_change
owned_files:
- src/specify_cli/orchestrator_api/**
- src/specify_cli/core/identity_aliases.py
- tests/specify_cli/orchestrator_api/**
---

# Work Package Prompt: WP04 – Orchestrator API Rename

## Objective

Complete the orchestrator API cutover: remove last 8 alias injection calls, delete `identity_aliases.py`, rename 3 commands, 2 error codes, and `--feature` → `--mission` parameter on all 8 commands. Insert compatibility gate. This is the externally-visible breaking change gated by FR-021 (Priivacy-ai/spec-kitty-orchestrator#6).

## Context

After WP03, the only remaining consumer of `identity_aliases.py` is `orchestrator_api/commands.py` with 8 `with_tracked_mission_slug_aliases()` calls. This WP removes those calls, deletes the module, then renames the feature-era command surfaces.

**Hard cutover posture (FR-004)**: No fallback, alias, redirect, or "deprecated but still works" behavior. Calls using old command names must fail as unknown/unsupported commands.

See `kitty-specs/064-complete-mission-identity-cutover/contracts/orchestrator-api.md` for the complete post-cutover contract.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`

## Implementation

### T019: Remove Last Alias Injection Calls

**Purpose**: Eliminate the last 8 `with_tracked_mission_slug_aliases()` calls.

**Steps**:
1. In `src/specify_cli/orchestrator_api/commands.py`:
   - Remove import at line 32: `from specify_cli.core.identity_aliases import with_tracked_mission_slug_aliases`
   - At lines 474, 537, 667, 749, 845, 907, 968, 1047: replace `with_tracked_mission_slug_aliases(data)` with `data`
2. Verify: `grep -r "with_tracked_mission_slug_aliases" src/` should return zero results

### T020: Delete identity_aliases.py

**Purpose**: The module has zero consumers after T019.

**Steps**:
1. `git rm src/specify_cli/core/identity_aliases.py`
2. Verify: `grep -r "identity_aliases" src/` should return zero results (excluding upgrade/migration paths if any)

### T021: Rename 3 Commands

**Purpose**: Feature-era command names → mission-era.

**Steps** (in `commands.py`):
1. `@app.command(name="feature-state")` → `@app.command(name="mission-state")`
2. `@app.command(name="accept-feature")` → `@app.command(name="accept-mission")`
3. `@app.command(name="merge-feature")` → `@app.command(name="merge-mission")`
4. Update all internal references to these command names in string literals (error messages, help text, `_fail()` calls with command name strings)

### T022: Rename 2 Error Codes

**Purpose**: Feature-era error codes → mission-era.

**Steps**:
1. Replace all occurrences of `"FEATURE_NOT_FOUND"` with `"MISSION_NOT_FOUND"` in commands.py
2. Replace all occurrences of `"FEATURE_NOT_READY"` with `"MISSION_NOT_READY"` in commands.py
3. Update the module docstring (lines 6-17) which documents the error codes
4. Search: `grep -r "FEATURE_NOT_FOUND\|FEATURE_NOT_READY" src/` to catch any references outside commands.py

### T023: Rename --feature → --mission Parameter

**Purpose**: CLI flag must use canonical naming (FR-022).

**Steps**:
All 8 command functions have `feature: str = typer.Option(..., "--feature", ...)`. Change each to:
1. Parameter name: `feature` → `mission` (the Python variable name)
2. Flag name: `"--feature"` → `"--mission"`
3. Help text: update from "Mission slug (legacy flag name)" to "Mission slug"
4. Every reference to the `feature` variable inside each function body must change to `mission`

**Affected functions** (8 total):
- `feature_state()` → `mission_state()` (line ~420)
- `list_ready()` (line ~487)
- `start_implementation()` (line ~549)
- `start_review()` (line ~685)
- `transition()` (line ~765)
- `append_history()` (line ~860)
- `accept_feature()` → `accept_mission()` (line ~920)
- `merge_feature()` → `merge_mission()` (line ~982)

### T024: Update Internal Names + Insert Gate

**Purpose**: Function names and internal references must be canonical.

**Steps**:
1. Rename Python function definitions:
   - `def feature_state(` → `def mission_state(`
   - `def accept_feature(` → `def accept_mission(`
   - `def merge_feature(` → `def merge_mission(`
2. Update any internal helper calls that reference these functions
3. Update `_resolve_feature_dir()` → `_resolve_mission_dir()` (line ~186)
4. Update `_resolve_merge_target_branch()` parameter names
5. Insert `from specify_cli.core.contract_gate import validate_outbound_payload` at the top
6. Add gate call before each command's envelope emission (inside `make_envelope()` or just before return)

### T025: Update Tests + Unknown Command Integration Test

**Purpose**: All tests must use new names; old names must fail.

**Steps**:
1. Update all test files in `tests/specify_cli/orchestrator_api/` to use new command names, error codes, and `--mission` flag
2. Add integration test: invoke CLI with `feature-state`, `accept-feature`, `merge-feature` → must fail as unknown commands (exit code != 0, no JSON output)
3. Add integration test: invoke CLI with `--feature` flag on `mission-state` → must fail as unknown option
4. Run: `pytest tests/specify_cli/orchestrator_api/ -v`

## Definition of Done

- [ ] `identity_aliases.py` is deleted; zero imports remain
- [ ] 3 commands renamed: `mission-state`, `accept-mission`, `merge-mission`
- [ ] 2 error codes renamed: `MISSION_NOT_FOUND`, `MISSION_NOT_READY`
- [ ] `--mission` flag on all 8 commands; `--feature` not accepted
- [ ] No `feature_slug` in any response payload
- [ ] Old command names fail as unknown
- [ ] Compatibility gate invoked on outbound payloads
- [ ] Full test suite passes

## Risks

- Many string replacements in a large file (~1048 lines) — systematic search, not manual scanning
- Internal helper functions reference `feature` in names/parameters — grep for `feature` in commands.py after all changes
