# Quickstart: Close #2160 Coord-Shadows Read/Gate Arm

Validation scenarios (all through production paths):

1. **Gate closes on every path** — on a coord-topology mission with unchecked subtask
   rows, `spec-kitty agent status --to for_review` WITHOUT `--subtasks-complete` (and the
   orchestrator-api transition) is BLOCKED. See `tests/specify_cli/status/test_infer_subtasks_primary.py`
   and `tests/specify_cli/orchestrator_api/test_transition_subtask_gate.py`.
2. **One subtask-row definition** — guard, dashboard count, and rollback-uncheck agree on the
   bite battery (incl. re-appearing `## WPnn` heading). See `tests/specify_cli/core/test_subtask_rows.py`.
3. **Lane recovery leaks no status** — a recovered coord-topology lane registers sparse-checkout and
   materializes no `status.events.jsonl`/`status.json`. See `tests/specify_cli/lanes/test_worktree_allocator_recovery.py`.
4. **Live claim not stale** — `is_process_alive` suppresses the stale flag for a live claim.
   See `tests/specify_cli/core/test_process_liveness.py`.
5. **Progress tick keeps analysis fresh** — checkbox flips don't change the freshness hash.
   See `tests/specify_cli/cli/commands/agent/test_freshness_checkbox_insensitive.py`.
