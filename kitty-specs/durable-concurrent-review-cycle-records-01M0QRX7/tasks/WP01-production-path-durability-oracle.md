---
work_package_id: WP01
title: Production-Path Durability Oracle
dependencies: []
requirement_refs:
- C-003
- C-004
- FR-003
- FR-006
- FR-008
- NFR-001
- NFR-002
- NFR-005
planning_base_branch: mission/durable-concurrent-review-cycle-records
merge_target_branch: mission/durable-concurrent-review-cycle-records
branch_strategy: Planning artifacts for this mission were generated on mission/durable-concurrent-review-cycle-records. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/durable-concurrent-review-cycle-records unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Red-first acceptance
history:
- at: '2026-08-23T18:37:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/integration/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/integration/test_review_durability_matrix.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3235
---

# Work Package Prompt: WP01 – Production-Path Durability Oracle

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the `python-pedro` profile and behave according to its initialization, boundaries, directives, and tactics before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## ⚠️ IMPORTANT: Review Feedback

Before implementation, inspect `review_ref` with `spec-kitty agent tasks status --mission 01M0QRX7`. If feedback exists, treat every item as required work and append resolution evidence to the Activity Log.

## Objectives & Success Criteria

Replace the current issue #3235 concurrency test with a non-fakeable acceptance oracle. This WP is intentionally red-first: it may expose the current product defect, but the test itself must be correct, portable, deterministic enough for CI, and capable of failing independently when either durability protection is removed.

Completion requires:

- at least 50 synchronized rounds using two persistent, independent OS processes;
- the real `spec-kitty agent tasks move-task` command surface rather than direct cycle creation or manual event append;
- distinct reviewer identity and evidence content for the two submissions in every round;
- independent inspection of authoritative event history and committed evidence at the governed destination ref;
- exactly two permitted round outcomes: two distinct durable successes, or one durable success plus a causally proven 10-second queue timeout or independently valid state refusal;
- at least one deterministic concurrent two-success case proving that the waiting writer wins after the first lease clears within 10 seconds;
- one mutation control for production serialization/event integrity and one for evidence commitment;
- portable `spawn` workers with no `fork`, `SIGKILL`, `/tmp`, or shell-only assumptions.

Do not green-wash the existing failure. If the strengthened test is red before WP02–WP04, record that as the expected reproduction rather than weakening assertions.

## Context & Constraints

Read these before editing:

- `kitty-specs/durable-concurrent-review-cycle-records-01M0QRX7/spec.md`, especially FR-003, FR-006, FR-008, SC-001, SC-002, and SC-004.
- `kitty-specs/durable-concurrent-review-cycle-records-01M0QRX7/plan.md`, especially Verification Strategy.
- `kitty-specs/durable-concurrent-review-cycle-records-01M0QRX7/research.md`, especially independent durability verification.
- `kitty-specs/durable-concurrent-review-cycle-records-01M0QRX7/contracts/verdict-save-queue.md`.
- `.kittify/charter/charter.md`, especially ATDD-first, live evidence, mutation-sensitive gates, and red-main discipline.

Current defects to remove from the test:

- the existing worker manually appends events and bypasses the reviewer entry point;
- the headline assertion permits the Markdown evidence record to be absent;
- POSIX `fork` prevents honest Windows evidence;
- a negative control that drops only an event does not prove the evidence leg;
- working-tree existence does not prove the record is committed to the selected ref.

This WP owns only `tests/integration/test_review_durability_matrix.py`. Do not modify production code or other tests. A failing correct acceptance test is a valid output for this package; downstream WPs own the fix.

## Branch Strategy

- **Planning base branch**: `mission/durable-concurrent-review-cycle-records`
- **Final merge target**: `mission/durable-concurrent-review-cycle-records`
- **Execution**: run `spec-kitty agent action implement WP01 --agent codex --mission 01M0QRX7`; Spec Kitty allocates the actual lane worktree from `lanes.json`.
- Work only in that lane worktree and do not assume the project-root checkout is the implementation workspace.

## Subtasks & Detailed Guidance

### T001 – Drive the real reviewer command from spawned processes

**Purpose**: Ensure the acceptance path includes the production orchestration, evidence writer, commit router, event emission, and result shaping.

**Steps**:

1. Replace the helper that directly calls evidence creation and manually appends events.
2. Define module-level, pickleable worker functions suitable for `multiprocessing.get_context("spawn")`.
3. Keep two workers alive across at least 50 rounds so Windows startup cost is amortized.
4. Synchronize each pair with an explicit parent/worker barrier or message protocol.
5. Invoke the real Typer/root command runner inside each spawned process so baseline and mutation controls exercise the same production command while allowing the worker to install and prove its mutation seam. Do not add a production-only test hook.
6. Seed a separate WP in `in_review` for each round; both workers target the same WP for that round.
7. Give each submission distinguishable reviewer and body content.
8. Capture exit code, parsed JSON, stdout/stderr, and round/reviewer identity.

**Validation**:

- Prove the worker never calls `create_rejected_review_cycle` directly.
- Prove it never manually writes `status.events.jsonl`.
- Bound every process join and report actionable diagnostics on a hung child.

### T002 – Build the two-authority durability oracle

**Purpose**: Avoid trusting the result field whose correctness is under test.

**Steps**:

1. For each reported success, look up the exact returned `event_id` in authoritative event history rather than scanning for any plausible event.
2. Require that exact event to match mission, WP, reviewer, verdict, and the stable evidence pointer returned by that same command result.
3. Resolve the evidence destination through the existing placement seam.
4. Run `git show <destination-ref>:<relative-evidence-path>` and require it to succeed.
5. Parse or inspect the committed bytes and match the expected reviewer/body for that submission.
6. Reject evidence reachable only in the working tree, index, or wrong branch.
7. Reject duplicate pointers shared by two successful submissions.

**Validation**:

- A fabricated result flag without an event fails.
- A committed event with missing evidence fails.
- A file present locally but absent at the governed ref fails.

### T003 – Pin allowed outcomes and refusal non-vacuity

**Purpose**: Make the test accept legitimate state-machine contention without tolerating silent loss.

**Steps**:

1. Classify each round after both workers exit.
2. Accept two exit-zero durable outcomes only when both event/evidence pairs are distinct and complete.
3. Accept one durable success plus one explicit nonzero refusal only when the refusal contains a stable busy/persistence reason and claims no durability.
4. Require causal evidence for every refusal: either measured queue acquisition reaching the 10-second bound or an independently valid state-machine prohibition. Reject unexplained/immediate contention refusal.
5. Add a deterministic concurrent case in which both submissions remain state-valid, writer A holds and then releases the queue within 10 seconds, and waiting writer B subsequently completes; require two distinct durable pairs. A sequential or merely "controlled admissible" two-success proxy is insufficient.
6. Reject warning-only success, success with false durability, timeout-as-success, missing pointer, duplicate pointer, and uncommitted evidence.
7. Do not require natural races to choose a particular winner; deterministic queue-timeout non-vacuity belongs to WP04 after the queue is integrated.

### T004 – Serialization/event mutation control

**Purpose**: Prove the acceptance oracle observes production serialization rather than a test-only substitute.

**Steps**:

1. Enumerate and seam-hit the actual production event-serialization paths: the fallback command/emit bindings and the independent `specify_cli.coordination.transaction.feature_status_lock` binding used by coordination transactions. Include at least one coordination-topology negative control; do not assume two patched fallback names cover every topology.
2. Leave `review.cycle.feature_status_lock`, the verdict evidence path, and evidence commitment intact so allocation/evidence collisions cannot satisfy this mutant.
3. Use a role-ordered two-stage handshake around the real status-store replace seam: both workers capture the same authoritative preimage; writer A completes its replacement, read-back, and command return; only then writer B completes its stale replacement and read-back.
4. Add seam-hit counters proving the selected topology's real lock binding and both handshake stages executed.
5. Do not add a test lock around the product call.
6. Require both workers to exit normally with parseable durable-success envelopes and both committed evidence records to exist, then require the oracle's exact `missing_authoritative_event` classification.
7. Restore event locking and prove the identical schedule passes after implementation in both fallback and coordination transaction topologies.

### T005 – Independent evidence-commit mutation control

**Purpose**: Satisfy SC-004's second, independent negative control.

**Steps**:

1. Patch the commit seam inside each spawned command worker to return a fabricated `committed` result without modifying Git.
2. Leave event serialization intact so only the evidence leg is disabled.
3. Require a seam-hit handshake/counter and normal worker exits with parseable envelopes before judging the mutant.
4. Run the same durable oracle and require the exact `missing_committed_evidence` classification.
5. Keep this test distinct from an `unchanged` or event-drop case; broad `pytest.raises(AssertionError)` is not sufficient proof.

## Test Strategy

Canonical nodes:

```bash
uv run python -m pytest tests/integration/test_review_durability_matrix.py::test_sc004_two_concurrent_processes_never_clobber_a_verdict_over_50_iterations -n0 -q --tb=short
uv run python -m pytest tests/integration/test_review_durability_matrix.py::test_sc004_event_serialization_mutant_reports_missing_authoritative_event -n0 -q --tb=short
uv run python -m pytest tests/integration/test_review_durability_matrix.py::test_sc004_evidence_commit_mutant_reports_missing_committed_evidence -n0 -q --tb=short
```

Use these exact names when creating/renaming the nodes. Run all three individually while debugging. The final stress tests must run serially at the pytest layer because they own shared Git state internally.

## Risks & Mitigations

- **Vacuous two-success branch**: the same-WP FSM may consistently refuse one writer. The deterministic wait-in-line case must keep both concurrent submissions state-valid and prove the second waits then succeeds; a sequential proxy is prohibited.
- **Slow Windows execution**: use two persistent workers, not 100 cold starts.
- **Inactive subprocess mutation**: invoke the real in-process root command inside each spawned worker and require seam-hit handshakes before interpreting oracle output.
- **Wrong destination assertions**: query placement; never assume the primary branch.
- **Flakiness**: use synchronization, bounded joins, and deterministic fault seams; never retry-to-green.

## Review Guidance

Reject this WP if any success is accepted without both independent durable reads, if a helper bypasses the reviewer command, if a test-only lock makes the mutant safe, or if the evidence mutant does not turn the oracle red. Verify the test is honest on all platforms and that current production failure is documented rather than hidden.

## Definition of Done

- T001–T005 are recorded done via `spec-kitty agent tasks mark-status`.
- Named baseline, event-lock-mutant, and evidence-commit-mutant nodes execute; each mutant is killed for its exact expected classification with no skip, xfail, quarantine, retry-to-green, or broad exception acceptance.
- The current product's expected red/green state is clearly reported.
- No production file was modified.
- The WP is ready for an independent reviewer.

## Activity Log

- 2026-08-23T18:37:05Z – system – Prompt created.

Status is event-sourced. Use `spec-kitty agent tasks move-task WP01 --to for_review --mission 01M0QRX7` when implementation is ready for review.
