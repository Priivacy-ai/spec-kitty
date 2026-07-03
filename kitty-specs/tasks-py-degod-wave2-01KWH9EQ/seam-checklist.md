# Seam Checklist — tasks-py-degod-wave2-01KWH9EQ

The mission-wide Layer-4 evidence artifact (parity-contract Layer 4 / NFR-002).
WP02 created it; every family WP (WP05–WP08) APPENDS its rows in the same
format. Columns:

- **symbol** — the relocated def (or seam-surface binding).
- **tasks.py binding (line)** — the module-attribute binding in `tasks.py`
  post-move (re-import line, `__all__` declaration, or in-module definition).
- **routed-via-`_tasks`?** — whether the relocated body reaches its patched
  collaborators through the lazy `from specify_cli.cli.commands.agent import
  tasks as _tasks` bridge (and which attrs), per research.md D1/D7.
- **interception/identity test id** — the test in
  `tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py` proving the
  patch still BITES (interception) and/or the binding is the same object
  (identity). `identity` = the parametrized
  `test_tasks_binding_is_tasks_shared_object[<symbol>]` case (runs for EVERY
  row — listed explicitly only where it is the sole evidence).
- **monkeypatch sites swept** — `monkeypatch.setattr(tasks…, "<name>", …)`
  sites checked to still target a live, intercepting binding.

## WP02 — shared-helpers move-set (`tasks_shared.py`), 20 defs + 1 constant

Line numbers refer to `src/specify_cli/cli/commands/agent/tasks.py` at the
WP02 commit (re-import block lines 253–273).

| symbol | tasks.py binding (line) | routed-via-`_tasks`? | interception/identity test id | monkeypatch sites swept |
|---|---|---|---|---|
| `resolve_primary_branch` | 273 (re-import) | no seam calls (lazy `core.git_ops` import kept verbatim) | identity | none found |
| `_review_currency_check_branch` | 269 | yes: `resolve_placement_only`, `resolve_topology`, `routes_through_coordination` | `test_patched_topology_symbols_intercept_review_currency_branch` | `tasks_mod, "resolve_topology"` ×3 + `routes_through_coordination` ×2 (test_move_task_orchestration) — bite via `_tasks.` route |
| `_RUNTIME_STATE_DENY_LIST` | 253 | n/a (constant; moved with its only consumer) | identity | none; 1 direct test import from `tasks` kept working |
| `_filter_runtime_state_paths` | 259 | no seam calls (`_is_dossier_snapshot` direct import — 0 patch sites) | identity | none found |
| `_emit_sparse_session_warning` | 256 | no seam calls (self-contained lazy import) | identity; ×13 `@patch` sites target the binding, callers stay in `tasks.py` | none found |
| `_ensure_target_branch_checked_out` | 257 | yes: `get_main_repo_root`, `console` | `test_patched_get_main_repo_root_intercepts_ensure_target_branch` | none in module form; ×48 `@patch` sites target the binding |
| `_find_mission_slug` | 260 | yes: `get_main_repo_root`, `console` | `test_patched_get_main_repo_root_intercepts_find_mission_slug` | `tasks_mod, "_find_mission_slug"` ×1 — binding, bites |
| `_output_result` | 266 | yes: `console` | `test_patched_console_intercepts_output_result` | none found |
| `_output_error` | 265 | yes: `console` | `test_patched_console_intercepts_output_error` | none found |
| `_protected_branch_status_commit_error` | 267 | yes: `ProtectionPolicy` | `test_patched_protection_policy_intercepts_protected_branch_error` | none found; ×4 `@patch("…tasks.ProtectionPolicy.resolve")` bite via `_tasks.ProtectionPolicy` |
| `_coord_topology_active` | 255 | no seam calls (lazy coordination/lanes imports kept verbatim) | `test_patched_coord_topology_intercepts_skip_target_branch_commit` (as patch target) | none found |
| `_skip_target_branch_commit` (C-001) | 270 | yes: `_coord_topology_active` (moved sibling), `ProtectionPolicy` | `test_patched_coord_topology_intercepts_skip_target_branch_commit`, `test_patched_protection_policy_intercepts_skip_target_branch_commit` | none found; caller wiring in move_task family untouched (C-001) |
| `_mission_identity_payload` | 264 | no seam calls (`resolve_mission_identity` direct — 0 patch sites) | identity | none found |
| `_resolve_git_common_dir` | 268 | yes: `subprocess` | `test_patched_subprocess_intercepts_resolve_git_common_dir` | none; `test_review_feedback_pointer_2x_unit.py` patches `tasks.subprocess.run` around it — bites |
| `_check_unchecked_subtasks` | 254 | yes: `get_main_repo_root` (`resolve_planning_read_dir` direct — 0 patch sites) | `test_patched_get_main_repo_root_intercepts_check_unchecked_subtasks` | `tasks_module, "_check_unchecked_subtasks"` ×1 — binding, bites |
| `_validate_ready_for_review` | 271 | yes (all injected collaborators): `get_main_repo_root`, `get_mission_type`, `get_feature_target_branch`, `resolve_workspace_for_wp`, `_review_currency_check_branch`, `_behind_commits_touch_only_planning_artifacts`, `_filter_runtime_state_paths`, `_list_wp_branch_specs_changes_for_guard`, `console` | `test_patched_get_main_repo_root_intercepts_validate_ready_for_review` | `tasks_module, "_validate_ready_for_review"` ×2 — binding, bites |
| `_wp_branch_merged_into_target` | 272 | yes: `resolve_workspace_for_wp`, `subprocess` | `test_patched_workspace_and_subprocess_intercept_wp_branch_merged` | `tasks_module, "_wp_branch_merged_into_target"` ×1 — binding, bites |
| `_filter_by_planning_tip_content` | 258 | yes: `subprocess` | `test_patched_filter_intercepts_list_wp_branch_changes` (as patch target) | none found |
| `_list_wp_branch_mission_specs_changes` | 261; dynamic alias re-assigned at 491 | yes: `subprocess`, `_filter_by_planning_tip_content` (moved sibling) | `test_patched_filter_intercepts_list_wp_branch_changes` | none found |
| `_list_wp_branch_specs_changes_for_guard` | 262 | yes: dynamic-alias lookup via `getattr(_tasks, "_list_wp_branch_" + KITTY_SPECS_DIR… )` — reads the LIVE `tasks` namespace so `tasks._list_wp_branch_kitty_specs_changes` patches (test_tasks.py ×2) keep intercepting | `test_patched_kitty_specs_alias_intercepts_guard`, `test_kitty_specs_dynamic_alias_bound_in_tasks_namespace` | none found |
| `_mark_status_json_payload` | 263 | no seam calls (pure payload builder) | identity | none found |

Full-battery pins (all rows): `test_tasks_binding_is_tasks_shared_object`
(parametrized over the 21-row move-set) and
`test_move_set_matches_tasks_shared_public_defs` (completeness guard — a def
added to `tasks_shared` without a checklist/battery row goes RED).

### D7 infra symbols with a caller in the WP02 move-set (bindings retained in `tasks.py`)

| symbol | tasks.py binding (line) | notes |
|---|---|---|
| `locate_project_root` | 56 (import) | NO relocated WP02 caller (all callers are command bodies remaining in `tasks.py`); interception through a live command pinned by `test_patched_locate_project_root_intercepts_list_tasks_command` (top D7 symbol, ×66) |
| `get_main_repo_root` | 57 (`as` re-export) | direct callers all moved; D7 ×15 — routed back via `_tasks.` |
| `get_feature_target_branch` | 58 (`as` re-export) | D7 ×3 — collaborator injection route |
| `get_mission_type` | 60 (`as` re-export) | D7 ×26 — collaborator injection route |
| `resolve_placement_only` | 68 (`as` re-export) | patched ×1 (`test_tasks.py:1130`) — `_review_currency_check_branch` route |
| `resolve_topology` / `routes_through_coordination` | 69–70 (import) + `__all__` | still called directly by `_primary_bundle_status_artifacts` (move_task family, stays until WP06) AND routed by `_review_currency_check_branch` |
| `resolve_workspace_for_wp` | 79 (import) + `__all__` | D7 ×3 |
| `subprocess` | 26 (import) + `__all__` | D7 ×2; also used directly by staying family helpers |
| `console` | 372 (module def) | D7 ×5; stays a `tasks.py`-owned object — relocated bodies print via `_tasks.console` |
| `ProtectionPolicy` | 74 (import) + `__all__` | ×4 `@patch("…tasks.ProtectionPolicy.resolve")`; also called directly by staying family code (`_mt_commit_wp_file`, `_ms_commit`, `_mr_auto_commit`) |

### T007 partition record — single-family helpers NOT in the move-set (call-site evidence)

Left in `tasks.py` for their family WP; each has callers in exactly ONE family:

| symbol | family | call sites (pre-move tasks.py) |
|---|---|---|
| `_map_requirements_feature_dir` | map_requirements | `_mr_resolve_read_dirs` ×1 |
| `_review_stall_threshold_minutes` | status | `_st_apply_review_flags` ×1 |
| `_get_hic_marker` | status | `_st_board_cell` + `_st_render_*` ×8 |
| `_primary_bundle_status_artifacts` | move_task | `_mt_commit_wp_file` ×1 |
| `_coord_status_events_path` | move_task | `_mt_output` ×1 |
| `_status_event_result_fields` | move_task | `_mt_output` ×1 |
| `_detect_reviewer_name` | move_task | `_mt_approval_facts` ×1 (module patched: `tasks_module, "_detect_reviewer_name"` ×2 + `tasks.subprocess.run` — unaffected, def did not move) |
| `_apply_stale_status_fields` | status | `_st_emit_json`, `_st_render_human` ×2 |
| `_render_stale_status` | status | `_st_render_active` ×1 |
| `_detect_arbiter_override` | move_task | `_mt_gather_late_facts` ×1 |
| `_run_arbiter_override` | move_task | `_mt_gather_late_facts` ×1 |
| `_resolve_inline_subtasks` | mark_status | `_ms_apply_updates` ×1 |

Notes:
- `_mark_status_json_payload` is ms-family by call sites (×2) but is named in
  the data-model/T007 move-set explicitly — included per plan authority; its
  callers keep the bare-name call in `tasks.py` (binding via re-import).
- `_get_latest_review_cycle_verdict` / `_self_review_fallback_option_error`
  are Wave-1 residents of `tasks_parsing_validation.py` (D7a) — NOT moved;
  the `tasks.py` re-import of `_get_latest_review_cycle_verdict` was made an
  explicit `as` re-export (WP02 mypy campsite fold).
- `SPEC_MD_FILENAME` / `UTC_SECOND_TIMESTAMP_FORMAT` stay in `tasks.py`: no
  WP02-moved def references them (users: mr family, mt family, `add_history`).

## WP03 — coord-router adapters move-set (`tasks_command_adapters.py`), 3 classes

Line numbers refer to `src/specify_cli/cli/commands/agent/tasks.py` at the
WP03 commit (re-import block lines 264–268; seam-symbol `as` re-exports at 47
and 86). Patch-site census: `grep -rn "CoordRouter" tests/` finds NO
`@patch`/`monkeypatch` site targeting the router class names themselves — all
class references are direct imports/constructions; the patched collaborators
are the two seam symbols the method bodies route via `_tasks.<attr>`.

| symbol | tasks.py binding (line) | routed-via-`_tasks`? | interception/identity test id | monkeypatch sites swept |
|---|---|---|---|---|
| ~~`_MoveTaskCoordRouter`~~ | ~~267 (re-import)~~ | **SUPERSEDED** (degod-follow-ups constructor-DI collapse, #2308): subclass deleted; move_task now builds the router via `tasks.seam_coord_router(route_emit=True)`, whose injected wrappers route BOTH `emit_status_transition_transactional` and `commit_for_mission` via `_tasks.<attr>` at call time. Late binding + identity pins preserved (`test_move_task_orchestration.py` `seam_coord_router(route_emit=True)`; `test_tasks_move_task_seam.py` patches `tasks.seam_coord_router`). See design-decisions.md #13. |
| ~~`_MapReqCoordRouter`~~ | ~~265 (re-import)~~ | **SUPERSEDED** (constructor-DI collapse, #2308): subclass deleted; map_requirements builds via `tasks.seam_coord_router(thread_target_branch=True, target_branch=…)` — the `target_branch` threading (C-001) is now a constructor flag, not a subclass override. T030 pin retained (`test_tasks_core_backed_orchestration.py` asserts `target_branch="wip-lane"` through the same `_tasks.commit_for_mission` route). See design-decisions.md #13. |
| ~~`_MarkStatusCoordRouter`~~ | ~~266 (re-import)~~ | **SUPERSEDED** (constructor-DI collapse, #2308): subclass deleted; mark_status builds via `tasks.seam_coord_router()` (commit-seam routing only, NO `target_branch`, base emitter binding). T033 no-`target_branch` byte-parity pin retained (`test_tasks_coreless_orchestration.py`). See design-decisions.md #13. |

WP03 notes:
- `_StatusRender` NOT moved (WP04 deletes it per D2); `_default_*_ports`
  factories stay in `tasks.py` until their family WPs (WP06–WP08).
- No-cycle proof: `tasks_command_adapters` imports at module scope only
  `collections.abc`/`pathlib` (stdlib), `mission_runtime`,
  `specify_cli.agent_tasks_ports`, `specify_cli.core.commit_guard`,
  `specify_cli.git.protection_policy`, `specify_cli.status` — none import
  `specify_cli.cli.commands.agent.*`; the only edge back to `tasks` is the
  lazy in-method D1 bridge. Proven by pytest collection/execution of the full
  parity guard (61 passed) importing `tasks` → `tasks_command_adapters`.

## WP04 — render-seam unification (`RealRender` indent param), 1 new binding row

Line numbers refer to `src/specify_cli/cli/commands/agent/tasks.py` at the
WP04 commit (`c4056907f`). Patch-site census: `grep -rn "RealRender" tests/`
finds NO `@patch`/`monkeypatch` site targeting `RealRender` itself; the render
seam is exercised through stdout byte assertions (the 13-case freeze suite),
so interception evidence is byte-level, not mock-level.

| symbol | tasks.py binding (line) | routed-via-`_tasks`? | interception/identity test id | monkeypatch sites swept |
|---|---|---|---|---|
| `RealRender` | 247 (direct import from `agent_tasks_ports`, exported via `__all__` per C-007) | yes — the 3 `tasks_shared.py` emission helpers (`_find_mission_slug`, `_output_result`, `_output_error`) default their keyword-only `render` seam to `_tasks.RealRender()`, so a future `@patch("…tasks.RealRender")` bites; the 9 in-`tasks.py` compact sites construct a local `render = RealRender()` from the same module binding | `test_tasks_ports.py::test_real_render_default_is_compact_bytes` + `::test_real_render_indent_two_is_indented_bytes` (T016 adapter identity); `test_tasks_json_bytes.py` 13-case suite green at every subtask (byte interception proof); `test_tasks_ports.py::test_default_ports_builds_real_bundle` (bundle identity) | none found (`RealRender` grep: 0 monkeypatch sites) |

WP04 notes:
- `_StatusRender` DELETED (D2): `_default_status_ports` now builds
  `RealRender(console=console, indent=2)` — the ONE production adapter,
  constructor-configured (C-004). Deleted-symbol re-points (all prose, no code
  references existed): `test_tasks_json_bytes.py` module docstring and the
  historical mention in the WP03 notes above; the freeze-time fixture label in
  `byte_contracts.json:40` is immutable and keeps the old name.
- `json` import removed from `tasks_shared.py` and `Mapping`
  (`collections.abc`) import removed from `tasks.py` — both dead after the
  routing (ruff F401 guard).

## WP05 — move_task family move-set (`tasks_move_task.py`), 26 defs

Line numbers refer to `src/specify_cli/cli/commands/agent/tasks.py` at the WP05
commit (re-import block lines 609–636; seam-symbol `as` re-exports:
`primary_feature_dir_for_mission` :21, `_collect_status_artifacts` :133,
`decide_transition` :182). Patch-site census: NO `@patch`/`monkeypatch` site
targets a moved family symbol itself (`grep "_mt_\|_do_move_task\|_MoveTaskState\|_default_move_task_ports"`
over `tests/`: the only direct references are `test_move_task_orchestration.py:33`'s
import of `_do_move_task` from `tasks` — binding identity — and the coreless-gate
entry list); the patched collaborators are the D7 seam symbols the bodies route
via `_tasks.<attr>`. Interception/identity battery:
`tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py`
(`identity` = `test_tasks_binding_is_tasks_move_task_object[<symbol>]`, runs for
EVERY row; completeness pinned by `test_move_set_matches_tasks_move_task_defs`).

| symbol | tasks.py binding (line) | routed-via-`_tasks`? | interception/identity test id | monkeypatch sites swept |
|---|---|---|---|---|
| `_default_move_task_ports` | 611 (re-import) | yes: `_MoveTaskCoordRouter`, `RealFsReader`, `RealGitOps`, `RealRender` (construction via `tasks` bindings — WP03 checklist invariant preserved) | `test_default_ports_constructs_through_tasks_bindings` | none found |
| `_MoveTaskState` | 610 | n/a (dataclass; type-only refs) | identity | none found |
| `_mt_warn_worktree_kitty_specs` | 635 | yes: `console` (`is_worktree_context`/`KITTY_SPECS_DIR` direct — 0 patch sites) | identity; untrusted-path inventory row follows this body (tasks_move_task.py:204) | none found |
| `_mt_resolve_targets` | 633 | yes: `locate_project_root` (×67), `_emit_sparse_session_warning` (×13), `get_auto_commit_default` (×7), `_find_mission_slug` (×66), `_ensure_target_branch_checked_out` (×50), `_skip_target_branch_commit` (C-001 pre-gate, original flow position), `_protected_branch_status_commit_error`, `_output_error`, `locate_work_package` (×16) (`ensure_lane`/`extract_scalar`/`check_pre30_layout`/`_read_transactional_wp_lane`/`_self_review_fallback_option_error` direct — 0 patch sites) | `test_c001_pre_gate_intercepts_through_tasks_namespace` + `test_c001_pre_gate_not_consulted_when_auto_commit_resolves_false`; full-flow evidence: coord harness T004 skip-arm + wrong-leg detector green | none found |
| `_mt_resolve_feedback` | 632 | no seam calls | identity | none found |
| `_mt_build_request` | 614 | no seam calls (`MoveTaskRequest` direct — 0 patch sites) | identity | none found |
| `_mt_gather_review_facts` | 624 | yes: `_check_unchecked_subtasks` (×12), `_validate_ready_for_review` (×12) (`_get_latest_review_cycle_verdict` direct — 0 patch sites) | `test_patched_review_gates_intercept_gather_review_facts` | none found |
| `_mt_fire_override_persist` | 622 | no seam calls (`override_persist_signal`, `_persist_review_artifact_override`, `_persist_review_artifact_override_in_coord` direct — 0 patch sites) | identity | none found |
| `_mt_done_ancestry_facts` | 617 | yes: `resolve_workspace_for_wp` (×3), `_wp_branch_merged_into_target` (×2) | `test_patched_workspace_and_ancestry_intercept_done_facts` | `tasks_module, "_wp_branch_merged_into_target"` ×1 — targets the WP02 binding, bites via this route |
| `_mt_issue_matrix_facts` | 627 | yes: `primary_feature_dir_for_mission` (×1, test_pre30_guard_wiring:342) (`_canonicalize_primary_read_handle`, `_issue_matrix_approval_blocker` direct — 0 patch sites; C-002 co-location preserved) | `test_patched_primary_feature_dir_intercepts_issue_matrix_facts` | none found |
| `_mt_approval_facts` | 613 | yes: `_detect_reviewer_name` (def stays in tasks.py) | `test_patched_detect_reviewer_intercepts_approval_facts` | `tasks_module, "_detect_reviewer_name"` ×2 — def did not move, bites via this route |
| `_mt_gather_late_facts` | 623 | yes: `_detect_arbiter_override` (def stays in tasks.py) (`replace`/`resolve_lane_alias` direct — 0 patch sites) | identity; drive-through evidence: arbiter-override cases in coord/contract harnesses green | none found |
| `_mt_fire_arbiter_persist` | 621 | yes: `_run_arbiter_override` (def stays in tasks.py) (`arbiter_persist_signal`/`_effective_note_text` direct — 0 patch sites) | identity; drive-through evidence: T006 arbiter scenario green | none found |
| `_mt_run_decision` | 634 | yes: `decide_transition` (monkeypatch ×2, sentinel tests test_tasks_transition_core.py:682/:723), `console`, `_output_error` | `test_patched_decide_transition_intercepts_run_decision`; sentinel tests green post-move | `tasks_module, "decide_transition"` ×2 — bites via this route |
| `_mt_finalize_plan` | 620 | yes: `console` (`build_transition_plan`/`_resolve_wp_slug` direct — 0 patch sites; `create_rejected_review_cycle` lazy import kept verbatim) | identity | none found |
| `_mt_current_event_lane` | 616 | yes: `read_events_transactional` (×9) | `test_patched_read_events_intercepts_current_event_lane` | none found |
| `_mt_hop_review_result` | 626 | no seam calls | identity | none found |
| `_mt_hop_actor` | 625 | no seam calls (`resolve_lane_alias` direct — 0 patch sites) | identity | none found |
| `_mt_emit_transitions` | 618 | no seam calls (ports-injected `commit_status`; `GuardCapability`/`TransitionRequest` direct — 0 patch sites); the coord WRITE seam stays interceptable because `_default_move_task_ports` constructs `_tasks._MoveTaskCoordRouter`, whose body routes `emit_status_transition_transactional` (×13) via `_tasks.` (WP03 rows) | identity; `test_atomic_status_commits_unit.py` paired patches green post-move | none found |
| `_mt_commit_wp_file` | 615 | yes: `console`, `_primary_bundle_status_artifacts` (def stays in tasks.py), `ProtectionPolicy` (×4 `@patch("…tasks.ProtectionPolicy.resolve")`) (`write_text_within_directory`/`_collect_status_artifacts` direct — 0 patch sites; `_collect_status_artifacts` keeps a tasks.py `as` re-export at :133 for workflow.py/implement.py/test imports) | `test_patched_protection_policy_intercepts_commit_wp_file` | none found |
| `_mt_persist_tracker_refs` | 629 | yes: `console` (lazy frontmatter/status imports kept verbatim) | `test_patched_console_intercepts_tracker_ref_warning` | none found |
| `_mt_persist_wp_file` | 630 | yes: `UTC_SECOND_TIMESTAMP_FORMAT` (tasks.py-owned constant) (`split_frontmatter`/`set_scalar`-family + `append_activity_log`/`build_document`/`write_text_within_directory` direct — 0 patch sites) | identity; byte-level evidence: wp_file_write coord case green | none found |
| `_mt_release_review_lock` | 631 | yes: `resolve_workspace_for_wp` (×3) (`ReviewLock` lazy import kept verbatim) | identity; drive-through: coord harness review flows green | none found |
| `_mt_execute` | 619 | yes: `feature_status_lock` (×23) (`emit_reviewer_self_approval` lazy import kept verbatim) | `test_patched_feature_status_lock_intercepts_execute` | none found |
| `_mt_output` | 628 | yes: `_status_event_result_fields`, `_coord_status_events_path` (defs stay in tasks.py), `_output_result`, `_check_dependent_warnings` (×1 monkeypatch) | `test_patched_output_helpers_intercept_mt_output` | `tasks…, "_check_dependent_warnings"` ×1 — targets the re-import binding, bites via this route |
| `_do_move_task` | 612 (re-import; `move_task` wrapper calls this module-global — patchable as `tasks._do_move_task`) | yes: `emit_error_logged` (×3), `_output_error` (`emit_error_logged` exception arm; `EventPersistenceError` direct — 0 patch sites) | identity; `test_move_task_orchestration.py:33` direct import from `tasks` (binding identity) + fake-ports drives green post-move | none found |

WP05 notes:
- **C-001 divergence wiring**: the `_skip_target_branch_commit` pre-gate call sits at
  its ORIGINAL position in `_mt_resolve_targets` (post branch-resolution, gated on
  `resolved_auto_commit`, pre protected-branch refusal and event-log read); coord
  harness T004 (skip-exit-0 + wrong-leg detector) green, unmodified.
- No-cycle proof: `tasks_move_task` imports at module scope only stdlib,
  `mission_runtime`, `specify_cli.agent_tasks_ports`, `core.*`, `git`, `status`,
  `task_utils`, `upgrade.pre30_guard`, `missions._read_path_resolver` and the
  sibling seam modules (`tasks_finalize_validation`, `tasks_materialization`,
  `tasks_parsing_validation`, `tasks_transition_core`) — none import
  `specify_cli.cli.commands.agent.tasks`; the only edge back is the lazy
  in-function D1 bridge.
- Dead-import cleanup in `tasks.py` (F401 sweep, 0 external references verified per
  symbol): `replace`, `ReviewResult`, `TransitionRequest`, `EventPersistenceError`,
  `is_worktree_context`, `SafeCommitPathPolicyError`, `write_text_within_directory`,
  `ensure_lane`, `set_scalar`, `WorkPackage`, `GuardCapability`,
  `CommitArtifactResult`, `Emit`, `TransitionPlan`, `MoveTaskRequest`,
  `RefuseExit1`, `_effective_note_text`, `arbiter_persist_signal`,
  `build_transition_plan`, `override_persist_signal`,
  `_persist_review_artifact_override`, `_self_review_fallback_option_error`,
  `_read_transactional_wp_lane`, `_canonicalize_primary_read_handle`.
  (`_resolve_wp_slug` / `_issue_matrix_approval_blocker` are NOT dead — kept
  as explicit `as` re-exports because `tests/agent/cli/commands/test_tasks_helpers.py`
  imports both from `tasks`; caught by the post-sweep AST import audit.)
- Strict-mypy fold: the 8 D7 seam symbols the family routes via `_tasks.<attr>`
  (`locate_project_root`, `locate_work_package`, `get_auto_commit_default`,
  `feature_status_lock`, `read_events_transactional`, `emit_error_logged`,
  `RealFsReader`, `RealGitOps`) converted to explicit `as` re-export form in
  `tasks.py` (strict no-implicit-reexport; WP02 precedent).
- FR-012 ratchet re-point (T024): `_FLOORED_FUNCTION_HOMES` multi-home map
  (entry + wave-1-extracted pure cores = the calibrated single-body basis;
  `map_requirements` reproduces the calibrated arc universe 106-vs-104), vacuous
  `else 100.0` arm replaced by `pytest.fail` on 0 arcs; floors untouched; RED
  fire demonstrated (see WP05 Activity Log).

## WP06 — map_requirements family move-set (`tasks_map_requirements.py`), 14 defs

Line numbers refer to `src/specify_cli/cli/commands/agent/tasks.py` at the WP06
commit (re-import block lines 676–691; seam-symbol `as` re-exports:
`plan_mapping` :210; `SPEC_MD_FILENAME` stays a tasks.py-owned constant at
:338, routed via `_tasks.<attr>`). Patch-site census (incl. multiline patch
strings, the WP05 lesson): NO `@patch`/`monkeypatch` site targets a moved
family symbol itself (`grep "_mr_\|_do_map_requirements\|_MapReqState\|_default_map_requirements_ports"`
over `tests/`: the only direct reference is
`test_tasks_core_backed_orchestration.py`'s import of `_do_map_requirements` /
`_MapReqCoordRouter` from `tasks` — binding identity — and the coreless-gate
entry list); the patched collaborators are the D7 seam symbols the bodies
route via `_tasks.<attr>`. The census caught the `plan_mapping` sentinel
(`monkeypatch.setattr(tasks_module, "plan_mapping", …)` ×2,
test_tasks_mapping_core.py:307/:341) and the `_map_requirements_feature_dir`
patch (tests/upgrade/test_pre30_guard_wiring.py:104) as routed seams.
Interception/identity battery:
`tests/specify_cli/cli/commands/agent/test_tasks_map_requirements_seam.py`
(`identity` = `test_tasks_binding_is_tasks_map_requirements_object[<symbol>]`,
runs for EVERY row; completeness pinned by
`test_move_set_matches_tasks_map_requirements_defs`).

| symbol | tasks.py binding (line) | routed-via-`_tasks`? | interception/identity test id | monkeypatch sites swept |
|---|---|---|---|---|
| `_default_map_requirements_ports` | 678 (re-import) | yes: `_MapReqCoordRouter` (carries resolved `target_branch`), `RealFsReader`, `RealGitOps`, `RealRender` (construction via `tasks` bindings — WP03 checklist invariant preserved) | `test_default_ports_constructs_through_tasks_bindings` | none found |
| `_MapReqState` | 677 | n/a (dataclass; `CommitTarget`/`MappingPlan`/`CoverageSummary` type refs direct — 0 patch sites) | identity | none found |
| `_mr_validate_modes` | 689 | yes: `_output_error` (×3 legs) | `test_patched_output_error_intercepts_validate_modes` | none found |
| `_mr_resolve_context` | 685 | yes: `locate_project_root` (×67), `_emit_sparse_session_warning` (×13), `_find_mission_slug` (×66), `_ensure_target_branch_checked_out` (×50), `get_auto_commit_default` (×7), `_protected_branch_status_commit_error` (C-001 REFUSE arm — NO `_skip_target_branch_commit` pre-gate, wiring moved untouched), `_output_error` (`_resolve_planning_placement` lazy commit_router import kept verbatim — canonical-home patches ×3 bite) | `test_c001_refuse_arm_intercepts_through_tasks_namespace` + `test_c001_protected_gate_not_consulted_when_auto_commit_resolves_false`; full-flow evidence: coord harness refuse-arm case (harness label T005) green | none found |
| `_mr_build_new_mappings` | 681 | yes: `_output_error` (×4 legs) | `test_patched_output_error_intercepts_build_new_mappings_bad_json` | none found |
| `_mr_unknown_wp_gate` | 688 | yes: `RealRender` (json leg), `console` (human leg) (`re` direct — 0 patch sites) | `test_patched_console_intercepts_unknown_wp_gate_human_leg`, `test_patched_render_intercepts_unknown_wp_gate_json_leg` | none found |
| `_mr_resolve_read_dirs` | 686 | yes: `_map_requirements_feature_dir` (×1, test_pre30_guard_wiring:104; def stays in tasks.py — T007 partition record), `SPEC_MD_FILENAME` (tasks.py-owned constant), `_output_error` (`check_pre30_layout`/`resolve_planning_read_dir`/`MissionHandle` direct — 0 patch sites; ports-injected `fs.primary_anchor_dir` fold preserved) | `test_patched_map_requirements_feature_dir_intercepts_resolve_read_dirs` | none found |
| `_mr_plan` | 684 | yes: `plan_mapping` (monkeypatch ×2, sentinel tests test_tasks_mapping_core.py:307/:341) (`read_all_wp_requirement_refs`/`_parse_requirement_refs_from_tasks_md` lazy imports kept verbatim; `TRACKER_ONLY_MODE`/`MappingRequest` direct — 0 patch sites) | `test_patched_plan_mapping_intercepts_mr_plan`; sentinel tests green post-move | `tasks_module, "plan_mapping"` ×2 — targets the :210 re-export binding, bites via this route |
| `_mr_gate_offenders` | 683 | yes: `RealRender` (json legs ×2), `console` (human legs) | identity; drive-through evidence: malformed-ref + unknown-spec-ids byte-freeze cases green | none found |
| `_mr_write_frontmatter` | 690 | no seam calls (lazy `write_frontmatter`/`read_wp_frontmatter` imports kept verbatim — 0 patch sites) | identity | none found |
| `_mr_stale_gate` | 687 | yes: `RealRender` (json leg), `console` (human leg) (lazy `classify_stale_refs`/`read_all_wp_raw_requirement_refs`/`validate_ref_format`/`validate_refs` imports kept verbatim — 0 patch sites) | `test_patched_render_intercepts_stale_gate_json_leg`; byte-level evidence: stale-frontmatter byte-freeze case green | none found |
| `_mr_auto_commit` | 680 | yes: `ProtectionPolicy` (×4 `@patch("…tasks.ProtectionPolicy.resolve")`), `console` (warning leg) (ports-injected `commit_artifact`; `MissionHandle`/`MissionArtifactKind` direct — 0 patch sites) | `test_patched_protection_policy_intercepts_auto_commit`, `test_patched_console_intercepts_auto_commit_warning` | none found |
| `_mr_emit_output` | 682 | yes: `_mission_identity_payload`, `RealRender` (json leg), `console` (human legs) (lazy `read_all_wp_requirement_refs` import kept verbatim) | `test_patched_identity_payload_intercepts_emit_output`; byte-level evidence: `--json` success byte-freeze case green | none found |
| `_do_map_requirements` | 679 (re-import; `map_requirements` wrapper calls this module-global — patchable as `tasks._do_map_requirements`) | yes: `_output_error` (generic exception arm); phase siblings reached by bare same-module name (the ratchet-closure invariant — deliberately NOT patch targets) | identity; `test_patched_output_error_intercepts_do_map_requirements_exception_arm` + `test_tasks_core_backed_orchestration.py` direct import from `tasks` (binding identity) green post-move | none found |

WP06 notes:
- **C-001 divergence wiring (REFUSE arm)**: `map_requirements` refuses exit-1
  through `_tasks._protected_branch_status_commit_error` inside
  `_mr_resolve_context` at its ORIGINAL position (post placement-resolution,
  gated on `auto_commit_on`) with NO `_skip_target_branch_commit` skip
  pre-gate (that pre-gate is `move_task`-only); the seam battery pins
  `skip_mock.assert_not_called()` and the coord harness refuse-arm case
  (harness label T005) is green, unmodified.
- No-cycle proof: `tasks_map_requirements` imports at module scope only stdlib,
  `kernel._safe_re`, `typer`, `mission_runtime`, `specify_cli.agent_tasks_ports`,
  `missions._read_path_resolver`, `requirement_mapping`, `upgrade.pre30_guard`
  and the sibling seam modules (`tasks_mapping_core`, `tasks_outline`) — none
  import `specify_cli.cli.commands.agent.tasks`; the only edge back is the lazy
  in-function D1 bridge.
- Dead-import cleanup in `tasks.py` (F401 sweep, 0 external references verified
  per symbol incl. multiline patch strings): `TRACKER_ONLY_MODE`, `MappingPlan`,
  `MappingRequest`, `CoverageSummary`, `CommitTarget`, `json`, `re`
  (kernel._safe_re). (`plan_mapping` is NOT dead — kept as an explicit `as`
  re-export for its sentinel seam; `SPEC_MD_FILENAME` stays a tasks.py-owned
  constant routed via `_tasks.<attr>`, the WP05 `UTC_SECOND_TIMESTAMP_FORMAT`
  precedent; `_MapReqCoordRouter`/`RealFsReader`/`RealGitOps`/`RealRender`
  bindings stay live for the ports-construction seam.)
- FR-012 ratchet re-point (T029): `map_requirements` ENTRY home re-pointed
  `(tasks, "_do_map_requirements")` → `(tasks_map_requirements,
  "_do_map_requirements")` in the WP05-built multi-home map; the wave-1
  pure-core home (`tasks_mapping_core`, `plan_mapping`) KEPT; `include=` set
  derives from the map (new module verified inside the analyze wiring by a
  real measured %, not a 0-arc hard fail); floors byte-identical 65/48/46;
  RED fire demonstrated: shortfall `{'map_requirements': (49.1, 90.0)}` with
  the floor temporarily raised 48.0→90.0 then restored (see WP06 Activity Log).

## WP07 — status family move-set (`tasks_status_cmd.py`), 17 defs

Line numbers refer to `src/specify_cli/cli/commands/agent/tasks.py` at the WP07
commit (re-import block lines 713–731; seam-symbol `as` re-exports:
`build_status_view` :223 (sentinel seam), `get_status_read_root` :79 (D7 ×3),
`RealCoordCommitRouter` :256 (ports-construction seam); the module is named
`tasks_status_cmd` — `_cmd` suffix — to stay distinct from the WP05 pure core
`tasks_status_view`). Patch-site census (incl. multiline patch strings, the
WP05 lesson): NO `@patch`/`monkeypatch` site targets a moved family symbol
itself (`grep "_st_\|_do_status\|_StatusState\|_default_status_ports"` over
`tests/`: the only direct references are `test_tasks_core_backed_orchestration.py`'s
import of `_do_status` from `tasks` — binding identity — and the coord-harness
ratchet entry, re-pointed in this WP); the patched collaborators are the D7
seam symbols the bodies route via `_tasks.<attr>`. The census caught the
`build_status_view` sentinel (`monkeypatch.setattr(tasks_module,
"build_status_view", …)` ×2, test_tasks_status_view.py:333/:352), the conftest
`console` rebinding (`monkeypatch.setattr(tasks_module, "console", …)`,
agent/conftest.py:81) and the `get_status_read_root` patches (×3:
test_tasks_2x_unit.py:73/:133 + multiline test_pre30_guard_wiring.py:74) as
routed seams. Interception/identity battery:
`tests/specify_cli/cli/commands/agent/test_tasks_status_cmd_seam.py`
(`identity` = `test_tasks_binding_is_tasks_status_cmd_object[<symbol>]`,
runs for EVERY row; completeness pinned by
`test_move_set_matches_tasks_status_cmd_defs`).

| symbol | tasks.py binding (line) | routed-via-`_tasks`? | interception/identity test id | monkeypatch sites swept |
|---|---|---|---|---|
| `_default_status_ports` | 715 (re-import) | yes: `RealFsReader`, `RealCoordCommitRouter`, `RealGitOps`, `RealRender(console=_tasks.console, indent=2)` (construction via `tasks` bindings — WP03 checklist invariant preserved; the ONE indent=2 envelope, WP04/C-004) | `test_default_ports_constructs_through_tasks_bindings` (pins `console=tasks.console, indent=2`); byte-level evidence: `status_success_indent2` byte-freeze case green | `tasks_module, "console"` conftest rebinding — bites (ports built at call time via `_tasks.console`) |
| `_StatusState` | 714 | n/a (dataclass; `StatusEvent`/`StatusSnapshot` type refs direct — 0 patch sites) | identity | none found |
| `_st_resolve_dirs` | 729 | yes: `locate_project_root` (×67), `_find_mission_slug` (×66), `_ensure_target_branch_checked_out` (×50), `get_status_read_root` (×3, incl. the multiline pre30-wiring site), `console` (error legs ×2) (`resolve_handle_to_read_path` lazy resolver import kept verbatim — canonical-home patches ×3 bite; `candidate_feature_dir_for_mission`/`resolve_planning_read_dir`/`MissionArtifactKind` direct — 0 tasks-path patch sites) | `test_patched_resolution_seams_intercept_resolve_dirs` | none found |
| `_st_resolve_execution_mode` | 730 | yes: `resolve_workspace_for_wp` (×3, the mocked-env fixture seam) (`extract_scalar`/`get_normalized_wp`/`MissingLanesError` direct — 0 patch sites) | `test_patched_workspace_resolver_intercepts_resolve_execution_mode` | none found |
| `_st_load_work_packages` | 720 | yes: `console` (no-WPs leg) (lazy `read_events`/`reduce` status imports kept verbatim; `split_frontmatter`/`extract_scalar`/`resolve_lane_alias`/`Lane` direct — 0 tasks-path patch sites) | `test_patched_console_intercepts_load_work_packages_empty_leg` | `tasks_module, "read_events"` ×1 (test_review_feedback_pointer_2x_unit.py:144) targets a NEVER-BOUND tasks attr for the move_task path — not a status seam; the status body's lazy `specify_cli.status` import is unchanged |
| `_st_apply_review_flags` | 717 | yes: `_review_stall_threshold_minutes` (tasks.py-resident, T007 partition record) (`_apply_review_status_flags` direct from `tasks_parsing_validation` — 0 patch sites) | `test_patched_stall_threshold_intercepts_apply_review_flags` | none found |
| `_st_emit_json` | 719 | yes: `build_status_view` (sentinel ×2), `get_auto_commit_default` (×9), `_apply_stale_status_fields` (tasks.py-resident), `_mission_identity_payload` (`check_doing_wps_for_staleness` lazy stale_detection import kept verbatim; `StatusRequest`/`PROGRESS_SEMANTICS`/`build_stale_fallback_results` direct — 0 patch sites; `print(ports.render.json_envelope(result))` moved verbatim) | `test_patched_sentinel_view_and_identity_drive_emit_json`; sentinel test `test_sentinel_view_drives_the_json_envelope` green post-move; byte-level evidence: `status_success_indent2` green | `tasks_module, "build_status_view"` ×2 — targets the :223 re-export binding, bites via this route |
| `_st_board_cell` | 718 | yes: `_get_hic_marker` (tasks.py-resident, ×8 family sites) | `test_patched_hic_marker_intercepts_board_cell` | none found |
| `_st_render_overview` | 725 | no seam calls (ports-injected `render.human`; lazy rich imports kept verbatim) | identity | none found |
| `_st_render_board` | 723 | no seam calls (`_st_board_cell` reached by bare same-module name — ratchet-closure invariant; lazy rich import kept verbatim) | identity | none found |
| `_st_render_arbiter` | 722 | no seam calls (lazy `get_arbiter_overrides_for_wp` review import kept verbatim — ImportError arm preserved) | identity | none found |
| `_st_render_review_queues` | 727 | yes: `_get_hic_marker` ×3 | identity | none found |
| `_st_render_active` | 721 | yes: `_get_hic_marker` ×3, `_render_stale_status` (tasks.py-resident, T007 partition record) | `test_patched_stale_label_intercepts_render_active` | none found |
| `_st_render_planned` | 726 | yes: `_get_hic_marker` ×1 | identity | none found |
| `_st_render_summary` | 728 | yes: `get_auto_commit_default` (lazy rich imports kept verbatim) | `test_patched_auto_commit_intercepts_render_summary` | none found |
| `_st_render_human` | 724 | yes: `build_status_view` (sentinel ×2), `_apply_stale_status_fields` (lazy `check_doing_wps_for_staleness` + `AgentProfileRepository` imports kept verbatim; render siblings reached by bare same-module name) | `test_patched_sentinel_view_drives_render_human`; sentinel test `test_sentinel_view_drives_the_human_summary` green post-move | `tasks_module, "build_status_view"` ×2 — bites via this route |
| `_do_status` | 716 (re-import; `status` wrapper calls this module-global — patchable as `tasks._do_status`) | yes: `_output_error` (generic exception arm); phase siblings reached by bare same-module name (the ratchet-closure invariant — deliberately NOT patch targets) | identity; `test_patched_output_error_intercepts_do_status_exception_arm` + `test_tasks_core_backed_orchestration.py` direct import from `tasks` (binding identity) green post-move | none found |

WP07 notes:
- **Indent=2 byte tripwire**: the `_default_status_ports` →
  `RealRender(console=console, indent=2)` construction (WP04's one-adapter
  fold) moved as-is; the `status --json` emission
  (`print(ports.render.json_envelope(result))`) moved verbatim inside
  `_st_emit_json`. The WP01 `status_success_indent2` byte-freeze case ran
  green after every subtask, fixtures unmodified.
- No-cycle proof: `tasks_status_cmd` imports at module scope only stdlib,
  `typer`, `mission_runtime`, `specify_cli.agent_tasks_ports`,
  `missions._read_path_resolver`, `specify_cli.status`, `specify_cli.task_utils`,
  `lanes.persistence`, `workspace.context` and the sibling seam modules
  (`tasks_parsing_validation`, `tasks_status_view`) — none import
  `specify_cli.cli.commands.agent.tasks`; the only edge back is the lazy
  in-function D1 bridge.
- Dead-import cleanup in `tasks.py` (F401 sweep, 0 external references verified
  per symbol incl. multiline patch strings): `Any` (typing), `StatusEvent`,
  `PROGRESS_SEMANTICS`, `resolve_lane_alias`, `MissingLanesError`,
  `get_normalized_wp`, `StatusRequest`, `StatusView`,
  `build_stale_fallback_results`, `StatusSnapshot`. (`build_status_view` is
  NOT dead — kept as an explicit `as` re-export for its sentinel seam;
  `get_status_read_root` kept for its D7 patch seam ×3;
  `RealCoordCommitRouter` converted to the explicit `as` form for the
  ports-construction seam + its remaining `_default_finalize_ports` caller;
  `_review_stall_threshold_minutes`/`_get_hic_marker`/`_apply_stale_status_fields`/
  `_render_stale_status` stay tasks.py-owned per the T007 partition record,
  routed via `_tasks.<attr>`.)
- FR-012 ratchet re-point (T033): `status` ENTRY home re-pointed
  `(tasks, "_do_status")` → `(tasks_status_cmd, "_do_status")` in the
  WP05-built multi-home map; the wave-1 pure-core homes (`tasks_status_view`,
  `build_status_view` / `build_stale_fallback_results`) KEPT; `include=` set
  derives from the map (new module verified inside the analyze wiring by a
  real measured %, not a 0-arc hard fail); floors byte-identical 65/48/46;
  RED fire demonstrated: shortfall `{'status': (51.7, 90.0)}` with the floor
  temporarily raised 46.0→90.0 then restored (see WP07 Activity Log).

## WP08 — mark_status family move-set (`tasks_mark_status.py`)

Per-symbol rows for the WP08 mark_status relocation (12 symbols). Patch-site
census swept `@patch("...agent.tasks.<sym>")`, `monkeypatch.setattr(tasks*,
"<sym>")` AND multiline/concatenated patch strings across `tests/` before
routing each symbol; tasks.py-resident collaborators
(`_resolve_inline_subtasks` — T007-partition analogue) stay behind
routed seams. Interception/identity battery:
`tests/specify_cli/cli/commands/agent/test_tasks_mark_status_seam.py`
(`identity` = `test_tasks_binding_is_tasks_mark_status_object[<symbol>]`,
runs for EVERY row; completeness pinned by
`test_move_set_matches_tasks_mark_status_defs`).

| symbol | tasks.py binding (line) | routed-via-`_tasks`? | interception/identity test id | monkeypatch sites swept |
|---|---|---|---|---|
| `_MarkStatusState` | 896 | n/a (dataclass; `TaskIdResult` type ref direct — 0 patch sites) | identity | none found |
| `_default_mark_status_ports` | 897 | yes: `RealFsReader`, `_MarkStatusCoordRouter`, `RealGitOps`, `RealRender` (construction via `tasks` bindings — WP03 checklist invariant preserved; the router's `commit_status` body routes `emit_status_transition_transactional` ×13 through `_tasks.<attr>`, WP03) | `test_default_ports_constructs_through_tasks_bindings` | none found |
| `_ms_validate_inputs` | 907 | yes: `_output_error` ×2 (`_normalize_task_id_input` direct from `tasks_outline` — 0 patch sites; kept as explicit `as` re-export in tasks.py for `tests/contract/test_mark_status_input_shapes.py` ×7 imports) | `test_patched_output_error_intercepts_validate_inputs_bad_status` + `_empty_ids` | none found |
| `_ms_resolve_context` | 905 | yes: `locate_project_root` (×67 D7), `_output_error`, `_emit_sparse_session_warning`, `get_auto_commit_default` (×7 D7), `_find_mission_slug`, `_ensure_target_branch_checked_out`, `_protected_branch_status_commit_error` (C-001 REFUSE arm — NO `_skip_target_branch_commit` pre-gate, harness label T005) | `test_c001_refuse_arm_intercepts_through_tasks_namespace` (positional pin incl. `skip_mock.assert_not_called()`) + `test_c001_protected_gate_not_consulted_when_auto_commit_resolves_false`; coord harness `test_mark_status_refuses_exit_1_on_coord_protected_tree` green post-move | `tasks_mod, "locate_project_root"` (test_mark_status_input_shapes.py:87) — bites via this route |
| `_ms_resolve_read_dir` | 906 | yes: `_output_error` (pre30 error leg) (`MissionHandle`/`MissionArtifactKind`/`check_pre30_layout`/`Pre30LayoutError`/`TASKS_MD_FILENAME` direct — 0 tasks-path patch sites; kind-aware TASKS_INDEX read through the injected `FsReader` port, #2154) | `test_resolve_read_dir_routes_tasks_index_kind_through_fs_port`; pre30 wiring `TestMarkStatusGuard` green post-move | none found |
| `_ms_report_none_resolved` | 904 | yes: `RealRender` (json leg — the family-owned no-IDs error byte case, research.md D3), `_mark_status_json_payload`, `_output_error` (WP_ID-detail + default legs) | `test_patched_render_intercepts_report_none_resolved_json_leg` + `_wp_id_leg` + `_default_leg`; byte-level evidence: the mark-status no-IDs byte case green after each family move | none found |
| `_ms_commit` | 900 | yes: `ProtectionPolicy` (policy identity into `commit_artifact`), `console` (committed + warning + exception legs) | `test_patched_protection_policy_intercepts_ms_commit` + `test_patched_console_intercepts_ms_commit_exception_leg` | none found |
| `_ms_apply_updates` | 899 | yes: `feature_status_lock` (×21 D7 — lock spans read→resolve→write→commit exactly as pre-move), `_output_error`, `_resolve_inline_subtasks` (tasks.py-resident) (`_resolve_checkbox`/`_resolve_pipe_table`/`_resolve_wp_id` direct — 0 patch sites) | `test_patched_feature_status_lock_intercepts_apply_updates` + `test_patched_resolve_inline_subtasks_intercepts_apply_updates` | none found |
| `_ms_emit_history` | 902 | yes: `emit_history_added` (×10 — converted to explicit `as` re-export in tasks.py: dual direct-use (`add_history`) + routed seam, mypy --strict no-implicit-reexport), `console` (unresolved-WP + exception legs) (`_resolve_history_wp_id` direct — 0 patch sites) | `test_patched_emit_history_added_intercepts_emit_history` + `test_patched_console_intercepts_emit_history_unresolved_warning` | none found |
| `_ms_dossier_sync` | 901 | no seam calls (lazy `trigger_feature_dossier_sync_if_enabled` dossier import kept verbatim — canonical-home patches bite) | identity | none found |
| `_ms_output` | 903 | yes: `_mark_status_json_payload`, `console` (not-found warning), `_output_result` | `test_patched_output_result_intercepts_ms_output` | none found |
| `_do_mark_status` | 898 (re-import; `mark_status` wrapper calls this module-global — patchable as `tasks._do_mark_status`) | yes: `emit_error_logged` (D7), `_output_error` (generic exception arm); phase siblings reached by bare same-module name (the ratchet-closure invariant — deliberately NOT patch targets) | identity; `test_patched_output_error_intercepts_do_mark_status_exception_arm`; `test_tasks_coreless_orchestration.py` direct import from `tasks` green post-move | none found |

## WP08 — finalize family move-set (`tasks_finalize.py`)

Per-symbol rows for the WP08 finalize relocation (7 symbols — the
squad-recovered FIFTH family; ALL five command families are now out of
``tasks.py``). Finalize has ZERO direct emission sites (research.md D3).
Interception/identity battery:
`tests/specify_cli/cli/commands/agent/test_tasks_finalize_seam.py`
(`identity` = `test_tasks_binding_is_tasks_finalize_object[<symbol>]`,
runs for EVERY row; completeness pinned by
`test_move_set_matches_tasks_finalize_defs`).

| symbol | tasks.py binding (line) | routed-via-`_tasks`? | interception/identity test id | monkeypatch sites swept |
|---|---|---|---|---|
| `_FinalizeState` | 1156 | n/a (dataclass; `FrontmatterUpdatePlan`/`BootstrapResult` type refs direct — 0 patch sites) | identity | none found |
| `_default_finalize_ports` | 1157 | yes: `RealFsReader`, `RealCoordCommitRouter` (the plain router — finalize commits nothing itself), `RealGitOps`, `RealRender` (construction via `tasks` bindings) | `test_default_ports_constructs_through_tasks_bindings` | none found |
| `_ft_resolve_context` | 1161 | yes: `locate_project_root` (×67 D7), `_output_error` (no-root, pre30, tasks.md-missing, tasks/-missing legs), `_emit_sparse_session_warning`, `_find_mission_slug`, `_ensure_target_branch_checked_out` (`MissionHandle`/`MissionArtifactKind`/`check_pre30_layout`/`Pre30LayoutError`/`TASKS_MD_FILENAME` direct — 0 tasks-path patch sites; kind-aware WORK_PACKAGE_TASK guard-only read through the injected `FsReader` port, FR-010) | `test_resolve_context_routes_resolution_seams_through_tasks` + `test_patched_output_error_intercepts_resolve_context_no_root`; pre30 wiring `TestFinalizeTasksGuard` green post-move | none found |
| `_ft_validate` | 1162 | yes: `_output_error` (coverage / cycles / conflict pre-write refusals) (`validate_wp_coverage`/`detect_dependency_cycles`/`read_existing_frontmatter`/`detect_dependency_conflicts` direct from `tasks_finalize_validation` — 0 patch sites; lazy `parse_dependencies_from_tasks_md` import kept verbatim) | `test_patched_output_error_intercepts_validate_coverage_gate` | none found |
| `_ft_apply_writes` | 1159 | yes: `console` (plan-warning leg), `resolve_feature_dir_for_mission` (pre30-guard-wiring seam — converted to explicit `as` re-export in tasks.py: dual direct-use (`list_tasks`/`validate_workflow`) + routed seam), `bootstrap_canonical_state` (×7 — converted to explicit `as` re-export; STATUS-partition read stays coord-aware) (lazy `write_frontmatter` import kept verbatim; `compute_wp_frontmatter_updates` direct — 0 patch sites) | `test_patched_bootstrap_seams_intercept_apply_writes` + `test_patched_console_intercepts_apply_writes_warning_leg`; `test_tasks_canonical_cleanup.py` (×5 bootstrap patches) green post-move | none found |
| `_ft_output` | 1160 | yes: `_mission_identity_payload`, `_output_result` (both envelope shapes) | `test_patched_output_result_intercepts_ft_output_success_leg` + `_validate_only_leg` | none found |
| `_do_finalize_tasks` | 1158 (re-import; `finalize_tasks` wrapper calls this module-global — patchable as `tasks._do_finalize_tasks`) | yes: `emit_error_logged` (D7), `_output_error` (generic exception arm); phase siblings reached by bare same-module name (the ratchet-closure invariant — deliberately NOT patch targets) | identity; `test_patched_output_error_intercepts_do_finalize_tasks_exception_arm`; `test_tasks_coreless_orchestration.py` direct import from `tasks` green post-move | none found |

WP08 notes:
- **No-ratchet-entry verification (WP08 claim)**: verified against the live
  multi-home map in `test_tasks_cli_contract_coord.py` —
  `_BRANCH_COVERAGE_FLOORS` = {`move_task`: 65.0, `map_requirements`: 48.0,
  `status`: 46.0} and `_FLOORED_FUNCTION_HOMES` carries the same three keys
  only. Neither `mark_status` nor `finalize_tasks` has an entry; NO re-point
  needed (the WP05 mechanism was not exercised). Coord harness 16/16 green
  post-move confirms the ratchet plumbing is undisturbed.
- No-cycle proof: `tasks_mark_status` imports at module scope only stdlib,
  `typer`, `mission_runtime`, `specify_cli.agent_tasks_ports`,
  `upgrade.pre30_guard` and the sibling seam modules (`tasks_materialization`,
  `tasks_outline`); `tasks_finalize` only stdlib, `typer`, `mission_runtime`,
  `specify_cli.agent_tasks_ports`, `specify_cli.status`, `upgrade.pre30_guard`
  and `tasks_finalize_validation`/`tasks_outline` — none import
  `specify_cli.cli.commands.agent.tasks`; the only edge back is the lazy
  in-function D1 bridge.
- Dead-import cleanup in `tasks.py` (F401 sweep, 0 external references
  verified per symbol via AST import/attr/patch-string scan incl. multiline
  patch strings): `BootstrapResult`, `MissionHandle`, `TasksPorts`,
  `TASKS_MD_FILENAME`, `dataclass`/`field`, `_resolve_checkbox`,
  `_resolve_pipe_table`, `_resolve_wp_id`, `_resolve_history_wp_id`,
  `FrontmatterUpdatePlan`, `compute_wp_frontmatter_updates`,
  `detect_dependency_conflicts`, `detect_dependency_cycles`,
  `read_existing_frontmatter`, `validate_wp_coverage`.
  (`bootstrap_canonical_state`, `resolve_feature_dir_for_mission`,
  `emit_history_added` are NOT dead — converted to/kept as explicit `as`
  re-exports for their patch seams; `_normalize_task_id_input` kept as an
  explicit `as` re-export for its test-contract imports;
  `_resolve_inline_subtasks` stays tasks.py-owned, routed via
  `_tasks.<attr>`.)
- `_CEILING` 1979 → 1470 (exact achieved size, same commit as the finalize
  move; +12 lines over the raw post-move 1458 are the strict-mypy explicit
  `as` re-export forms + rationale for the two dual-use seam symbols).
