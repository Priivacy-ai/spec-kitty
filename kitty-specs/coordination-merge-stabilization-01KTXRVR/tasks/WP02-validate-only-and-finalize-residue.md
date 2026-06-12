---
work_package_id: WP02
title: Read-Only Honesty and Finalize Residue (mission.py)
dependencies: []
requirement_refs:
- FR-002
- FR-006
- FR-013
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: "claude:fable-5:reviewer-renata:reviewer"
shell_pid: "54887"
history:
- '2026-06-12: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/upgrade.py
- tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py
- tests/specify_cli/test_wp06_sc2_paused_mission_blockers.py
role: implementer
tags: []
---

# WP02 — Read-Only Honesty and Finalize Residue (mission.py)

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its initialization declaration, boundaries, and governance scope for this WP.

## Objective

Three small honesty fixes anchored in `src/specify_cli/cli/commands/agent/mission.py` and `upgrade.py`: (1) `finalize-tasks --validate-only` performs zero git mutations (FR-002, closes #1861 Part 1); (2) task finalization leaves no planning-artifact residue on the primary checkout (FR-006, closes #1814 residual); (3) `upgrade --dry-run` stops printing a success line implying changes were applied (FR-013, #1784 P3 crumb).

## Context

Read first: [contracts/class-c-validate-only-readonly.md](../contracts/class-c-validate-only-readonly.md), [contracts/class-a-residual-cleanups.md](../contracts/class-a-residual-cleanups.md) §A-r1, [research.md](../research.md) R3 + R6, and the Class C / Class A-r1 sections of [validation/debbie-analysis.md](../validation/debbie-analysis.md) (file:line evidence at HEAD `956ab0e3e`; re-verify lines before editing — the file may have drifted).

Falsified — do not re-investigate: #1861 Part 2 ("safe-commit bounces the checkout") is already resolved by `SafeCommitHeadMismatch` (`8e79b3f6d`).

Constraint **C-003**: the residue fix is cleanup-at-source. Widening `COORD_OWNED_STATUS_FILES` is FORBIDDEN (double mechanism).

## Subtasks

### T005 — Red test: validate-only is read-only (write FIRST, watch it fail)

`tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py`. Fixture: temporary git repo with a coordination-topology mission whose target branch differs from the checked-out branch (reuse fixture helpers from the finalize-tasks test suite / `test_merge_coord_topology_1772.py` patterns rather than hand-rolling).

Assertions (AC-C1):
1. Capture `git symbolic-ref HEAD` and `git status --porcelain` (full bytes) before.
2. Run `finalize-tasks --validate-only --mission <m> --json` via the CLI runner.
3. Both captures byte-identical after. Also assert no new files staged (`git diff --cached --name-only` empty).
4. Validation findings in the JSON equal those from a commit-phase run's validation step on the same fixture.

At HEAD this test FAILS because of the eager checkout — that's the red proof. Commit the red test before the fix (separate commit).

### T006 — The guard

`mission.py:2462` (re-locate by searching `_ensure_branch_checked_out` call inside the finalize-tasks flow): gate the call behind `not validate_only`. Per research R3, post-WP07 validate-only reads anchor on the primary feature dir — verify no read in the validate path depends on the checkout by running the full finalize-tasks suite (AC-C2: existing tests stay green unmodified).

### T007 — Honest dry-run

`upgrade.py:987` (search the "Upgrade complete!" emission): suppress or replace with a dry-run-specific line ("Dry run complete — no changes applied.") when `--dry-run`. Add/extend the nearest existing upgrade CLI test to assert the success line is absent on dry-run and present on a real run.

### T008 — Residue cleanup at source

`_stage_finalize_artifacts_in_coord_worktree` (`mission.py:99-131`): the function stages finalize artifacts (lanes.json, tasks/*, matrices) into the coordination worktree but leaves untracked copies on the primary checkout. Fix at the writer:
- Track exactly which primary-side paths the stager materialized itself.
- After successful staging into the coord worktree, remove those copies (or avoid writing them to the primary at all if the write is incidental — choose whichever the code structure makes safest, and say which in the PR).
- NEVER delete a path the stager did not create this invocation (research R6). Defensive check: skip + warn if mtime/content differs from what was staged.
- C-003: `COORD_OWNED_STATUS_FILES` untouched.

### T009 — Residue regression test

Extend `tests/specify_cli/test_wp06_sc2_paused_mission_blockers.py` (AC-A1):
1. Coordination-topology fixture; run finalize; assert `git status --porcelain` on the primary checkout shows no `lanes.json` / `tasks/` / matrix residue.
2. Assert a subsequent `record-analysis` invocation is not blocked by DIRTY_WORKTREE from stager residue.
3. Negative control: an operator-authored untracked file planted pre-finalize SURVIVES (proves R6 scoping).

## Branch Strategy

Planning base and merge target are both `main`. Your execution worktree and branch are allocated by `spec-kitty agent action implement WP02 --agent <name>` from `lanes.json` — consume the resolved path; never construct it. Final landing on origin/main is via PR (C-005).

## Definition of Done

- [ ] T005 red test committed first, then green after T006
- [ ] AC-C1 byte-identical assertions pass; AC-C2 existing finalize suite green unmodified
- [ ] Dry-run prints no success-implying line; real run unchanged (T007)
- [ ] AC-A1: post-finalize porcelain clean; record-analysis unblocked; operator-file negative control passes (T008/T009)
- [ ] `COORD_OWNED_STATUS_FILES` diff is empty (C-003)
- [ ] ruff + mypy --strict zero suppressions; ≥90% changed-line coverage; terminology guard green

## Risks & Reviewer Guidance

- **R6 scoping is the danger zone**: reviewer, inspect T008 for any deletion path that could touch operator files; demand the negative-control test (T009.3).
- The `validate_only` guard must not change commit-phase behavior — reviewer: confirm zero diffs in commit-phase code paths.
- Error/output text changes (T007) are user-facing: check Terminology Canon (Mission, not feature).

## Activity Log

- 2026-06-12T11:57:50Z – claude:fable-5:python-pedro:implementer – shell_pid=83268 – Assigned agent via action command
- 2026-06-12T12:29:32Z – claude:fable-5:python-pedro:implementer – shell_pid=83268 – WP02 complete: T005 red test (committed first) then T006 validate-only guard; T007 honest dry-run line; T008 stager residue cleanup (R6-scoped, C-003 intact); T009 residue+negative-control tests. ruff exit 0 (diff-scoped); mypy --strict exit 0 on mission.py+upgrade.py; pytest tests/specify_cli/cli/commands/ = 962 passed / 3 pre-existing failures (verified failing on baseline with changes stashed: test_wrapper_delegation x2, test_project_migration_needed_project_dry_run_json_contract); terminology guard 2 passed. Note: WP06 test file actually lives at tests/specify_cli/cli/commands/ (owned_files path typo); test_upgrade_command.py extension mandated by T007.
- 2026-06-12T12:30:35Z – claude:fable-5:reviewer-renata:reviewer – shell_pid=54887 – Started review via action command
- 2026-06-12T12:37:32Z – user – shell_pid=54887 – Review passed: AC-C1 read-only test green with byte-identical symbolic-ref HEAD + porcelain + empty staged diff + finding parity; guard is exactly 'if not validate_only:' gating _ensure_branch_checked_out with commit-phase unchanged. AC-C2 finalize suite 71 passed/2 xfailed. T008 R6-scoped residue cleanup verified: snapshot-before-writers, byte-divergence skip+warn, operator-file negative control passes, COORD_OWNED_STATUS_FILES untouched (C-003, exact-members test pin). T007 dry-run honest, real-run unchanged, failure exits 1. T009 13 passed incl record-analysis unblocked. ruff 0, mypy --strict 0, no new suppressions. 3 claimed pre-existing failures verified environmental by reverting WP02 files to base in-place. No overlap with WP03/04/05 owned files.
