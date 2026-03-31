---
work_package_id: WP08
title: Migration Fence + Docs + Guards
dependencies: []
requirement_refs:
- FR-012
- FR-014
- FR-015
- FR-016
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 16db0586be2fcd116b74cd52564496c1c99a6b73
created_at: '2026-03-31T07:42:30.731524+00:00'
subtasks: [T030, T031, T032, T033]
shell_pid: "4238"
agent: "orchestrator"
history:
- at: '2026-03-31T06:58:09+00:00'
  actor: planner
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/task_metadata_validation.py
execution_mode: code_change
owned_files:
- src/specify_cli/task_metadata_validation.py
- src/specify_cli/status/history_parser.py
- src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py
- src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py
- docs/status-model.md
- tests/specify_cli/test_lane_regression_guard.py
---

# WP08: Migration Fence + Docs + Guards

## Objective

Mark remaining frontmatter-lane code as migration-only. Demote `history_parser.py`. Add migration-only docstrings. Update active docs. Add targeted regression guard tests that prevent reintroduction.

## Context

- After WP01-WP07, no active runtime code reads or writes frontmatter lane
- These remaining files still contain frontmatter-lane logic but are migration-only
- Active docs need updating to describe the 3.0 model consistently
- Regression guards prevent accidental reintroduction

## Implementation Command

```bash
spec-kitty implement WP08 --base WP07
```

---

## Subtask T030: Mark Migration-Only Code

**Files**: `src/specify_cli/task_metadata_validation.py`, `src/specify_cli/status/history_parser.py`

**Steps**:

1. **task_metadata_validation.py**: Add `# MIGRATION-ONLY` comment and docstring to `repair_lane_mismatch()`:
   ```python
   def repair_lane_mismatch(...):
       """MIGRATION-ONLY: Repair lane field in legacy WP frontmatter.

       This function reads and writes frontmatter ``lane`` for legacy
       migration purposes only. It must NOT be called from active runtime
       commands. Active status authority is ``status.events.jsonl``.
       """
   ```

2. **status/history_parser.py**: Add module-level docstring:
   ```python
   """MIGRATION-ONLY: Reconstruct status transitions from legacy frontmatter history.

   This module reads WP frontmatter ``history[]`` arrays to rebuild transition
   chains for migration from pre-3.0 frontmatter-lane state to canonical
   event-log state. It must NOT be called from active runtime paths.
   """
   ```

---

## Subtask T031: Add Migration-Only Docstrings to Migrations

**Files**:
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`
- `src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py`

**Steps**: Add or update module docstring to clarify these are legacy migration paths:
```python
"""Legacy migration: reads and writes frontmatter ``lane`` field.

This migration predates the canonical event-log status model (3.0).
Frontmatter lane is no longer authoritative for active features.
"""
```

No code changes — docstring-only.

---

## Subtask T032: Update Active Docs

**Steps**:

1. **docs/status-model.md** (if exists): Update to describe 3.0 model:
   - `status.events.jsonl` as sole status authority
   - `status.json` as derived materialized snapshot
   - WP frontmatter as static definition + operational metadata only
   - `finalize-tasks` as canonical bootstrap point
   - Frontmatter lane is historical/migration-only

2. **CLAUDE.md**: Update the "Status Model Patterns (034+)" section:
   - Clarify that frontmatter lane is no longer part of the active model
   - Phase description should note Phase 2 is current (event-log authority)

3. **Command help text**: Verify that `--help` output for `move-task`, `status`, and `finalize-tasks` does not reference frontmatter lane as active behavior

---

## Subtask T033: Add Regression Guard Tests

**File**: `tests/specify_cli/test_lane_regression_guard.py` (new)

**Two targeted guards**:

1. **Template guard**: Scan all `.md` files under `src/specify_cli/missions/` and `src/doctrine/` for:
   - `lane:` appearing between `---` YAML frontmatter markers
   - `lane=` in text that looks like activity log format strings
   - Fail if any match found
   - This catches templates reintroducing lane

2. **Runtime guard**: Scan all `.py` files under `src/specify_cli/` EXCLUDING:
   - `src/specify_cli/upgrade/migrations/`
   - `src/specify_cli/migration/`
   - `src/specify_cli/status/history_parser.py`
   - `src/specify_cli/task_metadata_validation.py`

   For patterns:
   - `frontmatter.get("lane"` or `frontmatter["lane"]`
   - `extract_scalar` combined with `"lane"`
   - `frontmatter` assignment with `lane`

   Fail if any match found outside the exclusion list.

   **Do NOT match**: `wp["lane"]`, `state.get("lane")`, `snapshot.lane` — these are legitimate canonical reads from reducer/materialized state.

---

## Definition of Done

- [ ] `repair_lane_mismatch` and `history_parser` marked as migration-only with clear docstrings
- [ ] Migration files have updated docstrings noting they predate 3.0
- [ ] Active docs describe the 3.0 canonical status model
- [ ] CLAUDE.md status model section updated
- [ ] Template regression guard catches lane reintroduction
- [ ] Runtime regression guard catches frontmatter-lane reads outside migration modules
- [ ] Guards do NOT false-positive on legitimate canonical state reads

## Activity Log

- 2026-03-31T07:42:31Z – orchestrator – shell_pid=4238 – lane=doing – Started implementation via workflow command
- 2026-03-31T07:48:46Z – orchestrator – shell_pid=4238 – lane=for_review – Ready for review - final WP: migration-only fences, docs update, regression guards (430 tests pass)
- 2026-03-31T07:49:15Z – orchestrator – shell_pid=4238 – lane=approved – Review passed: migration-only fences on 4 files, docs/CLAUDE.md updated for 3.0 model, 430 regression guard tests (template + runtime scan), all pass. Approved.
