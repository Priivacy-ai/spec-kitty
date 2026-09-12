---
work_package_id: WP05
title: Governed Topology Contract
dependencies:
- WP01
- WP04
requirement_refs:
- C-001
- C-004
- C-006
- FR-004
- FR-007
- FR-008
- NFR-002
planning_base_branch: mission/durable-concurrent-review-cycle-records
merge_target_branch: mission/durable-concurrent-review-cycle-records
branch_strategy: Planning artifacts for this mission were generated on mission/durable-concurrent-review-cycle-records. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/durable-concurrent-review-cycle-records unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-durable-concurrent-review-cycle-records-01M0QRX7
base_commit: 3ed0ef185632f60091ce294916ba46a69c77b37b
created_at: '2026-08-24T07:29:06.249028+00:00'
subtasks:
- T023
- T024
- T025
phase: Phase 4 - Topology verification
history:
- at: '2026-08-23T18:37:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/integration/review/
create_intent:
- tests/integration/review/test_verdict_save_topologies.py
execution_mode: code_change
model: ''
owned_files:
- tests/integration/review/test_verdict_save_topologies.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3235
---

# Work Package Prompt: WP05 – Governed Topology Contract

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` and apply its Python, pytest, typing, and implementation guidance before reading further.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## ⚠️ IMPORTANT: Review Feedback

Inspect `review_ref` with `spec-kitty agent tasks status --mission 01M0QRX7`. Address all feedback before resubmission and append resolution evidence chronologically.

## Objectives & Success Criteria

Create one focused production-command integration matrix proving the durable verdict contract across every canonical mission topology, both commit modes, representative approval/rejection transitions, and event-failure compensation. The matrix must query governed placement and inspect actual refs; topology flags and working-tree existence are not evidence.

Completion requires:

- `SINGLE_BRANCH`, `LANES`, `COORD`, and `LANES_WITH_COORD` cases built with real Git topology;
- automatic and explicit local-only behavior in every topology;
- real reviewer command invocation and real event history;
- exact committed evidence read through `git show` at the placement-selected destination;
- representative rejected→planned, approved→approved, and approved→done behavior where current policy allows it;
- serialized evidence compensation after event failure, including the loud compensation-failure branch;
- no patch that forces placement, no direct cycle writer, and no manually appended event.

## Context & Constraints

Dependencies: WP01 and WP04, transitively WP02/WP03.

Read `spec.md` FR-004/FR-007/FR-008, the plan's topology matrix, `research.md`, the internal contract, and `tests/integration/coord_topology_fixture.py`. Use canonical `MissionTopology` values from `src/mission_runtime/context.py` and production-delegating mission factories.

WP01 owns the issue-pinned concurrency file. This WP owns only a new topology module, so reuse stable helpers through imports only when they are intended test interfaces; otherwise keep concise module-local helpers. Do not edit production or WP01's file.

## Branch Strategy

- **Planning base**: `mission/durable-concurrent-review-cycle-records`
- **Merge target**: `mission/durable-concurrent-review-cycle-records`
- **Dependencies**: WP01 and WP04.
- **Execution**: `spec-kitty agent action implement WP05 --agent codex --mission 01M0QRX7`; use the lane worktree resolved from `lanes.json`.

## Subtasks & Detailed Guidance

### T023 – Build the real-command topology matrix

**Purpose**: Ensure the fix follows existing placement governance in every supported mission shape.

**Steps**:

1. Create `tests/integration/review/test_verdict_save_topologies.py`.
2. Parameterize over the four canonical topology enum values with readable IDs.
3. Use real repositories/worktrees; for coordination shapes, use the established coord fixture rather than patching resolver output.
4. Seed a real mission and WP in the required review lane.
5. Invoke the real root reviewer command and parse its actual exit code/JSON.
6. Read authoritative events using production readers.
7. Ask placement for STATUS and REVIEW_CYCLE destinations and include both in failure diagnostics.

**Validation**: a deliberately wrong primary-ref assertion must fail in coordination topology.

### T024 – Cross topology with commit modes and governed refs

**Purpose**: Prevent configuration from being mistaken for achieved durability.

**Automatic mode**:

- exit zero only for durable result;
- returned event ID resolves to exact mission/WP/reviewer/verdict/evidence pointer;
- `git show <review-destination>:<evidence-path>` returns matching content;
- status event is present at its governed status destination;
- no wrong-ref or uncommitted-only fallback is accepted.

**Local-only mode**:

- queue and commit router are not called;
- result is successful but explicitly `local_only`;
- durability is false and reason is `no_auto_commit`;
- local evidence follows the existing sanctioned behavior;
- no automatic failure is mislabeled local-only.

Cross all eight topology×mode cells. Keep matrix setup outside assertion helpers so each case remains diagnosable.

### T025 – Verify scenarios and compensation policy

**Purpose**: Pin authority coherence beyond one rejection path.

**Steps**:

1. Exercise rejected→planned, approved→approved, and approved→done where current state policy permits.
2. Match reviewer, verdict, event ID, and evidence pointer per scenario.
3. Inject event/status failure only after evidence has been verified committed.
4. Require the existing evidence revert compensator to acquire the verdict queue and attempt its Git deletion.
5. On successful compensation, require the evidence commit to be removed according to current contract and command failure returned.
6. On compensation failure, require a loud compounded error and allow the committed evidence only as explicitly non-current history.
7. Do not silently retire or bypass compensation; any future policy change requires an explicit decision and contract update.
8. Include a coordination-topology event-serialization negative control that hits the independent `coordination.transaction.feature_status_lock` binding and produces the exact `missing_authoritative_event` cause when disabled.

## Test Strategy

```bash
uv run python -m pytest tests/integration/review/test_verdict_save_topologies.py -n0 -q --tb=short
uv run ruff check tests/integration/review/test_verdict_save_topologies.py
```

Run individual parameter IDs while debugging. Do not use outer xdist for shared Git topology.

## Concrete Acceptance Matrix

For each topology, record these facts in assertion diagnostics:

| Fact | Automatic | Local-only |
|---|---|---|
| Command exit | zero only after durable completion | zero after sanctioned local write |
| Classification | `durable` | `local_only` |
| Durable flag | true | false |
| Event ID | exact persisted event | per existing local-only event contract |
| Evidence pointer | stable and event-correlated | local path, never claimed committed |
| Status destination | placement-selected and readable | unchanged contract |
| Evidence destination | placement-selected and `git show` readable | no commit-router write |
| Queue | acquired in automatic evidence path | never acquired |

For event-failure injection, record:

1. evidence was verified committed before event execution;
2. the event failed with a known injected cause;
3. compensation acquired the verdict queue;
4. compensation attempted the correct governed ref/path;
5. successful compensation removed only that evidence commit; or
6. failed compensation produced the expected compounded diagnostic and left the artifact explicitly non-current.

The matrix must not pass through row counts alone. Every row correlates exact event ID, evidence pointer, reviewer, verdict, WP, and committed bytes.

## Risks & Mitigations

- **Fake topology**: construct real coord/lane refs and query placement.
- **Matrix opacity**: use descriptive IDs and include actual refs/result envelope in failures.
- **Compensation drift**: assert both attempted serialization and exact success/failure aftermath.
- **Fixture duplication**: reuse stable factories but do not widen ownership casually.
- **Wrong authority**: event is current verdict; artifact is evidence content.

## Review Guidance

Reject if any cell infers destination, trusts only `verdict_durably_persisted`, omits local-only negative controls, or permits evidence without an exact event correlation. Check compensation ordering and loud failure separately.

## Definition of Done

- T023–T025 are marked done via event status.
- All eight topology×mode cells and scenario/compensation cases pass.
- The new module stays within ownership and passes Ruff.
- Failures identify topology, mode, scenario, status ref, and evidence ref.
- Independent review can reproduce every ref read.

## Activity Log

- 2026-08-23T18:37:05Z – system – Prompt created.

Use `spec-kitty agent tasks move-task WP05 --to for_review --mission 01M0QRX7` when ready.
