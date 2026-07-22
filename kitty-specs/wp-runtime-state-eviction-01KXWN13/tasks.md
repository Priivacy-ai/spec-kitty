# Tasks: Evict WP runtime state into the event log

**Mission**: `wp-runtime-state-eviction-01KXWN13` · **Branch**: `mission-prep/2684-wp-runtime-state-eviction`
**Planning base / merge target**: `mission-prep/2684-wp-runtime-state-eviction`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Design of record**: ADR 2026-07-19-1

Work packages are grouped by **file ownership** (non-overlapping `owned_files`) while preserving the
plan's per-field-vertical sequencing and C-001 atomicity. Execution worktrees are allocated per lane
by `finalize-tasks`; run `spec-kitty next --agent <agent> --mission wp-runtime-state-eviction-01KXWN13`.

**Deferred (documented follow-up, NOT in these WPs):**
- **Corpus cutover (human decision 2026-07-19: ship dual-write, defer cutover).** This mission delivers
  the event infrastructure + dual-write **behind the phase-1 flag** (`_phase1_dual_write_enabled`,
  default OFF) + the WP03 backfill *library*. The field verticals (WP01/WP04/WP05/WP07) landed their
  snapshot readers behind the flag, not as unconditional behavior, and no WP wired the runtime-state
  `backfill → verify → cutover` CLI. Per `contracts/migration.md` the flag/fallback teardown is the
  FINAL migration step, gated on that backfill. Deferred to a follow-up mission: wire the
  `backfill → verify(fail-closed) → cutover` CLI, flip the flag unconditional across the ~12 read/write
  sites, and delete the T037 legacy fallbacks. **This re-scopes WP10** (see its RE-SCOPE banner):
  T037 is deferred; T036/T038/T038a/T039/T040 are proven at `status_phase:1` (flag ON).
- **IC-08 post-cutover reduction** (`wp_metadata` inert fields, `WP_FIELD_ORDER` cosmetic slots) — only
  safe after the corpus cutover above completes; land as a separate bounded reduction.

## Subtask Index

| ID | Description | WP | Parallel |
| --- | --- | --- | --- |
| T001 | `InnerStateChanged` + typed `WPInnerStateDelta` models | WP01 | | [D] |
| T002 | Wire discriminator + store read path (`read_events`/`is_non_lane_event`/`from_dict`) | WP01 | | [D] |
| T003 | Reducer branch-on-kind + preserve slots + event-kind-partition fold + snapshot slots | WP01 | | [D] |
| T004 | Sanctioned non-transition `annotate()` path (no FSM matrix change) | WP01 | | [D] |
| T005 | `emit_inner_state_changed` API + claim `policy_metadata`→snapshot fold + `_infer_subtasks_complete` re-source | WP01 | | [D] |
| T006 | Unit fold tests + architectural "annotation never reduced as transition" test | WP01 | | [D] |
| T007 | `build_transition_plan` ask-the-FSM force suppression (FR-015) | WP02 | | [D] |
| T008 | `_guard_subtasks` re-source to reduced snapshot (FR-003) | WP02 | | [D] |
| T009 | Re-point existing plan-level force tests + persisted-force command-layer regression | WP02 | | [D] |
| T010 | Extend `MUTABLE_FIELDS`; move `history` out of `STATIC_FIELDS`; retire `progress` | WP03 | | [D] |
| T011 | Backfill module: seed transition + `InnerStateChanged`; deterministic namespaced ULIDs; subtask clamp | WP03 | | [D] |
| T012 | Fail-closed verify (count+value parity vs old reader; abort before cutover; fault-injection) | WP03 | | [D] |
| T013 | Zero-reader verification for `history[]` / `progress` | WP03 | | [D] |
| T014 | Migration idempotency + fail-closed tests | WP03 | | [D] |
| T015 | `mark-status` emits subtask `InnerStateChanged` (stop writing `tasks.md` checkbox) | WP04 | [D] |
| T016 | `_check_unchecked_subtasks` re-source to snapshot | WP04 | [D] |
| T017 | Owned unit test: `_check_unchecked_subtasks` follows the reduced snapshot, not `tasks.md`/`HistoryAdded` | WP04 | [D] |
| T018 | Claim-liveness `stale_detection` → snapshot (behind flag) | WP05 | [D] |
| T019 | `WorkPackage.{shell_pid,agent,assignee}` → snapshot | WP05 | [D] |
| T020 | `WPMetadata` coercion → snapshot | WP05 | [D] |
| T021 | Two-sided liveness test (dead snapshot PID flips stale) | WP05 | [D] |
| T022 | Cut `_mt_persist_wp_file` field writes → emit `InnerStateChanged` | WP06 | | [D] |
| T023 | Delete `_mt_persist_tracker_refs` + `_mt_*uncheck*` trio + `_mt_clear_rollback_claim_markers` | WP06 | | [D] |
| T024 | Emit sites resolve `destination_ref` from stored topology (never `Path.cwd()`, #2647/SC-008) | WP06 | | [D] |
| T025 | Proof-of-drive lifecycle hash test (no WP-file write across lifecycle) | WP06 | | [D] |
| T026 | `shell_pid` claim → `policy_metadata` on `planned→claimed` (implement.py, FR-014 restructuring) | WP07 | [D] |
| T027 | `workflow_executor` claim writers (`:695`/`:1370`) → `policy_metadata` | WP07 | [D] |
| T028 | Delete `write_shell_pid_claim*` + `add_history_entry` + `__all__`; re-point orphaned baseline tests | WP07 | [D] |
| T029 | Strike `tracker_refs` from `WP_FIELD_ORDER` | WP07 | [D] |
| T029a | Resume/re-claim `shell_pid` refresh emitted as `InnerStateChanged` (FR-004/US3) | WP07 | [D] |
| T030 | `tracker_refs` union emit from `map-requirements` | WP08 | [D] |
| T031 | External activity-log writer → `InnerStateChanged` (`orchestrator_api`) | WP08 | [D] |
| T032 | SC-008 cross-package topology-resolution test | WP08 | [D] |
| T033 | Event-source `review_artifact_override_*` write half + collapse coord mirror | WP09 | [D] |
| T034 | Migrate read half + merge-gate override recognition → `review` snapshot slot | WP09 | [D] |
| T035 | Override-recognition regression (no false merge block) | WP09 | [D] |
| T036 | Delete FR-005 fallback flag + any dual-write shim | WP10 | | [D] |
| T037 | Delete legacy fallbacks `workflow_cores.py:340-348` + `done_bookkeeping.py:104-105` (post-backfill) | WP10 | | [D] |
| T038 | Land AC-5 stable-hash guard (proof-of-drive lifecycle) — sole SC-001/SC-005 acceptance | WP10 | | [D] |
| T038a | SC-004 render-parity golden (activity/history/review vs legacy-sourced golden) | WP10 | | [D] |
| T039 | #2093 refactor-stable arch test (no dynamic-frontmatter authority; no dual-home) + reconcile `test_no_dead_symbols` | WP10 | | [D] |
| T040 | Full-suite green; re-pointed force tests reconciled | WP10 | | [D] |

## Work Packages

### WP01 — Event foundation + reducer fold + emit API
- **Goal**: The `InnerStateChanged` event, typed delta, reducer branch/preserve/partition, snapshot
  slots (incl. `agent`/`assignee`/`review`), the `emit_inner_state_changed` API, the claim
  `policy_metadata`→snapshot fold, and `_infer_subtasks_complete` re-source. **Priority: P1 (foundation).**
- **Independent test**: unit fold tests + the architectural "annotation never reduced as a lane
  transition" test pass.
- **Subtasks**: T001–T006. **Depends on**: none. **Owns**: `src/specify_cli/status/{models,store,reducer,wp_state,emit}.py`, `tests/unit/status/**`, `tests/architectural/test_innerstatechanged_invariants.py`.
- **Est.**: ~450 lines. **Risk**: the reducer replace-dict hazard; discriminator collision; ordering partition.

### WP02 — Transition-core gates: force-fix + subtask gate re-source
- **Goal**: FR-015 ask-the-FSM force suppression **and** `_guard_subtasks` re-source (both live in
  `tasks_transition_core.py`). **Land early** (post-WP01) so writer WPs rebase onto corrected logic.
- **Independent test**: persisted `StatusEvent.force` falsy on the five edges (+ genuine-force control);
  `_guard_subtasks` reads the snapshot.
- **Subtasks**: T007–T009. **Depends on**: WP01. **Owns**: `src/specify_cli/cli/commands/agent/tasks_transition_core.py`, `tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py`, `tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py`, `tests/regression/test_2684_force_provenance.py`.
- **Est.**: ~350 lines.

### WP03 — Migration engine: backfill + fail-closed verify
- **Goal**: Extend `MUTABLE_FIELDS`, backfill seed events (deterministic ULIDs), fail-closed verify
  gating cutover, zero-reader checks. **Priority: P1 (gates cutovers).**
- **Subtasks**: T010–T014. **Depends on**: WP01. **Owns**: `src/specify_cli/migration/strip_frontmatter.py`, `src/specify_cli/migration/backfill_runtime_state.py` (new), `tests/integration/test_migration_backfill.py`, `tests/unit/migration/**`.
- **Est.**: ~480 lines. **Risk**: ULID ordering at equal `at`; fail-closed abort; clamp honesty.

### WP04 — Subtask emit + reader delegate (turns the red test green)
- **Subtasks**: T015–T017. **Depends on**: WP01, WP02. **Owns**: `src/specify_cli/cli/commands/agent/{tasks_mark_status,tasks_shared}.py`. **Est.**: ~300 lines.

### WP05 — Liveness + model readers
- **Subtasks**: T018–T021. **Depends on**: WP01, WP03. **Owns**: `src/specify_cli/core/stale_detection.py`, `src/specify_cli/task_utils/support.py`, `src/specify_cli/status/wp_metadata.py`. **Est.**: ~340 lines.

### WP06 — Writer cut: move-task god-write (+ #2647 invariant)
- **Subtasks**: T022–T025. **Depends on**: WP01, WP02, WP03, WP04. **Owns**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`, `tests/integration/test_wp_file_hash_stability.py`. **Est.**: ~470 lines. **Risk**: the god-write hub; destination_ref must never be `Path.cwd()`.

### WP07 — Claim writers + frontmatter cleanup (FR-014)
- **Subtasks**: T026–T029. **Depends on**: WP01, WP03. **Owns**: `src/specify_cli/cli/commands/agent/{implement,workflow_executor}.py`, `src/specify_cli/frontmatter.py`, `tests/specify_cli/core/test_shell_pid_claim_baseline.py`, `tests/specify_cli/cli/commands/agent/test_implement_runtime_frontmatter_claim.py`, `tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py`. **Est.**: ~420 lines.

### WP08 — map-requirements + external activity-log writer
- **Subtasks**: T030–T032. **Depends on**: WP01, WP03. **Owns**: `src/specify_cli/cli/commands/agent/tasks_map_requirements.py`, `src/specify_cli/orchestrator_api/commands.py`. **Est.**: ~300 lines. **Risk**: cross-package writer; SC-008 topology-resolution.

### WP09 — Review-cycle eviction (both halves)
- **Subtasks**: T033–T035. **Depends on**: WP01, WP03. **Owns**: `src/specify_cli/cli/commands/agent/tasks_materialization.py`, `src/specify_cli/review/artifacts.py`. **Est.**: ~360 lines. **Risk**: write-only eviction breaks the merge gate — migrate both halves.

### WP10 — Closeout: delete fallbacks + land invariants
- **Subtasks**: T036–T040. **Depends on**: WP04, WP05, WP06, WP07, WP08, WP09. **Owns**: `src/specify_cli/cli/commands/agent/workflow_cores.py`, `src/specify_cli/merge/done_bookkeeping.py`, `tests/architectural/test_no_dead_symbols.py`, `tests/architectural/test_2093_authority_invariant.py`, `tests/integration/test_ac5_hash_guard.py`. **Est.**: ~420 lines. **Risk**: no inert fallback / dual-write shim left; delete only post-backfill.

## Dependencies (graph)

```
WP01 ──┬─ WP02 ──┬─ WP04 ─┐
       ├─ WP03 ──┼─ WP05 ─┤
       │         ├─ WP06 ─┤
       │         ├─ WP07 ─┼─ WP10
       │         ├─ WP08 ─┤
       │         └─ WP09 ─┘
```

**MVP slice**: WP01 → WP02 → WP04 turns the merged P0 red test green (the headline outcome).
**Parallel band**: after WP01+WP02+WP03, {WP05, WP06, WP07, WP08, WP09} run largely in parallel
(2–3 lanes sustained). **Land order note**: WP02 (force + gate) before the writer WPs to avoid
`tasks_transition_core.py`/`tasks_move_task.py`/`emit.py` merge races. **PR #2766** has no inbound
gate — it rebases onto WP07's writer cutover, not the reverse (C-006).
