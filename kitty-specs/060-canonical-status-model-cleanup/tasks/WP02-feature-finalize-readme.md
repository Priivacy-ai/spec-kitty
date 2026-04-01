---
work_package_id: WP02
title: feature.py Changes
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: d6a4d21122fb44cd0629394506a182fad1c92753
created_at: '2026-03-31T07:14:30.787876+00:00'
subtasks: [T003, T004, T005]
history:
- at: '2026-03-31T06:58:09+00:00'
  actor: planner
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/feature.py
execution_mode: code_change
mission_id: 01KN2371WW548PPDMY6HMSB7W2
owned_files:
- src/specify_cli/cli/commands/agent/feature.py
- tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py
wp_code: WP02
---

# WP02: feature.py Changes

## Objective

Integrate canonical bootstrap into `feature.py`'s `finalize_tasks` command, add `--validate-only` support, and update the README generator at line 640 to describe lane-free WP frontmatter.

## Context

- `feature.py` finalize-tasks is at lines 1560-1639. It currently parses dependencies and updates frontmatter but does NOT seed canonical status.
- The README generator at line 640 currently documents `lane:` in WP frontmatter.
- `bootstrap_canonical_state()` from WP01 provides the shared bootstrap logic.

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

---

## Subtask T003: Integrate Bootstrap + --validate-only

**Purpose**: After dependency parsing, call `bootstrap_canonical_state()` to seed planned events for uninitialized WPs.

**Steps**:
1. Read the existing `finalize_tasks()` function in `feature.py` (around line 1560)
2. After the dependency-parsing and frontmatter-update logic, add:
   ```python
   from specify_cli.status.bootstrap import bootstrap_canonical_state
   result = bootstrap_canonical_state(feature_dir, feature_slug, dry_run=validate_only)
   ```
3. If `validate_only`: include bootstrap result in the JSON/console output (how many WPs would be seeded)
4. If not `validate_only`: bootstrap runs, events emitted, `status.json` materialized
5. Include bootstrap stats in the JSON output: `"bootstrap": {"total_wps": N, "newly_seeded": M, "already_initialized": K}`

**Files**: `src/specify_cli/cli/commands/agent/feature.py` (~20 lines added)

---

## Subtask T004: Update README Generator

**Purpose**: The generated README at line 640 currently documents `lane:` in WP frontmatter. Update it to describe the 3.0 model.

**Steps**:
1. Find the README generation code around line 640
2. Replace the `lane:` field documentation with: "Status is tracked in `status.events.jsonl`, not in WP frontmatter."
3. Remove "Valid Lane Values" section if present
4. Remove "Moving Between Lanes updates frontmatter" wording
5. Keep "Use `spec-kitty agent tasks move-task` to change WP status" guidance

**Files**: `src/specify_cli/cli/commands/agent/feature.py` (~10 lines changed)

---

## Subtask T005: Write Tests

**Steps**:
1. Create `tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py`
2. Test that finalize-tasks calls `bootstrap_canonical_state()` after dependency parsing
3. Test that `--validate-only` calls with `dry_run=True` and does not mutate files
4. Test that bootstrap stats appear in JSON output

**Files**: `tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py` (~100 lines)

---

## Definition of Done

- [ ] `feature.py` finalize-tasks calls `bootstrap_canonical_state()` after dependency parsing
- [ ] `--validate-only` uses `dry_run=True` and reports bootstrap readiness
- [ ] JSON output includes bootstrap stats
- [ ] Generated README describes lane-free frontmatter
- [ ] Tests verify bootstrap integration
- [ ] `mypy --strict` passes

## Activity Log

- 2026-03-31T07:14:31Z – orchestrator – shell_pid=83266 – lane=doing – Started implementation via workflow command
- 2026-03-31T07:19:44Z – orchestrator – shell_pid=83266 – lane=for_review – Ready for review: bootstrap integrated into finalize-tasks, README updated to lane-free, 4 tests passing
- 2026-03-31T07:20:07Z – orchestrator – shell_pid=83266 – lane=approved – Review passed: bootstrap integrated into feature.py finalize-tasks, --validate-only works with dry_run, README generator updated to lane-free model, 4 tests. Approved.
