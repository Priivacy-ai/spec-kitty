---
work_package_id: WP03
title: 'Merge Pipeline: Ref-Advance Resync and Driver Hardening'
dependencies: []
requirement_refs:
- FR-001
- FR-008
- FR-012
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
- T016
- T017
agent: "claude:fable-5:reviewer-renata:reviewer"
shell_pid: "85711"
history:
- '2026-06-12: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/merge.py
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/git/commit_helpers.py
- src/specify_cli/git/ref_advance.py
- src/specify_cli/coordination/status_transition.py
- tests/specify_cli/cli/commands/test_merge_coord_worktree_resync_1826.py
- tests/status/test_event_log_merge.py
- tests/architectural/test_merge_pipeline_ratchets.py
role: implementer
tags: []
---

# WP03 — Merge Pipeline: Ref-Advance Resync and Driver Hardening

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its initialization declaration, boundaries, and governance scope for this WP.

## Objective

Kill the only fully-live release blocker of the 3.2.0 cluster: after merge-pipeline `git update-ref` calls, the coordination worktree is left behind its own checked-out branch and the next bookkeeping safe-commit aborts with `SafeCommitBackstopError` (#1826, FR-001). Ship the resync as a shared helper with a no-raw-update-ref ratchet, make the backstop message name the divergence (FR-012), and land the Class F merge-driver hardening that shares these files (FR-008b/c/d, #1736 residuals).

## Context

Read first: [contracts/class-b-ref-advance-resync.md](../contracts/class-b-ref-advance-resync.md), [contracts/class-f-merge-driver-hardening.md](../contracts/class-f-merge-driver-hardening.md), [research.md](../research.md) R1/R2/R7, and the Class B + Class F sections of [validation/debbie-analysis.md](../validation/debbie-analysis.md).

Mechanism (verified at HEAD `956ab0e3e` — re-verify line numbers before editing):
- Stage-1 lane→mission merges advance `refs/heads/<mission-branch>` via `git update-ref` from detached temp worktrees: `src/specify_cli/lanes/merge.py:440` and `:474`.
- Mission-number baking does the same: `src/specify_cli/cli/commands/merge.py:993-998`.
- That branch is checked out in the coordination worktree (`merge.py:2513-2515`); `update-ref` bypasses git's checked-out-branch protection → the coord worktree's index is behind its own HEAD.
- `_record_merged_wps_done_for_merge` (`merge.py:662-695`) then commits status events through that worktree (`BookkeepingTransaction`, `coordination/transaction.py:744-815`) → safe_commit backstop (`git/commit_helpers.py:474-519`, message `:333`) sees phantom staged deletions → `SafeCommitBackstopError`.
- No repair exists: `_refresh_primary_checkout_after_merge` (`merge.py:698-718`) resets only the primary; `CoordinationWorkspace.resolve` checks the symbolic-ref name only.

Falsified — do not re-litigate: "the backstop is buggy" (it is the detector working as designed); "self-heal in BookkeepingTransaction" (rejected, R1 — one mechanism).

Constraints: **C-002** migrate ONLY the three sites above. **C-004** T016 (except-narrowing) lands after T011–T013. **NFR-002** no silent data discard. **C-001** no resolver/topology changes.

## Subtasks

### T010 — Red test (FIRST)

`tests/specify_cli/cli/commands/test_merge_coord_worktree_resync_1826.py`, fixture pattern from `test_merge_coord_topology_1772.py`: coordination-topology mission, ≥2 lane WPs, mission-number baking enabled. Assertions:
- AC-B1: `spec-kitty merge` end-to-end completes; `_record_merged_wps_done_for_merge` commits with NO `SafeCommitBackstopError`; zero manual git interventions (NFR-001).
- AC-B2: after each Stage-1 ref advance, coord worktree `git rev-parse HEAD` == branch tip AND `git status --porcelain` clean (probe via a test hook or by asserting between stages if the pipeline is staged in-process).
Commit the red test before the fix.

### T011 — The helper

New module `src/specify_cli/git/ref_advance.py` (name final; keep in `git/` beside commit_helpers): `advance_branch_ref(repo_root, branch, new_sha, *, lock=...)`:
1. Perform the `update-ref`.
2. Enumerate worktrees (`git worktree list --porcelain`) for any checkout of `branch`.
3. For each: if `git status --porcelain` is empty → `git -C <wt> reset --hard <branch>`; else raise the T013 structured error.
4. Run under the same feature-status lock discipline the call sites already hold (do not introduce a second lock ordering — inspect callers first).
Docstring states the invariant: "no worktree may be left checked out behind a ref this function advanced" and cites #1826.

### T012 — Migrate the three sites

`lanes/merge.py:440`, `:474`, `cli/commands/merge.py:993-998` call the helper. NO other site (C-002). Diff review rule: raw `update-ref` count in `src/specify_cli` drops to zero outside `ref_advance.py`.

### T013 — Dirty-worktree refusal (AC-B4)

Structured exception (e.g. `RefAdvanceDirtyWorktreeError`) carrying: worktree path, branch, old→new SHA, dirty entries list (NFR-003). Merge surfaces it like other merge failures — `merge-state.json` stays resumable. Test: plant a file in the coord worktree mid-fixture; assert refusal, assert the file survives untouched, assert `spec-kitty merge --resume` works after the operator commits/cleans.

### T014 — Backstop message (FR-012)

`git/commit_helpers.py:321-339`: when the backstop trips, the message names which worktree, which ref, behind/ahead state, and the most likely cause — replacing the bare "working tree is behind HEAD". Keep `SafeCommitBackstopError` semantics identical (message-only change + structured fields if cheap). Update any test asserting the old literal.

### T015 — `_make_merge_env()` (AC-F1)

In `lanes/merge.py`: extract the inline subprocess environment construction into one helper; route EVERY subprocess invocation in the lane-merge pipeline through it. Pure refactor — byte-identical env for existing paths.

### T016 — Narrow the except (AC-F3; AFTER T011–T013 per C-004)

`coordination/status_transition.py:399-400`: `except Exception` → `except (ValueError, FileNotFoundError)` with a comment documenting the GENESIS-fallback contract (the two types = absent log / pre-schema log). Tests: each expected type → fallback; an injected `PermissionError` → propagates.

### T017 — Ratchets

New `tests/architectural/test_merge_pipeline_ratchets.py`:
- AC-B3: AST/grep-based assert that no `update-ref` subprocess invocation exists in `src/specify_cli` outside `git/ref_advance.py` (follow the existing architectural-test patterns in `tests/architectural/` — AST walk preferred over regex where the suite already does so).
- AC-F1: every subprocess call site in `lanes/merge.py` routes env through `_make_merge_env` (assert by AST: no bare `os.environ` copies in that module's subprocess calls).
Extend `tests/status/test_event_log_merge.py`:
- AC-F2: `test_merge_event_payloads_mixed_at_timestamp_neither` — log with `at`-only, `timestamp`-only, and neither; sort is deterministic and total across repeated runs; document the tie-break in the test docstring.

## Branch Strategy

Planning base and merge target are both `main`. Execution worktree/branch come from `lanes.json` via `spec-kitty agent action implement WP03 --agent <name>` — consume the resolved path. Landing on origin/main via PR only (C-005).

## Definition of Done

- [ ] T010 red → green; AC-B1/B2 assertions pass
- [ ] Helper exists; exactly 3 sites migrated; AC-B3 ratchet green (T011/T012/T017)
- [ ] Dirty refusal: loud, named, resumable, data-preserving (T013, NFR-002)
- [ ] Backstop names the divergence (T014); no semantic change
- [ ] AC-F1/F2/F3 green; T016 landed after T011–T013 (C-004)
- [ ] Existing ratchets green (NFR-005); ruff + mypy --strict zero suppressions; ≥90% changed-line coverage; terminology guard before push

## Risks & Reviewer Guidance

- **`reset --hard` is the sharpest tool in this mission.** Reviewer: T013's clean-check must execute strictly before ANY reset path; demand the planted-file survival test.
- Lock ordering: the helper must not acquire a lock the call sites already hold in a different order — reviewer, trace the lock stack at all three sites.
- T015 is refactor-only: reviewer, diff the constructed env byte-for-byte in a test.
- Newly-propagating exceptions from T016 may surface in unrelated suites — run the full `tests/` once locally before review handoff.

## Activity Log

- 2026-06-12T11:57:59Z – claude:fable-5:python-pedro:implementer – shell_pid=83268 – Assigned agent via action command
- 2026-06-12T12:40:12Z – claude:fable-5:python-pedro:implementer – shell_pid=83268 – WP03 complete. advance_branch_ref helper + 3-site migration + dirty refusal + FR-012 backstop diagnostics + _make_merge_env + except-narrowing + ratchets. Verification: pytest 1826-suite+tests/status+tests/architectural (1 pre-existing unrelated failure test_status_module_boundary on branch base, deselected; rest exit 0), cli/commands -k merge 50 passed exit 0, lanes/git/unit 763 passed exit 0, coordination+status 410 passed exit 0, terminology guard exit 0; ruff diff-scoped exit 0; mypy clean (mypy --strict on new module + ratchets exit 0); ref_advance coverage 93%.
- 2026-06-12T12:40:52Z – claude:fable-5:reviewer-renata:reviewer – shell_pid=85711 – Started review via action command
- 2026-06-12T12:46:07Z – user – shell_pid=85711 – Review passed: data-safety verified line-by-line in ref_advance.py (dirty-check on ALL checkouts strictly before update-ref AND before any reset --hard = atomic refusal, stronger than contract — accepted); untracked/ignored exclusion verified empirically (reset --hard leaves untracked files) and covered by test_advance_branch_ref_untracked_files_do_not_block_or_vanish + dirty-refusal/resume/survival tests. AC-B1/B2 7/7 green (real coord worktree + real baking); AC-B3 ratchet exact-string AST scan non-vacuous; C-002 grep clean (update-ref only in ref_advance.py); lock discipline correct (no lock in helper, all 3 sites under __global_merge__; orchestrator_api path pre-existing, flagged in docstring); FR-012 backstop names worktree/ref/HEAD/behind-ahead, same exception+error_code; T016 3-type except accepted (CanonicalStatusNotFoundError IS the concrete absent-log signal; PermissionError propagation tested); AC-F1/F2/F3 green incl. byte-identity env test; ratchets+terminology+gitop-guard 35/35; lifecycle 20/20; ruff 0; boundary-test failure confirmed pre-existing (migration/mission_state.py:43 untouched by diff); scope exactly the 8 owned files, zero WP02/04/05 overlap. Non-blocking observation: mypy --strict on test_merge_pipeline_ratchets.py reports 1 no-any-return at line 172 (_absent_log_error; Any via project follow_imports=skip override, outside CI mypy scope) — trivial follow-up: assign to a typed local before returning.
