# Tasks: Implement-Loop Commit & Move-Task Hardening

**Mission**: `implement-loop-commit-hardening-01KXJ1ZX`
**Branch**: `mission/2533-pr-bound-coord-claim-precondition` (stacks on the merged #2533)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

7 work packages across **3 file-linearized lanes** (post-pre-tasks-squad shape, lane-cycle-free).
Lane A owns `implement.py` + `implement_cores.py`; Lane B owns `coordination/commit_router.py`;
Lane C owns `agent/tasks_move_task.py`. Each lane's WPs are a strict dependency chain
(sequential — they legitimately share their lane's files). The FR-006 characterization gate is
folded into Lane A's WP04 (with the cli-side ref unification) so it is NOT a separate mid-chain
lane — that keeps the lane graph acyclic.

## Lane / dependency map

```
Lane A (implement.py):        WP01 → WP02 → WP03 → WP04
Lane B (commit_router.py):    WP05                       (depends_on WP04)
Lane C (tasks_move_task.py):  WP06 → WP07                (WP07 depends_on WP06 AND WP02)

Lane graph:  Lane B → Lane A ,  Lane C → Lane A   (acyclic; Lane A independent)
```

MVP / first value & parallelism: **WP01** (#2648) and **WP06** (#2647, the P1 bug) have no
dependencies and start immediately — Lane C (move-task) runs in parallel with Lane A. Lane B
(the commit_router swap) and WP07 (the move-task degod) join once their Lane A dependencies
(WP04 / WP02) are approved.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | RED repro: narrow-triple currently diverts silently | WP01 | |
| T002 | Baseline: pin the 755/790 + #2533 arms that must stay green | WP01 | |
| T003 | Replace the 767 arm with an explicit fail-close (Option B) | WP01 | |
| T004 | Flip RED→GREEN; re-assert preserved arms | WP01 | |
| T005 | Correct the misleading docstring | WP01 | |
| T006 | Characterization: _resolve_bookkeeping_transaction_identifiers invariants | WP02 | |
| T007 | Consumer-side import-contract test (freeze C-006 5-tuple) | WP02 | |
| T008 | Extract module-private helpers (signature + 5-tuple preserved) | WP02 | |
| T009 | Gate clean (ruff/mypy) | WP02 | |
| T010 | Characterization: _json_safe_output invariants | WP03 | |
| T011 | Characterization: _run_recover_mode | WP03 | |
| T012 | Extract helpers for _json_safe_output | WP03 | |
| T013 | Extract helpers for _run_recover_mode | WP03 | |
| T014 | Gate clean (ruff/mypy) | WP03 | |
| T015 | Gate: enumerate + pin the three sites' current partition decisions | WP04 | |
| T016 | Gate: pin the disagreement set → PRIMARY | WP04 | |
| T017 | Gate: characterize flat/legacy None-at-seam (confirm WP01 triple) | WP04 | |
| T018 | Gate: pin the intended unified contract | WP04 | |
| T019 | Ref-unif: extract the shared primary-ref expression | WP04 | |
| T020 | Ref-unif: structural + detached-HEAD regression test | WP04 | |
| T021 | Ref-unif: turn cli-side contract green + regressions | WP04 | |
| T022 | Gate clean (ruff/mypy) | WP04 | |
| T023 | Swap commit_router:404 classifier onto the residue predicate | WP05 | |
| T024 | Structural test: kind classifier dropped for the split | WP05 | |
| T025 | Regressions stay green (#2533, #2648, WP04 gate) | WP05 | |
| T026 | Gate clean (ruff/mypy) | WP05 | |
| T027 | Locate the stale move-task read (:244/:306, not :308) | WP06 | [P] |
| T028 | RED repro from a lane-worktree cwd | WP06 | [P] |
| T029 | Fix: resolve status surface from the canonical mission root | WP06 | [P] |
| T030 | GREEN + repo-root no-regression | WP06 | [P] |
| T031 | Gate clean (ruff/mypy) | WP06 | [P] |
| T032 | Characterization: #2576 dual-handler + move-task behavior | WP07 | |
| T033 | Parameter-object for _do_move_task (≤13) | WP07 | |
| T034 | Degod _mt_commit_wp_file (folds #2604) | WP07 | |
| T035 | Tidy _mt_uncheck_rollback_subtasks (preserve C-001) | WP07 | |
| T036 | Gate clean (ruff/mypy) + param ceiling | WP07 | |

> The `[P]` column marks Lane C as parallelizable against Lane A — it is not a status marker.
> Progress is tracked by the per-WP checkbox rows below.

---

## Lane A — `implement.py` / `implement_cores.py`

### WP01 — #2648 delete the 767 divert, narrow-triple fail-close

**Goal**: remove the silent protected-branch coord-divert; fail-close ONLY on the narrow
triple (`placement_ref is None` + meta `coord_branch` + protected `planning_branch`),
matching the status half; preserve the 755/790 strangler arms.
**Priority**: P2 bug · **Dependencies**: none · **Prompt**: [WP01-narrow-triple-failclose.md](./tasks/WP01-narrow-triple-failclose.md)
**Independent test**: narrow-triple claim raises `PlacementResolutionRequired`; the 3 write-side `None` cases + #2533 regression stay green.

- [x] T001 RED repro: narrow-triple currently diverts silently (WP01)
- [x] T002 Baseline: pin the 755/790 + #2533 arms that must stay green (WP01)
- [x] T003 Replace the 767 arm with an explicit fail-close (Option B) (WP01)
- [x] T004 Flip RED→GREEN; re-assert preserved arms (WP01)
- [x] T005 Correct the misleading docstring (WP01)

### WP02 — #2649 degod _resolve_bookkeeping_transaction_identifiers (C-006 symbol)

**Goal**: reduce S3776 on the C-006 5-tuple function, signature + return frozen.
**Priority**: P2 tech-debt · **Dependencies**: WP01 · **Prompt**: [WP02-bookkeeping-identifiers-degod.md](./tasks/WP02-bookkeeping-identifiers-degod.md)
**Independent test**: characterization invariants + the consumer 5-tuple contract test green.

- [x] T006 Characterization: _resolve_bookkeeping_transaction_identifiers invariants (WP02)
- [x] T007 Consumer-side import-contract test (freeze C-006 5-tuple) (WP02)
- [x] T008 Extract module-private helpers (signature + 5-tuple preserved) (WP02)
- [x] T009 Gate clean (ruff/mypy) (WP02)

### WP03 — #2649 degod _json_safe_output + _run_recover_mode

**Goal**: reduce S3776 on the two heavy functions, behavior-preserving.
**Priority**: P2 tech-debt · **Dependencies**: WP02 · **Prompt**: [WP03-json-safe-recover-degod.md](./tasks/WP03-json-safe-recover-degod.md)
**Independent test**: characterization invariants (dual-exception arms, quiet/file resets) green.

- [x] T010 Characterization: _json_safe_output invariants (WP03)
- [x] T011 Characterization: _run_recover_mode (WP03)
- [x] T012 Extract helpers for _json_safe_output (WP03)
- [x] T013 Extract helpers for _run_recover_mode (WP03)
- [x] T014 Gate clean (ruff/mypy) (WP03)

### WP04 — #2650 characterization gate + read/write primary-ref unification (FR-006 + FR-005 ref half)

**Goal**: document-first — pin the three sites + the disagreement set + the flat/legacy
None-at-seam behavior; THEN unify the read (`"HEAD"`) / write (`planning_branch`) primary ref
into one cli-local expression. Gate folded here (not a separate lane) to keep the lane graph
acyclic. Does not touch `commit_router`.
**Priority**: P2 tech-debt · **Dependencies**: WP03 · **Prompt**: [WP04-gate-and-ref-unification.md](./tasks/WP04-gate-and-ref-unification.md)
**Independent test**: the characterization suite pins each site + the intended `kind=None`→PRIMARY
contract; read/write agree by construction; detached-HEAD regression green.

- [x] T015 Gate: enumerate + pin the three sites' current partition decisions (WP04)
- [x] T016 Gate: pin the disagreement set → PRIMARY (WP04)
- [x] T017 Gate: characterize flat/legacy None-at-seam (confirm WP01 triple) (WP04)
- [x] T018 Gate: pin the intended unified contract (WP04)
- [x] T019 Ref-unif: extract the shared primary-ref expression (WP04)
- [x] T020 Ref-unif: structural + detached-HEAD regression test (WP04)
- [x] T021 Ref-unif: turn cli-side contract green + regressions (WP04)
- [x] T022 Gate clean (ruff/mypy) (WP04)

---

## Lane B — `coordination/commit_router.py`

### WP05 — #2650 classifier-only swap of commit_router onto the residue predicate (FR-005 partition half)

**Goal**: swap `commit_router:404` onto the existing `is_coordination_artifact_residue_path`;
`kind=None`→PRIMARY; keep `resolve_placement_only` for the COORD ref; no new cli-side wrapper.
**Priority**: P2 tech-debt · **Dependencies**: WP04 · **Prompt**: [WP05-commit-router-classifier-swap.md](./tasks/WP05-commit-router-classifier-swap.md)
**Independent test**: structural test that the kind classifier is dropped for the split;
#2533 + #2648 + WP04 gate green.

- [x] T023 Swap commit_router:404 classifier onto the residue predicate (WP05)
- [x] T024 Structural test: kind classifier dropped for the split (WP05)
- [x] T025 Regressions stay green (#2533, #2648, WP04 gate) (WP05)
- [x] T026 Gate clean (ruff/mypy) (WP05)

---

## Lane C — `agent/tasks_move_task.py`

### WP06 — #2647 move-task cwd-independent status surface

**Goal**: `move-task` resolves the status surface from the canonical mission root regardless
of cwd; red-first through the real entry point; repo-root no-regression.
**Priority**: P1 bug · **Dependencies**: none · **Prompt**: [WP06-movetask-cwd-fix.md](./tasks/WP06-movetask-cwd-fix.md)
**Independent test**: move-task from a lane-worktree cwd succeeds and equals the repo-root result.

- [x] T027 Locate the stale move-task read (:244/:306, not :308) (WP06)
- [x] T028 RED repro from a lane-worktree cwd (WP06)
- [x] T029 Fix: resolve status surface from the canonical mission root (WP06)
- [x] T030 GREEN + repo-root no-regression (WP06)
- [x] T031 Gate clean (ruff/mypy) (WP06)

### WP07 — #2649 tasks_move_task.py degod + param-object (folds #2604)

**Goal**: degod `_mt_commit_wp_file` (folds #2604), `_do_move_task` param-object (≤13),
tidy `_mt_uncheck_rollback_subtasks` preserving the #2576 dual-handler. Consumes the frozen
WP02 5-tuple (C-006).
**Priority**: P2 tech-debt · **Dependencies**: WP06, WP02 · **Prompt**: [WP07-movetask-degod.md](./tasks/WP07-movetask-degod.md)
**Independent test**: `_do_move_task` params ≤13; #2576 dual-handler characterization green.

- [x] T032 Characterization: #2576 dual-handler + move-task behavior (WP07)
- [x] T033 Parameter-object for _do_move_task (≤13) (WP07)
- [x] T034 Degod _mt_commit_wp_file (folds #2604) (WP07)
- [x] T035 Tidy _mt_uncheck_rollback_subtasks (preserve C-001) (WP07)
- [x] T036 Gate clean (ruff/mypy) + param ceiling (WP07)

---

## Requirement coverage

| Requirement | WP(s) |
|-------------|-------|
| FR-001 | WP06 |
| FR-002 | WP01 |
| FR-003 | WP02, WP03 |
| FR-004 | WP07 |
| FR-005 | WP04, WP05 |
| FR-006 | WP04 |
| NFR-001 | WP01, WP02, WP03, WP04, WP05, WP06, WP07 |
| NFR-002 | WP02, WP03, WP04, WP07 |
| NFR-003 | WP04, WP05 |
| NFR-004 | WP02, WP03, WP07 |
| C-001 | WP07 |
| C-002 | WP01, WP06 |
| C-004 | WP01, WP05 |
| C-005 | WP07 |
| C-006 | WP02, WP07 |
| C-007 | WP04, WP05 |
| C-008 | WP02, WP03, WP04, WP05, WP07 |
| C-009 | WP01, WP04 |

> C-003 (file-linearized lanes) is embodied by the lane structure itself (Lane A `implement.py`
> vs Lane B `commit_router.py` vs Lane C `tasks_move_task.py`), not a single WP.
