---
work_package_id: "WP01"
title: "Introduce failed_transient status and non-mutating queue branch"
dependencies: []
planning_base_branch: "main"
merge_target_branch: "main"
branch_strategy: "Planning artifacts were generated on main; completed changes must merge back into main."
subtasks:
  - "T001"
  - "T002"
  - "T003"
phase: "Phase 1 - Contract"
assignee: ""
agent: ""
shell_pid: ""
history:
  - timestamp: "2026-05-11T18:15:00Z"
    agent: "claude"
    action: "Prompt generated for Mission 5"
---

# Work Package WP01 — Introduce `failed_transient` status + non-mutating queue branch

## Goal

Add a new `BatchEventResult.status` value, `"failed_transient"`, and teach
`OfflineQueue.process_batch_results` to treat it as a no-op (no DELETE, no
retry_count bump). This is the contract change every batch-level call site in
WP02 will rely on.

## Files

- `src/specify_cli/sync/batch.py`
  - Update the `BatchEventResult` docstring/comment to declare the new status.
  - Update the `BatchSyncResult.failed_results` property so the operator
    summary continues to enumerate transient failures by category.
- `src/specify_cli/sync/queue.py`
  - In `process_batch_results`, add the `failed_transient` branch (no-op).
  - Preserve transactional semantics and the existing
    `success` / `duplicate` / `failed_permanent` (DELETE) and `rejected`
    (UPDATE retry_count) branches.

## Acceptance

- `BatchEventResult` docstring mentions `failed_transient` and explains it.
- `process_batch_results` is a 4-way switch:
  - `success` / `duplicate` / `failed_permanent` → DELETE
  - `rejected` → UPDATE retry_count = retry_count + 1
  - `failed_transient` → no mutation
- `BatchSyncResult.failed_results` returns all of `rejected`,
  `failed_permanent`, AND `failed_transient` so summaries keep working.
- Existing tests in `tests/sync/test_batch_error_surfacing.py` covering the
  `rejected` and `failed_permanent` paths still pass.

## Out of Scope

- Wiring HTTP error paths to use the new status (WP02).
- Adding new regression tests (WP02).

## Implementation Notes

- Keep the `process_batch_results` transaction structure exactly as today.
- The order of operations remains: classify, then in one transaction perform
  the DELETE and UPDATE batches. Add a third (empty) bucket for
  `failed_transient` for code clarity even though no SQL is issued.
