---
work_package_id: WP04
title: Truthful Verdict Command Orchestration
dependencies:
- WP02
- WP03
requirement_refs:
- C-001
- C-002
- FR-001
- FR-002
- FR-004
- FR-005
- FR-006
- NFR-002
planning_base_branch: mission/durable-concurrent-review-cycle-records
merge_target_branch: mission/durable-concurrent-review-cycle-records
branch_strategy: Planning artifacts for this mission were generated on mission/durable-concurrent-review-cycle-records. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/durable-concurrent-review-cycle-records unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-durable-concurrent-review-cycle-records-01M0QRX7
base_commit: 19e43199d2ea7254e3a1945b9d9058077df1c8d8
created_at: '2026-08-24T05:58:35.175068+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
phase: Phase 3 - Production integration
history:
- at: '2026-08-23T18:37:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_transition_core.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- src/specify_cli/coordination/status_transition.py
- tests/specify_cli/cli/commands/agent/test_move_task_approval_body_collision.py
- tests/specify_cli/cli/commands/agent/test_move_task_durability.py
- tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3235
---

# Work Package Prompt: WP04 – Truthful Verdict Command Orchestration

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` with `/ad-hoc-profile-load` and apply its implementation, typing, testing, and boundary rules before reading further.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## ⚠️ IMPORTANT: Review Feedback

Inspect the current `review_ref` using `spec-kitty agent tasks status --mission 01M0QRX7`. Treat feedback as mandatory and append resolution evidence chronologically.

## Objectives & Success Criteria

Wire WP02's queue and WP03's typed evidence outcome into the production reviewer command. An automatic verdict may report success only after its evidence is verified at the governed Git destination and its authoritative event has been persisted referencing that evidence. Busy/persistence/event failures exit nonzero. `--no-auto-commit` remains a deliberate successful local-only mode with false durability.

Completion requires:

- automatic-only acquisition of the checkout queue;
- no allocation/status lock introduced by the new evidence-commit path held across its Git subprocess;
- queue release before authoritative event emission;
- evidence outcome propagated rather than reduced to a warning or inferred from `auto_commit`;
- compensation Git operations serialized by the same queue;
- nonzero typed busy/persistence errors with no success envelope;
- coherent JSON and human output including stable evidence/destination fields;
- unchanged sanctioned local-only behavior;
- real command tests for every failure/retry/idempotence path.

## Context & Constraints

Dependencies: WP02 and WP03.

Read the plan sequence diagram and Result Contract, the internal contract file, and the data-model invariants. Inspect current sequencing:

- `_mt_finalize_plan` persists evidence before `_mt_execute` emits status.
- `_mt_execute` owns the short `feature_status_lock` around event/WP persistence.
- `_do_move_task` currently compensates an already committed evidence write when event execution fails.
- `_mt_output` currently begins with `result: success` and durability fields are shaped later.

Preserve the accepted authority split and placement router. Do not broaden the queue to unrelated commits or move event authority into Markdown.

This WP owns the two orchestration modules and their focused command test. Do not edit `cycle.py`, the queue module, the headline integration matrix, or generic status/Git modules.

## Branch Strategy

- **Planning base**: `mission/durable-concurrent-review-cycle-records`
- **Merge target**: `mission/durable-concurrent-review-cycle-records`
- **Dependencies**: WP02 and WP03.
- **Execution**: `spec-kitty agent action implement WP04 --agent codex --mission 01M0QRX7`; the lane comes from finalized `lanes.json`.

## Subtasks & Detailed Guidance

### T017 – Integrate automatic-only queue acquisition

**Purpose**: Serialize the complete evidence critical section without serializing local-only writes or status events.

**Steps**:

1. At the narrow verdict persistence boundary, branch on resolved automatic-commit mode.
2. For automatic mode, acquire WP02's queue before pending-record discovery/allocation.
3. This orchestration seam is the sole queue-acquisition owner. Invoke WP03's non-acquiring persistence operation inside the lease; `cycle.py` must never reacquire it. Allow `cycle.py` to take its short mission status lock while the verdict queue is held.
4. Confirm that the review-cycle allocation lock is released before the evidence router invokes Git. Existing authoritative status-transaction locking is outside this invariant and remains unchanged.
5. Hold the verdict queue through governed-ref verification.
6. Release the queue before `_mt_execute` takes the event status lock.
7. Map queue timeout to an explicit command failure; do not retry.
8. In local-only mode, bypass queue and commit entirely.

**Lock-order invariant**: verdict queue → optional short allocation status lock → Git → queue release → event status lock. Never acquire queue from inside `_mt_execute`.

### T018 – Propagate typed evidence outcomes

**Purpose**: Stop configuration or warnings from masquerading as durability.

**Steps**:

1. Replace `VerdictDurabilitySignal` inference that depends only on skip reason with WP03's actual persistence outcome.
2. Carry classification, durability flag, evidence ref, destination ref, and reason through `_MoveTaskState` or the narrow existing seam.
3. Prevent `_mt_execute` when an automatic evidence outcome is busy or failed.
4. Preserve `None` only for paths that genuinely do not create verdict evidence.
5. Ensure both rejection rollback and approval writers use the same outcome logic.
6. Avoid duplicate parallel result models; choose one canonical type.

### T019 – Gate events and serialize compensation

**Purpose**: Keep current verdict and evidence coherent across partial failure.

**Steps**:

1. Build `ReviewResult` only from a verified evidence outcome.
2. Emit the current-verdict transition only after evidence verification.
3. If event/status persistence fails, report overall failure and first attempt the existing evidence revert compensation under the verdict queue.
4. Preserve committed evidence as non-current history only when compensation is deliberately retired by an explicit future decision or when compensation itself fails loudly; never silently skip the current compensator.
5. Inspect the existing revert compensator: because it performs evidence deletion through Git, acquire the same verdict queue around that Git operation.
6. Never hold the event status lock while acquiring the verdict queue.
7. Preserve loud compounded failure when both event execution and compensation fail, explicitly identifying that non-current evidence may remain.
8. Add an acquisition-order test or instrumentation assertion around the new evidence Git invocation specifically; do not assert that unrelated existing status transactions never hold their own lock across Git.

### T020 – Preserve explicit local-only mode

**Purpose**: Avoid breaking an intentional non-durable workflow.

**Required behavior**:

- `--no-auto-commit` does not acquire the queue;
- it does not call the commit router;
- exit remains zero when the local write succeeds;
- JSON says `verdict_durably_persisted=false` and reason `no_auto_commit`;
- human output says the record is local/non-durable;
- the current event behavior remains exactly the sanctioned existing contract;
- no automatic path can reuse `no_auto_commit` to hide failure.

### T021 – Add command failure and retry coverage

**Purpose**: Verify orchestration, not merely the cycle helper.

**Cases**:

- router `committed` + read-back + event append → success;
- returned router error → nonzero, retained path, no success event;
- wrong-surface no-op → nonzero;
- raised commit exception → nonzero, retained path;
- queue timeout → typed busy nonzero and no evidence/event mutation;
- event failure after evidence commit → nonzero; successful serialized compensation removes evidence, while loud compensation failure may leave coherent non-current evidence;
- identical retry after returned/raised failure → same path succeeds;
- response interruption after commit → idempotent retry, no duplicate;
- `--no-auto-commit` negative control;
- evidence Git subprocess probe confirms the review-cycle allocation lock is not held; it must not fail on unrelated existing status-transaction Git behavior.

Use real router fixtures where feasible and fault-inject only at documented seams.

### T022 – Align machine and human result contracts

**Purpose**: Make automation and people receive the same truth.

**Fields**:

- `result`;
- `verdict_durably_persisted`;
- `durability_classification`;
- `durability_reason` when non-durable;
- `evidence_ref` when an artifact exists;
- `destination_ref` for durable success;
- event ID/reference for durable success.

Busy and persistence failures must use the normal error envelope and exit 1 (or the repository's stable nonzero convention). Do not emit `result: success` alongside a failed automatic durability flag. Keep backwards-compatible fields where they do not contradict the new contract.

## Test Strategy

```bash
uv run python -m pytest tests/specify_cli/cli/commands/agent/test_move_task_durability.py -n0 -q --tb=short
uv run ruff check src/specify_cli/cli/commands/agent/tasks_move_task.py src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py tests/specify_cli/cli/commands/agent/test_move_task_durability.py
uv run mypy --strict src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
uv run mypy --strict src/specify_cli/cli/commands/agent/tasks_move_task.py
```

Run focused compatibility guards for exported task-command seams if these modules are covered by frozen-surface tests.

## Risks & Mitigations

- **Deadlock**: never hold event status lock while acquiring queue; test acquisition order.
- **False success envelope**: derive output from typed outcome and assert exit/result together.
- **Compensation race**: queue any compensating Git mutation.
- **Local-only regression**: keep a dedicated no-queue/no-router negative control.
- **God-function expansion**: use existing persistence seam; keep orchestration edits small and typed.

## Review Guidance

Reject if any failed automatic commit reaches `_mt_output` success, if queue spans event emission, if the review-cycle allocation/status lock introduced or used by the new evidence path spans its evidence Git invocation, if compensation bypasses the queue, or if local-only changes meaning. Existing status-transaction locking is not part of this rejection rule. Verify returned and raised failures separately.

## Definition of Done

- T017–T022 event-marked done.
- Focused real-command suite passes.
- JSON/human/exit contracts agree.
- Lock-order invariant is directly observed by a test.
- Ruff and strict mypy pass for both touched production modules, `tasks_move_task.py` and `tasks_verdict_persistence.py`; applicable frozen-surface compatibility gates pass.

## Activity Log

- 2026-08-23T18:37:05Z – system – Prompt created.

Use `spec-kitty agent tasks move-task WP04 --to for_review --mission 01M0QRX7` when ready.
