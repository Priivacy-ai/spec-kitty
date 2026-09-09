---
work_package_id: WP01
title: 'Tidy-first: decompose upgrade() entry (behavior-preserving)'
dependencies: []
requirement_refs:
- FR-005
- NFR-002
planning_base_branch: issue-1931-ci-rework-test-remainders
merge_target_branch: issue-1931-ci-rework-test-remainders
branch_strategy: Planning artifacts for this mission were generated on issue-1931-ci-rework-test-remainders. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-1931-ci-rework-test-remainders unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-upgrade-no-migrations-provisioning-fix-01M20NK8
base_commit: 864e4d1dd7a12e71b0876345430c8cc127c8ee5f
created_at: '2026-09-08T15:02:37.802571+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Tidy-first enabler
history:
- at: '2026-09-08T14:41:39Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/upgrade.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/upgrade.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objective

Decompose the ~345-line `upgrade()` entry point (`src/specify_cli/cli/commands/upgrade.py:1421`, currently `# noqa: C901`) into named, testable sub-functions with **zero behavior change**, and remove the suppression. This is the tidy-first enabler that gives WP02 a testable surface. (FR-005, NFR-002, C-004.)

## Context

- This is a **distinct, behavior-preserving step** that precedes the functional fix (charter Standing Order #2). Do NOT fold any provisioning/guard logic change into this WP — that is WP02.
- `upgrade()` spans ~1421→1766. Its blocks include: migration invocation (`MigrationRunner(...).upgrade`, ~:1640), dry-run preview, finalizer repairs (`_prepare_finalizer_repairs`, ~:1662-1698), outcome + exit-code derivation, and human/JSON reporting.
- Canonical source discipline: do not copy structure from older missions; extract from the live function.

## Subtasks & Guidance

### T001 — Map the extraction seams
Read `upgrade()` end to end. Produce (in the Activity Log) a short map of cohesive blocks and the seams between them. **Hard constraint:** identify the `repair_preflight` `with` span — the `ExitStack` + `_RECHECKED_PROJECT`/`_COMMAND_PARENTS` ContextVars + `_PROJECT_SKILL_LOCK` RLock (`upgrade/finalize.py:59-64`, `skills/installer.py:476-480`) — and mark it as an **atomic unit that must NOT be split** across functions that open/close their own contexts.

### T002 — Extract cohesive sub-functions (+ expose a generic diagnostic-render seam)
Extract named helpers (e.g. `_run_migration_phase`, `_build_upgrade_outcome`, `_report_upgrade_outcome`) so `upgrade()` becomes an orchestrator. Keep intact: the preflight `with` span spanning provision+surface as one extracted unit; the exit-code matrix (`outcome.derive_exit_code()`); and the `if not dry_run and outcome.result.success` guard before `_prepare_finalizer_repairs` (`:1662-1663`). No signature change to the public `upgrade()` Typer command.

**Ownership seam (resolves the WP01/WP02 ownership finding):** `cli/commands/upgrade.py` is owned by WP01 only, but WP02 must surface a non-error `deferred_provisioning` diagnostic through the human `Note:` render (~:428/:478) and the JSON payload (`dict(result.rendered_json)`, ~:145-148). So `_report_upgrade_outcome` must render **any** non-error diagnostics carried generically on the outcome (iterate the outcome's non-error diagnostic collection → `Note:` lines), and the JSON path must already pass `result.rendered_json` through unchanged. This seam is **behavior-preserving**: no non-error deferred diagnostic exists yet, so it renders nothing today. WP02 then only *populates* the diagnostic from its owned `assessment.py`/`finalize.py` layer and it flows out through this seam — no per-signal CLI code, no WP02 edit to this file. (If a per-signal CLI line proves unavoidable, WP02 takes a single, recorded out-of-map edit here per charter ownership-map leeway — safe because execution is strictly sequential WP01→WP02.)

### T003 — Drop the suppression; satisfy complexity
Remove `# noqa: C901` from `upgrade()`. Ensure every extracted function passes Ruff `C901` (≤15) and the whole file is `ruff check` + `mypy` clean with **no** new `# noqa`/`# type: ignore`/per-file-ignore (C-002).

### T004 — Prove behavior-preserving
Run and pass `test_no_stray_noqa_c901_marker` (`tests/upgrade/test_upgrade_integration.py`). Run the pre-existing upgrade behavior tests and confirm every test that passed before this WP still passes (no assertion changes). Do NOT attempt to green the config-absent failures — those are WP02's (they stay red after WP01).

## Branch Strategy
- **Planning base**: `issue-1931-ci-rework-test-remainders` · **Merge target**: `issue-1931-ci-rework-test-remainders`
- Execution worktree is allocated per computed lane from `lanes.json`; do not hand-construct it.

## Definition of Done
- `upgrade()` decomposed; `# noqa: C901` removed; ruff + mypy clean.
- `test_no_stray_noqa_c901_marker` green; all previously-passing upgrade tests still green.
- No behavior change (no provisioning/guard logic touched).

## Reviewer guidance
- Confirm the preflight `with` span was not split; confirm exit-code/dry-run guard intact; diff should be pure extraction (no logic edits). Verify no new suppressions.
