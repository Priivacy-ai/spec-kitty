---
work_package_id: WP06
title: '#2647 — move-task cwd-independent status surface'
dependencies: []
requirement_refs:
- C-002
- FR-001
- NFR-001
tracker_refs:
- '2647'
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
shell_pid_created_at: "1784125350.25"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2807328"
history:
- at: '2026-07-15T07:36:38Z'
  actor: claude
  note: Head of Lane C; red-first through the real move-task entry point; localization caveat (:308 already anchored).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/test_tasks_move_task_cwd.py
- tests/specify_cli/coordination/test_transaction_legacy_topology_routing.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/coordination/transaction.py
- tests/specify_cli/cli/commands/test_tasks_move_task_cwd.py
- tests/specify_cli/coordination/test_transaction_legacy_topology_routing.py
- tests/architectural/test_no_write_side_rederivation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**.

## Objective

Close #2647. `agent tasks move-task WP## --to <lane>` fails with "Illegal transition" when
run from a **lane-worktree cwd** but succeeds from the repo root, even though
`status.json`/`status.events.jsonl` on the mission branch correctly show the from-lane. Fix:
resolve the status surface from the **canonical mission root** independent of cwd. Red-first
through the real entry point (DIRECTIVE_041 / C-002).

## Context — READ BEFORE CODING (localization caveat, squad RISK-4)

- **Do NOT assume the named seam is the taint.** `_read_transactional_wp_lane`
  (`tasks_move_task.py:308-312`) ALREADY reads with `repo_root=st.main_repo_root` (the
  mission root) — it is NOT the bug. The cwd taint enters UPSTREAM at:
  - `locate_project_root()` (`:244`), and
  - `locate_work_package(repo_root, …)` (`:306`).
  **First locate which read returns the stale lane; if no fixture can make the currently
  suspected seam go RED, the seam is misidentified — escalate before extracting.**
- `is_worktree_context(cwd)` (`:223-224`) is the cwd signal the repro must genuinely trip.
- **Boundary:** fix the status-surface resolution only; do not change move-task transition
  semantics beyond making them cwd-independent.

## Subtasks

### T027 — Confirm the bug still reproduces, then locate the stale read

**Confirm-first (squad RISK-1 — the bug may already be fixed).** Both named reads that the
status flows through (`_read_transactional_wp_lane` at `:308`, and `_mt_resolve_targets`'
`mt_feature_dir` via `MissionHandle`) are ALREADY anchored to `st.main_repo_root`. So before
authoring a fix, verify #2647 still reproduces at the entry point from a lane-worktree cwd on
the current HEAD (a prior #2160 mission may have already anchored the taint).
- If it **does NOT reproduce**: STOP. Convert this WP to a **regression-guard-only** WP —
  assert cwd-independence stays green (T028/T030 become a passing guard, no fix) and report the
  already-fixed finding to the mission (append to `../traces/design-decisions.md`). Do NOT
  manufacture a fix for a non-bug.
- If it **does reproduce**: trace `_mt_resolve_targets` → `feature_dir` derivation and the
  `locate_project_root()` (`:244`) / `locate_work_package(repo_root, …)` (`:306`) reads;
  determine which one, under a lane-worktree cwd, yields the stale/worktree-local lane.
  Record the tainted read in the test docstring.

**Validation**: either the bug is confirmed RED at the entry point + the tainted read is
identified with evidence, OR the already-fixed finding is recorded and the WP is converted to a
regression guard.

### T028 — RED repro from a lane-worktree cwd

Create `tests/specify_cli/cli/commands/test_tasks_move_task_cwd.py`:
1. Build a REAL `git worktree` fixture for a mission WP that is `in_progress`.
2. `monkeypatch.chdir(worktree)` so `is_worktree_context(cwd)` is genuinely true.
3. Drive `move-task WP## --to for_review` and assert (RED) the concrete "Illegal
   transition" error string against current code.

**Validation**: the test FAILS with "Illegal transition" against current code.

### T029 — Fix: resolve the status surface from the canonical mission root

1. Correct the tainted read located in T027 so `feature_dir` / the status-read path derive
   from the canonical mission root regardless of cwd.

**Validation**: `ruff` + `mypy --strict` clean.

### T030 — GREEN + repo-root no-regression

1. Flip T028 to GREEN (the worktree-cwd move-task succeeds, matching the repo-root result).
2. Add an explicit assertion that the **repo-root cwd** invocation still succeeds (FR-001
   no-regression).

**Validation**: both cwd contexts produce the identical successful transition.

### T031 — Gate clean

1. `ruff` + `mypy --strict` zero new issues; existing move-task suites green.

**Validation**: clean gate.

## Branch Strategy

Planning branch / final merge target: **mission/2533-pr-bound-coord-claim-precondition**.
Head of **Lane C** (no dependencies); runs in parallel with Lane A.

## Definition of Done

- `move-task` succeeds from a lane-worktree cwd AND from repo root, resolving the status
  surface from the mission root (FR-001, SC-001).
- Red-first repro through the real entry point (C-002); repo-root no-regression asserted.
- `ruff` + `mypy --strict` clean (NFR-001).

## Risks & Reviewer Guidance

- Reviewer must confirm the repro genuinely trips `is_worktree_context(cwd)` (a real
  worktree + chdir), not a mocked cwd — otherwise the RED is hollow.
- Confirm the fix targets the actual tainted read (T027), not the already-anchored `:308`.

## Activity Log

- 2026-07-15T11:21:45Z – claude:sonnet:python-pedro:implementer – shell_pid=2407987 – Assigned agent via action command
- 2026-07-15T11:57:18Z – claude:sonnet:python-pedro:implementer – shell_pid=2407987 – BLOCKED (scope escalation): #2647 DOES reproduce (retracted earlier false-negative — see traces/design-decisions.md). Root cause is coordination/transaction.py::_resolve_legacy_lane_destination (Path.cwd()-based write-time from_lane re-derivation for coordination-less single_branch/lanes missions), already tracked as deferred debt under #2453 in tests/architectural/test_no_write_side_rederivation.py's allow-list. Out of WP06 owned_files (tasks_move_task.py) and too high-risk to fix unscoped in a shared coordination primitive. Committed xfail(strict=True) repro test (test_write_side_from_lane_rederivation_reproduces_2647) that flips green when #2453 is fixed. T029 reverted to pending (no fix made). Recommend: either expand WP06/mission scope to include the #2453 fix (route modern coordination-less missions to repo_root+target_branch instead of Path.cwd(), reusing _warrants_legacy_warning's topology classification), or file/confirm a dedicated #2453 follow-up mission and close WP06 as characterization-only.

---
- 2026-07-15T12:58:26Z – claude:sonnet:python-pedro:implementer – shell_pid=2579814 – Assigned agent via action command
- 2026-07-15T13:45:20Z – claude:sonnet:python-pedro:implementer – shell_pid=2579814 – Ready for review: #2453 write-side fix — modern coordination-less routed to repo_root+target_branch; xfail flipped green; ratchet updated
- 2026-07-15T13:47:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=2715299 – Started review via action command
- 2026-07-15T14:13:09Z – user – Moved to planned
- 2026-07-15T14:15:50Z – claude:sonnet:python-pedro:implementer – shell_pid=2797190 – Started implementation via action command
- 2026-07-15T14:21:55Z – claude:sonnet:python-pedro:implementer – shell_pid=2797190 – Cycle-2: lane-c cleaned to code-only. The #2453 scope-expansion authorization + C-004 re-pin justification + EXPANDED SCOPE live on the mission branch (mission/2533-...) at commit 946360a99 — the canonical location for planning artifacts (lanes are code-only). Verify via: git show mission/2533-pr-bound-coord-claim-precondition:kitty-specs/implement-loop-commit-hardening-01KXJ1ZX/traces/design-decisions.md
- 2026-07-15T14:22:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=2807328 – Started review via action command
- 2026-07-15T14:26:26Z – user – shell_pid=2807328 – Cycle-2 approved: #2453 fix code-quality confirmed cycle-1; C-004 authorization discoverable on the mission branch (946360a99); lane-c correctly code-only.

## ⚠️ EXPANDED SCOPE (operator decision 2026-07-15): fix #2453 — the WRITE-SIDE root cause

**Cycle-1 finding (confirmed, in `../traces/design-decisions.md`):** #2647 is real but the taint is
NOT the read/decision side (those are cwd-invariant, already pinned green by T027/T028). The real
cause is the **write side**: `emit_status_transition_transactional` → `BookkeepingTransaction._acquire_locked`
→ `_is_legacy_mission` (`src/specify_cli/coordination/transaction.py:200`) →
`_resolve_legacy_lane_destination` (`:279`), whose first line is `cwd = Path.cwd().resolve()` — it
re-derives `from_lane` from *that lane worktree's* stale local `status.events.jsonl` at commit time.
`_is_legacy_mission` misclassifies **every modern coordination-less `single_branch`/`lanes` mission**
(topology stored, no `coordination_branch`) as "legacy", so they all hit the cwd read. Tracked as
**#2453**; a sibling mission (`topology-aware-legacy-warning-01KWQ8WH`) fixed only the warning text
(C-005), leaving routing unchanged.

**The operator chose to fix #2453 now.** This is a SHARED status-transition primitive — apply
brownfield discipline (characterization-FIRST) and run the full coordination/status suites.

### Expanded subtasks (map onto the existing T029/T030/T031; T027/T028 characterization are DONE)

- **T029a — Characterization gate FIRST (new test `tests/specify_cli/coordination/test_transaction_legacy_topology_routing.py`):** pin the CURRENT `_is_legacy_mission` + `_resolve_legacy_lane_destination` behavior for the THREE cases before changing anything: (a) genuinely-legacy (no stored topology in meta.json) → must keep current behavior; (b) modern coordination-less (`topology: single_branch`/`lanes` stored, no `coordination_branch`) → currently misrouted via cwd; (c) coordination topology → unaffected. Reuse the production-shaped fixture from `test_tasks_move_task_cwd.py` (real `meta.json` + `mission_id` + topology, lane worktree forked before the WP advanced on primary).
- **T029 — Fix (`transaction.py`):** distinguish genuinely-legacy from modern coordination-less using the SAME stored-topology classification the warning-fix added (reuse/adjacent to `_warrants_legacy_warning`). Route modern coordination-less missions' status commits to **`repo_root` + `target_branch`** (the canonical mission surface), NOT `cwd`. Do NOT change genuinely-legacy behavior. Preserve `_is_legacy_mission`'s other callers.
- **T030 — Flip the repro GREEN:** the `xfail(strict=True)` `test_write_side_from_lane_rederivation_reproduces_2647` in `test_tasks_move_task_cwd.py` must now PASS (remove the xfail marker). Add the repo-root no-regression assertion. FR-001 is now genuinely satisfied: `move-task` succeeds from a lane-worktree cwd.
- **T031 — Gate clean (EXPANDED):** update the architectural ratchet allow-list
  `tests/architectural/test_no_write_side_rederivation.py` — the #2453 entry for this write-side
  re-derivation is being fixed, so remove/adjust it (the ratchet must go green WITHOUT the
  allow-list exception for the fixed path). Run the FULL `tests/specify_cli/coordination/` +
  status-transition + `tests/architectural/` suites (this is a shared primitive). `ruff` + `mypy
  --strict` zero new issues.

### Guards
- **Characterization-first** on the shared primitive (do not guess the legacy-vs-modern split).
- Genuinely-legacy missions (truly no stored topology) MUST retain current routing — do not break them.
- This is the mission's own dogfooding bug (it bit our loop). Confirm the fix by re-running a real
  `move-task` from THIS lane-c worktree and observing it succeed.
- Run all `move-task` from the **repo root** for status handoff to avoid tripping the bug before it's fixed.
