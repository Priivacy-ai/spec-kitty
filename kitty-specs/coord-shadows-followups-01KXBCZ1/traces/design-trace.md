# Design Trace — coord-shadows-followups

The design itself: invariants kept (KEEP set), forward alignment, what must hold under implementation.
Tracked under #2095.

## Seed (planning) — KEEP set (invariants that MUST hold)

1. **One canonical authority per operation.** After this mission: ONE subtask-gate-dir resolver (`resolve_subtasks_gate_dir` in `missions/_read_path_resolver.py`), ONE checkbox authority (`core/subtask_rows`), ONE liveness authority (`core/process_liveness`). No stray copies survive (dead-code gate enforces).
2. **Strong fallback, no husk read.** The consolidated resolver uses emit.py's superset: `repo_root` → else `resolve_canonical_root(feature_dir)` git-ancestry → else `feature_dir` (only on `WorkspaceRootNotFound`). The previously-weak `status_transition.py` site MUST stop falling straight to the coord husk. (Aligns [[feedback_no_legacy_resolver_paths]] — require-canonical, not husk-fallback.)
3. **Behavior preservation on strong paths.** The two already-strong F1 sites + the #2568 fold produce byte-identical resolution/verdict for all pre-existing inputs (NFR-001, pinned by characterization tests).
4. **Load-bearing casts stay.** `cast(Path, ...)` at the resolver + `bool(...)` liveness wraps carried verbatim (C-002). They are load-bearing under per-file `follow_imports=skip`; whole-repo mypy calling them "redundant" is advisory noise — do NOT clean it.
5. **Liveness conservatism.** `is_process_alive` never raises; absent/unparseable/identity-unverifiable → not-alive; AccessDenied → alive (cannot-prove-dead). `(pid)->bool` signature preserved so `review/lock` + other consumers keep working. Baseline = ONE additive field (C-007).
6. **F3 out-of-lock preserved.** The rollback-uncheck stays OUT of `feature_status_lock` (C-001). Failure mode = SURFACED not swallowed (must not silently re-leave `- [x]` on a `planned` WP), and must NOT abort `_mt_release_review_lock` (which runs after the reset at `tasks_move_task.py:1595`).
7. **#2567 tightening is RATIFIED.** The acceptance gate narrows to T###/fence-aware/anchored — this is an intentional loosening of what it flags, pinned by a characterization test (FR-009). Terminal-mission normalization preserved.
8. **Scope containment.** No psutil-consumer sweep beyond {`process_liveness`, `stale_detection` claim path, `review/lock`} (C-005/NFR-005). F3 owned_files tight — do NOT touch `_mt_run_pre_review_gate` (#2573 collision, C-004).

## Forward alignment

Extends the #2572-shipped seams (`core/subtask_rows`, `core/process_liveness`) rather than redesigning; keeps epic #2160 converging on single-authority-per-surface.

## Append (implement)

<!-- append: invariant pressure, design decisions made under implementation, deviations + why -->

## Assess (close)

<!-- fill at close: which KEEP-set invariants held, which bent, forward-alignment check -->
