---
work_package_id: WP12
title: One-Shot Migration — Identity and Ownership Backfill
lane: "doing"
dependencies:
- WP03
requirement_refs:
- C-006
- FR-018
- FR-021
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: 057-canonical-context-architecture-cleanup-WP03
base_commit: 13d557839a5e27b17c4005649dc5af63c97f975c
created_at: '2026-03-27T19:48:43.961374+00:00'
subtasks:
- T059
- T060
- T061
- T062
- T063
- T064
phase: Phase D - Surface and Migration
assignee: ''
agent: "coordinator"
shell_pid: "96229"
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

# Work Package Prompt: WP12 – One-Shot Migration — Identity and Ownership Backfill

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- `project_uuid` assigned to `metadata.yaml`.
- `mission_id` assigned to every feature's `meta.json`.
- `work_package_id` and `wp_code` assigned to every WP's frontmatter.
- `execution_mode` and `owned_files` inferred and written to WP frontmatter.
- Mutable frontmatter fields (lane, review_status, reviewed_by, progress) stripped.
- Agent command files rewritten as thin shims.

## Context & Constraints

- **Spec**: FR-018 (one-shot migration), FR-021 (immutable identity), C-006 (legacy as migration input)
- **Plan**: Migration Design section
- **Depends on**: WP03 (ownership inference), WP09 (shim generator), WP11 (schema version)
- **Key constraint**: Migration reads legacy state but does NOT preserve legacy runtime behavior.

## Subtasks & Detailed Guidance

### Subtask T059 – Create migration/__init__.py

- **Purpose**: Package initialization with public exports.
- **Steps**: Create `src/specify_cli/migration/__init__.py`, export main functions
- **Files**: `src/specify_cli/migration/__init__.py` (new, ~15 lines)

### Subtask T060 – Create migration/backfill_identity.py

- **Purpose**: Assign immutable IDs to all entities.
- **Steps**:
  1. Create `src/specify_cli/migration/backfill_identity.py`
  2. Implement `backfill_project_uuid(repo_root: Path) -> str`:
     - Generate ULID
     - Write to `.kittify/metadata.yaml` under `spec_kitty.project_uuid`
     - Return the UUID
  3. Implement `backfill_mission_ids(repo_root: Path) -> dict[str, str]`:
     - Scan `kitty-specs/` for all feature directories
     - For each feature: read `meta.json`, generate `mission_id` (ULID), write back
     - Return mapping of feature_slug → mission_id
  4. Implement `backfill_wp_ids(feature_dir: Path, mission_id: str) -> dict[str, str]`:
     - Scan `tasks/*.md` for all WP files
     - For each WP:
       - Generate `work_package_id` (ULID)
       - Extract `wp_code` from existing WP label (e.g., filename `WP01-foo.md` → `wp_code: "WP01"`)
       - Write `work_package_id`, `wp_code`, `mission_id` to frontmatter
     - Return mapping of wp_code → work_package_id
  5. Use `ruamel.yaml` for round-trip YAML editing (preserve comments, formatting)
- **Files**: `src/specify_cli/migration/backfill_identity.py` (new, ~100 lines)
- **Parallel?**: Yes — can proceed alongside T061

### Subtask T061 – Create migration/backfill_ownership.py

- **Purpose**: Infer execution_mode and owned_files for legacy WPs.
- **Steps**:
  1. Create `src/specify_cli/migration/backfill_ownership.py`
  2. Implement `backfill_ownership(feature_dir: Path, feature_slug: str) -> None`:
     - For each WP in `tasks/*.md`:
       - Read WP body content
       - Call `infer_execution_mode()` from ownership/inference.py
       - Call `infer_owned_files()` from ownership/inference.py
       - Call `infer_authoritative_surface()` from ownership/inference.py
       - Write inferred values to frontmatter (only if not already present)
  3. Optional: try to infer from git branch diff if branch exists:
     - `git diff --name-only <target_branch>..<wp_branch>`
     - Use changed files as owned_files
     - This is best-effort — not all WPs have branches
  4. Run `validate_all()` on inferred manifests — log warnings, don't fail
- **Files**: `src/specify_cli/migration/backfill_ownership.py` (new, ~80 lines)
- **Parallel?**: Yes — can proceed alongside T060

### Subtask T062 – Create migration/strip_frontmatter.py

- **Purpose**: Remove mutable status fields from all WP frontmatter.
- **Steps**:
  1. Create `src/specify_cli/migration/strip_frontmatter.py`
  2. Implement `strip_mutable_fields(feature_dir: Path) -> StripResult`:
     - For each WP in `tasks/*.md`:
       - Read frontmatter
       - BEFORE stripping: record current `lane` value (needed for state rebuild in T065)
       - Remove keys: `lane`, `review_status`, `reviewed_by`, `review_feedback`, `progress`, `shell_pid`, `assignee`, `agent`
       - Keep keys: `work_package_id`, `wp_code`, `mission_id`, `title`, `dependencies`, `execution_mode`, `owned_files`, `authoritative_surface`, `subtasks`, `phase`, `planning_base_branch`, `merge_target_branch`, `branch_strategy`
       - Write back using ruamel.yaml (preserve body content)
     - Also strip from `tasks.md` if it contains status blocks
     - Return result with count of fields stripped, WPs processed
  3. This step MUST run AFTER state rebuild (T065) — the lane values are needed as migration input
- **Files**: `src/specify_cli/migration/strip_frontmatter.py` (new, ~80 lines)
- **Parallel?**: Yes — but must coordinate ordering with T065

### Subtask T063 – Create migration/rewrite_shims.py

- **Purpose**: Replace agent command files with thin shims.
- **Steps**:
  1. Create `src/specify_cli/migration/rewrite_shims.py`
  2. Implement `rewrite_agent_shims(repo_root: Path) -> RewriteResult`:
     - Call `generate_all_shims(repo_root)` from shims/generator.py
     - Delete any existing command files that are NOT in the generated set (cleanup)
     - Return result with: agents processed, files written, files deleted
  3. This reuses the shim generator from WP09 — no duplication
- **Files**: `src/specify_cli/migration/rewrite_shims.py` (new, ~30 lines)
- **Parallel?**: Yes

### Subtask T064 – Tests for migration steps

- **Purpose**: Verify each migration step works correctly in isolation.
- **Steps**:
  1. Create `tests/specify_cli/migration/`
  2. `test_backfill_identity.py`:
     - project_uuid assigned and persisted
     - mission_id assigned to each feature
     - work_package_id and wp_code assigned to each WP
     - IDs are ULIDs (valid format)
     - Existing IDs are not overwritten
  3. `test_backfill_ownership.py`:
     - code_change inferred for source code WPs
     - planning_artifact inferred for kitty-specs WPs
     - Existing ownership not overwritten
  4. `test_strip_frontmatter.py`:
     - Mutable fields removed
     - Static fields preserved
     - Body content preserved
     - Works with ruamel.yaml round-trip
  5. `test_rewrite_shims.py`:
     - Agent command files replaced with thin shims
     - Old template content gone
  6. Use fixture: create a legacy project directory structure with realistic content
- **Files**: `tests/specify_cli/migration/` (new, ~200 lines total)
- **Parallel?**: Yes

## Risks & Mitigations

- **YAML round-trip corruption**: Use `ruamel.yaml` with `preserve_quotes=True` for frontmatter editing.
- **Missing WP files**: Some features may have `tasks.md` but no `tasks/` directory. Handle gracefully.
- **Ownership inference quality**: Inference is best-effort. The migration should log warnings for low-confidence inferences.

## Review Guidance

- Verify IDs are ULIDs (not UUIDs, not sequential)
- Verify existing IDs are never overwritten
- Verify mutable fields are completely removed from frontmatter
- Verify body content (after frontmatter) is preserved byte-for-byte
- Verify shim rewrite uses generator from WP09

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
- 2026-03-27T19:48:44Z – coordinator – shell_pid=96229 – lane=doing – Assigned agent via workflow command
