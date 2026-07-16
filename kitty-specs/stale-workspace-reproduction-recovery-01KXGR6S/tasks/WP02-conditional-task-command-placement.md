---
work_package_id: WP02
title: Conditional task-command and placement remediation
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-002
- C-003
- C-004
- C-005
- C-006
- C-008
tracker_refs: []
planning_base_branch: fix/stale-workspace-reproduction
merge_target_branch: fix/stale-workspace-reproduction
branch_strategy: Planning artifacts for this mission were generated on fix/stale-workspace-reproduction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/stale-workspace-reproduction unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_mark_status.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- src/specify_cli/coordination/commit_router.py
- tests/specify_cli/cli/commands/agent/test_tasks_mark_status.py
- tests/specify_cli/cli/commands/agent/test_tasks_mark_status_seam.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_placement.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py
- tests/specify_cli/coordination/test_commit_router_placement.py
- tests/specify_cli/coordination/test_commit_router_partition.py
role: implementer
tags: []
shell_pid_created_at: "1784023781.31"
shell_pid: "138606"
agent: "codex"
---

# WP02 — Conditional Task-Command and Placement Remediation

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load python-pedro` before reading or changing anything.
Adopt that profile's Python, test-first, locality, and verification discipline for
the entire work package.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

Stop if the profile cannot be loaded.

## Objective

Consume the committed, independently reviewed disposition matrix. Change task-command or
placement code only for a row that is both `RED` and `continue` and whose reached
owner is one of this WP's declared paths. Preserve every GREEN arm unchanged.
If no owned row is RED, complete this package as an evidence-backed no-op.

This WP exists so a current defect in `mark-status`, ordinary `move-task`, or the
canonical placement router is actionable without silently broadening lifecycle
or review ownership. It is not authority for a general command refactor.

## Canonical Workspace Entry

Prepare the implementation workspace only through:

```bash
spec-kitty agent action implement WP02 --agent codex
```

Use the returned workspace path and branch. Do not guess a `.worktrees` path,
manually create a worktree, or edit from the repository-root planning checkout.
Confirm WP01 is canonically approved or done, inactive, and with a clean
dependency lane, and that the committed disposition matrix has no pending review
metadata or pending rows before touching code.

## Owned Surface

The complete ownership allowlist is the `owned_files` frontmatter above. The
production candidates divide into:

- task transition entry points: `tasks_mark_status.py`, `tasks_move_task.py`;
- shared parsing/validation only if the reviewed call path reaches it;
- canonical placement: `coordination/commit_router.py`;
- existing focused tests for those exact seams.

### Charter Exception Handling decision

ATDD / Reviewer Renata, Architect Alphonso, and the runtime-governance reviewer
have approved this exception as recorded in the disposition matrix. This is a
case-by-case Charter Exception Handling decision, not authority from generic
ownership-map leeway.

WP01 is canonically approved or done, inactive, and with a clean dependency lane.
Lane-b contains the exact approved blob
`d1f89937dc25353d74615d7305c97e9af00848ee` at ref `ff7eca5e2`, and WP02/WP04
are serial dependencies with no concurrent writer. The exception is one test-only
file: WP02 may edit exactly
`tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`
for these immutable pytest IDs only:

- `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[move-task-recoverable]` (matrix row 6)
- `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[move-task-unavailable]` (matrix row 7)
- `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[move-task-divergent]` (matrix row 8)

Record this one-line rationale in the test-only commit and review handoff:
`Charter exception: WP01 canonically approved or done, inactive, and with a clean dependency lane; witness rows 6–8 only; frozen harness, serial writer, no topology recomputation.`
WP01 retains creation ownership and the immutable reviewed evidence at ref
`ff7eca5e2c248730909d91cddde93c6c01232701`, whose approved witness blob is
`d1f89937dc25353d74615d7305c97e9af00848ee`.

Do not reorder or rename `_MATRIX`, its IDs, or its row-number binding. Freeze
fixture construction, `_snapshot`, `_observe`, `_assert_common_record`, the
registered invocation path, all common six-surface measurements, and every
non-owned node expectation against that approved blob. Only the state-specific
desired-outcome branches for the three named IDs may change.

Shared `owned_files` is not an alternative: it would recompute active topology,
conflict with live workspaces, and reproduce #2644. Duplicating the fixture is
prohibited because a parallel witness is fakeable. A fresh replacement Mission
would discard truthful reviewed state. Historical evidence and the frozen harness
remain immutable; the existing PR stays DRAFT and operator-only readiness/merge
remains the final review.

This decision supersedes only ownership-map-leeway step 1 and its corresponding
failure mode for this file and these three nodes. It grants no general ownership.
Stop if any recorded approval is withdrawn or rejected. Stop unless WP01 is
canonically approved or done, inactive,
and with a clean dependency lane. Also stop if the lane-b ref/blob differs, a
concurrent writer appears, dependency order is broken, or any frozen surface,
other node/file, shared ownership, or topology change is needed. Return a
structured exception finding to the orchestrator.

Do not edit workspace context, lifecycle synchronization, review workflow,
Mission planning artifacts, status runtime modules, or unrelated tests. WP03 owns
lifecycle reconciliation. WP04 owns review action ordering and aggregate proof.

## Mandatory Activation Gate

For each reviewed matrix row relevant to this package, extract:

- exact command and state classification;
- baseline SHA and test node ID;
- RED/GREEN verdict;
- reached owner;
- six-surface delta;
- stop/continue decision;
- reviewer identity and review reference.

Then apply:

1. No RED/continue row in an owned path: do not edit production or tests; run the
   focused regression set and report byte-identical owned production paths.
2. RED/continue in an owned path: author only the three named desired-contract
   branches in the justified out-of-map witness, commit that test-only RED
   evidence, then make the smallest owner-local production fix.
3. RED/continue reaches an undeclared path: stop for plan amendment and task
   refinalization. Do not expand ownership ad hoc.
4. Contradictory, missing, or unreviewed matrix evidence: reject the package.

## Behavioral Invariants

### `mark-status`

`mark-status` is the workspace-free negative control. It may mutate canonical
tracking state without requiring a lane worktree, but must still preserve the
correct placement and atomic failure contract. Do not add workspace resolution
merely to make commands look uniform.

### Ordinary `move-task`

The acceptance path is:

```text
agent tasks move-task WP01 --to for_review --mission <slug> --agent codex --json
```

Do not use `--skip-pre-review-gate` as proof of the normal path. The skip option
returns before workspace resolution and is only a negative control.

### Placement

PRIMARY owns WP/task tracking and COORD owns status state in coordinated
topologies. If the reviewed row proves placement RED, adapt the existing command
to the canonical partition-aware commit seam. Do not hand-roll two commits, do
not write from the wrong checkout, and do not claim #2160 as solved.

### Failure Atomicity

Unavailable or divergent authority must fail before durable mutation. Evidence
must show:

- empty before/after ref ranges;
- byte-identical WP/tasks and status surfaces;
- no leaked lock;
- no fabricated directory or branch;
- clean relevant checkout porcelain.

A matching existing branch plus missing path may use existing canonical recovery
when the reviewed row authorizes it. An absent branch or divergent authority may
not fall back to the primary checkout.

## Red-First Discipline

ATDD order is mandatory:

1. Starting from the WP01 dependency base, change only the three named
   state-specific desired-outcome branches and commit that test-only contract.
2. Run the three exact pytest IDs and prove they are RED for the reviewed
   production behavior before any production edit.
3. Implement the smallest production repair and make the unchanged test-only
   contract GREEN.

Never change acceptance expectations after production implementation begins.
Earlier WP01 commits, review artifacts, and the approved blob remain immutable.
The six-surface observation and coverage stay intact; only expected deltas change
to the atomic success/refusal contract.

## Subtasks

### T006 — Validate row authorization

Map each task-command/placement row to one owned path and confirm the matrix is
committed, complete, reviewed, and based on the recorded baseline.

### T007 — Preserve or add focused RED evidence

Author the desired contract for the three exact pytest IDs, commit it test-only,
and prove all three nodes RED on the dependency base before production changes.
For no-op, record the exact green commands and production-file hashes.

### T008 — Implement the smallest owner-local correction

Change only the reached owner. Resolve workspace identity at most once where the
command actually requires it, and use the canonical placement seam for commits.

### T009 — Prove six-surface atomicity and placement

Run the three exact IDs plus focused placement and authority tests without editing
their post-RED expectations. Compare ref OIDs, committed path sets, bytes,
locks/paths, state events, and porcelain; all six common surfaces remain asserted.

### T010 — Regression and handoff

Run focused tests, Ruff, mypy for changed modules, and relevant architectural
guards. Report activated rows, no-op rows, commits, commands, and residual risks
to the independent reviewer and WP03.

## Focused Verification

Use only tests relevant to activated owners, drawing from:

```bash
pytest -q tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py
pytest -q tests/specify_cli/cli/commands/agent/test_tasks_mark_status.py
pytest -q tests/specify_cli/cli/commands/agent/test_tasks_mark_status_seam.py
pytest -q tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py
pytest -q tests/specify_cli/cli/commands/agent/test_tasks_move_task_placement.py
pytest -q tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py
pytest -q tests/specify_cli/coordination/test_commit_router_placement.py
pytest -q tests/specify_cli/coordination/test_commit_router_partition.py
ruff check <changed Python paths>
mypy <changed production Python paths>
```

Also run `git diff --check`, inspect changed path ownership, and confirm the lane
workspace is clean after commits. Do not use retry-to-green.

## Definition of Done

- The committed, independently reviewed matrix is the sole activation authority.
- The ordinary non-skipped `move-task` row is classified.
- Every activated RED has a distinct red-first evidence commit.
- WP01's approved commits/review artifacts and blob remain immutable; the only
  out-of-map diff is the pre-production desired contract for the three named IDs.
- Only the reached owned production path and the three named justified
  out-of-map desired-contract branches may change.
- GREEN rows retain byte-identical production files.
- Failure rows have empty commit ranges and no durable side effects.
- Successful rows preserve canonical PRIMARY/COORD placement.
- The complete focused verification set for activated owners passes.
- An undeclared reached owner blocks for refinalization.

## Reviewer Guidance

Use a reviewer distinct from the implementer. Re-run the exact authorized WP01
nodes and focused owner tests; inspect commit ordering and path ownership rather
than trusting the handoff. Reject skip-gated `move-task` as acceptance evidence.
Reject any edit for a GREEN/stop row, any production path absent from the manifest,
any witness edit outside the three exact IDs, any `_MATRIX` reorder/rename, any
change to frozen fixture/observation surfaces, any expectation edit after
production begins, any rewrite of WP01's reviewed evidence, or any command-local
placement workaround. Verify the one-line out-of-map rationale in both the
test-only commit and review handoff.

## Activity Log

- 2026-07-14T17:46:04Z – codex – shell_pid=138606 – Assigned agent via action command
- 2026-07-14T17:50:32Z – codex – shell_pid=138606 – Blocked: authorized rows 6-8 require post-fix assertions in tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py, but that external WP01 witness is absent from WP02 owned_files. The unchanged test hard-codes exit 0, durable mutations, and missing path for all stale move-task states, so recoverable success-with-recreated-path and unavailable/divergent atomic refusal cannot pass without editing an undeclared path. Requires plan ownership amendment/refinalization.
- 2026-07-14T17:52:09Z – user – Planning amendment required: sequential acceptance-witness ownership omitted from WP02/WP04
- 2026-07-14T18:22:46Z – codex – shell_pid=138606 – Assigned agent via action command
- 2026-07-14T18:33:37Z – codex – shell_pid=138606 – Ready for review: rows 6-8 enforce recoverable reattachment and atomic unavailable/divergent refusal; Charter exception: WP01 canonically approved or done, inactive, and with a clean dependency lane; witness rows 6-8 only; frozen harness, serial writer, no topology recomputation.
- 2026-07-14T18:34:15Z – codex – shell_pid=138606 – Started review via action command
- 2026-07-14T18:43:18Z – user – shell_pid=138606 – Independent review approved: ATDD 3acc4bacc RED then 8289cf39 GREEN for exact move-task recoverable/unavailable/divergent nodes; frozen witness surfaces unchanged; 70 focused tests, Ruff, strict mypy, and 11 architectural checks passed; complete matrix is 8 green task/mark rows plus 4 intentional WP04 review REDs. Approved witness blob 48ca83d8091dde8cd288fc7905ea6c128aec62f8 at 8289cf39.
