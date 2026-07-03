# Data Model — tasks-py-degod-wave2-01KWH9EQ

The "entities" of this pure-parity refactor are modules, move-sets, and seams. All
counts squad/research-verified against `381db8d5f` (see research.md).

## Target module layout

| Module (all under `src/specify_cli/cli/commands/agent/` unless noted) | State | Contents |
|---|---|---|
| `tasks.py` | SHRINKS 4569 → ≤1400 | `@app.command` wrappers (or `app.command(name=...)(fn)` registrations per template), the 4 small bodies (`list_tasks`, `add_history`, `validate_workflow`, `list_dependents`), module-level seam bindings (imports/re-exports for every D7 symbol), `console`, app setup |
| `tasks_move_task.py` | NEW | `_do_move_task` + 23 `_mt_*` + `_MoveTaskState` + `_default_move_task_ports` |
| `tasks_map_requirements.py` | NEW | `_do_map_requirements` + 11 `_mr_*` + `_MapReqState` + `_default_map_requirements_ports` |
| `tasks_status_cmd.py` | NEW | `_do_status` + 14 `_st_*` + `_StatusState` + `_default_status_ports` (named `_cmd` to avoid clashing with the existing `tasks_status_view.py` core) |
| `tasks_mark_status.py` | NEW | `_do_mark_status` + 9 `_ms_*` + `_MarkStatusState` + `_default_mark_status_ports` |
| `tasks_finalize.py` | NEW | `_do_finalize_tasks` + 4 `_ft_*` + `_FinalizeState` + `_default_finalize_ports` |
| `tasks_shared.py` | NEW | ~28 cross-family helpers: `_output_result`, `_output_error`, `_find_mission_slug`, `_ensure_target_branch_checked_out`, `_coord_topology_active`, `_skip_target_branch_commit`, `resolve_primary_branch`, `_validate_ready_for_review`, `_check_unchecked_subtasks`, `_emit_sparse_session_warning`, `_wp_branch_merged_into_target`, `_protected_branch_status_commit_error`, `_mark_status_json_payload`, … (full list = the 112-def census minus family/adapter/registration sets; enumerated by WP02 into the committed `seam-checklist.md`). NOTE: `_get_latest_review_cycle_verdict`/`_self_review_fallback_option_error` are already in `tasks_parsing_validation.py` (Wave 1) — not part of this move |
| `tasks_command_adapters.py` | NEW | `_MoveTaskCoordRouter`, `_MapReqCoordRouter`, `_MarkStatusCoordRouter` (subclass `RealCoordCommitRouter` from `specify_cli.agent_tasks_ports`) |
| `tasks_ports.py` | FR-008 disposition | 7-line `from specify_cli.agent_tasks_ports import *` shim — absorb or retain with recorded rationale + external-importer grep evidence |
| `src/specify_cli/agent_tasks_ports.py` | MODIFIED (only Stream A) | `RealRender.__init__` gains `indent: int | None = None`; `json_envelope` → `json.dumps(payload, indent=self._indent)`; nothing else changes |
| `tasks_transition_core.py`, `tasks_status_view.py`, `tasks_mapping_core.py` | UNCHANGED | Wave 1 pure cores, consumed as-is (spec Non-Goal) |

Deleted symbols: `_StatusRender` (collapsed by FR-006 into parameterized `RealRender`).

## Invariants

1. **Interception invariant** (NFR-002): for every symbol in the D7 seam table,
   `tasks.<symbol>` remains a module attribute AND every relocated caller reaches it via
   `_tasks.<symbol>` — so `@patch("...agent.tasks.<symbol>")` intercepts the real call.
2. **Divergence invariant** (C-001): `move_task` keeps its `_skip_target_branch_commit`
   pre-gate wiring; `mark_status`/`map_requirements` keep the unguarded
   `_protected_branch_status_commit_error` path. The shared helper relocates ONCE into
   `tasks_shared.py`; the pre-gate wiring stays in the move_task family. Pinned by coord
   harness T004/T005.
3. **Emission invariant** (SC-002/SC-003): every JSON emission goes through
   `ports.render.json_envelope` (or a default-param `render or RealRender()` for the
   port-less small bodies); bytes pinned by the byte-freeze suite.
4. **Ceiling invariant** (NFR-004): `len(tasks.py.splitlines()) <= ceiling`; ceiling
   only ratchets DOWN, final value `min(achieved, 1400)`.
5. **Baseline invariant** (FR-009/C-006): no path matching the tasks-domain glob appears
   in `_gate_coverage_baseline.json`.

## Tasks-domain glob (FR-009, committed definition)

```
tests/tasks/**
tests/specify_cli/cli/commands/agent/test_tasks*
+ every test file added by this mission (byte-freeze suite, gate tests)
```

## State transitions (per relocation WP)

```
freeze (byte-freeze + harness green on base)
  → move (cut family/shared/adapter set to sibling; add _tasks routing; keep tasks.py bindings)
  → re-point (coord-harness ratchet target for the moved orchestrator — same WP, FR-012)
  → verify (43 harness + 13 byte-freeze + family targeted tests + interception checks + mypy/ruff)
  → ratchet (lower the LOC ceiling to the new tasks.py size)
```

Any parity delta at "verify" → revert the move, never adjust a fixture (NFR-001(d)).

## Seam inventory (D7 table, research.md) — per-WP checklist source

23 distinct patched symbols / 367 sites; top traffic: `locate_project_root` ×66,
`_find_mission_slug` ×65, `_ensure_target_branch_checked_out` ×48. Each family WP copies
the rows whose symbols its move-set defines or calls, and checks: (a) `tasks.py` binding
present, (b) all relocated calls routed via `_tasks.<attr>`, (c) interception check for
defensively-patched seams, (d) `monkeypatch.setattr` sites for the same symbols swept.
