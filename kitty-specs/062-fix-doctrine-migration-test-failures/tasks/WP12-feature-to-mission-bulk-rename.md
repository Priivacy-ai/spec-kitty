---
work_package_id: WP12
title: Feature-to-Mission Bulk Rename
dependencies: [WP11]
requirement_refs:
- FR-015
planning_base_branch: feature/agent-profile-implementation-rebased
merge_target_branch: feature/agent-profile-implementation-rebased
branch_strategy: Planning artifacts for this mission were generated on feature/agent-profile-implementation-rebased. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation-rebased unless the human explicitly redirects the landing branch.
subtasks:
- T043
- T044
- T045
- T046
- T047
history:
- at: '2026-04-03T20:00:00Z'
  actor: human
  action: WP added from WP08 architectural review follow-up item 3
agent_profile: python-implementer
authoritative_surface: src/specify_cli/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/tracker/origin_models.py
- src/specify_cli/tracker/saas_client.py
- src/specify_cli/tracker/origin.py
- src/specify_cli/status/bootstrap.py
- src/specify_cli/legacy_detector.py
- src/specify_cli/core/vcs/types.py
- src/specify_cli/core/worktree.py
- src/specify_cli/migration/runner.py
- src/specify_cli/scripts/debug-dashboard-scan.py
task_type: implement
---

# Work Package Prompt: WP12 -- Feature-to-Mission Bulk Rename

## Objectives & Success Criteria

- Rename ~30 missed `feature*` identifiers (parameters, variables, functions, classes, docstrings) to `mission*` equivalents across 18 production files
- Preserve backward-compat aliases where they are intentional and documented
- Do NOT touch wire-format fields (`sync/emitter.py` `feature_slug` payload key) — that requires SaaS coordination
- All tests pass after renames, with test file updates as needed
- Terminology Canon compliance for all active codepaths

## Context & Constraints

- **Origin**: WP08 architectural review finding T030
- **Scope**: This WP covers the safe renames — identifiers that are internal to the codebase and do not affect wire formats, persisted data, or external APIs
- **Excluded from scope**:
  - `sync/emitter.py` `MissionOriginBound` event schema `feature_slug` payload key — breaking wire-format change requiring SaaS coordination (document as future work)
  - Intentional backward-compat aliases (~30 across 15 files) — these have documented deprecation schedules
  - Legitimate uses of "feature" (feature flags, generic English) — 4 instances, no action needed
  - Legacy data fallbacks reading persisted JSONL `feature*` keys — 3 instances, data-format compat required
- **Terminology Canon**: `feature*` aliases in active codepaths violate the hard-break policy

## Branch Strategy

- **Planning base branch**: `feature/agent-profile-implementation-rebased`
- **Merge target branch**: `feature/agent-profile-implementation-rebased`

**Implementation command**: `spec-kitty implement WP12 --base WP11`

## Subtasks & Detailed Guidance

### Subtask T043 -- Rename tracker module identifiers

- **Purpose**: Fix missed renames in the tracker subsystem.
- **Priority files**:
  1. `tracker/origin_models.py` — Rename `feature_dir` → `mission_dir`, `feature_slug` → `mission_slug` on `MissionFromTicketResult` fields
  2. `tracker/saas_client.py` — Rename `feature_slug` parameter in `bind_mission_origin()` → `mission_slug`
  3. `tracker/origin.py` — Update call sites to pass renamed kwargs
- **Steps**:
  1. Rename the fields/parameters
  2. Add backward-compat aliases on the model fields if external consumers exist (check usage)
  3. Update all call sites in the same commit
  4. Run tracker tests: `pytest tests/tracker/ -v`
- **Files**: `origin_models.py`, `saas_client.py`, `origin.py`

### Subtask T044 -- Rename status and legacy detector identifiers

- **Purpose**: Fix missed renames in status bootstrap and legacy detection.
- **Priority files**:
  1. `status/bootstrap.py` — Rename `feature_dir` → `mission_dir`, `feature_slug` → `mission_slug` parameters
  2. `legacy_detector.py` — Rename `feature_path` → `mission_path` parameter
- **Steps**:
  1. Rename parameters and update all call sites
  2. Update docstrings to use mission terminology
  3. Run affected tests: `pytest tests/status/ tests/ -k legacy -v`
- **Files**: `bootstrap.py`, `legacy_detector.py`

### Subtask T045 -- Rename core VCS and worktree identifiers

- **Purpose**: Fix the most visible missed renames in the core module.
- **Priority files**:
  1. `core/vcs/types.py` — Rename `FeatureVCSConfig` → `MissionVCSConfig` class
  2. `core/worktree.py` — Rename `create_feature_worktree()` → `create_mission_worktree()` function
- **Steps**:
  1. Rename the class and function
  2. Add backward-compat aliases: `FeatureVCSConfig = MissionVCSConfig` and `create_feature_worktree = create_mission_worktree`
  3. Update all internal call sites to use the new names
  4. Run core tests: `pytest tests/core/ -v`
- **Files**: `types.py`, `worktree.py`

### Subtask T046 -- Rename migration runner and utility script identifiers

- **Purpose**: Fix lower-priority missed renames.
- **Files**:
  1. `migration/runner.py` — Rename any `feature*` parameters/variables
  2. `scripts/debug-dashboard-scan.py` — Update feature terminology
- **Steps**:
  1. Search each file for `feature` references
  2. Rename internal identifiers; preserve any that read legacy data formats
  3. Run migration tests: `pytest tests/migration/ -v`

### Subtask T047 -- Full test suite verification and wire-format documentation

- **Purpose**: Confirm no regressions and document excluded scope.
- **Steps**:
  1. Run the full test suite: `pytest --tb=short -q`
  2. Document the excluded wire-format rename (`sync/emitter.py` `feature_slug`) as a TODO comment in the source file with a reference to this WP
  3. Verify no new `feature*` identifiers were introduced in active codepaths (grep check)
- **Acceptance**: Zero test failures, documented wire-format exclusion

## Risks & Mitigations

- **Call site cascade**: Renaming a parameter on a widely-used function may break many call sites. Use IDE/grep to find all callers before renaming.
- **Wire-format breakage**: The `sync/emitter.py` `feature_slug` is explicitly excluded. Do NOT rename it.
- **Backward-compat aliases**: When adding aliases (e.g., `FeatureVCSConfig = MissionVCSConfig`), add a deprecation comment with the mission ID for future removal.
- **Test file renames**: Some test files may reference the old names in assertions or mocks. Update these alongside production renames.

## Review Guidance

- Verify wire-format fields are untouched
- Verify backward-compat aliases are added where needed (especially for `FeatureVCSConfig` and `create_feature_worktree`)
- Verify all call sites are updated (no orphaned references)
- Check that intentional compat aliases (~30 existing) are not disturbed

## Activity Log

- 2026-04-03T20:00:00Z -- human -- WP created from WP08 review follow-up item 3.
