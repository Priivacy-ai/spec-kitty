# Research / Disambiguation Map

Phase-0 output. Condensed from two profile-loaded scouts (verified file:line, current `upstream/main` base eff6353260). Hand this to WP implementers so they do not re-scout.

## #3780 — provenance-gated advancement

### Current predicate (`src/runtime/next/runtime_bridge.py`)
- `_should_advance_wp_step(step_id, feature_dir)` (:692) loops WP files; per WP: `raw_lane = get_wp_lane(feature_dir, wp_id)` (:714, **lane-only — the gap**) → `state = wp_state_for(raw_lane)` (:716) → `if _wp_blocks_step(step_id, state): return False` (:721).
- `_wp_blocks_step(step_id, state)` (:727):
  - `implement` → `state.is_blocked or (state.is_run_affecting and lane not in (FOR_REVIEW, APPROVED))`
  - `review` → `lane not in (DONE, APPROVED)`

### Truth table (True = BLOCKS advancement)
| lane | implement | review |
|---|---|---|
| DONE | False | False |
| APPROVED | False | False |
| **CANCELED** | False (already passes) | **True ← the #3780 bug** |
| FOR_REVIEW | False | True |
| PLANNED/CLAIMED/IN_PROGRESS/IN_REVIEW | True | True |
| BLOCKED | True | True |

`CanceledState` (`wp_state.py:538`): `is_blocked=False`, `is_run_affecting=False` (base default; CANCELED ∉ run-affecting set at `wp_state.py:109`).

### Authority (consume, do not modify) — `src/specify_cli/status_lanes.py`
- `is_acceptable_ending(lane, *, has_provenance)` (:42): approved/done → True always; canceled → `has_provenance`; else False.
- `has_operator_provenance(wp_snapshot)` (:70): `wp_snapshot.get("reason_source") == "operator"`; None/absent/other → False.

### Provenance discriminator — `src/specify_cli/status/reducer.py`
- Only writer of the slot: `reducer.py:249-251` sets `reason_source = _cancellation_reason_source(event)` on a CANCELED event.
- `_cancellation_reason_source` (:104): durable `event.reason_source` wins; else empty reason → `"synthetic"`; else `"Force move to "`/`"move-task: "` prefix → `"synthetic"`; else `"operator"`.
- Single-WP snapshot accessor: `wp_snapshot_state(feature_dir, wp_id)` (:532) → reduced per-WP mapping (has `reason_source`) or `None`.

### The C-003 trap
`get_wp_lane` (`lane_reader.py:51`) → `_require_event_log` **raises `CanonicalStatusNotFoundError`** on absent log. `wp_snapshot_state` → `read_event_stream` returns empty (no raise) on absent log (`store.py:751`). So a naive swap silently breaks fail-loud. Design: **one** `reduce()` per WP yielding lane + `reason_source`, fronted by an explicit `has_event_log`/`_require_event_log` gate.

### Signature / callers (keep 2-arg)
`_should_advance_wp_step` consumed at `runtime_bridge.py:785`, `:1574`, `runtime_bridge_composition.py:500` (live-lookup `_rb._should_advance_wp_step`). Extend only `_wp_blocks_step` with `has_provenance=False` default (single caller :721).

### Tests
- Direct-unit home: `tests/specify_cli/next/test_runtime_bridge.py`. Helper `_write_status_events` writes `reason: None` → **synthetic**; the operator-provenance repro must emit a canceled event with `reason_source: "operator"` (or a non-empty non-template reason). Existing `test_should_advance_implement_one_canceled` (:229) stays green.
- Guard/arity + fail-loud to keep green: `tests/runtime/test_bridge_decide_next.py:404/417/440/465` (2-arg monkeypatch + `CanonicalStatusNotFoundError`), `test_bridge_parity.py:817`, `test_bridge_composition.py:751/784`, `tests/next/test_cli_guard_family.py:231`.

## #2947 — committed-authority state resolution

### `next` query path (`src/runtime/next/runtime_bridge.py`)
- CLI: `next_step()` (`cli/commands/next_cmd.py:122`), query mode → `_run_query_mode` (:802) → `query_current_state` (`runtime_bridge.py:2289`).
- `query_current_state`: `mission_context_for(...)` (:2310, workspace selection FIRST) → binds `status_state` (:2334) → `progress = _compute_wp_progress(task_board.read_dir, status_dir=status_state.read_dir)` (:2346, reduces the **selected** surface).
- No merged/terminal pre-check before selection. `_finalized_task_board_override_step` (:652) is the only all-done detector; runs AFTER selection (:2391), gated on `tasks.md` presence on the stale surface (:669), reads stale lanes → degrades to first DAG step (discovery/research) via `_build_initial_query_decision` when `issued_step_id is None` (:2409).
- Merged mission → `_existing_run_ref` (`runtime_bridge_io.py:538`) returns `None` → `_start_ephemeral_query_run` fresh snapshot → `issued_step_id is None` path.

### Shared read-path seam
- `mission_context_for` (`src/mission_runtime/resolution.py:1043`) → `candidate_feature_dir_for_mission` → `_resolve_mission_read_path` (`src/specify_cli/missions/_read_path_resolver.py:868`). Existence-gated (`require_exists`, `CoordinationBranchDeleted` #1848), **freshness-blind**.
- `agent tasks status`: `_do_status` → `_st_resolve_dirs` (`tasks_status_cmd.py:152`) → `resolve_handle_to_read_path(...)` (:178) → same `_resolve_mission_read_path`. `tasks/` read from PRIMARY (:193) but **lanes read from coord** `feature_dir` → all-`planned` rollup. `require_exists` defaults False (:872).

### Merge evidence (realizable committed signal)
- `meta.json.mission_number`: assigned at merge `max+1` (`merge/ordering.py:135`); `mission_number is None` = pre-merge (`merge/state.py:391`). **Use this.**
- NOT `merge-state.json`/`MergeState` (transient in-progress, cleared after merge) nor `MERGE_HEAD` (active merge) — absent when finished. (C-005)

### Terminal verdict target
`_build_finalized_override_query_decision` already maps `done == total` → `mission_state="done"` (`runtime_bridge.py:685, 2153`); `DecisionKind.terminal` → `mission_state="done"` (:2268). Use the existing terminal result shape.

### Tests
- New home `tests/runtime/next/test_merged_mission_terminal.py`: mission with committed `meta.json.mission_number` set + committed status all-accepted + a stale coord checkout → assert `query_current_state` returns `kind: terminal` and no run; assert `agent tasks status` reports committed lanes not `planned`. Conflict + artifact-missing → `kind: blocked`.
- No existing test exercises merged/terminal/stale-coord detection in `next` (grep clean for #2947).
