---
work_package_id: WP05
title: Fix Dashboard Scanner and JS Key Mismatch
dependencies: []
requirement_refs:
- FR-008
- FR-009
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
agent: "opencode"
role: "reviewer"
shell_pid: "199038"
history:
- at: '2026-04-02T17:58:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-implementer
authoritative_surface: src/specify_cli/dashboard/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/dashboard/static/dashboard/dashboard.js
task_type: implement
---

# Work Package Prompt: WP05 -- Fix Dashboard Scanner and JS Key Mismatch

## Objectives & Success Criteria

- Validate the two dashboard fixes already applied during triage
- Dashboard loads at `http://127.0.0.1:9239` and mission selector shows all missions
- No JS console errors related to undefined properties

## Context & Constraints

- **Both fixes were already applied** during the triage conversation. This WP validates correctness.
- **Fix 1** (`scanner.py:367,371`): `feature_dir` (undefined) replaced with `mission_dir` (in scope) in the `CanonicalStatusNotFoundError` handler
- **Fix 2** (`dashboard.js:1244-1246`): `data.features` replaced with `data.missions || data.features` for backward compatibility
- **Spec**: `kitty-specs/062-fix-doctrine-migration-test-failures/spec.md`

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP05`

## Subtasks & Detailed Guidance

### Subtask T016 -- Verify scanner.py NameError fix

- **Purpose**: Confirm the fix eliminates the `NameError: name 'feature_dir' is not defined` crash.
- **File**: `src/specify_cli/dashboard/scanner.py` (lines 367, 371)
- **Verification**:
  ```python
  from pathlib import Path
  from specify_cli.dashboard.scanner import scan_all_missions
  project = Path(".")
  missions = scan_all_missions(project)
  print(f"Found {len(missions)} missions")  # Should be > 0
  ```
- **Also check**: The error message now references the correct CLI command (`spec-kitty agent tasks finalize-tasks --mission` not `--feature`)

### Subtask T017 -- Verify dashboard.js key mismatch fix

- **Purpose**: Confirm the JS correctly reads `data.missions` from the API response.
- **File**: `src/specify_cli/dashboard/static/dashboard/dashboard.js` (lines 1244-1246)
- **Verification**: The fallback pattern `data.missions || data.features` ensures backward compatibility if an older API version is somehow cached.

### Subtask T018 -- Verify dashboard loads missions in browser

- **Purpose**: End-to-end validation.
- **Steps**:
  1. Start dashboard: `spec-kitty dashboard`
  2. Open `http://127.0.0.1:9239`
  3. Verify the Feature dropdown selector is populated (not empty)
  4. Select a mission and verify the kanban/overview loads
  5. Check browser console for JS errors

## Risks & Mitigations

- Dashboard may be running from a cached old version → restart with `spec-kitty dashboard --kill && spec-kitty dashboard`
- JS backward-compat pattern may mask future issues → WP08 architect review evaluates clean break

## Review Guidance

- Verify `feature_dir` does not appear anywhere in `scanner.py` (grep for it)
- Verify `data.features` only appears in the fallback position (after `||`)

## Activity Log

- 2026-04-02T17:58:00Z -- system -- Prompt created.
- 2026-04-03T14:42:45Z – opencode – Fixed remaining feature_dir NameError at line 554. JS fix already in place. 45/45 dashboard tests pass.
- 2026-04-03T14:42:50Z – opencode:unknown:generic:unknown – shell_pid=199038 – Started review via workflow command
- 2026-04-03T14:43:02Z – opencode – shell_pid=199038 – Review passed: feature_dir→mission_dir fix verified against function signature (line 500: mission_dir = resolve_mission_dir()). Zero feature_dir refs remain. 45/45 tests pass.
- 2026-04-03T16:47:46Z – opencode – shell_pid=199038 – Moved to done
