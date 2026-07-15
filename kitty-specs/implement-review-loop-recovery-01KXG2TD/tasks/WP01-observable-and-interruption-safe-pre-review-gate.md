---
work_package_id: WP01
title: Observable and Interruption-Safe Pre-Review Gate
dependencies: []
tracker_refs:
  - "#2573"
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-005
- NFR-006
- C-001
- C-002
- C-003
- C-004
- C-005
- C-006
- C-007
- C-008
- C-009
planning_base_branch: fix/implement-review-loop-recovery
merge_target_branch: fix/implement-review-loop-recovery
branch_strategy: Planning artifacts for this mission were generated on fix/implement-review-loop-recovery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/implement-review-loop-recovery unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Red-first implementation and verification
assignee: ''
shell_pid_created_at: "1784035860.82"
agent: "codex:default:reviewer-renata:reviewer"
shell_pid: "664495"
history:
- at: '2026-07-14T12:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/pre_review_gate.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/review/test_pre_review_gate_engine.py
- tests/review/test_pre_review_gate_integration.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_escape_hatch.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Observable and Interruption-Safe Pre-Review Gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Make the default real pre-review gate visibly alive in human mode and machine-safe in JSON mode while preserving one canonical gate authority. Timeout and catchable cancellation must terminate and reap the owned child process, produce a typed local refusal, and stop before deliverable auto-commit or transition mutation.

The first commit in this WP must contain only the new exact-entry acceptance test and must be proven RED on the planning base. Production implementation begins only after that evidence exists.

## Context

The current `move-task WP## --to for_review` path prints one notice and blocks in `subprocess.run(..., timeout=300)`. Timeout is collapsed into `NO_COVERAGE`, so warn-default policy can still advance the transition. The current call order also auto-commits dirty lane deliverables before the gate.

The reviewed plan corrects both authority and ordering:

- `pre_review_gate.py` owns scope, process launch, one timeout deadline, liveness cadence, typed termination, child cleanup/reap, lock release, JUnit parsing, and verdict classification.
- `tasks_move_task.py` owns human/JSON presentation and the decision whether a typed outcome permits mutation.
- Dirty implementation files remain part of prospective gate scope, but tool-owned recovery writes occur only after the gate permits progress.
- Test-owned writes are preserved and surfaced. Never reset or restore operator/test changes.

Read before editing:

- `.kittify/charter/charter.md`
- `kitty-specs/implement-review-loop-recovery-01KXG2TD/spec.md`
- `kitty-specs/implement-review-loop-recovery-01KXG2TD/plan.md`
- `kitty-specs/implement-review-loop-recovery-01KXG2TD/research.md`
- `kitty-specs/implement-review-loop-recovery-01KXG2TD/contracts/pre-review-observability.md`
- `kitty-specs/implement-review-loop-recovery-01KXG2TD/quickstart.md`

## Branch Strategy

- **Planning base branch**: `fix/implement-review-loop-recovery`
- **Merge target branch**: `fix/implement-review-loop-recovery`
- **Execution**: run `spec-kitty agent action implement WP01 --agent codex`; consume the workspace path returned by Spec Kitty and do not reconstruct it.
- **Landing**: the orchestrator may later push the authorized branch and open a PR against `origin/main`, but that PR must remain DRAFT. Do not mark ready, auto-merge, merge, or push `origin/main`.

## Subtasks & Detailed Guidance

### Subtask T001 – Commit the exact-entry RED acceptance test

**Purpose**: Establish non-vacuous ATDD evidence that the planning base has only a one-shot notice and no continuing liveness.

**Steps**:

1. Create `tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py`.
2. Invoke the pre-existing Typer command surface for `agent tasks move-task WP01 --to for_review`; do not test only `_mt_run_pre_review_gate`.
3. Replace only the canonical gate-runner ownership seam with a synchronized controllable double. Preserve the real command orchestration and output selection.
4. Assert an initial indication plus more than one heartbeat at the configured cadence. The existing one-shot notice must not satisfy the test.
5. Use events/fake monotonic time rather than real 30- or 65-second sleeps.
6. Run the test against the untouched planning-base production code and capture the expected failure reason.
7. Commit only this acceptance test. Verify its commit precedes every production-code commit in this WP.
8. Stop for the first internal review checkpoint: preserve the RED command/output and confirm the test is non-vacuous before T002 begins.

**Files**:

- Create `tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py`.

**Validation**:

- The test fails for missing ongoing liveness, not fixture setup or an unrelated guard.
- `git show --name-only` for the RED commit lists only the acceptance test.
- Do not weaken timing/cadence assertions after implementation.

### Subtask T002 – Preserve typed terminal outcomes in the canonical runner

**Purpose**: Stop erasing timeout and cancellation into generic `NO_COVERAGE` while keeping one gate authority.

**Steps**:

1. Extend the canonical runner data model in `pre_review_gate.py` with typed completion states covering completed, timed out, cancelled, launch failed, and incomplete output.
2. Replace string-based timeout inference with typed state carried through `HeadRunResult`, verdict composition, or an equivalently cohesive result.
3. Preserve existing behavior for launch failures, missing JUnit, unverified baseline, new failures, and no new failures.
4. Ensure timeout and cancellation remain distinguishable at the CLI seam without a second timer or parsing `reason` text.
5. Keep the public surface as small as possible and avoid a universal output/progress abstraction.

**Files**:

- Modify `src/specify_cli/review/pre_review_gate.py`.
- Extend `tests/review/test_pre_review_gate_engine.py`.

**Validation**:

- Existing incomplete-run tests remain truthful.
- New tests prove timeout and cancellation are typed and cannot become `NO_COVERAGE`.
- No duplicated 300-second deadline exists in `tasks_move_task.py`.

### Subtask T003 – Implement polling, liveness, termination, reap, and lock release

**Purpose**: Give the authority owning the subprocess enough control to emit liveness and cleanly finish timeout/cancellation.

**Steps**:

1. Replace the blocking scoped-test invocation with a polling process lifecycle owned by `pre_review_gate.py`.
2. Accept a presentation-only progress callback and injectable monotonic/wait collaborators. JSON mode will pass a no-op callback.
3. Emit liveness on a bounded schedule without delaying quick completion.
4. On timeout or catchable cancellation, target only the runner-owned child/process tree: request termination, wait a bounded interval, escalate to kill, and reap.
5. Make POSIX and Windows behavior explicit. Use platform-shaped tests/doubles; never sweep unrelated host PIDs.
6. Release the advisory scoped-run lock on completion, exception, timeout, and cancellation.
7. Capture output and preserve the existing JUnit parsing authority; do not stream pytest prose to CLI stdout.
8. Prevent captured-pipe backpressure deadlock by using a proven concurrent-drain or repeated bounded-`communicate` design; polling without draining is not acceptable.

**Files**:

- Modify `src/specify_cli/review/pre_review_gate.py`.
- Extend `tests/review/test_pre_review_gate_engine.py` and `tests/review/test_pre_review_gate_integration.py`.

**Validation**:

- Fast completion emits no artificial heartbeat and exits promptly.
- Synchronized tests prove multiple heartbeats, exception propagation, termination escalation, child reap, and lock release.
- A child that writes more than pipe-buffer capacity continues to make progress, emits heartbeats, completes or terminates, preserves captured diagnostics, and releases the lock.
- Tests use events or controllable doubles, not timing races or retries.
- Stop for the second internal review checkpoint after T003: review the typed runner, process cleanup, pipe drainage, and platform branches before CLI mutation-order work.

### Subtask T004 – Move recovery mutations behind the gate and retain prospective scope

**Purpose**: Satisfy zero Spec Kitty-owned residue without hiding dirty deliverables from the tests being selected.

**Steps**:

1. Map the exact current mutation order in `tasks_move_task.py`: deliverable auto-commit, override persistence, arbiter persistence, transition emit, and WP persistence.
2. Split read-only preflight from mutating recovery so the `for_review` gate precedes every applicable write.
3. Move `_mt_commit_lane_deliverables` after a non-timeout/non-cancelled gate outcome permits progress.
4. Extend prospective changed-file derivation to include relevant target-branch commits plus staged, unstaged, and untracked deliverables.
5. Preserve existing readiness and guard semantics after successful gate execution. Freeze non-`for_review` override/arbiter ordering with regression evidence.
6. Do not reset or restore dirty worktrees on interruption.
7. Compare pre/post checkout state and surface paths created during the gate as a human warning and additive JSON gate metadata; do not claim authorship beyond identifying the new paths.

**Files**:

- Modify `src/specify_cli/cli/commands/agent/tasks_move_task.py`.
- Extend the new observability test and existing integration coverage.

**Validation**:

- A dirty-deliverable timeout/cancellation creates no auto-commit.
- The dirty file still participates in prospective scope.
- Successful execution retains existing auto-commit/readiness behavior.

### Subtask T005 – Map typed outcomes to human and JSON command results

**Purpose**: Keep human progress useful and JSON stdout singular while refusing timeout/cancellation before mutation.

**Steps**:

1. Human mode supplies the initial notice and heartbeat callback to the canonical runner.
2. JSON mode supplies a no-op callback. No progress prose may reach stdout.
3. At the exact gate seam, map typed timeout and cancellation to a nonzero local result containing additive gate metadata and `transition_applied: false`.
4. Catch `KeyboardInterrupt` narrowly around the gate after canonical child cleanup. Do not add a broad `BaseException` catch around `_do_move_task`.
5. Ensure success, gate failure, timeout, and cancellation each produce exactly one parseable JSON stdout document in JSON mode.
6. Preserve the existing opt-in block/force policy for ordinary gate verdicts.
7. Stop for the third internal review checkpoint after T005: validate exact human/JSON output and prove timeout/cancellation cannot call any mutating leg before the broad acceptance matrix.

**Files**:

- Modify `src/specify_cli/cli/commands/agent/tasks_move_task.py`.
- Extend `tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py`.

**Validation**:

- Parse captured stdout directly with one `json.loads` call.
- Timeout/cancellation never invoke finalization, transition emit, or WP persistence.
- Human liveness never claims a passing verdict.

### Subtask T006 – Complete the interruption and compatibility acceptance matrix

**Purpose**: Prove the design under real orchestration boundaries and preserve delivered #2573 controls.

**Steps**:

1. Snapshot all Spec Kitty-owned residue facets before timeout/cancellation: event log, materialized lane, WP tracking content, git HEAD/commits, and tool-owned dirty paths in planning, coordination, and lane checkouts.
2. Assert zero deltas afterward. Add a test-owned sentinel write and prove it is preserved, appears in the human warning and additive JSON metadata, and is not cleaned.
3. Exercise explicit sync-disable and minimal-import controls as truthful pre-I/O skips: no workspace, no subprocess, and no passing/verified-clean representation. Do not compare a skip outcome with the enabled real-gate verdict.
4. Add an isolated-child SIGKILL scenario followed by the existing authoritative status/reconciliation read. Prove prior lane and absence of a new transition event; do not claim rollback. The test harness, not product cleanup, must reap any isolated child left by SIGKILL.
5. Preserve the existing skip flag, synchronization-disable environment variables, initial notice, and default-path behavior from `35f3a2206`.
6. Run focused suites without retries.

**Files**:

- Extend both `tests/review/test_pre_review_gate_*.py` files.
- Extend both focused CLI pre-review test files.

**Validation**:

- Every terminal case has a direct acceptance assertion.
- Timeout/catchable-cancellation product cleanup leaves no child and releases the lock; the SIGKILL harness separately reaps its child before teardown.
- Existing control tests are not weakened or replaced by mocks below their promised seam.

### Subtask T007 – Run quality gates and preserve Mission evidence

**Purpose**: Close the WP with reproducible evidence and durable Mission learnings.

**Steps**:

1. Run the focused commands from `quickstart.md` through `uv run`, with no retries.
2. Run `uv run ruff check` and `uv run mypy` on touched source/tests; fix causes rather than adding blanket suppressions.
3. Run `uv run pytest tests/architectural/test_no_legacy_terminology.py -q`.
4. Check touched functions remain within complexity 15 and repeated non-trivial literals are constants.
5. Include proposed concise entries for all three Mission tracers in the implementation handoff; the orchestrator applies them on the planning branch because code-change WPs cannot own `kitty-specs/` paths.
6. Record the RED commit, implementation commits, test commands/results, platform limitations, and any remaining UI-side quality work for the draft PR.

**Files**:

- Do not edit `kitty-specs/` Mission artifacts or the ignored second brain from the implementation worktree; return proposed tracer entries in the handoff.

**Validation**:

- `git diff --check` is clean.
- Focused tests, lint, typing, and terminology gates pass.
- Commit history proves red-first ordering.

## Definition of Done

- [ ] T001 exact-entry acceptance test was separately committed RED before production code.
- [ ] Human mode receives initial and continuing bounded liveness without delaying fast completion.
- [ ] JSON stdout is exactly one parseable document for all required outcomes.
- [ ] Timeout/cancellation remain typed and cannot fall through as generic `NO_COVERAGE`.
- [ ] Runner-owned children are terminated, escalated if necessary, reaped, and locks released.
- [ ] Deliverable auto-commit and every applicable Spec Kitty mutation occur after the gate permits progress.
- [ ] Prospective scope includes relevant dirty deliverables.
- [ ] Timeout/cancellation leave zero Spec Kitty-owned residue; test-owned writes are preserved and surfaced.
- [ ] SIGKILL reconciliation proves authoritative prior state without rollback claims.
- [ ] Existing skip/sync-disable/notice behavior remains green, truthful, and pre-I/O; no skip is represented as passing or verified clean.
- [ ] Focused tests, ruff, mypy, terminology, complexity, and diff gates pass without retries.
- [ ] The handoff contains proposed tracer entries and complete draft-PR evidence for the orchestrator.

## Risks

- **Orphaned process trees**: constrain cleanup to the runner-owned process tree, test terminate-to-kill escalation, and verify reap before return.
- **Second timeout authority**: keep the deadline exclusively in `pre_review_gate.py`; the CLI consumes typed results only.
- **JSON corruption**: use a no-op progress callback in JSON mode and parse captured stdout directly in tests.
- **Hidden dirty files**: derive prospective scope before auto-commit from committed and working-tree changes.
- **Operator data loss**: never reset/restore worktrees; preserve and surface test-owned writes.
- **Flaky cadence tests**: combine fake-time cadence tests with event-synchronized real-mechanism cleanup tests; do not retry-to-green.
- **Guard-order regressions**: freeze the ordered mutation map and existing non-`for_review` paths with focused tests.

## Reviewer Guidance

Review the RED commit first. Reject if it does not invoke the Typer entry point, fails for an unrelated reason, includes production code, or no longer remains meaningful after implementation.

This WP is intentionally one atomic package at 7 subtasks/~330 lines. Require internal review checkpoints after T001, T003, and T005. Splitting would either strand the exact-entry test red after the runner-only slice or overlap the runner/CLI contract surfaces.

Then verify authority and cleanup boundaries:

- only the canonical gate runner owns timeout/process lifecycle;
- the CLI does not parse error strings or control the child;
- timeout/cancellation cannot reach auto-commit, finalization, emit, or persistence;
- JSON cancellation uses one local envelope and a narrow catch;
- child/process-tree cleanup is bounded and cross-platform-shaped;
- test-owned writes are never destructively cleaned;
- delivered controls and ordinary verdict policy remain compatible.

Use independent review execution and require concrete command output. Do not approve based solely on mocked unit tests when process cleanup or exact CLI behavior is claimed.

## Activity Log

- 2026-07-14T12:16:35Z – system – Prompt created via governed tasks phase.

### Updating Status

Status is managed through the append-only event log. Use canonical Spec Kitty action/status commands; do not edit lane fields in frontmatter.
- 2026-07-14T12:31:13Z – codex:default:python-pedro:implementer – shell_pid=138606 – Assigned agent via action command
- 2026-07-14T12:58:17Z – codex:default:python-pedro:implementer – shell_pid=138606 – Ready for review: observable typed gate lifecycle, pre-mutation interruption refusal, and focused compatibility evidence
- 2026-07-14T12:59:02Z – codex:default:reviewer-renata:reviewer – shell_pid=138606 – Started review via action command
- 2026-07-14T13:07:04Z – user – Moved to planned
- 2026-07-14T13:08:54Z – codex:default:python-pedro:implementer – shell_pid=138606 – Started implementation via action command
- 2026-07-14T13:29:56Z – codex:default:python-pedro:implementer – shell_pid=138606 – Cycle 2 ready: Windows descendant cleanup, complete refusal snapshots, and exact-command SIGKILL reconciliation validated
- 2026-07-14T13:31:05Z – codex:default:reviewer-renata:reviewer – shell_pid=664495 – Started review via action command
