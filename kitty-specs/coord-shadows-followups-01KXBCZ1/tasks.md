# Work Packages: Coord-Shadows Follow-ups Closeout

**Inputs**: Design documents from `kitty-specs/coord-shadows-followups-01KXBCZ1/`
**Prerequisites**: plan.md (required), spec.md (user stories)

**Tests**: Required — this mission's value is correctness/robustness; every behavior-changing WP carries a red-first or characterization test as a first-class subtask.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each WP is independently deliverable and testable. 1 IC → 1 WP (post-plan squad confirmed; do not split).

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).

## Path Conventions

- Single project: `src/specify_cli/`, `tests/specify_cli/`.

---

## Work Package WP01: Subtask-gate single seam (Priority: P1)

**Goal**: Collapse the three divergent subtask-gate-dir resolvers into one canonical `resolve_subtasks_gate_dir` with the strong git-ancestry fallback, so no call site gates on a stale coordination husk.
**Independent Test**: On a git-rooted coord-topology fixture with `repo_root=None`, all three call sites resolve the PRIMARY `tasks.md`; the two already-strong sites are byte-identical to today; a bare `tmp_path` falls back to `feature_dir`.
**Prompt**: `/tasks/WP01-subtask-gate-single-seam.md`
**Requirement Refs**: FR-001, FR-002, FR-003, NFR-001, NFR-002, C-002, C-003

### Included Subtasks

- [x] T001 [P] Red-first test: prove `coordination/status_transition.py::_prepare_event` with `repo_root=None` on a git-rooted coord fixture currently resolves the coord husk (failing assertion for the intended primary resolution) in `tests/specify_cli/status/test_subtasks_gate_dir_seam.py`
- [x] T002 Add `resolve_subtasks_gate_dir(feature_dir, repo_root, mission_slug) -> Path` to `src/specify_cli/missions/_read_path_resolver.py` (emit.py's superset contract: `repo_root` → `resolve_canonical_root` → `feature_dir` on `WorkspaceRootNotFound`; carry the `cast(Path, ...)` verbatim per C-002)
- [x] T003 Repoint `src/specify_cli/status/emit.py`: delete `_resolve_primary_subtasks_dir`, route both callers (L581, L737) through the seam
- [x] T004 Repoint `src/specify_cli/status/aggregate.py::_resolve_review_gate_inputs` inline resolver to the seam
- [x] T005 Repoint `src/specify_cli/coordination/status_transition.py::_prepare_event` inline resolver to the seam (this grants the strong fallback and makes T001 green)
- [x] T006 [P] Characterization test: the two strong sites (emit, aggregate) produce byte-identical resolution for pre-existing inputs; non-git `tmp_path` falls back to `feature_dir` unchanged
- [x] T007 Verify dead-code gate clean (no orphaned `_resolve_primary_subtasks_dir`); `ruff` + `mypy` zero new findings

### Dependencies

- None (independent spine keystone).

### Risks & Mitigations

- `status_transition.py` change is a behavior fix → T001 red-first proves it; T006 pins the strong sites. Dead-code gate flags an incomplete repoint (T007).

---

## Work Package WP02: PID-reuse-aware liveness + truth-in-labeling (Priority: P1)

**Goal**: Make `is_process_alive` unfoolable by a recycled PID via a persisted creation-time baseline co-written at every claim site, and correct the mislabeled test + docstring overclaim. Degradation is additive — absent baseline preserves today's behavior (zero legacy regression).
**Independent Test**: A simulated baseline mismatch is treated as not-alive → falls to the timestamp heuristic; a `workflow_executor`-claimed WP carries the baseline; a legacy (absent-baseline) claim preserves live-PID trust; `is_process_alive(pid)->bool` signature unchanged.
**Prompt**: `/tasks/WP02-pid-reuse-liveness.md`
**Requirement Refs**: FR-004, FR-005, FR-006, NFR-003, NFR-004, NFR-005, C-005, C-007

### Included Subtasks

- [x] T008 [P] Truth-in-labeling (independent of baseline work, D4): fix the `process_liveness.py` module/function docstring overclaim about "recycled PIDs"; rename the mislabeled test `test_recycled_pid_generic_exception_returns_false` to describe the current blindness it actually exercises
- [x] T009 Register the additive baseline field (process creation-time) in `src/specify_cli/frontmatter.py`; model it in `src/specify_cli/status/wp_metadata.py`
- [x] T010 Extract ONE claim-write helper that co-writes `shell_pid` + the creation-time baseline (close-by-construction, D3b)
- [x] T011 Route `src/specify_cli/cli/commands/implement.py` (~L1400) through the helper
- [x] T012 Route `src/specify_cli/cli/commands/agent/workflow_executor.py` implement-claim (~L668) AND review-claim (~L1338) through the helper (both write the `shell_pid` key staleness reads)
- [x] T013 Add baseline-aware compare in `src/specify_cli/core/process_liveness.py` (companion `is_claiming_process_alive(pid, baseline)` or optional param, keeping `is_process_alive(pid)->bool` frozen) and wire `src/specify_cli/core/stale_detection.py::_is_claiming_process_alive` to pass + compare it; absent baseline preserves today's live-PID trust (D3a)
- [x] T014 [P] Test: simulated baseline mismatch → not-alive → timestamp-heuristic fallback (the deterministic seam) in `tests/specify_cli/core/test_process_liveness.py`
- [x] T015 [P] Test: real spawn→kill liveness path
- [x] T016 [P] Test: a WP claimed via `workflow_executor` carries the baseline (regression guard for the primary implement-loop claim path)
- [x] T017 [P] Test: legacy claim (absent baseline) preserves live-PID trust (no regression)
- [x] T018 Verify C-005 (no psutil-consumer sweep beyond process_liveness + stale_detection) and C-007 (one additive field); `ruff` + `mypy` zero new findings

### Dependencies

- None.

### Risks & Mitigations

- Scope-creep magnet → C-005/C-007 fence + T018 verify. Primary-loop regression → T012 co-writes all sites + T016 guards it. Deterministic testing → T014 mismatch seam, not an OS PID-recycle.

---

## Work Package WP03: Guarded rollback-uncheck (Priority: P2)

**Goal**: Ensure a WP rolled back to `planned` reliably loses its `- [x]` rows even when the out-of-lock write errors, so #2513 cannot silently re-manifest — without folding under the status lock.
**Independent Test**: A simulated write failure in the rollback-uncheck window does not silently leave `- [x]` rows on a `planned` WP (the failure is surfaced in the result); the write routes through `write_text_within_directory`; out-of-lock ordering and review-lock release are preserved.
**Prompt**: `/tasks/WP03-guarded-rollback-uncheck.md`
**Requirement Refs**: FR-007, C-001, C-004

### Included Subtasks

- [x] T019 [P] Failure-mode test: simulate a write failure in `_mt_uncheck_rollback_subtasks` and assert rows are NOT silently left checked on a `planned` WP and the `move-task` result reflects the incomplete rollback, in `tests/specify_cli/cli/commands/agent/test_move_task_rollback_uncheck_robust.py`
- [x] T020 Route the uncheck read/write through `write_text_within_directory` (house guard) in `src/specify_cli/cli/commands/agent/tasks_move_task.py::_mt_uncheck_rollback_subtasks`
- [x] T021 Implement the surfaced-not-swallowed failure mode (record incomplete-rollback on `_MoveTaskState` / result envelope + error log) WITHOUT aborting `_mt_release_review_lock`
- [x] T022 [P] Test: out-of-lock ordering preserved (uncheck runs after the status lock exits; review-lock release still fires on failure)
- [x] T023 Confirm `owned_files` stays at the `_mt_uncheck_rollback_subtasks` seam only (C-004: `_mt_run_pre_review_gate`/#2573 shares the module); `ruff` + `mypy` zero new findings

### Dependencies

- None.

### Risks & Mitigations

- Must NOT fold under `feature_status_lock` (C-001) nor touch `_mt_run_pre_review_gate` (C-004). Surface must not abort lock release → T022 pins ordering.

---

## Work Package WP04: Checkbox-parser canonicalization (Priority: P3)

**Goal**: Replace the acceptance gate's stray whole-file `[ ]` regex with a canonical fence-aware, T###-scoped whole-file iterator, unifying checkbox semantics — with the tightening ratified consciously.
**Independent Test**: On a fixture with T### rows, prose `- [ ]` lines, and fenced example checkboxes, the acceptance gate flags only genuine T###-scoped rows; a characterization test captures the old→new flagging; terminal-mission normalization is preserved.
**Prompt**: `/tasks/WP04-checkbox-parser-canon.md`
**Requirement Refs**: FR-008, FR-009, NFR-003

### Included Subtasks

- [x] T024 Add `iter_unchecked_subtask_rows(text) -> Iterator[str]` (whole-file, fence-aware, T###-scoped, yields offending line strings) on `src/specify_cli/core/subtask_rows.py` shared constants
- [x] T025 [P] Characterization test: capture the acceptance gate's unchecked-row output before→after migration on a mixed fixture (T### rows + prose `[ ]` + fenced examples), ratifying the T###/fence/indent tightening (FR-009), in `tests/specify_cli/acceptance/test_find_unchecked_tasks_canon.py`
- [x] T026 Migrate `src/specify_cli/acceptance/gates_core.py::_find_unchecked_tasks` onto the new iterator
- [x] T027 [P] Test: terminal-mission normalization (all-WPs-terminal zeroes unchecked tasks) preserved after migration
- [x] T028 Verify dead-code gate clean (stray regex removed); `ruff` + `mypy` zero new findings

### Dependencies

- None.

### Risks & Mitigations

- Observable acceptance-gate change → T025 characterization ratifies it; T027 preserves the terminal normalization. Lowest value; keep tightly scoped.

---

## Work Package WP05: Review-lock liveness fold (Priority: P2)

**Goal**: Fold `review/lock.is_stale` onto the canonical `core/process_liveness.is_process_alive` (`return not is_process_alive(pid)`), removing the last stray liveness probe.
**Independent Test**: `is_stale` is branch-equivalent (live / dead / permission-denied) to the prior `os.kill(pid,0)` implementation; `os.getpid()` at acquire is retained.
**Prompt**: `/tasks/WP05-review-lock-liveness-fold.md`
**Requirement Refs**: FR-010, NFR-001

### Included Subtasks

- [ ] T029 Fold `src/specify_cli/review/lock.py::is_stale` to `return not is_process_alive(self.pid)`; remove the liveness `os.kill(pid,0)`; keep `os.getpid()` at acquire
- [ ] T030 [P] Characterization test: 3-branch equivalence (live / dead / permission-denied) in `tests/specify_cli/review/test_lock_liveness_fold.py`
- [ ] T031 Verify no orphaned imports (dead-code gate); `ruff` + `mypy` zero new findings

### Dependencies

- Depends on WP02 (consumes the `is_process_alive(pid)->bool` signature; sequence after it settles). Equivalence-only — no PID-reuse hardening for the lock.

### Risks & Mitigations

- Preserve branch-equivalence → T030 pins all three branches. Keep `os.getpid()` intact.
