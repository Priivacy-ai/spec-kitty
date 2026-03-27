---
work_package_id: WP03
title: WP Ownership Manifest
lane: "for_review"
dependencies: [WP01]
requirement_refs:
- FR-004
- FR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: 057-canonical-context-architecture-cleanup-WP01
base_commit: c59fdb7be18bffff79d158144cd072fca7673135
created_at: '2026-03-27T18:10:54.856235+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
phase: Phase A - Foundation
assignee: ''
agent: coordinator
shell_pid: '5606'
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

# Work Package Prompt: WP03 – WP Ownership Manifest

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- Build the `ownership/` module with execution mode enum, manifest dataclass, validation, inference, and task-finalization integration.
- After this WP, every WP at finalization time has `execution_mode`, `owned_files`, and `authoritative_surface` in frontmatter.
- Overlapping `owned_files` across WPs within a mission is rejected with a validation error.
- `planning_artifact` WPs have `owned_files` that include only `kitty-specs/` or documentation paths.

## Context & Constraints

- **Spec**: FR-004 (execution_mode), FR-005 (owned_files manifest)
- **Data model**: WorkPackage entity, OwnershipManifest (embedded)
- **Plan**: Move 2 — Ownership Manifest section
- **Key constraint**: `execution_mode` must be one of: `code_change`, `planning_artifact`
- **Key constraint**: Validation runs at finalization time, not at WP creation time

## Subtasks & Detailed Guidance

### Subtask T012 – Create `ownership/__init__.py`

- **Purpose**: Package initialization with public exports.
- **Steps**: Create `src/specify_cli/ownership/__init__.py`, export `ExecutionMode`, `OwnershipManifest`, `validate_ownership`, `infer_ownership`
- **Files**: `src/specify_cli/ownership/__init__.py` (new, ~10 lines)

### Subtask T013 – Create `ownership/models.py`

- **Purpose**: Define execution mode and ownership manifest types.
- **Steps**:
  1. Create `src/specify_cli/ownership/models.py`
  2. Define `ExecutionMode` as a `StrEnum`:
     ```python
     class ExecutionMode(StrEnum):
         CODE_CHANGE = "code_change"
         PLANNING_ARTIFACT = "planning_artifact"
     ```
  3. Define `OwnershipManifest` dataclass:
     ```python
     @dataclass(frozen=True)
     class OwnershipManifest:
         execution_mode: ExecutionMode
         owned_files: tuple[str, ...]       # Glob patterns
         authoritative_surface: str          # Path prefix
     ```
  4. Add `from_frontmatter(data: dict) -> OwnershipManifest` class method
  5. Add `to_frontmatter() -> dict` method
- **Files**: `src/specify_cli/ownership/models.py` (new, ~50 lines)

### Subtask T014 – Create `ownership/validation.py`

- **Purpose**: Validate ownership across all WPs in a mission — no overlaps, completeness, prefix consistency.
- **Steps**:
  1. Create `src/specify_cli/ownership/validation.py`
  2. Implement `validate_no_overlap(manifests: dict[str, OwnershipManifest]) -> list[str]`:
     - For each pair of WPs, check if any `owned_files` glob patterns overlap
     - Use `fnmatch` or `pathspec` for glob matching
     - Return list of error messages (empty if valid)
  3. Implement `validate_authoritative_surface(manifest: OwnershipManifest) -> list[str]`:
     - Check that `authoritative_surface` is a prefix of at least one `owned_files` entry
     - Return list of error messages
  4. Implement `validate_execution_mode_consistency(manifest: OwnershipManifest) -> list[str]`:
     - If `execution_mode` is `planning_artifact`, check that `owned_files` are all under `kitty-specs/` or `docs/`
     - If `execution_mode` is `code_change`, check that `owned_files` include at least one `src/` or non-kitty-specs path
     - Return list of warnings (not hard errors — allow manual override)
  5. Implement `validate_all(manifests: dict[str, OwnershipManifest]) -> ValidationResult`:
     - Run all validations, collect errors and warnings, return structured result
- **Files**: `src/specify_cli/ownership/validation.py` (new, ~100 lines)

### Subtask T015 – Create `ownership/inference.py`

- **Purpose**: Infer `execution_mode` and `owned_files` from WP content for legacy and new WPs.
- **Steps**:
  1. Create `src/specify_cli/ownership/inference.py`
  2. Implement `infer_execution_mode(wp_content: str, wp_files: list[str]) -> ExecutionMode`:
     - If WP mentions `kitty-specs/`, `spec.md`, `plan.md`, `tasks.md`, `data-model.md` as primary deliverables → `planning_artifact`
     - If WP mentions `src/`, test files, or source code files → `code_change`
     - Default: `code_change`
  3. Implement `infer_owned_files(wp_content: str, feature_slug: str) -> list[str]`:
     - Parse file paths mentioned in the WP body (look for `src/`, `tests/`, `kitty-specs/` patterns)
     - For `planning_artifact`: default to `kitty-specs/<feature_slug>/**`
     - For `code_change`: extract specific source paths from subtask descriptions
     - Return list of glob patterns
  4. Implement `infer_authoritative_surface(owned_files: list[str]) -> str`:
     - Find the longest common prefix across owned_files
     - Return as the authoritative surface path
- **Files**: `src/specify_cli/ownership/inference.py` (new, ~80 lines)
- **Notes**: Inference is best-effort. Users can manually override any inferred value.

### Subtask T016 – Update task finalization for ownership manifest

- **Purpose**: Require ownership fields in WP frontmatter at finalization time.
- **Steps**:
  1. Locate the `finalize-tasks` command implementation (likely in `src/specify_cli/cli/commands/` or `src/specify_cli/agent/`)
  2. After dependency parsing, add ownership processing:
     - For each WP: if `execution_mode` not in frontmatter, run `infer_execution_mode()`
     - For each WP: if `owned_files` not in frontmatter, run `infer_owned_files()`
     - For each WP: if `authoritative_surface` not in frontmatter, run `infer_authoritative_surface()`
     - Write inferred values to frontmatter
  3. Run `validate_all()` across all WPs
  4. If validation errors: report and fail
  5. If validation warnings: report and continue
- **Files**: Existing finalize-tasks command file (modify, ~30 lines added)

### Subtask T017 – Tests for ownership module

- **Purpose**: 90%+ coverage on ownership module.
- **Steps**:
  1. Create `tests/specify_cli/ownership/`
  2. `test_models.py`: ExecutionMode enum values, OwnershipManifest creation, from_frontmatter/to_frontmatter round-trip
  3. `test_validation.py`: No overlap (pass), overlap detected (fail), authoritative surface prefix (pass/fail), mode consistency (pass/warn)
  4. `test_inference.py`: Code change inference, planning artifact inference, owned_files extraction from WP content
- **Files**: `tests/specify_cli/ownership/` (new, ~150 lines total)
- **Parallel?**: Yes

## Risks & Mitigations

- **Glob overlap detection**: Simple string comparison won't work for globs. Use `pathspec` library or implement basic glob intersection logic.
- **Inference accuracy**: Inference is heuristic — allow manual override. Don't block finalization on uncertain inference; emit warnings instead.

## Review Guidance

- Verify ExecutionMode has exactly two values: `code_change`, `planning_artifact`
- Verify overlap validation catches `src/**` vs `src/context/**` (nested overlap)
- Verify inference defaults to `code_change` when uncertain
- Verify finalization writes inferred values to frontmatter

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
- 2026-03-27T18:10:55Z – coordinator – shell_pid=5606 – lane=doing – Assigned agent via workflow command
- 2026-03-27T18:17:09Z – coordinator – shell_pid=5606 – lane=for_review – Ownership manifest module complete with models, validation, inference, and tests
