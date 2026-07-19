---
work_package_id: WP04
title: Conditional review atomicity and verification
dependencies:
- WP03
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
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
- C-009
- C-010
- C-011
- C-012
- C-013
- C-014
- C-015
tracker_refs: []
planning_base_branch: fix/stale-workspace-reproduction
merge_target_branch: fix/stale-workspace-reproduction
branch_strategy: Planning artifacts for this mission were generated on fix/stale-workspace-reproduction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/stale-workspace-reproduction unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/status/review_transaction.py
- tests/specify_cli/status/test_review_transaction.py
- tests/architectural/test_review_receipt_producer_gate.py
- tests/specify_cli/git/test_ref_advance.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/coordination/types.py
- src/specify_cli/coordination/transaction.py
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/coordination/outbound.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/git/commit_helpers.py
- src/specify_cli/git/ref_advance.py
- src/specify_cli/status/review_transaction.py
- src/specify_cli/status/work_package_lifecycle.py
- src/specify_cli/sync/local_commit.py
- tests/agent/test_workflow_review_lane_gate.py
- tests/architectural/test_review_receipt_producer_gate.py
- tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py
- tests/specify_cli/coordination/test_commit_router_partition.py
- tests/specify_cli/coordination/test_status_transition.py
- tests/specify_cli/coordination/test_transaction.py
- tests/specify_cli/coordination/test_types.py
- tests/specify_cli/coordination/test_outbound.py
- tests/specify_cli/git/test_commit_helpers.py
- tests/specify_cli/git/test_ref_advance.py
- tests/specify_cli/sync/test_local_commit.py
- tests/specify_cli/status/test_review_transaction.py
- tests/status/test_work_package_lifecycle.py
role: implementer
tags: []
shell_pid_created_at: "1784023781.31"
shell_pid: "138606"
agent: "codex"
---

# WP04 — Conditional Review Atomicity and Verification

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` before reading anything else. Adopt the
profile's implementer identity, governance scope, boundaries, and verification
discipline for the entire work package.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

Then read, in order:

1. `kitty-specs/stale-workspace-reproduction-recovery-01KXGR6S/spec.md`
2. `kitty-specs/stale-workspace-reproduction-recovery-01KXGR6S/plan.md`
3. `kitty-specs/stale-workspace-reproduction-recovery-01KXGR6S/research.md`
4. `kitty-specs/stale-workspace-reproduction-recovery-01KXGR6S/data-model.md`
5. `kitty-specs/stale-workspace-reproduction-recovery-01KXGR6S/contracts/stale-workspace-transition-contract.md`
6. `kitty-specs/stale-workspace-reproduction-recovery-01KXGR6S/disposition-matrix.md`
7. `docs/adr/3.x/2026-07-14-2-cross-partition-workflow-transaction.md`
8. The completed WP01 through WP03 review evidence and both preserved WP04 review cycles.

---

## Objective

Conditionally repair the review action only where WP01's production-shaped
disposition proves a current-base RED: establish one reconciled execution
workspace before the review claim, track resources owned by this invocation,
and compensate those resources if a later operation fails. Preserve already-green
arms unchanged, keep PRIMARY tracking and COORD status at their canonical
placements, and finish with aggregate evidence that the original WP01 witness
remains unchanged and green.

The reviewed operator amendment now completes only the architectural gap found after
review cycle 2: Mission Management owns the review-only PRIMARY+COORD composite,
canonical receipts and typed post-commit failure drive reverse CAS compensation, and
outbound effects wait for local commit. The earlier readiness/resource implementation
is preserved; amendment work begins at T022.

## Context

Issue #2626 reports that stale lane-workspace metadata can make a transition fail
after durable tracking state has already changed. Research found a concrete review
ordering hazard: the review path may claim `for_review -> in_review` before
`_prepare_review_workspace` establishes that the execution workspace is usable.
It also found that review can resolve workspace state twice, permitting path or
branch disagreement between readiness and execution.

This WP is not authorization for a broad workflow refactor. WP01 owns the real-CLI
stale-workspace witness and the reviewed matrix carries the row-by-row
`stop`/`continue` disposition. WP03 owns conditional lifecycle reconciliation.
WP04 consumes both outputs and changes
production code only for review rows that are explicitly RED and marked
`continue`. A GREEN review row is a mandatory no-op arm: record the evidence,
run its regression tests, and do not edit production code for that behavior.

The governing state model is:

- `PersistedWorkspaceContext` is evidence, not proof that a path still exists.
- `CurrentLaneAssignment` is reconciled with persisted context once.
- One `ResolvedWorkspace` identity is passed unchanged through readiness,
  recovery, claim, review execution, and cleanup.
- `status.events.jsonl` remains the lane-state authority.
- PRIMARY owns WP/task tracking; COORD owns status in coordinated topologies.
- A successful result requires every intended placement commit and clean relevant
  checkouts; refusal requires zero durable deltas.

## Branch and Workspace Contract

- **Planning base and merge target**: `fix/stale-workspace-reproduction`.
- **Dependencies**: WP01 through WP03 must all be `approved` or `done` before WP04 is
  claimed. Do not bypass dependency gating.
- **Start command**:

  ```bash
  spec-kitty agent action implement WP04 --agent codex --mission stale-workspace-reproduction-recovery-01KXGR6S
  ```

- The action command resolves the computed lane workspace. Work only in the
  returned workspace path and current branch; do not create, guess, or reconstruct
  a worktree path from the Mission slug.
- Before editing, verify the Mission branch contract resolves to
  `fix/stale-workspace-reproduction` and that the allocated lane workspace is the
  path reported by the canonical action/branch-context surfaces.
- Completed WP04 changes merge back to `fix/stale-workspace-reproduction`. The
  existing pull request remains DRAFT; only the human operator may mark it ready
  or merge it.
- Stay inside the expanded `owned_files` frontmatter list. It is the reviewed
  operator-authorized WP04 scope amendment; it does not alter dependencies, lane-d,
  the prompt ID, or topology. Stop if implementation requires any other file.

### Charter Exception Handling decision

ATDD / Reviewer Renata, Architect Alphonso, and the runtime-governance reviewer
have approved this exception as recorded in the disposition matrix. This is a
case-by-case Charter Exception Handling decision, not authority from generic
ownership-map leeway. WP04 must not consume it until WP02 is approved.

WP01 is canonically approved or done, inactive, and with a clean dependency lane.
Lane-b contains approved blob `d1f89937dc25353d74615d7305c97e9af00848ee`
at ref `ff7eca5e2`; WP02 then WP04 execute serially with no concurrent writer. The
exception covers one test-only file: WP04 may edit exactly
`tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`
for these immutable pytest IDs only:

- `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[review-healthy]` (matrix row 9)
- `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[review-recoverable]` (matrix row 10)
- `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[review-unavailable]` (matrix row 11)
- `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[review-divergent]` (matrix row 12)

Record this one-line rationale in the test-only commit and review handoff:
`Charter exception: dependency witness rows 9–12 only; frozen harness, serial writer, no topology recomputation.`
The approved WP02 witness blob, recorded in WP02's review handoff, is WP04's
immutable dependency baseline.

Do not reorder or rename `_MATRIX`, its IDs, or row-number binding. Freeze fixture
construction, `_snapshot`, `_observe`, `_assert_common_record`, the registered
invocation path, all common six-surface measurements, and rows 1–8 against the
approved WP02 blob. Only state-specific desired-outcome branches for the four
named IDs may change.

Shared `owned_files` would recompute active topology, conflict with live
workspaces, and reproduce #2644. Duplicating the fixture is prohibited because a
parallel witness is fakeable. A fresh replacement Mission would discard truthful
reviewed state. Historical evidence and the frozen harness remain immutable; the
PR stays DRAFT and operator-only readiness/merge remains the final review.

This decision supersedes only ownership-map-leeway step 1 and its corresponding
failure mode for this file and these four nodes. It grants no general ownership.
Stop if any recorded approval is withdrawn or rejected. Stop unless WP01 is
canonically approved or done, inactive,
and with a clean dependency lane. Also stop if WP02 state/dependency evidence is
invalid, the lane-b ref/blob or approved WP02 blob differs, a concurrent writer
appears, or any frozen surface, other node/file, shared ownership, or topology
change is needed. Return a structured exception finding to the orchestrator.

### Reviewed operator scope amendment — binding

The operator directed the architectural ownership finding to be folded into this
same WP04. IC-01 through IC-06, WP01 through WP03 approvals, witness commit
`980eae6a9`, remediation commit `eaff3130c`, approved WP02 witness blob
`48ca83d8091dde8cd288fc7905ea6c128aec62f8` at ref `8289cf39`, both WP04 review
cycles, and all existing activity history are immutable inputs. T016 through T021
are historical execution records and MUST NOT be re-executed, reinterpreted, or used
to reactivate rows 1–8 or adjacent-ticket work. Amendment execution starts at T022.

The frozen acceptance witness remains governed only by the earlier Charter exception.
Its fixture, `_MATRIX`, ordering, registered invocation, observation helpers, rows 1–8,
and the row 9–12 desired contract committed at `980eae6a9` are byte-frozen. There are
no post-`980eae6a9` expectation edits. New failure coverage belongs in the newly named
focused tests and direct Mission Management integration, not in witness expectations.

#### Narrow shared-file Charter Exception Handling

WP04 may edit the WP02-owned files below only for the composite receipt adapter and
its focused regression:

- `src/specify_cli/coordination/commit_router.py`
- `tests/specify_cli/coordination/test_commit_router_partition.py`

This exception is valid because WP02 is approved, inactive, and has a clean dependency
lane; its approved witness blob/ref above is frozen; WP04 is the sole serial writer; and
no topology recomputation occurs. It grants no authority over any other WP02 file or
behavior. Stop if an approval is withdrawn, a concurrent writer appears, the approved
blob/ref differs, the frozen witness changes, or the edit cannot remain limited to
Git-evidence-to-canonical-receipt adaptation. Do not run `finalize-tasks`, edit
`lanes.json`, add a WP, or recompute ownership topology.

### Subtask T016: Consume the disposition and preserve no-op GREEN arms

**Purpose**: Convert WP01 through WP03 evidence into an explicit authorization gate so
WP04 never performs speculative production work.

**Steps**:

1. Read every `agent action review` row in `disposition-matrix.md`, including:
   - baseline SHA and exact registered CLI argv;
   - workspace classification (`ready`, `recoverable`, `unavailable`, or
     `divergent`);
   - RED/GREEN verdict and `stop`/`continue` decision;
   - the six-surface before/after delta;
   - the reached production owner and placement result.
2. Read WP03's approved result and determine whether lifecycle reconciliation was:
   - activated and implemented for a proven RED;
   - characterized as already correct and left unchanged; or
   - blocked, in which case WP04 must not begin production edits.
3. Build a local implementation checklist mapping each review row to exactly one
   action:
   - `GREEN/stop`: no production edit; retain as a regression witness;
   - `RED/continue — ordering`: activate T017 through T019;
   - `RED/continue — review placement`: activate T020 only when the reached owner
     is one of WP04's workflow paths and the reviewed matrix checkpoint already records adjacency;
   - `RED owned elsewhere`: stop and report the ownership boundary.
4. Confirm the RED was witnessed on WP01's planning base through the registered
   command, not created by a helper-only test or a production monkeypatch.
5. Preserve the witness expectations. Do not weaken a failing assertion, relax a
   zero-delta requirement, or reclassify a row merely to make implementation green.
6. If all review rows are GREEN/stop, make no production changes. Run T021's
   aggregate verification, record the no-op disposition in the handoff, and finish.

**Files**:

- Read-only input: `disposition-matrix.md` and WP01 through WP03 evidence.
- No owned file must change for an all-GREEN disposition.

**Validation**:

- Every activated production edit points to a named RED/continue row.
- Every GREEN/stop row has zero behavior-changing diff.
- The handoff states whether T017–T020 were activated, skipped, or stopped.

### Subtask T017: Establish non-mutating readiness before claim

**Purpose**: For a proven review-ordering RED, ensure the command classifies and
establishes workspace readiness before any durable `for_review -> in_review`
mutation, using one reconciled identity throughout.

**Steps**:

1. Trace the live review command from `workflow.py` into `workflow_executor.py`.
   Identify the current ordering of:
   - Mission/WP context resolution;
   - canonical workspace resolution;
   - readiness/materialization;
   - review-lock acquisition;
   - status claim and WP tracking mutation;
   - commit routing and prompt/executor handoff.
2. Retain the canonical resolver as the single authority. Do not compose a branch,
   lane name, or `.worktrees/...` path at the command call site.
3. Introduce or adapt the smallest internal input/result shape needed to carry the
   same `ResolvedWorkspace` value through the review path. Prefer an existing typed
   value over a new parallel model.
4. Split readiness into a non-mutating classification/validation phase and, only
   for `recoverable`, an invocation-owned acquisition phase.
5. Order the path so `ready` and successfully recovered workspaces reach claim,
   while `unavailable` and `divergent` results fail before:
   - event append or materialization;
   - WP tracking mutation;
   - any PRIMARY or COORD ref movement;
   - lock persistence or orphaned worktree creation.
6. Preserve actionable diagnostics from the canonical seam. The error must name
   the missing path or lane and a supported recovery action without leaking a raw
   `FileNotFoundError` or inventing a misleading coordination path.
7. Preserve JSON/human output ownership. Do not print incidental diagnostics to
   stdout in JSON mode.
8. Add focused tests in the owned test modules for ordering and identity reuse.
   Assert readiness occurs before claim and the downstream consumer receives the
   exact resolved object or immutable identity, not a recomputed equivalent.

**Files**:

- `src/specify_cli/cli/commands/agent/workflow.py`: minimal orchestration ordering
  and canonical resolved-workspace threading.
- `src/specify_cli/cli/commands/agent/workflow_executor.py`: executor input and
  readiness-before-mutation sequencing where this module owns it.
- `tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py`: focused
  stale/recoverable/unavailable readiness tests.
- `tests/agent/test_workflow_review_lane_gate.py`: review claim-order and identity
  propagation tests.

**Validation**:

- An unavailable/divergent workspace produces no claim call and no durable delta.
- A ready/recoverable workspace reaches claim only after readiness succeeds.
- Resolver invocation count and object-identity assertions prove resolve-once.
- Existing healthy review behavior and output remain unchanged.

### Subtask T018: Track invocation-owned recovery and lock resources

**Purpose**: Make acquisition ownership explicit so later cleanup removes only
resources created or acquired by the current review invocation.

**Steps**:

1. Inspect `_prepare_review_workspace` and the current review-lock API before
   designing a result. Reuse existing ownership signals where present.
2. Represent, without global mutable state, the resources the current invocation
   owns, including at minimum:
   - whether it created or attached the lane worktree;
   - the exact canonical workspace path;
   - whether it acquired the review lock;
   - the lock identity/token needed for safe release.
3. Do not infer ownership from `Path.exists()` after the operation. Record it at
   the acquisition boundary so a pre-existing worktree is never mistaken for an
   invocation-created one.
4. Preserve the existing behavior for a workspace that was already ready:
   - do not recreate it;
   - do not mark it invocation-created;
   - acquire only the resources the review action already requires.
5. For a recoverable husk, allow materialization only after WP03/canonical
   reconciliation confirms an agreeing existing branch.
6. For branch absence or identity divergence, return refusal without attempting
   worktree creation or lock acquisition.
7. Ensure active-lock conflicts remain hard failures and do not remove the other
   invocation's lock.
8. Extend the husk tests to cover pre-existing versus invocation-created resources,
   lock conflicts, worktree-add failure, and successful acquisition ordering.

**Files**:

- `workflow.py` and/or `workflow_executor.py`: invocation-local ownership result
  and propagation, kept at the narrow existing review seam.
- `test_workspace_husk_resolution_1833.py`: resource-ownership and failure tests.
- `test_workflow_review_lane_gate.py`: live review orchestration assertions.

**Validation**:

- Tests distinguish pre-existing, recovered-by-this-invocation, and unavailable
  workspaces.
- No failed acquisition leaves a lock or newly created path behind.
- No cleanup path removes a pre-existing worktree or another invocation's lock.
- No module-level receipt or mutable singleton becomes cleanup authority.

### Subtask T019: Compensate invocation-owned resources on later failure

**Purpose**: If claim, placement commit, prompt construction, or another later
review step fails after readiness, restore invocation-owned resources without
rolling back or deleting pre-existing authority.

**Steps**:

1. Enumerate failure points after readiness and before the command hands control to
   a successfully started reviewer. Tie each failure to its durable-state boundary.
2. Prefer ordering that prevents mutation. Compensation is a last resort for
   resources acquired during readiness, not a substitute for preflight.
3. Add one structured cleanup path that runs for every post-readiness exception or
   refusal and receives the invocation ownership record from T018.
4. Release a review lock only when this invocation acquired that lock.
5. Remove a worktree only when this invocation created or attached it and removal
   is safe through the existing Git/worktree abstraction.
6. Never remove a pre-existing worktree, delete persisted workspace context, erase
   a canonical lane branch, or fall back to raw directory deletion.
7. Preserve the original failure as the operator-visible outcome. Cleanup failure
   may add diagnostic context but must not turn the command into success or hide the
   primary cause.
8. Add failure-injection tests at meaningful later boundaries. Each test snapshots
   before/after lock state, path existence, status/WP bytes, refs, and porcelain as
   appropriate to the reached boundary.
9. Prove idempotent or guarded cleanup: repeated cleanup attempts do not remove
   resources the invocation no longer owns.

**Files**:

- `workflow.py` / `workflow_executor.py`: narrow exception-safe lifetime around
  readiness, claim, and executor handoff.
- Both owned test modules: focused compensation and non-ownership regression tests.

**Validation**:

- Later failure releases invocation-owned lock state.
- Later failure removes only an invocation-created worktree.
- Pre-existing workspace and lock authority remain untouched.
- The command remains non-zero and truthful when cleanup also reports a problem.

### Subtask T020: Handle a proven placement RED without absorbing issue #2160

**Purpose**: If and only if WP01 proves the review bookkeeping bundle commits at
the wrong authority, adapt review to the existing partition-aware commit seam while
recording the finding as adjacent to #2160 rather than claiming or closing it.

**Steps**:

1. Activate this subtask only when the disposition matrix has an explicit
   `RED/continue — placement` review row with ref/path-set evidence.
2. Before production editing, confirm the reviewed matrix checkpoint already
   recorded the #2160-adjacent residual in `issue-matrix.md`. WP04 does not own
   that planning surface and must
   not edit it directly.
3. Do not assign, claim, comment on, close, or otherwise change issue #2160.
4. Trace the repository's canonical partition-aware commit router. Confirm how it
   maps WORK_PACKAGE_TASK tracking to PRIMARY and STATUS_STATE to COORD under the
   stored topology.
5. Adapt the review path to that seam. Do not hand-roll two Git commits, commit the
   mixed bundle through the coordination transaction, or fall back to whichever
   checkout happens to exist.
6. Preserve one truthful aggregate outcome: success only when every required
   placement commit succeeds and all relevant checkouts are clean.
7. On placement refusal/failure, preserve the contract established by the RED:
   never report overall success alongside an uncommitted tracking mutation.
8. Add tests that enumerate new commit ranges and committed path sets, proving WP
   tracking lands on PRIMARY and status lands on COORD where topology requires it.
9. If no canonical partition-aware seam can be consumed within owned files, stop
   and return an architectural ownership finding. Do not invent one inside workflow.

**Files**:

- Production edits remain limited to `workflow.py` and `workflow_executor.py`.
- Focused placement assertions belong in `test_workflow_review_lane_gate.py`.
- `issue-matrix.md` is orchestrator-owned, reviewed read-only input; PR progress is
  orchestrator-owned follow-through, not a WP04 file edit.

**Validation**:

- Commit path sets prove canonical PRIMARY/COORD partitioning.
- Failure cannot produce success-plus-dirt or success-plus-warning.
- No implementation or tracker action claims to resolve #2160.
- GREEN placement rows remain behaviorally unchanged.

### Subtask T021: Run aggregate GREEN gates and preserve the WP01 witness

**Purpose**: Demonstrate that every activated remediation closes its exact RED,
healthy review behavior remains stable, and no gate was weakened to manufacture a
green result.

**Steps**:

1. Before production changes, author and commit the test-only desired contract for
   the four named review IDs while preserving rows 1–8 and all frozen surfaces
   byte-for-byte against the approved WP02 blob.
2. Run the four exact pytest IDs on the dependency base and prove them RED for the
   reviewed production behavior. Only then begin production implementation.
3. Require every former RED/continue review row to be GREEN with six-surface
   observation and coverage intact; expected deltas may change only for the four
   named nodes and only to the pre-production desired contract.
4. Require every original GREEN/stop row and healthy positive-control twin to stay
   GREEN with byte-compatible public outcomes.
5. Run the complete owned test surfaces:

   ```bash
   PWHEADLESS=1 uv run --extra test pytest \
     tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py \
     tests/agent/test_workflow_review_lane_gate.py -q
   ```

6. Run the dependency-ordered acceptance module using the exact command documented
   by WP01. Do not substitute a narrower helper test or change the test-only
   desired contract after production implementation begins.
7. Run focused regression suites named by WP01 through WP03 for healthy workspace and lane
   lifecycle behavior, including WP03's integration module when WP03 activated.
8. Run lint and strict typing on every changed production/test file, including
   the justified out-of-map acceptance witness:

   ```bash
   uv run ruff check \
     src/specify_cli/cli/commands/agent/workflow.py \
     src/specify_cli/cli/commands/agent/workflow_executor.py \
     tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py \
     tests/agent/test_workflow_review_lane_gate.py
   uv run mypy --strict \
     src/specify_cli/cli/commands/agent/workflow.py \
     src/specify_cli/cli/commands/agent/workflow_executor.py
   ```

9. Run the architectural checks relevant to shared-package boundaries, placement,
   dead symbols, and terminology. At minimum include:

   ```bash
   PWHEADLESS=1 uv run --extra test pytest \
     tests/architectural/test_shared_package_boundary.py \
     tests/architectural/test_no_legacy_terminology.py -q
   ```

   Add any non-vacuous placement/authority guard identified by WP01, WP03, or WP04.
10. Run `git diff --check` and verify every relevant checkout has clean porcelain
   after the test run.
11. Report activated versus skipped subtasks, exact commands, counts, the approved
    WP02 blob, the one-line out-of-map rationale, and any
    remaining externally owned issue in the review handoff. Never retry-to-green.

**Files**:

- No new files are expected.
- Test updates remain within the two owned test modules plus the single justified
  out-of-map acceptance file.
- The out-of-map acceptance diff is limited to the pre-production desired-outcome
  branches for the four exact review IDs; frozen construction/observation surfaces
  and earlier reviewed evidence remain immutable.

**Validation**:

- The dependency-ordered acceptance witness is GREEN, with rows 1–8 and common
  six-surface coverage preserved from the approved WP02 blob.
- Existing healthy review tests and all three owned test modules are GREEN.
- Ruff, strict mypy, architectural checks, terminology guard, and diff check pass.
- Relevant worktrees are clean and the DRAFT PR boundary remains intact.

### Subtask T022: Correct rejected scaffolding and land Wave A

**Purpose**: Establish the reviewed API/type/port surface without executing a composite
transaction or treating rejected discovery work as authority.

**Steps**:

1. Record commits `7e8f6f579`, `52d5f02ab`, and scaffold `98ccc4dc` as
   **rejected, non-authorizing discovery evidence**. `98ccc4dc` is rejected specifically
   because switching the exact alias before migrating the live
   `BookkeepingTransaction.commit` constructor breaks that canonical producer. None of
   their code, expectations, producer sets, or green results satisfy a gate.
2. The next commit MUST be a test-only correction/remediation RED before any production
   change. Remove the Wave A exact-alias-now expectation and replace/delete rejected
   scaffolding without weakening frozen witness or unrelated assertions. Pin:
   - full future data-only `PlacementCommitReceipt` and `PlacementCommitFailure`;
   - the existing legacy `CommitReceipt` as a distinct class with exact existing
     fields, constructor signature, behavior, and identity during Wave A;
   - real regression
     `tests/specify_cli/coordination/test_transaction.py::test_append_event_then_commit_returns_receipt`;
   - four-value result vocabulary, Mission Management signature/ports, Git import
     boundary, and mutation-free `CompositeImplementationUnavailable`.
   Record SHA, failing assertions, `git diff --name-status`, and assertion/fixture audit.
3. Every producer/import/signature mutation probe MUST run only in a collision-safe
   disposable copy. The scanner/gate accepts an explicit root/path; copy the declared
   committed preimage plus minimal package tree/config into a unique temporary root,
   mutate only that copy, prove rejection there, and delete the root in cleanup. Assert
   canonical source hashes equal committed preimage before and after. Never mutate the
   shared lane/repository, even under a lock/`finally`; crash, SIGKILL, overlap, and
   parallel readers must be unable to observe probe bytes.
4. Land a bounded Wave A remediation behavior commit whose production diff is
   allowlisted to exactly two files:
   - `src/specify_cli/coordination/types.py`: retain full future data-only
     `PlacementCommitReceipt` and `PlacementCommitFailure`, while restoring the legacy
     `CommitReceipt` fields/constructor/behavior/identity byte-compatible and distinct;
   - `src/specify_cli/status/review_transaction.py`: enums, frozen dataclasses,
     protocols, public entry signature, and the unavailable scaffold unchanged.
5. The AST/diff allowlist MUST reject every other production path and any executable
   scaffold behavior. The entry immediately raises
   `CompositeImplementationUnavailable` before resource creation/attachment, any
   resource/review/status/Git lock, owner/ref call, delta, receipt, pending outbound,
   channel, or retry. It returns no terminal result. Prohibit `__init__.py` exports,
   workflow wiring, Git/status/router/outbound calls, hidden fallback, compatibility
   execution, owner construction, ref inspection/movement, and terminal return.
6. Run all corrected Wave A tests, including the real transaction regression, and
   record RED then GREEN SHAs/assertions. Prove the remediation diff/AST exactly match
   the two-file allowlist, legacy/future identities remain distinct, and the canonical
   hashes never changed during probes. Do not begin B1 until all corrected Wave A tests
   are GREEN.

**Validation**:

- `98ccc4dc` remains historical/non-authorizing and is remediated test-first.
- Corrected Wave A has test-only RED before its bounded two-file remediation commit.
- The unavailable entry is observably mutation-free and the AST/diff gate is exact.
- Active IDs, frontmatter ownership, lane-d, topology, frozen witness, and history are
  unchanged.

### Subtask T023: Land B1 first-terminal foundation and B2 error receipt adaptation

**Purpose**: Make the first truthful terminal outcomes possible, then add the sole
typed post-commit failure seam. Each slice is exactly test-only RED then behavior.

**Steps**:

1. **B1 test-only RED commit**: through real PRIMARY/COORD owners, pin all of:
   - exact two-receipt `committed` and under-lock `refused` with zero delta, receipts,
     lower-seam commits, and outbound attempts;
   - missing COORD receipt, wrong hash, duplicate destination, mismatched IDs,
     unattributed movement, and the complete negative matrix as
     `compensation_failed`;
   - result/receipt/evidence inheritance of one invocation/transaction ID pair;
   - real resource/review → `feature_status_lock` → Git entry/exit order, one outer
     status-lock acquisition, lifecycle reuse of the held lock/transaction, and no
     implicit lower-seam commit;
   - Git-owned pending `LocalCommit` plus every named outbound intent staged before
     mutation; committed is only releasable after local terminal, while refused and
     every non-success discard/suppress with zero persistence/send/delivery attempts;
   - byte-compatible default non-composite safe-commit and `LocalCommit` behavior;
   - the final FR-011 `CommitReceipt is PlacementCommitReceipt` switch together with
     migration of **every** existing canonical producer/adapter to the expanded
     constructor, the real legacy transaction regression, the final non-vacuous
     shrink-only producer gate, and both complete PRIMARY/COORD success adapters. The
     RED must prove the alias switch cannot pass independently of full migration.
   On Wave A, this RED MAY stop at explicit unavailable, but instrumentation must prove
   zero locks, owners, refs, lower-seam commits, outbound evidence, or retry before it.
2. **B1 behavior commit**: atomically migrate every existing canonical producer/
   adapter to the full `PlacementCommitReceipt` constructor, add both complete PRIMARY
   and COORD success adapters, finalize the non-vacuous shrink-only producer allowlist,
   and switch to exact `CommitReceipt = PlacementCommitReceipt` in this same commit.
   No intermediate revision may switch the alias while a legacy constructor call
   remains. Also implement only prepare, pre-mutation deferral/staging/disposition,
   fixed lock/lifecycle seam, real owners, receipt/identity evaluator, and typed
   `committed`/`refused`/indeterminate `compensation_failed`. B1 wholly and solely owns
   the alias switch, complete migration, final producer set, and both success adapters.
   It performs no retry, compensation, persistence/send, or delivery. Rerun corrected
   Wave A, the real transaction regression, and B1 GREEN before B2.
3. **B2 test-only RED commit**: drive the real Git commit seam through post-commit
   caller-state recovery failure. Require the placement owner to raise
   `PlacementCommitFailure` carrying the complete receipt and recovery diagnostic;
   assert unrelated staged/unstaged/untracked bytes, modes, full index patch, and full
   worktree patch. A hook is stimulus only and records a reached marker.
4. **B2 behavior commit**: add generic Git post-commit evidence, caller-state capture/
   restore, and the sole Git-evidence→`PlacementCommitFailure` adapter with complete
   error-receipt propagation. Git remains coordination-type-free. No later slice may
   add/change an adapter or claim a fresh RED for this behavior. Rerun Wave A, B1, and
   B2 GREEN before T024.

**Non-fakeable RED rule**:

- Production owners are never monkeypatched. Direct typed evaluator cases use typed
  I/O; real-owner cases must reach the named production boundary. Hooks/helpers inject
  stimuli only. A fixture/setup failure, unobserved hook, synthetic receipt producer,
  test-only fake owner, or post-B1 unavailable failure does not authorize behavior.

**Validation**:

- Each B1/B2 test commit precedes exactly one behavior commit and all prior slices stay
  GREEN.
- B1 alone can produce truthful first terminals and atomically owns the final FR-011
  alias, all producer migrations, final producer gate, both success adapters, and
  `LocalCommit` deferral/staging.
- B2 alone owns typed post-commit failure and its complete error receipt.

### Subtask T024: Land B3 CAS, B4 compensation, and B5 retry/delivery

**Purpose**: Add the canonical compensation primitive before consuming it, then finish
Mission Management retry and post-commit delivery. Each slice is exactly RED→behavior.

**Steps**:

1. **B3 test-only RED commit**: exercise `git/ref_advance.py` with real refs/worktrees;
   prove expected-old CAS success, foreign-advance refusal without overwrite, and
   checked-out-worktree resync only after CAS. Only genuinely concurrent foreign-writer
   and synchronized post-CAS obstruction cases use deterministic fixture-owned
   `ready`/`release`/`done` files or pipes carrying destination ref and relevant OIDs;
   assert reached/order. No sleeps, timing windows, polling retry, or retry-to-green.
2. **B3 behavior commit**: implement canonical expected-old CAS plus post-CAS resync
   with exact ref/worktree/repair evidence. Never force over a foreign OID. Rerun Wave
   A and B1–B3 GREEN before B4.
3. **B4 test-only RED commit**: cover both composite paths:
   - pre-commit PRIMARY refusal after COORD lands compensates the COORD receipt;
   - reuse B2's error-carried PRIMARY receipt after both placements land, consume it
     without reconstruction, and compensate strict PRIMARY→COORD.
   Assert exact terminal refs/resources/caller state; mismatch is
   `compensation_failed`. Instrument the real outer `feature_status_lock`: the same
   continuously held instance spans every reverse CAS, successful-CAS resync, and
   terminal observation with no release/reacquisition or lower-seam reacquisition.
4. **B4 behavior commit**: compose B2 receipt propagation with B3 CAS/resync under that
   continuously held lock. Add no adapter, private ref mutation, receipt
   reconstruction, or B1/B2 adapter change. Rerun Wave A and B1–B4 GREEN before B5.
5. **B5 test-only RED commit**: prove workflow invokes Mission Management once with
   resolved identity + invocation ID. Mission Management alone retries only private
   `RetryablePreDurablePrepareConflict`, raised before resource creation/attachment,
   any resource/review/status/Git lock, owner/ref/delta, receipt, pending outbound,
   compensation, or channel attempt. Retry retains only invocation ID, mints a fresh
   transaction ID, and begins with empty receipt/compensation/outbound/channel/resource/
   owner state; assert no evidence leak. All terminal, post-lock, and post-durable
   outcomes are never retried. Use typed evidence/counters, not concurrency barriers.
   Also prove committed-only delivery, zero non-success attempts, middle-channel
   `dispatch_failed`, and later-channel `dispatch_succeeded` without changing local
   committed.
6. **B5 behavior commit**: Mission Management owns the private prepare retry loop;
   workflow calls once. Prepare runs before resource creation/attachment and all locks.
   After success, create/attach owned resources then acquire resource/review lock →
   `feature_status_lock` → Git locks with no remaining retry boundary. Add only internal
   retry and post-commit per-channel delivery. B1 `LocalCommit` deferral/staging and B2
   error receipt are regression-only. Preserve the four-value terminal vocabulary and
   default non-composite behavior. Rerun every Wave A/B slice GREEN.

**Non-fakeable RED rule**:

- B3 concurrent stimuli use barriers; deterministic CAS evaluation, B4 hook failures,
  B5 retry, and delivery use real boundaries plus typed evidence/counters/simple
  reached markers. Production owners are never monkeypatched. Every RED after B1 must
  reach its named production boundary; an unavailable/setup/fake-owner failure is not
  implementation authority.

**Validation**:

- B3 is GREEN before B4 consumes CAS/resync; B4 is GREEN before B5.
- Every test-only RED commit precedes its one behavior commit and all prior slices are
  rerun GREEN.
- Continuous-lock compensation, fresh retry state, terminal no-retry, and committed-
  only delivery match plan `b9dce9b` exactly.

### Subtask T025: Run aggregate two-layer proof and architectural gates

**Purpose**: Prove the registered operator contract and direct domain contract without
weakening historical evidence.

**Steps**:

1. Audit the exact commit chain: rejected historical scaffold `98ccc4dc`, mandatory
   Wave A correction RED → bounded two-file remediation, then B1 RED → atomic alias/
   producer-migration behavior, B2 RED → behavior,
   B3 RED → behavior, B4 RED → behavior, and B5 RED → behavior. For every pair record
   SHAs, failing/passing assertions, `git diff --name-status`, production/test paths,
   and proof all earlier slices were GREEN before the next RED.
2. Re-run the corrected Wave A AST/diff allowlist against its remediation commit and
   current tree. Prove only the two authorized files changed, the legacy transaction
   constructor/identity remained valid and distinct, and no prohibited execution was
   introduced. Preserve `7e8f6f579`, `52d5f02ab`, and `98ccc4dc` as rejected/non-
   authorizing evidence. Re-run every mutation probe against a disposable explicit-root
   copy and prove canonical source hashes remain the committed preimage.
3. Registered-CLI real-Git layer: run the unchanged 12-row witness plus focused
   workspace/workflow tests. Prove operator output, durable refs/bytes/index/worktrees,
   clean refusal, and zero outbound attempts on non-success.
4. Direct Mission Management real-Git layer: run every
   `tests/specify_cli/status/test_review_transaction.py` node and inspect typed result,
   ID inheritance, receipts, `PlacementCommitFailure`, reverse compensation, unrelated
   sentinels, continuous-lock terminal observations, fresh retry attempts with no
   evidence leakage, and per-channel delivery evidence.
5. Run all owned coordination, Git, sync, workflow, and workspace tests. Include real
   adapter regressions for `coordination/outbound.py`, transaction deferred outbound,
   and `sync/local_commit.py`.
6. Run this exact serial focused GREEN command. It covers every WP04-owned test path,
   the frozen witness, and the complete WP02/WP03 regression floor:

   ```bash
   PWHEADLESS=1 uv run --extra test pytest -n0 -q \
     tests/agent/test_workflow_review_lane_gate.py \
     tests/architectural/test_review_receipt_producer_gate.py \
     tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py \
     tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py \
     tests/specify_cli/coordination/test_commit_router_partition.py \
     tests/specify_cli/coordination/test_status_transition.py \
     tests/specify_cli/coordination/test_transaction.py \
     tests/specify_cli/coordination/test_types.py \
     tests/specify_cli/coordination/test_outbound.py \
     tests/specify_cli/git/test_commit_helpers.py \
     tests/specify_cli/git/test_ref_advance.py \
     tests/specify_cli/sync/test_local_commit.py \
     tests/specify_cli/status/test_review_transaction.py \
     tests/status/test_work_package_lifecycle.py \
     tests/specify_cli/cli/commands/agent/test_tasks_mark_status.py \
     tests/specify_cli/cli/commands/agent/test_tasks_mark_status_seam.py \
     tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py \
     tests/specify_cli/cli/commands/agent/test_tasks_move_task_placement.py \
     tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py \
     tests/specify_cli/coordination/test_commit_router_placement.py \
     tests/integration/test_lane_lifecycle_sync.py
   ```

7. Run Ruff across every owned Python path:

   ```bash
   uv run ruff check \
     src/specify_cli/cli/commands/agent/workflow.py \
     src/specify_cli/cli/commands/agent/workflow_executor.py \
     src/specify_cli/coordination/types.py \
     src/specify_cli/coordination/transaction.py \
     src/specify_cli/coordination/status_transition.py \
     src/specify_cli/coordination/outbound.py \
     src/specify_cli/coordination/commit_router.py \
     src/specify_cli/git/commit_helpers.py \
     src/specify_cli/git/ref_advance.py \
     src/specify_cli/status/review_transaction.py \
     src/specify_cli/status/work_package_lifecycle.py \
     src/specify_cli/sync/local_commit.py \
     tests/agent/test_workflow_review_lane_gate.py \
     tests/architectural/test_review_receipt_producer_gate.py \
     tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py \
     tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py \
     tests/specify_cli/coordination/test_commit_router_partition.py \
     tests/specify_cli/coordination/test_status_transition.py \
     tests/specify_cli/coordination/test_transaction.py \
     tests/specify_cli/coordination/test_types.py \
     tests/specify_cli/coordination/test_outbound.py \
     tests/specify_cli/git/test_commit_helpers.py \
     tests/specify_cli/git/test_ref_advance.py \
     tests/specify_cli/sync/test_local_commit.py \
     tests/specify_cli/status/test_review_transaction.py \
     tests/status/test_work_package_lifecycle.py
   ```

8. Run strict mypy on every owned production target:

   ```bash
   uv run mypy --strict \
     src/specify_cli/cli/commands/agent/workflow.py \
     src/specify_cli/cli/commands/agent/workflow_executor.py \
     src/specify_cli/coordination/types.py \
     src/specify_cli/coordination/transaction.py \
     src/specify_cli/coordination/status_transition.py \
     src/specify_cli/coordination/outbound.py \
     src/specify_cli/coordination/commit_router.py \
     src/specify_cli/git/commit_helpers.py \
     src/specify_cli/git/ref_advance.py \
     src/specify_cli/status/review_transaction.py \
     src/specify_cli/status/work_package_lifecycle.py \
     src/specify_cli/sync/local_commit.py
   ```

9. Run the new producer gate plus the shared-package and terminology gates, then the
   whitespace/error check, using these exact commands:

   ```bash
   PWHEADLESS=1 uv run --extra test pytest -n0 -q \
     tests/architectural/test_review_receipt_producer_gate.py \
     tests/architectural/test_shared_package_boundary.py \
     tests/architectural/test_no_legacy_terminology.py
   git diff --check
   ```
10. Verify the frozen witness blob and post-`980eae6a9` diff are unchanged; verify the
   WP02 shared-file exception remained limited to the two named files and its approved
   blob/ref still matches.
11. Verify all relevant worktrees are clean and PR #2641 remains DRAFT. Report exact
   correction/Wave/slice commit SHAs, commands, counts, real-boundary and concurrent
   stimulus markers, receipt producer set, scaffold AST/diff audit, continuous-lock
   trace, caller-state sentinels, fresh-retry-state proof, and channel evidence to the
   independent reviewer.

**Validation**:

- Both real-Git layers pass without a public JSON or persisted result artifact.
- Every Wave A/B RED precedes its behavior, all prior slices remain GREEN, and every
  applicable real boundary/stimulus marker is reached.
- Historical approvals, rows 1–8, witness expectations, lane-d, and topology remain
  unchanged.
- All quality, architectural, ownership-exception, and DRAFT-PR gates pass.

## Amendment Definition of Done

- [ ] Rejected `7e8f6f579`/`52d5f02ab`/`98ccc4dc` remain non-authorizing; the scaffold
      break is remediated by a mandatory test-only RED before production.
- [ ] Wave A and each B1–B5 test-only RED precede exactly one authorized behavior
      commit, with all prior slices GREEN.
- [ ] Corrected Wave A preserves distinct legacy `CommitReceipt` compatibility plus
      future types, stays mutation-free, and touches exactly two allowlisted files.
- [ ] `PlacementCommitReceipt` is the sole class and `CommitReceipt` is its exact alias.
- [ ] Git remains independent of coordination receipt types.
- [ ] B1 atomically owns the final exact alias, every canonical producer/adapter
      migration, final producer set, both success adapters, pending `LocalCommit`, and
      named-channel staging/disposition; no intermediate broken revision exists.
- [ ] B2 wholly owns typed post-commit failure and complete error-receipt adaptation.
- [ ] B3 canonical expected-old CAS/refusal/resync is GREEN before B4 consumes it.
- [ ] Both B4 compensation paths run PRIMARY→COORD as applicable under one continuously
      held status lock through CAS, resync, and terminal observation.
- [ ] Mission Management alone owns the B5 pre-durable prepare retry; workflow calls
      once, only invocation ID survives, and no post-lock/post-durable outcome retries.
- [ ] All safe-commit-affected caller state, including unrelated sentinels, is restored
      or the result is `compensation_failed`.
- [ ] LocalCommit/SaaS/offline/dossier effects have zero attempts before local commit
      and on every non-success; best-effort channel failure does not stop later channels.
- [ ] Registered-CLI and direct Mission Management real-Git proof layers pass.
- [ ] Receipt producer gate is non-vacuous and shrink-only; mutation probes use only
      collision-safe disposable explicit-root copies and canonical hashes stay fixed.
- [ ] Frozen witness, historical approvals/activity, shared-file exception, lane-d,
      topology, DRAFT PR, and operator-only merge boundary remain intact.

## Historical Definition of Done — retained as review evidence

The checklist below records T016–T021's original contract. It is not an active
implementation checklist and does not authorize adjacent-ticket or witness changes.

- [ ] WP01 through WP03 are approved/done and their dispositions were consumed before
      any WP04 production edit.
- [ ] Every production edit is authorized by a named `RED/continue` review row.
- [ ] Every `GREEN/stop` arm remains a no-op with regression evidence.
- [ ] Review workspace classification/readiness occurs before claim mutation.
- [ ] One reconciled workspace identity is passed through readiness and execution.
- [ ] Invocation-owned worktree and lock resources are tracked explicitly.
- [ ] Later failure compensates only resources owned by this invocation.
- [ ] Unavailable/divergent refusal leaves status, tracking bytes, refs, locks,
      paths, and porcelain unchanged.
- [ ] If placement work activated, canonical PRIMARY/COORD routing is proven by
      commit path sets and #2160 remains unclaimed/unclosed by this Mission.
- [ ] Earlier approved evidence is immutable; the test-only desired contract was
      RED before production and is GREEN after changes limited to the four exact
      review IDs.
- [ ] Owned tests, healthy regressions, Ruff, strict mypy, architectural checks,
      terminology guard, and `git diff --check` are GREEN.
- [ ] Review handoff lists exact evidence and skipped conditional work.
- [ ] Changes remain on the resolved WP04 lane and target
      `fix/stale-workspace-reproduction`; the PR remains DRAFT.

## Historical Risks — retained as review evidence

- **Speculative repair**: implementing an imagined review defect would violate
  FR-003. Mitigation: T016 makes the reviewed matrix an explicit authorization gate.
- **Second resolver**: recomputing a path in workflow can disagree with lifecycle.
  Mitigation: pass one canonical `ResolvedWorkspace` identity end to end.
- **Premature mutation**: claim before readiness recreates the reported atomicity
  gap. Mitigation: classify and establish readiness before any durable transition.
- **Over-cleanup**: compensation could delete a pre-existing worktree or foreign
  lock. Mitigation: record ownership at acquisition and clean only owned resources.
- **Placement scope creep**: the mixed bundle can pull #2160 into this Mission.
  Mitigation: require exact RED evidence, record adjacency, and consume only the
  existing partition-aware seam.
- **False green**: helper tests can bypass the registered CLI and real Git state.
  Mitigation: the dependency-ordered real-CLI witness remains the acceptance
  authority, frozen common six-surface measurements prevent coverage shrinkage,
  and earlier reviewed commits preserve the original RED evidence.
- **Output corruption**: incidental logs can break one-document JSON output.
  Mitigation: assert structured output and keep diagnostics on the owning channel.

## Historical Reviewer Guidance — retained as review evidence

The reviewer must load a reviewer profile distinct from `python-pedro` and reject
the WP if implementation begins without a WP01 RED/continue disposition. Review
the aggregate diff against the following questions:

1. Does review establish workspace readiness before `for_review -> in_review`?
2. Is exactly one canonical workspace identity resolved and threaded through the
   whole invocation, or does any call site reconstruct branch/path state?
3. Are created worktrees and acquired locks recorded as invocation-owned at the
   moment of acquisition?
4. Does cleanup leave pre-existing and foreign resources untouched?
5. Do unavailable/divergent cases prove an empty ref range and byte-identical
   status/WP evidence, not merely a non-zero exit?
6. If placement changed, are PRIMARY and COORD path sets proven through the
   canonical router, with #2160 only referenced as adjacent?
7. Is the approved WP02 blob recorded, are rows 1–8 and frozen surfaces unchanged,
   and did the four exact review IDs go RED in a test-only commit before the same
   contract passed through the registered CLI with real Git/worktree state?
8. Are GREEN/no-op arms preserved without production churn?
9. Are all new branches directly exercised without suppressions, complexity growth,
   timing-only assertions, or retry-to-green behavior?
10. Does the branch/workspace evidence show the resolved WP04 lane targets
    `fix/stale-workspace-reproduction` and the PR remains DRAFT?

Approve only when the durable outcome, structured result, resource lifetime, and
canonical placement all tell the same story.

## Amendment Reviewer Guidance

Use a reviewer profile distinct from the implementer and reject unless:

1. All three rejected commits remain non-authorizing; mandatory corrected Wave A and
   B1–B5 RED→behavior ordering is complete with no frozen-witness drift.
2. Corrected Wave A is the exact two-file remediation: legacy `CommitReceipt` remains
   distinct/compatible, future types remain available, and review raises unavailable
   before every prohibited boundary. Mutation probes touch only disposable roots.
3. B1 atomically switches the exact alias with every producer migration and final
   producer gate, and alone owns PRIMARY+COORD success adapters, first-terminal
   evaluation, held-lock lifecycle behavior, and pending channel staging/disposition.
4. B2 alone owns post-commit failure/error receipt; Git stays coordination-type-free
   and default non-composite behavior remains byte-compatible.
5. B3 CAS/refusal/post-CAS resync is proven independently before B4 compensation uses
   it; only actual concurrent B3 stimuli use ready/release/done barriers.
6. B4 proves both compensation paths, no receipt reconstruction, caller-state fidelity,
   strict reverse order, and one continuously held outer status lock through terminal.
7. B5 proves one workflow call, Mission Management-only pre-durable prepare retry,
   fresh attempt state, no evidence leak, no terminal/post-lock/post-durable retry, and
   committed-only best-effort delivery with later-channel continuation.
8. Registered-CLI/direct real-Git layers, all boundary/stimulus markers, producer gate,
   Ruff, strict mypy, architecture/terminology gates, and diff check pass.
9. The WP02 shared-file exception, lane-d/topology, prior approvals, historical T016–
   T021 text, and activity lines remain unchanged.
10. No public JSON result, persisted result artifact, topology recomputation, non-DRAFT
    PR transition, or operator-only merge-boundary violation was introduced.

## Activity Log

- 2026-07-14T18:54:19Z – codex – shell_pid=138606 – Assigned agent via action command
- 2026-07-14T19:18:48Z – codex – shell_pid=138606 – Ready for independent review: atomic review workspace preparation and partition-aware claim commit; exact rows 9-12 and full acceptance witness green.
- 2026-07-14T19:20:12Z – codex – shell_pid=138606 – Started review via action command
- 2026-07-14T19:27:56Z – user – Moved to planned
- 2026-07-14T19:29:23Z – codex – shell_pid=138606 – Assigned agent via action command
- 2026-07-14T19:42:29Z – codex – shell_pid=138606 – Ready for independent re-review: both placement refs proven from pre-emission hashes; partial outcomes refused; invocation cleanup ownership and failure precedence covered.
- 2026-07-14T19:43:14Z – codex – shell_pid=138606 – Started review via action command
- 2026-07-14T19:45:17Z – user – Moved to planned
- 2026-07-14T19:47:01Z – codex – shell_pid=138606 – Assigned agent via action command
- 2026-07-14T20:00:55Z – user – shell_pid=138606 – Blocked at reviewed ownership boundary: zero-delta split-placement requires upstream composite PRIMARY+COORD transaction receipt and conditional compensation; operator scope decision required.
