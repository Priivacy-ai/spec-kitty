---
work_package_id: WP03
title: Surgical test reconciliation off the standalone surface
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-009
- NFR-002
tracker_refs: []
planning_base_branch: mission/retire-standalone-tasks-cli
merge_target_branch: mission/retire-standalone-tasks-cli
branch_strategy: Planning artifacts for this mission were generated on mission/retire-standalone-tasks-cli. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/retire-standalone-tasks-cli unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
- T015
phase: Phase 3 - Test reconciliation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "818365"
history:
- at: '2026-06-29T22:08:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/cross_cutting/misc/test_acceptance_support.py
- tests/specify_cli/test_feature_metadata.py
- tests/specify_cli/acceptance/test_accept_pre30_hard_reject.py
- tests/specify_cli/test_acceptance_regressions.py
- tests/upgrade/test_pre30_guard_wiring.py
- tests/specify_cli/test_lane_regression_guard.py
- tests/specify_cli/test_codebase_sweep.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Surgical test reconciliation off the standalone surface

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

Edit the **behavior-bearing** test files so they stop depending on the standalone tasks CLI — repoint imports to canonical, delete genuinely-dead-only tests, and add the one real-CLI regression that preserves a contract — **while the standalone modules still exist**. The deletion itself happens in WP04; this WP must leave the suite green with the modules still present, so that WP04's deletion only removes the (by-then) DELETE-class scaffolding.

**Critical correctness rule (NFR-002)**: do not lose canonical coverage. Several of these files reach *canonical* behavior through the standalone alias/shim — those assertions must be **repointed**, not deleted. Only delete tests that exercise standalone-only code with no canonical equivalent (the plan/research name each).

## Subtasks

### T009 — `tests/cross_cutting/misc/test_acceptance_support.py` (the careful one)
This file is **SURGICAL, not delete**. It has 19 tests; **8 drive the real `spec-kitty accept`** via `from specify_cli import app as cli_app` + `CliRunner` and are **not duplicated anywhere else**. These 8 MUST survive (relocated, not deleted):
1. `test_accept_command_reports_approved_wps_without_closing` (:138)
2. `test_accept_diagnose_json_reports_missing_events_bootstrap_issue` (:192)
3. `test_accept_no_commit_reports_merge_pending_without_mutation` (:223)
4. `test_accept_diagnose_json_reports_skipped_checks_without_mutation` (:267)
5. `test_accept_diagnose_json_blocks_corrupt_lanes_json` (:306)
6. `test_accept_diagnose_does_not_mutate_matrix_metadata_or_events` (:345)
7. `test_accept_diagnose_does_not_execute_custom_negative_invariants` (:408)
8. `test_accept_does_not_require_done_evidence_for_approved_wp` (:467)

The `import acceptance_support as acc` is a thin re-export shim whose `acc.*` resolve to canonical `specify_cli.acceptance`.
- Swap module-level imports: `import acceptance_support as acc` → `from specify_cli import acceptance as acc`; `import task_helpers as th` → the needed canonical helpers from `specify_cli.task_utils.support`.
- Repoint any `run_tasks_cli(...)` seed setup to the real CLI (`cli_app` + `CliRunner`) or to `emit_status_transition` directly.
- **Keep** all real-CLI (`cli_app`) tests and the canonical-engine `acc.*` tests. If the `tests/cross_cutting/misc/` path is being retired, relocate the kept tests to `tests/specify_cli/acceptance/` (preserve their names).
- **Delete** only: the `normalize_feature_encoding` + encoding-error assertions (now covered on the real surface by WP02) and any test that asserts standalone-API *shape* with no canonical meaning.
- After: `grep "scripts.tasks\|run_tasks_cli\|import acceptance_support\|import task_helpers" <file>` → nothing.

### T010 — `tests/specify_cli/test_feature_metadata.py` `[P]`
Delete only the class `TestMergeToleranceMalformedMeta` (`:856-972`, 4 methods, all `from specify_cli.scripts.tasks.tasks_cli import _prepare_merge_metadata/_finalize_merge_metadata`). These wrap functions that have **zero production callers** (accepted loss — the canonical merge path writes status events, never `meta.json` merge_history). **Keep** the canonical `TestRecordMerge` / `TestFinalizeMerge` / `TestRecordMergeBoundedHistory` / `TestFinalizeMergeUpdatesHistory` classes (they import from `specify_cli.mission_metadata` and are unaffected).

### T011 — `tests/specify_cli/acceptance/test_accept_pre30_hard_reject.py`
- **Keep** `test_collect_feature_summary_rejects_pre30` (`:112-133`) and the helpers `_pre30_repo` / `_head` / `_run_git` / constants.
- **Delete** the `from specify_cli.scripts.tasks import tasks_cli` import (`:28`), `_accept_args` (`:141-152`), and the three standalone-command tests (`test_accept_command_hard_rejects_pre30_and_commits_nothing:155`, `test_verify_command_hard_rejects_pre30:185`, `test_merge_command_hard_rejects_pre30:209`).
- **Add** a thin real-CLI regression (FR-009): invoke `spec-kitty accept` via `CliRunner`/`cli_app` on the existing `_pre30_repo` fixture; assert exit code 1, output contains `spec-kitty upgrade`, and no commit was created. This pins `accept.py:305 except Pre30LayoutError` directly (the engine test already covers `collect_feature_summary`).

### T012 — `tests/specify_cli/test_acceptance_regressions.py` `[P]`
Delete only T014 `test_standalone_tasks_cli_help` (`:1075-1094`, subprocess-runs the standalone `tasks_cli.py --help`) and T016 (the `acceptance.py ↔ acceptance_support.py` API-alignment test, `:1173-1206`, `from specify_cli.scripts.tasks import acceptance_support` — moot once the shim is gone). Keep all other (canonical `specify_cli.acceptance`) regressions.

### T013 — `tests/upgrade/test_pre30_guard_wiring.py` `[P]`
Delete the test functions that arm the standalone `tasks_cli.update_command` / `list_command` / `history_command` pre-3.0 guard (the ones importing `specify_cli.scripts.tasks.tasks_cli`, ≈`:317-330+`). Keep any canonical guard-wiring tests in the file that target `upgrade/pre30_guard` directly. Confirm no module-level import of `tasks_cli` remains.

### T014 — `tests/specify_cli/test_lane_regression_guard.py` `[P]`
Delete the `_standalone_task_scripts` list (`:220-223`, hardcoded paths to both `tasks_cli.py`) and the test that parametrizes it (`test_standalone_task_scripts_do_not_write_lane_activity_entries:247-251`) — they read the files and would `FileNotFoundError` post-deletion. Keep `test_runtime_no_frontmatter_lane_access` and `_collect_runtime_py_files` (it rglobs `src/`+`scripts/` and tolerates the missing dir).

### T015 — `tests/specify_cli/test_codebase_sweep.py` `[P]`
Delete `test_no_direct_meta_json_writes_in_standalone_scripts` (`:117-133`) — it early-returns when `scripts/tasks/` is absent (becomes vacuous). The canonical `test_no_direct_meta_json_writes` (src/) remains the real guard.

## Verification (this WP)
```bash
# Nothing surgical may reference the standalone surface in ANY form (dotted import,
# bare sys.path import, run_tasks_cli, or path string) — the dotted-only grep is
# BLIND to test_acceptance_support.py's bare `import acceptance_support`/`task_helpers`
# and to test_lane_regression_guard.py's `scripts/tasks/...` path string:
for f in tests/cross_cutting/misc/test_acceptance_support.py tests/specify_cli/test_feature_metadata.py \
         tests/specify_cli/acceptance/test_accept_pre30_hard_reject.py tests/specify_cli/test_acceptance_regressions.py \
         tests/upgrade/test_pre30_guard_wiring.py tests/specify_cli/test_lane_regression_guard.py \
         tests/specify_cli/test_codebase_sweep.py; do
  grep -nE "specify_cli\.scripts\.tasks|scripts/tasks|run_tasks_cli|import acceptance_support|import task_helpers" "$f" \
    && echo "FAIL: $f still references the standalone surface"; done

# NFR-002 retention guard: the 8 real-CLI accept tests must survive. cli_app/CliRunner
# reference count must NOT drop below the pre-edit floor (none of the deleted
# standalone-encoding tests use cli_app, so the count can only stay equal):
test "$(grep -cE 'cli_app|CliRunner' tests/cross_cutting/misc/test_acceptance_support.py 2>/dev/null || \
        grep -rcE 'cli_app|CliRunner' tests/specify_cli/acceptance/ 2>/dev/null | paste -sd+ | bc)" -ge 11 \
  && echo "cli_app retention OK (>=11)" || echo "FAIL: real-CLI accept tests lost"

PWHEADLESS=1 .venv/bin/python -m pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q
```
Suite green; the seven files no longer reference the standalone surface in any form; the 8 real-CLI accept tests are retained (relocated if the cross_cutting path is torn down). (The DELETE-class scaffolding still references the surface — that is WP04.)

## Definition of Done
- All seven files reconciled per the subtasks; the **8 enumerated real-CLI tests** in `test_acceptance_support.py` survive (relocated if needed); the new real-CLI pre-3.0 reject regression added and passing.
- The broad grep (`specify_cli\.scripts\.tasks|scripts/tasks|run_tasks_cli|import acceptance_support|import task_helpers`) across these seven files → nothing (the dotted-only form is insufficient — it misses the bare imports and the path string).
- The `cli_app|CliRunner` retention check passes (≥11).
- Full suite green (standalone modules still present). `ruff` clean on changed files.

## Risks
- **Over-deletion of canonical coverage** (the gate's prior finding): when in doubt about whether a `test_acceptance_support.py` test is standalone-only or canonical, keep it and repoint. Losing the 8 real-CLI tests is a hard reject.
- **Hidden module-level import** left behind → collection error in WP04. Mitigation: the grep gate above must be clean before marking done.

## Reviewer guidance
Confirm NFR-002 is honored: every deleted test is genuinely standalone-only (named in plan/research), and every canonical/real-CLI assertion is repointed and surviving. Verify the new pre-3.0 real-CLI regression actually fails if `accept.py:305` is removed. Reject if any `cli_app` test from `test_acceptance_support.py` was dropped, or if any of the seven files still imports `specify_cli.scripts.tasks`.

## Activity Log

- 2026-06-30T00:04:45Z – claude:sonnet:python-pedro:implementer – shell_pid=797279 – Assigned agent via action command
- 2026-06-30T00:25:27Z – claude:sonnet:python-pedro:implementer – shell_pid=797279 – FR-004/FR-009/NFR-002: 7 files reconciled off the standalone surface; broad grep clean; cli_app retention=11 (8 named tests preserved); FR-009 pre-30 real-CLI regression added + mutation-verified; 1192 focused tests pass; modules still present; ruff clean. commit e22d4d8c5.
- 2026-06-30T00:25:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=818365 – Started review via action command
- 2026-06-30T00:30:35Z – user – shell_pid=818365 – Review passed (reviewer-renata): 8 cli_app tests preserved; broad grep clean; deletions dead-only; FR-009 regression non-vacuous; 1192 tests pass; modules still present; ruff clean.
