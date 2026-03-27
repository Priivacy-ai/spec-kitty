---
work_package_id: WP11
title: Schema Version and Upgrade Gate
lane: planned
dependencies: [WP05]
requirement_refs:
- C-003
- C-005
- FR-019
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T054
- T055
- T056
- T057
- T058
phase: Phase D - Surface and Migration
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-27T17:23:39Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP11 – Schema Version and Upgrade Gate

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- Schema version is an integer in `metadata.yaml`, not heuristic file/directory detection.
- Every CLI command checks schema version before executing.
- Unmigrated projects are refused with an actionable error message.
- Projects newer than the CLI are also refused (upgrade your CLI).
- The heuristic `VersionDetector` (~15 checks) is replaced with a single integer comparison.

## Context & Constraints

- **Spec**: FR-019, FR-020, C-003, C-005
- **Plan**: Move 5 — Schema Version Model section
- **Key files to rewrite**: `upgrade/detector.py`, `upgrade/runner.py`
- **Depends on**: WP05 (canonical state model defines what schema_version=3 means)

## Subtasks & Detailed Guidance

### Subtask T054 – Create migration/schema_version.py

- **Purpose**: Schema version detection and compatibility checking.
- **Steps**:
  1. Create `src/specify_cli/migration/schema_version.py`
  2. Define constant: `REQUIRED_SCHEMA_VERSION = 3`
  3. Define capabilities list:
     ```python
     SCHEMA_CAPABILITIES = {
         3: ["canonical_context", "event_log_authority", "ownership_manifest", "thin_shims"]
     }
     ```
  4. Implement `get_project_schema_version(repo_root: Path) -> int | None`:
     - Read `.kittify/metadata.yaml`
     - Return `spec_kitty.schema_version` (integer)
     - Return `None` if field missing (legacy project)
  5. Implement `check_compatibility(project_version: int | None, cli_version: int) -> CompatibilityResult`:
     - `None` → "unmigrated" (must upgrade project)
     - `project < cli` → "outdated" (must upgrade project)
     - `project == cli` → "compatible"
     - `project > cli` → "cli_outdated" (must upgrade CLI)
     - Return structured result with message and exit code
- **Files**: `src/specify_cli/migration/schema_version.py` (new, ~60 lines)
- **Parallel?**: Yes — can proceed alongside T055

### Subtask T055 – Create migration/gate.py

- **Purpose**: Upgrade gate that runs before every CLI command.
- **Steps**:
  1. Create `src/specify_cli/migration/gate.py`
  2. Implement `check_schema_version(repo_root: Path) -> None`:
     - Call `get_project_schema_version(repo_root)`
     - Call `check_compatibility(project_version, REQUIRED_SCHEMA_VERSION)`
     - If not compatible: print actionable message and `raise SystemExit(1)`
     - Messages:
       - Unmigrated: "Project requires migration. Run `spec-kitty upgrade` to continue."
       - Outdated: "Project schema version {n} is outdated. Run `spec-kitty upgrade` to update to version {required}."
       - CLI outdated: "Project schema version {n} is newer than this CLI supports ({required}). Upgrade your CLI: `pip install --upgrade spec-kitty-cli`"
  3. Implement as typer callback — runs before any command dispatch
  4. Exempt commands from gate: `upgrade`, `init`, `--version`, `--help`
  5. The gate should also check if `.kittify/` exists (not initialized → skip gate, let `init` handle it)
- **Files**: `src/specify_cli/migration/gate.py` (new, ~50 lines)
- **Parallel?**: Yes — can proceed alongside T054

### Subtask T056 – Rewrite upgrade/detector.py

- **Purpose**: Replace ~15 heuristic checks with schema version lookup.
- **Steps**:
  1. Read `src/specify_cli/upgrade/detector.py` — understand the `VersionDetector` class
  2. Rewrite to:
     - Primary detection: read `schema_version` from `metadata.yaml`
     - Legacy detection (for migration): if `schema_version` missing, check for `.kittify/` existence → version 0 (needs migration)
     - Remove ALL heuristic checks (directory existence, gitignore patterns, file presence)
  3. The detector should be ~20 lines after rewrite (down from ~200+)
- **Files**: `src/specify_cli/upgrade/detector.py` (rewrite, ~180 lines removed)

### Subtask T057 – Simplify upgrade/runner.py

- **Purpose**: Schema-version-based migration selection.
- **Steps**:
  1. Read `src/specify_cli/upgrade/runner.py` — understand `MigrationRunner`
  2. Simplify migration selection:
     - Old: check each migration's `should_apply()` (heuristic-based)
     - New: if `current_schema_version < REQUIRED_SCHEMA_VERSION`: apply the one-shot migration
     - Legacy migrations (pre-3.0) are kept for historical reference but skipped by schema version check
  3. Update to use `schema_version` from metadata.yaml instead of heuristic version detection
  4. After migration: update `metadata.yaml` with new schema_version
- **Files**: `src/specify_cli/upgrade/runner.py` (modify, ~50 lines changed)

### Subtask T058 – Tests for schema version gate

- **Purpose**: Verify gate behavior in both directions.
- **Steps**:
  1. Create `tests/specify_cli/migration/test_schema_version.py`
  2. Test: schema_version missing → "unmigrated" result
  3. Test: schema_version = 2 → "outdated" result
  4. Test: schema_version = 3 → "compatible" result
  5. Test: schema_version = 4 → "cli_outdated" result
  6. Test: gate raises SystemExit for incompatible projects
  7. Test: gate allows `upgrade` command to pass through
  8. Test: gate skips when no `.kittify/` exists (uninitialized project)
- **Files**: `tests/specify_cli/migration/test_schema_version.py` (new, ~80 lines)
- **Parallel?**: Yes

## Risks & Mitigations

- **Gate too aggressive on init**: Ensure the gate skips for `init` and `--help` commands.
- **Heuristic fallback**: DO NOT add a heuristic fallback "just in case." The whole point is to eliminate heuristics.

## Review Guidance

- Verify VersionDetector no longer has heuristic checks
- Verify gate is a typer callback on the main app
- Verify exempt commands list is complete
- Verify messages are actionable (include exact commands to run)

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
