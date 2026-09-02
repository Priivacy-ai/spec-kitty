# Tracer: Tooling Friction — design-phase-orchestrator-api-01M1HE6M

Seeded at plan phase (2026-09-02). Appended during implementation; assessed at close.

## Plan phase

None yet. `spec-kitty plan --mission design-phase-orchestrator-api-01M1HE6M --json` ran
cleanly, non-interactively, and returned the expected scaffold-state envelope
(`plan_file`, `feature_dir`, `spec_file`, `planning_base_branch` all correctly resolved
to the feature branch given this mission's `single_branch` topology). No blocking issue
reading the spec (983 lines, read in full), the operator ruling, the charter, or
`AGENTS.md`.

One minor observation, not friction exactly: the task instructions asked to "confirm"
`CLAUDE.md`'s Shared Package Boundary guidance (`src/runtime/next/_internal_runtime/` as
canonical runtime home) against the actual tree and against where the FR-014 functions'
real dependencies live. That confirmation surfaced a genuine nuance CLAUDE.md's one-line
summary doesn't capture: `_internal_runtime/` is a closed set of internalized-package
DAG-engine re-exports, not a general extension point, while the TOP LEVEL of
`src/runtime/next/` (`decision.py`, `runtime_bridge.py`) is where CLI-domain-importing
next-invocation orchestration code already lives. This is recorded as a design decision
(`tracer-design-decisions.md` #1), not filed as friction — CLAUDE.md's guidance was
correct at the level it was written, just not granular enough to answer "which exact
file inside `src/runtime/next/`," which is precisely the kind of question a plan phase
exists to resolve rather than escalate.

## WP01 — Baseline-red snapshot (T001)

Recorded at the mission's pre-change commit `30b23fe3c` on
`feat/design-phase-orchestrator-api-3837` (this mission's `planning_base_branch`,
`single_branch` topology per plan.md § (h)), BEFORE any functional edit landed. Runner:
`.venv/bin/python -m pytest` (never bare `uv run`, per this repo's `CLAUDE.md`).

Issue #3284 re-checked at run time (`gh issue view 3284`): still **OPEN**, title "main
full suite has 23 untracked failures and 2 errors after bootstrap prewarm". Its 23
failures + 2 errors were produced by a FULL-suite run (`pytest tests/ -n auto --dist
loadfile`) and group into: doctrine/config activation drift
(`tests/charter/test_config_stem_parity.py`, `tests/doctrine/drg/test_reachability.py`,
`tests/doctrine/drg/migration/test_extractor_projection.py`), runtime/timing (daemon
self-retirement, completion-budget, doctor-daemon-restart), console ANSI/plain-mode
assertions, CI route-collection probe timeout, mission-template-resolution defaults,
compact-charter-contract sizing, a safe-commit empty-shape test, two macOS-cache-path
E2E tests, and sync-teardown errors. None of those failing modules/paths overlap this
WP's three targeted directories below.

Targeted-shard results — **all three shards fully GREEN, 0 failed, 0 errors**:

1. `.venv/bin/python -m pytest tests/specify_cli/orchestrator_api/ -v`
   → `13 passed in 1.15s`. Node ids (all PASSED):
   `test_commands_fail_closed.py::test_resolve_history_commit_args_raises_structured_error_on_action_context_error`,
   `test_commands_fail_closed.py::test_resolve_history_commit_args_error_never_carries_current_branch_ref`,
   `test_commands_fail_closed.py::test_append_history_surfaces_structured_error_code_on_emit_failure`,
   `test_fail_message_preserved.py::test_fail_preserves_message_alongside_param_is_not_duplicated`,
   `test_fail_message_preserved.py::test_fail_without_data_still_carries_message`,
   `test_fail_message_preserved.py::test_fail_caller_message_matches_param_is_not_duplicated`,
   `test_transition_subtask_gate.py::test_unasserted_flag_blocks_on_silent_snapshot`,
   `test_transition_subtask_gate.py::test_unasserted_flag_allows_when_snapshot_marks_all_done`,
   `test_transition_subtask_gate.py::test_explicit_caller_assertion_cannot_bypass_snapshot_gate`,
   `test_transition_subtask_gate.py::test_force_bypasses_the_subtask_guard_entirely`,
   `test_typed_error_fail_closed.py::test_resolve_seam_resolves_primary_on_empty_coord_topology`,
   `test_typed_error_fail_closed.py::test_mission_state_endpoint_reads_primary_on_empty_coord_topology`,
   `test_typed_error_fail_closed.py::test_genuine_not_found_still_emits_mission_not_found`.
2. `.venv/bin/python -m pytest tests/specify_cli/cli/commands/test_next_answer_effective_root.py
   tests/specify_cli/cli/commands/test_next_fail_closed.py
   tests/specify_cli/cli/commands/test_next_owned_commit_guard.py
   tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py -v`
   → `23 passed in 7.18s`.
3. `.venv/bin/python -m pytest tests/architectural/test_shared_package_boundary.py
   tests/architectural/test_runtime_charter_doctrine_boundary.py -v`
   → `12 passed in 4.87s`.

**Conclusion**: this WP's targeted shards carry ZERO pre-existing reds — #3284's known
failures live entirely outside these three directories. No new GitHub issue opened (no
failure to classify — NFR-003's "cross-reference against #3284" step is vacuously
satisfied: nothing failed to cross-reference). Every later WP (WP02–WP09) can therefore
state "0 pre-existing reds observed in my targeted shard, N introduced" as the honest
floor for these specific directories, and should re-verify #3284's OPEN state / group
list has not shifted before citing this snapshot as unchanged truth.
