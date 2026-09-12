# Contracts — Next Resolves State From Committed Authority

This mission is a **behavioral fix** to the `spec-kitty next` control loop and the
`agent tasks status` board (issues #2947, #3780). It introduces **no new API,
data model, wire schema, envelope, or CLI contract** — it consumes the already-shipped
`is_acceptable_ending` / `has_operator_provenance` authority and the committed
`mission_number` signal, and returns the existing `next` result kinds
(`terminal` / `query` / `blocked`).

No contract artifacts are required. The observable behavior contract is the
Decision Outcomes table in [`../spec.md`](../spec.md) and the regression tests
(`tests/runtime/next/test_committed_authority.py`,
`tests/runtime/next/test_merged_mission_terminal.py`,
`tests/specify_cli/next/test_runtime_bridge.py`,
`tests/specify_cli/cli/commands/agent/test_tasks_status_committed_authority.py`).
