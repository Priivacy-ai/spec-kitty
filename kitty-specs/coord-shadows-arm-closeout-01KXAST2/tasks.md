# Tasks: Close #2160 Coord-Shadows Read/Gate Arm

**Mission**: coord-shadows-arm-closeout-01KXAST2 | **Branch**: `rework/ray-cluster-aggregation`
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

Aligns the faithful five-PR aggregate (#2503/#2505/#2511/#2514/#2515) already on this branch into
one coherent slice that genuinely closes epic #2160's read/gate arm: one canonical subtask-row
walk, a fully-closed emit-layer fail-open (every code path, not just the orchestrator door), a
lane-recovery path that never re-leaks status files, and a live claim-liveness check. Folds in
#1231 (claim friction) and closes #1862 verified-already-fixed.

6 WPs, 30 subtasks. Keystone WP01 → sequential single-owner chain WP02 → WP03 (critical path);
WP04/WP05/WP06 run fully parallel to the spine and to each other.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Extract `_walk_wp_section` generator (first-WPxx-token + fence + break-on-exit) | WP01 | |
| T002 | Rewire read counters onto `_walk_wp_section` (behavior parity) | WP01 | |
| T003 | Rewrite `uncheck_wp_section_subtask_rows` onto `_walk_wp_section` (behavior change: no re-entry) | WP01 | |
| T004 | Exactly one CHECKED/UNCHECKED pattern survives in the module | WP01 | |
| T005 | NFR-005 bite battery (re-appearing heading, section-end, nested headings, `depends:` mention, fences, T1000+) | WP01 | |
| T006 | Prove guard/dashboard-count/rollback-uncheck agree on the full battery | WP01 | |
| T007 | SPIKE: confirm the 4 production call sites + `WorkspaceRootNotFound` gotcha | WP02 | |
| T008 | Reimplement `_infer_subtasks_complete` row logic on `count_wp_section_subtask_rows` | WP02 | |
| T009 | Remove the fail-open on missing `tasks.md` (absent → block, never complete) | WP02 | |
| T010 | Thread primary surface at `aggregate.py:717` via `resolve_planning_read_dir` | WP02 | |
| T011 | Thread primary surface at `emit.py:532`/`:685` with `WorkspaceRootNotFound` guard | WP02 | |
| T012 | Thread primary surface at `status_transition.py:444` | WP02 | |
| T013 | Regression test: native `agent status --to for_review` blocks via `aggregate.py` production route | WP02 | |
| T014 | Full status-suite check; confirm native `move-task` guard untouched | WP02 | |
| T015 | Remove the #2511 per-door pre-derivation block in `orchestrator_api/commands.py` | WP03 | |
| T016 | Re-point #2511 test coverage at the shared-layer behavior (judge-the-test) | WP03 | |
| T017 | Dead-code gate green (no orphaned symbols from the removal) | WP03 | |
| T018 | Hoist `coordination_branch`/`short_id` computation above the recovery branch | WP04 | [P] |
| T019 | Extract `_register_sparse_checkout_if_coord`; call from BOTH create + recovery paths | WP04 | [P] |
| T020 | Tests: coord-lane recovery registers sparse-checkout; non-coord lane stays no-op | WP04 | [P] |
| T021 | Closeout: lint/type/architectural verification; non-coord path unchanged | WP04 | [P] |
| T023 | Create `core/process_liveness.py` (`is_process_alive`, promoted from `sync/daemon`) | WP05 | [P] |
| T024 | Repoint `sync/daemon.py` to import from the new module | WP05 | [P] |
| T025 | Wire `core/stale_detection.py` to suppress "stale" for a live claiming `shell_pid` | WP05 | [P] |
| T026 | NFR-004 matrix tests + stale_detection live-claim test | WP05 | [P] |
| T027 | `_mt_reset_for_planned_rollback` consolidation seam (no new behavior) | WP06 | [P] |
| T028 | Test: rollback leaves the WP fully re-implementable (SC-006) | WP06 | [P] |
| T029 | FR-009 regression guard: checkbox-insensitive freshness hashing (write + gate-check paths) | WP06 | [P] |
| T030 | Author `issue-matrix.md` (terminal verdicts) | WP06 | [P] |
| T031 | Full verification (tests, ruff, mypy, arch suite, issue-matrix schema) | WP06 | [P] |

---

## WP01 — IC-ROWS: one canonical subtask-row walk

**Summary**: Collapse the two divergent section-walk loops in `core/subtask_rows.py` onto one
private `_walk_wp_section` generator, consumed identically by the read counters and the uncheck
writer, so guard / dashboard / rollback all agree on what counts as a subtask row.
**Deps**: none (keystone — WP02 consumes `count_wp_section_subtask_rows`).
**Independent test**: `uv run pytest tests/specify_cli/core/test_subtask_rows.py
tests/specify_cli/core/test_uncheck_wp_section_subtask_rows.py -q`.
**Prompt**: [tasks/WP01-subtask-row-canon.md](tasks/WP01-subtask-row-canon.md)

- [x] T001 Extract `_walk_wp_section` generator (WP01)
- [x] T002 Rewire read counters onto `_walk_wp_section` (WP01)
- [x] T003 Rewrite uncheck writer onto `_walk_wp_section` — behavior change (WP01)
- [x] T004 Exactly one CHECKED/UNCHECKED pattern remains (WP01)
- [x] T005 NFR-005 bite battery (WP01)
- [x] T006 Guard/dashboard/rollback agreement proof (WP01)

**Sketch**: add `_walk_wp_section(lines, wp_id) -> Iterator[tuple[int, str, bool]]` encoding the
first-`WPxx`-token heading rule, fenced-code skipping, and break-on-section-exit exactly once;
rewire `iter_wp_section_subtask_rows` (and its `count_wp_section_subtask_rows` wrapper) onto it
with behavior parity; rewrite `uncheck_wp_section_subtask_rows` onto it too — this corrects the
writer's current re-enter-on-reappearing-heading bug to match the guard's canonical break
semantic. Bite battery proves the divergence fixtures (re-appearing heading foremost) and that all
three consumer shapes (counter/iterator/writer) now agree.

**Estimated prompt size**: ~430 lines.

## WP02 — IC-EMIT-CORE: close the emit-layer fail-open at its callers

**Summary**: Reimplement `_infer_subtasks_complete` on WP01's canonical counter, remove the
tasks.md-absent fail-open, and thread the primary planning surface through all four production
callers (`status/emit.py` x2, `status/aggregate.py:717`, `coordination/status_transition.py:444`).
The largest WP — the class-closer.
**Deps**: WP01.
**Independent test**: `uv run pytest tests/specify_cli/status/ -q` incl.
`test_infer_subtasks_primary.py` driven through the production `aggregate.py` route.
**Prompt**: [tasks/WP02-emit-core.md](tasks/WP02-emit-core.md)

- [x] T007 SPIKE: confirm 4 call sites + `WorkspaceRootNotFound` gotcha (WP02)
- [x] T008 Reimplement row logic on `count_wp_section_subtask_rows` (WP02)
- [x] T009 Remove the fail-open on missing `tasks.md` (WP02)
- [x] T010 Thread primary surface at `aggregate.py:717` (WP02)
- [x] T011 Thread primary surface at `emit.py:532`/`:685` w/ guard (WP02)
- [x] T012 Thread primary surface at `status_transition.py:444` (WP02)
- [x] T013 Regression test: native for_review blocked on unchecked rows (WP02)
- [x] T014 Full status-suite check; native guard untouched (WP02)

**Sketch**: delete the divergent regex/heading/fence-blind loop inside `_infer_subtasks_complete`
in favor of `core.subtask_rows.count_wp_section_subtask_rows`; delete the
`if not tasks_path.exists(): return True` fail-open, flipping the polarity to block-on-absent;
resolve `resolve_planning_read_dir(..., kind=TASKS_INDEX)` at all four callers, guarding the two
nullable-`repo_root` `emit.py` sites with a `try/except WorkspaceRootNotFound` fallback so
non-repo unit tests don't regress. `tasks_shared._check_unchecked_subtasks` (the native
`move-task` guard) is explicitly out of scope — already correct.

**Estimated prompt size**: ~470 lines.

## WP03 — IC-EMIT-DEDUP: retire #2511's per-door pre-derivation

**Summary**: Remove the orchestrator-api's now-redundant per-door `subtasks_complete`
pre-derivation (#2511), leaving the door to block solely through the shared emit layer WP02
fixed; re-point its test coverage; confirm dead-code-safe.
**Deps**: WP02 (structural — the door's block path must be primary-correct before the per-door
patch is safe to remove).
**Independent test**: `uv run pytest tests/specify_cli/orchestrator_api/test_transition_subtask_gate.py -q`
+ the dead-symbol architectural test.
**Prompt**: [tasks/WP03-emit-dedup.md](tasks/WP03-emit-dedup.md)

- [ ] T015 Remove the #2511 pre-derivation block + its local import (WP03)
- [ ] T016 Re-point #2511 tests at shared-layer behavior (WP03)
- [ ] T017 Dead-code gate green (WP03)

**Sketch**: delete `orchestrator_api/commands.py`'s `if subtasks_complete is None and not force:`
block (~:1418-1430) and its function-local `_infer_subtasks_complete` import; `subtasks_complete`
flows through unmodified, so the orchestrator door blocks solely via
`coordination/status_transition.py:444`. Judge (not delete) the #2511 test coverage — re-point
assertions from the removed mechanism onto the observable blocked/allowed outcome. Confirm
`_infer_subtasks_complete` and `_planning_read_dir` both retain their other live callers.

**Estimated prompt size**: ~260 lines.

## WP04 — IC-LANE: sparse-checkout on lane recovery [P]

**Summary**: Fix the #2514 recovery-path regression — a recovered coord-topology lane must apply
the same sparse-checkout exclusion as a freshly-created one. Scoped solely to FR-006; FR-008 (an
allocator-side stale-claim liveness check) has been withdrawn — the allocator has no stale-claim
decision to wire it into.
**Deps**: none — parallel to the WP01→WP02→WP03 spine. No import or build-order relationship with
WP05.
**Independent test**: `uv run pytest tests/specify_cli/lanes/test_worktree_allocator_recovery.py -q`.
**Prompt**: [tasks/WP04-lane-recovery.md](tasks/WP04-lane-recovery.md)

- [x] T018 Hoist `coordination_branch`/`short_id` above the recovery branch (WP04)
- [x] T019 Extract `_register_sparse_checkout_if_coord`; call from both paths (WP04)
- [x] T020 Tests: coord recovery registers sparse-checkout; non-coord stays no-op (WP04)
- [x] T021 Closeout: lint/type/architectural verification; non-coord path unchanged (WP04)

**Sketch**: close-by-construction, not mirrored guards — hoist the two values both paths need
above the recovery branch, extract one `_register_sparse_checkout_if_coord` helper, call it from
both the fresh-create and recovery branches so they cannot drift again.

**Estimated prompt size**: ~300 lines.

## WP05 — IC-LIVENESS: one claim-liveness helper (indicator + daemon) [P]

**Summary**: Promote the existing `sync/daemon._is_process_alive` psutil helper into a new
low-level `core/process_liveness.py` (no `core → sync` layering inversion), repoint its
consumers — `core/stale_detection.py` (the sole new consumer) and `sync/daemon.py` (via a thin
re-export alias, since `dashboard/lifecycle.py` imports `_is_process_alive` from that module) —
and wire `core/stale_detection.py` to suppress "stale" for a live claiming `shell_pid`.
**Deps**: none — parallel to the spine and to WP04/WP06. WP04 does not consume this WP's output
(FR-008 withdrawn).
**Independent test**: `uv run pytest tests/specify_cli/core/test_process_liveness.py -q` +
stale_detection live-claim test.
**Prompt**: [tasks/WP05-claim-liveness.md](tasks/WP05-claim-liveness.md)

- [x] T023 Create `core/process_liveness.py` (promoted `is_process_alive`) (WP05)
- [x] T024 Repoint `sync/daemon.py` to the new module (WP05)
- [x] T025 Wire `stale_detection.py` liveness suppression via `task_utils` frontmatter reader (WP05)
- [x] T026 NFR-004 matrix + live-claim stale_detection test (WP05)

**Sketch**: move `_is_process_alive`'s body verbatim (psutil-only, `NoSuchProcess`→`False`,
`AccessDenied`→`True`, bare `except Exception`→`False`, never raises) into
`core/process_liveness.is_process_alive`, importing only `psutil` + stdlib; repoint
`sync/daemon.py`'s three call sites; thread the claiming `shell_pid` (read via the existing
`task_utils.support.WorkPackage.shell_pid` reader — no new frontmatter parse) into
`check_wp_staleness`'s decision, suppressing "stale" when the process is live and falling back to
the existing timestamp heuristic otherwise.

**Estimated prompt size**: ~300 lines.

## WP06 — IC-TIDY: rollback-reset seam, freshness regression guard, issue-matrix [P]

**Summary**: Route the existing rollback-to-`planned` resets through one named seam (no new
behavior); pin #1764's checkbox-insensitive freshness hashing with a regression guard only (no
new logic); author `issue-matrix.md`.
**Deps**: none — parallel to everything; owns `tasks_move_task.py` exclusively (C-003).
**Independent test**: `uv run pytest tests/specify_cli/cli/commands/agent/test_freshness_checkbox_insensitive.py -q`
+ a production-path `move-task --to planned` rollback test.
**Prompt**: [tasks/WP06-tidy.md](tasks/WP06-tidy.md)

- [x] T027 `_mt_reset_for_planned_rollback` consolidation seam (WP06)
- [x] T028 Test: rollback leaves the WP fully re-implementable (WP06)
- [x] T029 FR-009 regression guard: checkbox-insensitive freshness hashing (WP06)
- [x] T030 Author `issue-matrix.md` (WP06)
- [x] T031 Full verification (WP06)

**Sketch**: consolidate the existing `agent`/`shell_pid` frontmatter clear (#2514) and subtask
uncheck (#2513, via `_mt_uncheck_rollback_subtasks`) onto one clearly-named seam without changing
the status-lock boundary either reset currently runs relative to; pin (do not re-implement)
`analysis_report._normalize_tasks_md`'s checkbox-stripping on both `write_analysis_report` and
`check_analysis_report_current`; author the mission's terminal-verdict issue-matrix using the
canonical `Issue | Verdict | Evidence ref | Scope` schema.

**Estimated prompt size**: ~330 lines.

---

## Sequencing

```
WP01 (IC-ROWS) ──▶ WP02 (IC-EMIT-CORE) ──▶ WP03 (IC-EMIT-DEDUP)   critical path
WP04 (IC-LANE)    ┐
WP05 (IC-LIVENESS) ├─ fully parallel with the WP01→WP02→WP03 spine
WP06 (IC-TIDY)     ┘
```

- **Keystone**: WP01 before WP02 — WP02 consumes `count_wp_section_subtask_rows`.
- **Structural (not just preferred)**: WP03 after WP02 — the orchestrator door blocks solely
  through `coordination/status_transition.py:444` once the per-door pre-derivation is gone; that
  line must already be primary-correct (WP02) before WP03 removes the patch.
- **No cross-lane coupling**: WP04 and WP05 are fully independent — FR-008 (the allocator-side
  liveness consult that previously coupled them) has been withdrawn; WP04 no longer imports
  anything from `core.process_liveness`.
- **Disjoint ownership (C-003)**: `subtask_rows.py` (WP01) / `emit.py`+`aggregate.py`+`status_transition.py`
  (WP02) / `orchestrator_api/commands.py` (WP03) / `worktree_allocator.py` (WP04) /
  `process_liveness.py`+`stale_detection.py`+`sync/daemon.py`-repoint (WP05) /
  `tasks_move_task.py`+`issue-matrix.md` (WP06) — no overlaps.
