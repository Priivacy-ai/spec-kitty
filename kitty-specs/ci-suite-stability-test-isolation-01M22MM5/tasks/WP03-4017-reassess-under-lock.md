---
work_package_id: WP03
title: '#4017 re-assess-under-lock core fix + operator signal + un-skip e2e'
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-003
- FR-005
- FR-006
- FR-007
- NFR-001
- NFR-002
planning_base_branch: issue-4017-ci-suite-stability
merge_target_branch: issue-4017-ci-suite-stability
branch_strategy: Planning artifacts for this mission were generated on issue-4017-ci-suite-stability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-4017-ci-suite-stability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-suite-stability-test-isolation-01M22MM5
base_commit: 972fb21e69e7dbeb8140df61e7ebe6e1699ec71d
created_at: '2026-09-09T10:31:55.109420+00:00'
subtasks: []
phase: Phase 2 - Lane A core fix
history:
- at: '2026-09-09T09:10:03Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/runtime/
create_intent:
- tests/runtime/test_reassess_under_lock.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/runtime/bootstrap.py
- src/specify_cli/runtime/merge.py
- tests/e2e/test_worktree_owned_root_concurrency.py
- tests/e2e/test_charter_epic_golden_path.py
- tests/runtime/test_reassess_under_lock.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer). Read the mission [spec.md](../spec.md), [plan.md](../plan.md), and [research.md](../research.md) — they carry the grounded mechanism + squad dispositions.

## Objective
The race fix: re-assess under the held cold-installer flock so the loser converges to a no-op; emit the operator signal; un-skip + DRIVE both quarantined e2e; guard source-drift; pin the #4082 live-composition interplay. (FR-001, FR-003, FR-005, FR-006, FR-007, NFR-001, NFR-002)

## Subtasks
### T006 — Re-assess-under-lock (the fix)
In ensure_runtime (bootstrap.py, COLD/effects path only), after acquiring the existing anchor flock (asset_preparation.py:516-522), RECOMPUTE effects against the now-warm home; if effects==[] return via the warm fast-path (loser no-op). Warm path (bootstrap.py:200-201) keeps exactly one assess and NO lock. Place the fix once at the authoritative seam so all three recheck nestings (bootstrap.py:202 / asset_preparation.py:567 / merge.py:94) benefit.
### T007 — Operator signal (OPERATOR_SIGNAL_CONTRACT)
On the converged-no-op path emit a human sentence + machine signal on an EXISTING operator-visible sink (CLI/log): runtime assets already materialized by a concurrent peer, nothing applied. The WP01 red-first now asserts on this SIGNAL and passes.
### T008 — Un-skip + DRIVE both e2e (must be PASSED, not skipped/xfailed — R4)
Remove the @pytest.mark.skip("#4017...") from BOTH tests/e2e/test_worktree_owned_root_concurrency.py::test_installed_cli_keeps_two_owned_worktrees_isolated and tests/e2e/test_charter_epic_golden_path.py::test_charter_epic_golden_path and RUN them for real (installed CLI). Evidence MUST show `2 passed, 0 skipped, 0 xfailed` for those nodeids (run with `-rsx`); do NOT replace skip with xfail/skipif. 0 "Global asset input changed" AND 0 "global_asset_write_failed". Register the (now-active) files per WP05's shard-map process.
### T009 — Source-drift guard (FR-003)
In tests/runtime/test_reassess_under_lock.py assert a genuine package-SOURCE change between assess and apply is STILL caught after role-tagging (no over-narrowing).
### T010 — FR-007 live-composition regression
Drive the LIVE managed_skills composition apply path (managed_skills.py:333-350: global_assets recheck + _recheck_command_completion under one lock); assert #4082 recheck_applied() YAML-receipt suppression still holds after re-assess.
### T011 — Warm-path test (NFR-002, instrumented — R6)
Assert via an INSTRUMENTED SPY (not latency/no-crash): on a warm canonical home, the assess-function call count == 1 and the lock-acquire count == 0. This is the only guard that the re-assess did not leak onto the warm path.
### T011b — FR-007 clause (a) byte-unchanged (R3)
Assert the upgrade dry-run repair-disclosure / #4082 authority-recovery PREVIEW is byte-identical before vs after the fix (SC-005 clause a), complementing T010's live-composition clause (b).

## Validation (DRIVE real e2e; create lane .venv via uv sync --frozen --all-extras first — e2e subprocess tests need <worktree>/.venv/bin/python; foreground, no Monitor parking)
PWHEADLESS=1 SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/python -m pytest tests/runtime/ tests/e2e/test_worktree_owned_root_concurrency.py tests/e2e/test_charter_epic_golden_path.py -p no:cacheprovider ; ruff+mypy clean.
## Definition of Done
- WP01 interleave GREEN asserting the operator signal; both e2e un-skipped + passing for real; source-drift + FR-007 composition + warm-path tests green; 0 new regressions vs base.
## Shard-map
Record any NEW tests/runtime/* file you create in your Activity Log for WP05's `tests/_next_shard_map.py` registration (tests/runtime is a shard-map root).

## Reviewer guidance
- Re-assess is cold-path-only (warm untouched); operator signal on an existing sink + asserted; both e2e actually DRIVEN; composition + source-drift are real tests.
