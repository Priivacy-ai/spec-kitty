---
work_package_id: WP07
title: Centralize commit routing + final shim sweep
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-006
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
merge_target_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-decompose-agent-tasks-god-module-01KVWVAR. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-decompose-agent-tasks-god-module-01KVWVAR unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
- T033
phase: Phase 3 - Shim finalization
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2627222"
history:
- at: '2026-06-24T13:22:13Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/test_wp03_bypass_writers_fr008.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Centralize commit routing + final shim sweep

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` on `authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py`.

---

## Objective

Final WP. **Sole owner of `tasks.py`.** Centralize the three planning-commit tails through
`commit_for_mission` while **preserving the protected-primary error messages and exit codes byte-for-byte**
(FR-006/007/008), add the `#2058` decomposition pointer comment (FR-002), and run the final
maxCC ≤15 / size / full-gate sweep (FR-001, FR-005).

**Read `research.md §3` carefully** — the original "silently skips → coord worktree" framing is
outdated. The protected-primary path already *refuses* (→ feature branch). Your job is to route the
decision through the canonical router AND keep the user-facing output identical.

## Context — the 3 tails and the router (verify current line numbers!)

The seam WPs shifted code around, so re-locate these by searching, not by the line numbers below:

- **Tail 1** — `move_task` WP-file commit, was `tasks.py:2486` (`safe_commit(...)`, `WORK_PACKAGE_TASK`).
- **Tail 2** — `mark_status` tasks.md commit, was `tasks.py:3131` (`safe_commit(...)`, `TASKS_INDEX`).
- **Tail 3** — `map_requirements` WP-file commit, was `tasks.py:3947` (`safe_commit(...)` after
  `_planning_commit_worktree(...)` imported from `mission.py`).
- **Router**: `commit_for_mission(repo_root, mission_slug, files, message, policy, *, kind,
  primary_paths_created_this_invocation=None, target_branch=None) -> CommitRouterResult`
  in `src/specify_cli/coordination/commit_router.py`. On a protected primary it returns
  `status="no_op_wrong_surface"` with a feature-branch diagnostic.

## Subtasks

### T027 — Route Tail 1 (`move_task`) through `commit_for_mission`
Replace the `resolve_placement_only` + `safe_commit` open-coding with a `commit_for_mission(...)` call
(kind `WORK_PACKAGE_TASK`). **Capture the CURRENT protected-primary message/exit code first** (the
golden test + the existing `_skip_target_branch_commit` note), then map the router's
`no_op_wrong_surface` result back to that exact message + exit code so output is unchanged.

### T028 — Route Tail 2 (`mark_status`) through `commit_for_mission`
Same pattern, kind `TASKS_INDEX`. Preserve the exact `_protected_branch_status_commit_error` message
text and exit code by mapping the router result back to it.

### T029 — Route Tail 3 (`map_requirements`) through `commit_for_mission`
Replace the `_planning_commit_worktree` + `safe_commit` pair with `commit_for_mission(...)`, kind
`WORK_PACKAGE_TASK`, **threading `target_branch=` for the WP09 ff-advance** (currently absent at this
call site — research §3 gap). Preserve message/exit code + the `--json` `commit_result` serialization.

### T030 — Delete the now-dead pre-checks — **DEFERRED (premise incorrect)**
Original intent: remove `_skip_target_branch_commit()`, `_protected_branch_status_commit_error()`,
their guard conditionals in `move_task`/`mark_status`. **Deferred**: these pre-checks are NOT dead.
`commit_for_mission` only governs the commit step (refuses protected primary → exit 1), whereas
`_skip_target_branch_commit` drives a load-bearing command-flow arm — in the coord-topology +
protected-primary case it suppresses the WP-file write, reshapes the `--json` envelope, drives the
`WP_METADATA_UNSUPPORTED_ON_PROTECTED_COORD_BRANCH` rejection, and **succeeds with exit 0** (coord
branch is authoritative). Deleting it would flip exit 0 → exit 1, breaking #1615-1618 + C-003
byte-identity. The `_planning_commit_worktree` import WAS removed from `tasks.py` (FR-006 ✓). True
consolidation (teaching the router the exit-0 coord arm) = follow-up #2116 under #1797. See spec FR-007.

### T031 — Extend the FR-008 regression test
Extend `tests/specify_cli/cli/commands/test_wp03_bypass_writers_fr008.py` to assert, for each of the 3
tails: (a) the commit reaches git **only** via `commit_for_mission` (patch/spy the router), and (b) on
a protected primary the **message text and exit code are byte-identical** to pre-refactor. This is the
proof for FR-008 + the message-preservation requirement.

### T032 — Pointer comment + maxCC ≤15 sweep
Add the top-of-file decomposition-pointer comment referencing `#2058` (match the #2056 `mission.py` /
#1623 `doctor.py` convention). Run `ruff check` (C901) on `tasks.py`; thin any residual function still
> maxCC 15 (e.g. remaining `status` / `move_task` orchestration) by extracting small local helpers or
pushing logic into the appropriate seam. Goal: **every function ≤15 CC**.

### T033 — Full gate sweep
Run and pass: golden contract test (WP01), the full `tests/specify_cli/cli/commands/agent/` suite, the
extended FR-008 test, `ruff check`, `mypy --strict`, and `pytest tests/architectural/test_no_legacy_terminology.py`
(CI-only gate — run locally). Confirm `wc -l tasks.py` ≤ ~1200 and coverage ≥90% on changed code.

## Branch Strategy

- Lanes merge into the mission branch **kitty/mission-decompose-agent-tasks-god-module-01KVWVAR** (PRs to `main` at mission end; `main` is protected). Depends on **WP02–WP06** — branch from a base including all five seams. Worktree per lane.

## Definition of Done

- [x] All 3 tails route through `commit_for_mission`; no residual `safe_commit` / `_planning_commit_worktree` CALL in `tasks.py` (comment refs only).
- [~] Dead pre-checks deleted — **DEFERRED**: pre-checks are not dead (govern the coord-topology exit-0 silent-skip the router cannot reproduce; deleting breaks #1615-1618). `mission.py` untouched (C-006). Follow-up #2116. See T030 / spec FR-007.
- [x] Protected-primary message text + exit codes proven byte-identical for all 3 tails (extended FR-008 test).
- [x] `#2058` pointer comment present at top of `tasks.py`.
- [~] Every function in `tasks.py` maxCC ≤15 — **MET** (ruff C901 clean). File ≤ ~1200 LOC — **NOT met**: 3365 LOC (mega-function bodies not internally decomposed; body-thinning deferred, follow-up #2116). See spec NFR-004/SC-002.
- [x] Golden contract test green; full suite green; ruff + mypy --strict clean; terminology guard green; no new suppressions.

## Risks

- **Message preservation is the trap** — `commit_for_mission`'s native diagnostic differs from the
  pre-check messages. You MUST map it back. Capture the exact current strings before editing; assert
  byte-identical in T031.
- **Tail 3 `target_branch` threading** — easy to omit; without it the ff-advance regresses.
- **maxCC residue** — if `status`/`move_task` are still >15 after seam extraction, push more logic into
  seams rather than adding `# noqa` (C-004 forbids new suppressions).
- **CI-only terminology gate** — runs only in `integration-tests-core-misc`; run it locally before merge.

## Reviewer guidance

This WP carries the only behavior-adjacent change in the mission. Verify: (1) every tail goes through
the router, (2) messages/exit codes are byte-identical (diff the test assertions against current
output), (3) no dead code remains and `mission.py` is untouched, (4) maxCC ≤15 everywhere with zero new
suppressions, (5) the golden contract test from WP01 is still green. Reject if any protected-primary
message changed.

## Activity Log

- 2026-06-24T16:23:31Z – user – shell_pid=2530913 – Moved to planned
- 2026-06-24T16:23:34Z – claude:opus:randy-reducer:implementer – shell_pid=2551738 – Started implementation via action command
- 2026-06-24T16:56:08Z – claude:opus:randy-reducer:implementer – shell_pid=2551738 – FR-006/008 done; FR-007 deletion deferred (pre-checks handle coord-topology silent-skip, not dead); 536 tests green. --force: lane-g net kitty-specs tree == mission (benign integration-merge history), merge-safe
- 2026-06-24T16:56:10Z – claude:opus:reviewer-renata:reviewer – shell_pid=2627222 – Started review via action command
- 2026-06-24T17:03:38Z – user – shell_pid=2627222 – Review cycle-2 PASS (reviewer-renata). --force: lane-g net kitty-specs divergence is status bookkeeping only (status.events.jsonl/status.json/WP07 frontmatter, 28 net lines, no foreign content, no code defects) -- benign integration-merge history. --skip-review-artifact-check overrides review-cycle-1.md, which is an orchestration reset note (blocked->planned post multi-lane integration, reviewer_agent=unknown), NOT a quality rejection; the WP07 commit-routing work was implemented afterward and is what this review covers. FR-006: all 3 tails route through commit_for_mission; zero direct safe_commit/_planning_commit_worktree CALLS in tasks.py (comment ref only); tail 3 threads target_branch=. FR-008: AST router-only guard + byte-identical protected-primary message/exit tests for all 3 tails (21 passed). FR-002 #2058 pointer present. FR-007-deletion DEFERRED+ACCEPTED: pre-checks NOT dead -- move_task has a live coord-topology arm that silently SKIPS the primary commit (dim note, exit 0, transition committed to coord branch) which the router CANNOT reproduce (router refuses WORK_PACKAGE_TASK primary -> no_op_wrong_surface/exit 1; planning->coord transit removed WP02/03). Deletion would flip coord case to exit 1, violating C-003 byte-identity + breaking 36 pinning tests (test_move_task_guard.py + test_issue_1615_1616_1617_1618.py, green). FR-007 premise incorrect (same class as 3-tails-not-4). C-006 mission.py untouched. Gates: ruff C901 maxCC<=15 clean; mypy --strict clean; agent/ 515 passed/2 xfailed; terminology green; cross-WP migrations correct (58 passed). NOTE tasks.py 3346 LOC vs NFR-004 ~1200 optimistic estimate -- non-blocking, binding maxCC<=15 met.
- 2026-06-24T17:05:04Z – user – shell_pid=2627222 – Approved by reviewer-renata: FR-006/008/002 verified, FR-007 deferral validated via pinning tests (36 passed), gates green. --force: lane-g net kitty-specs==mission (benign integration history)
- 2026-06-24T17:14:51Z – user – shell_pid=2627222 – Superseded rejection artifact (cycle re-approved); mission merged into mission branch with all lanes integrated, 515 tests green
