---
divio_type: explanation
audience: agentic-framework-core-team
updated: 2026-08-23
---

# Research: Durable Concurrent Review-Cycle Records

## Decision: Use a checkout-wide verdict-save queue

**Rationale**: Review-cycle allocation is protected only by a per-mission status lock, while the later evidence commit competes for checkout-wide Git state. A mission-independent lock rooted at `kernel.git_topology.git_common_dir` serializes linked worktrees and missions that share that state. `filelock` already supplies the repository's cross-platform process-locking convention. The queue is synchronous and lives only for the CLI invocation; no daemon or background service is needed.

**Alternatives considered**:

- Keep the existing short index-lock probes: rejected because a non-success result can still be reduced to a warning and then reported as command success.
- Isolated index plus compare-and-swap retries: rejected by the operator as unnecessary complexity for a rare path.
- Extend the status lock across Git: rejected because it violates C-002 and couples two different authorities.
- Serialize every Spec Kitty commit: rejected because the shared-index risk here is bounded to verdict evidence saves.

## Decision: Wait at most 10 seconds, then refuse explicitly

**Rationale**: The second save waits in line using the lock library's timeout, measured inside the command process with a monotonic clock. Ten seconds is the operator-confirmed bound. Timeout maps to a typed, nonzero busy result and performs no automatic business retry.

**Alternatives considered**:

- Four collision retries: rejected because retry count does not express a stable time bound and preserves race-dependent behavior.
- Indefinite waiting: rejected because it can stall automation without a diagnosable outcome.
- Background retry: rejected because it needs lifecycle ownership and contradicts the no-daemon decision.

## Decision: Keep the status lock and verdict queue distinct

**Rationale**: The queue may span evidence allocation/write and the evidence Git commit, but the short review-cycle allocation/status-lock section used by the new evidence path is released before that Git operation. Event emission occurs after the queue is released. The acquisition rule for this path is therefore: verdict queue may precede the short allocation-lock section; that allocation lock must never precede queue acquisition or span the evidence Git operation. Existing authoritative status-transaction locking is outside this invariant and remains unchanged. This meets C-002 and avoids a cross-lock deadlock.

**Alternatives considered**:

- Hold the queue through event emission: rejected because it nests verdict-evidence serialization with event-status serialization without adding durability; evidence is already verified before the event can claim success.
- Emit the event before committing evidence: rejected because it can make the current verdict reference unavailable evidence.

## Decision: Command orchestration is the sole queue owner

**Rationale**: The verdict command boundary in `tasks_verdict_persistence.py` acquires one queue lease before invoking the evidence operation and releases it before event execution. `cycle.py` exposes a non-acquiring persistence operation that assumes this lease; it must never reacquire the same file lock. This makes ownership explicit and prevents same-process nested acquisition from self-timing out.

**Alternatives considered**:

- Acquire inside both orchestration and `cycle.py`: rejected because separate `FileLock` objects for the same path can self-timeout.
- Acquire only inside `cycle.py`: rejected because orchestration also owns compensation and the required queue/event boundary.

## Decision: Retain failed evidence and adopt an identical retry

**Rationale**: The current exception path can delete a just-written artifact, while returned commit failures can leave an orphan. Both are unsafe. Automatic failures retain the file and expose its path. A retry derives identity from the canonical evidence content—mission, work package, reviewer, rendered body, and affected files—while ignoring allocation metadata. It adopts only an uncommitted candidate and verifies the governed destination ref before claiming success. This avoids manual cleanup without persisting a second verdict field.

**Alternatives considered**:

- Delete the artifact: explicitly rejected by the operator and destroys recovery evidence.
- Always allocate the next cycle: rejected because it strands the failed record and can duplicate the same submission.
- Persist a verdict fingerprint in the artifact: rejected because it risks turning evidence storage into a second verdict authority.

## Decision: Verify durability independently of the command result

**Rationale**: The existing headline test manually appends status events and permits the Markdown evidence record to be absent, so it does not prove SC-004. The replacement drives the real reviewer command with two `spawn` processes. Its oracle reads event history for the evidence reference and reads the artifact from the placement-selected Git ref. It treats two durable successes, or one durable success plus a causally proven 10-second queue timeout or independently valid state refusal, as the only valid outcomes. A deterministic concurrent case must also prove both writers succeed when the first lease clears within 10 seconds and policy permits both.

**Alternatives considered**:

- Trust `verdict_durably_persisted`: rejected because that is the output under test.
- Check only working-tree file existence or cleanliness: rejected because neither proves reachability from the governed destination.
- Keep the POSIX-only `fork` helper test: rejected because it bypasses the production entry point and cannot satisfy Windows portability.

## Decision: Make both protection legs mutation-sensitive

**Rationale**: SC-004 requires the suite to turn red when production event serialization is disabled and independently when evidence commitment is disabled. The event mutant must exercise the actual fallback and coordination transaction bindings, including `coordination.transaction.feature_status_lock`, and must include a coordination-topology negative control with seam-hit evidence. The evidence mutant fabricates a successful router result without changing Git; governed-ref read-back must reject it. Neither mutant may install a test-only production lock.

**Alternatives considered**:

- A negative control that drops only an event: rejected as incomplete evidence for SC-004.
- Natural-race-only testing: rejected as vacuous because a scheduler may never expose the vulnerable interleaving.

## Decision: Preserve local-only behavior and existing placement

**Rationale**: `--no-auto-commit` is an intentional, explicit non-durable mode. It bypasses the new queue and retains its current result classification. Automatic mode continues to use `CoordCommitRouter` and governed placement; durability is verified at the selected destination rather than inferred from topology flags.

**Alternatives considered**:

- Queue local-only writes: rejected because it broadens scope without providing durable success.
- Add special-case topology placement: rejected because it creates a second placement authority.

## Source evidence

- `src/specify_cli/review/cycle.py`: current allocation/write lock, separate commit path, warning-only returned failures, and deletion-on-exception behavior.
- `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`: current durability/result reduction and compensation behavior.
- `src/specify_cli/cli/commands/agent/tasks_move_task.py`: production verdict command sequencing and response envelope.
- `src/specify_cli/status/locking.py` and `src/kernel/git_topology.py`: cross-platform locking convention and canonical Git common-directory resolution.
- `src/specify_cli/coordination/commit_router.py`: canonical placement and commit seam.
- `docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md`: accepted evidence-placement decision.
- `tests/integration/test_review_durability_matrix.py`: current synthetic test, topology coverage, crash scenario, and false-green evidence gap.
- `tests/specify_cli/cli/commands/agent/test_move_task_durability.py`: real command/router fixtures and sanctioned local-only behavior.
- GitHub issue [#3235](https://github.com/Priivacy-ai/spec-kitty/issues/3235): observed shared-index refusal and missing-artifact failure shapes.
