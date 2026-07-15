# Implementation Plan: Observable Pre-Review Gate

**Branch**: `fix/implement-review-loop-recovery` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `/home/jeroennouws/dev/spec-kitty/kitty-specs/implement-review-loop-recovery-01KXG2TD/spec.md`

## Summary

Preserve the existing pre-review scope and verdict authority while making the exact `move-task WP## --to for_review` path observable and interruption-safe. The selected design upgrades the canonical gate runner to own a cancellable, polling subprocess lifecycle with typed terminal outcomes. Human mode supplies a liveness callback, JSON mode supplies a no-op callback, and timeout or catchable cancellation returns a typed refusal before any transition or pre-gate recovery mutation.

The first implementation change is a separately committed acceptance test that fails on this planning base because the current synchronous call emits no continuing liveness. Implementation follows only after that RED commit exists.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer, Rich console, Python `subprocess`, pytest; existing process-management dependencies may be reused, with no new runtime dependency
**Storage**: Existing append-only `status.events.jsonl`, materialized Mission status, WP tracking files, and git commits; this Mission adds no storage schema
**Testing**: pytest with deterministic fake clock/wait/progress collaborators, focused CLI orchestration tests, existing pre-review regression tests, ruff, mypy, and architectural terminology gate
**Target Platform**: Cross-platform Python CLI; behavior must remain valid on Linux, macOS, and Windows-supported execution paths
**Project Type**: Single Python CLI repository
**Performance Goals**: Initial human indication within 2 seconds; heartbeat gaps no greater than 30 seconds; no artificial wait for gates finishing before the first heartbeat
**Constraints**: One JSON document on stdout; no transition mutation before gate success; existing 300-second gate bound and verdict semantics remain authoritative; complexity at or below 15
**Scale/Scope**: One command entry point, one orchestration seam, one existing gate engine, and focused acceptance/regression coverage

## Charter Check

*GATE: passed before research and re-checked after design.*

| Binding rule | Plan response | Result |
|---|---|---|
| Single canonical authority | `pre_review_gate.py` remains the sole scope/run/verdict, timeout, cancellation, child-termination, and reap authority; orchestration supplies presentation and interprets typed terminal outcomes. | PASS |
| Architectural alignment | The change stays at `_mt_run_pre_review_gate`, before `_mt_finalize_plan` and `_mt_execute`; no routing, status, or workspace authority moves. | PASS |
| ATDD-first | The first WP must commit a planning-base RED acceptance test separately before production code. | PASS |
| Tiered rigour | Exact timing, JSON integrity, interruption cleanliness, and regression controls receive focused acceptance coverage. | PASS |
| Terminology adherence | Mission and work-package language is used throughout; the terminology gate is part of validation. | PASS |
| Adversarial cadence | Post-spec completed; post-plan and post-tasks pointcuts are mandatory before implementation. | PASS |
| Canonical workflow and git discipline | Spec Kitty controls Mission state/workspaces; no direct push to `origin/main`; eventual PR remains draft. | PASS |
| Campsite cleaning and no suppression | Touched code must remain simpler or equivalent, with no blanket lint/type suppression and focused tests for new branches. | PASS |
| Mission tracers | The three required tracer files are initialized under `traces/` and updated during implementation. | PASS |

Post-design re-check: the selected managed-observation boundary does not add a second gate authority, state store, output framework, or recovery mechanism. All gates remain PASS.

## Architecture and Data Flow

```text
move-task command
  -> read-only target/workspace resolution and guard facts
  -> _mt_run_pre_review_gate
       -> resolve prospective changed-file scope, including dirty deliverables
       -> existing _mt_pre_review_gate_verdict
            -> existing evaluate_with_scope/evaluate_pre_review_gate
            -> canonical polling scoped-test runner
                 -> one timeout deadline
                 -> human progress callback or JSON no-op
                 -> child/process-tree terminate + reap on timeout/cancellation
                 -> typed completion / timeout / cancellation / run error
       -> timeout/cancellation: one local command result, then exit
       -> ordinary verdict: existing metadata/block policy
  -> pre-review recovery writes (including optional deliverable auto-commit)
  -> final guard decision
  -> _mt_finalize_plan
  -> _mt_execute (authoritative transition mutation)
```

The CLI owns only presentation and the decision whether execution may advance. It does not own a timer or subprocess handle and does not parse reason strings. The canonical gate engine owns the child process, its single deadline, liveness callback cadence, termination/reaping, JUnit interpretation, and typed terminal classification.

### Interruption boundary

The current call graph performs a lane-deliverable auto-commit inside `_mt_gather_review_facts` before the gate. That ordering cannot satisfy the specification. Implementation must split read-only preflight from mutating review recovery and run the gate before `_mt_commit_lane_deliverables`, review/arbiter persistence, `_mt_finalize_plan`, or `_mt_execute`. Prospective scope must include committed target-branch differences plus relevant staged, unstaged, and untracked deliverables so moving the auto-commit does not hide work from the gate.

Timeout and cancellation are typed terminal outcomes, distinct from ordinary `NO_COVERAGE`. The exact command seam maps either outcome to a nonzero local result with `transition_applied: false` and gate metadata, then exits before mutations. Launch failure, missing JUnit, or an unverified baseline retain their existing truth-preserving warn policy and are never inferred from timeout strings.

SIGKILL is explicitly outside in-process cleanup. Deterministic recovery means a subsequent status read/reconciliation derives truth from the append-only event log and reports that no transition event exists; this Mission does not add a recovery store.

## Project Structure

### Documentation (this Mission)

```text
/home/jeroennouws/dev/spec-kitty/kitty-specs/implement-review-loop-recovery-01KXG2TD/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── pre-review-observability.md
├── traces/
│   ├── approach.md
│   ├── design-decisions.md
│   └── tooling-friction.md
└── tasks.md                         # generated during the tasks phase
```

### Source Code (repository root)

```text
/home/jeroennouws/dev/spec-kitty/src/specify_cli/
├── cli/commands/agent/tasks_move_task.py    # command orchestration, output mode, mutation boundary
└── review/pre_review_gate.py                # existing canonical gate engine; minimal seam only if needed

/home/jeroennouws/dev/spec-kitty/tests/specify_cli/
├── cli/commands/agent/
│   ├── test_tasks_move_task_pre_review_gate_escape_hatch.py
│   └── test_tasks_move_task_pre_review_gate_observability.py

/home/jeroennouws/dev/spec-kitty/tests/review/
├── test_pre_review_gate_engine.py
└── test_pre_review_gate_integration.py
```

**Structure Decision**: Extend the existing command orchestration module and focused test neighborhood. Add no general progress package: this Mission's contract is deliberately local to one entry point.

## Selected Design

Extend `run_scoped_tests_at_head` in `pre_review_gate.py` into a testable polling runner. It owns process launch, the existing 300-second deadline, progress cadence, cross-platform bounded termination escalation, process reap, and lock release. Its typed result distinguishes at least completed, timed out, cancelled, launch failed, and incomplete output. `evaluate_with_scope` preserves timeout/cancellation as typed gate terminal states rather than collapsing them into `NO_COVERAGE`.

Cleanup is scoped to the runner-owned child/process tree: request graceful termination, wait for a short bounded interval, escalate to kill, then reap before releasing the advisory lock. POSIX and Windows branches must be explicit and exercised through platform-shaped doubles; no PID discovery or broad host-process sweep is permitted.

`tasks_move_task.py` supplies only an output-mode-aware progress callback and interprets typed gate results. Human mode uses the existing initial notice plus periodic heartbeat messages. JSON mode uses a no-op callback and emits exactly one established error/result envelope on timeout or cancellation, including `transition_applied: false` and additive gate metadata. Catching `KeyboardInterrupt` is narrow to the gate seam after the runner has terminated and reaped its child; there is no broad `BaseException` catch around the command.

The orchestration phase order is adjusted so no mutating recovery occurs before the gate. Read-only facts may be gathered first. Dirty lane deliverables are included in prospective scope and auto-committed only after a non-timeout/non-cancelled gate outcome permits progress. Override and arbiter persistence are outside the `for_review` path but are frozen by an ordered mutation-map regression test so future reordering cannot silently widen the promise.

### Alternatives considered

| Alternative | Decision | Rationale |
|---|---|---|
| Canonical polling runner with a CLI-supplied progress callback | Selected | Gives the gate authority one deadline and full child cleanup while keeping presentation local to the exact command. |
| Put the blocking gate in a worker thread and observe it from the CLI | Rejected | The CLI cannot terminate or reap the internally owned pytest child, and executor shutdown can hang or orphan work. |
| Stream pytest stdout/stderr directly | Rejected | Couples CLI liveness to runner output cadence, risks JSON corruption, and leaks noisy test output without solving silent tests. |
| Reduce the 300-second timeout or rely on the skip flag | Rejected | Hides rather than fixes observability, changes existing gate semantics, and does not satisfy default-path liveness. |
| Build a universal CLI progress subsystem | Rejected | Exceeds C-005 and creates a new cross-command contract for a one-entry-point residual. |

## Test Strategy

1. Commit a deterministic acceptance test that invokes the pre-existing Typer entry point `spec-kitty agent tasks move-task WP## --to for_review`. Substitute only a controllable long-running canonical gate runner at its ownership seam. Assert the initial indication plus multiple heartbeats/cadence so the one-shot planning-base notice fails. This commit must be RED before any production edit.
2. Unit-test the polling runner with fake monotonic time and synchronized process doubles: quick completion, multiple heartbeats, runner error, typed timeout, catchable cancellation, bounded termination escalation, child reap, and lock release.
3. Exercise human and JSON modes at the exact entry point. Capture streams separately; parse JSON directly and assert the nonzero timeout/cancellation envelope includes `transition_applied: false`.
4. For timeout and cancellation fixtures, snapshot and assert zero deltas across every Spec Kitty-owned residue facet: event log, materialized status, WP tracking content, git HEAD/commits, and tool-owned dirty paths for planning, coordination, and lane checkouts. Include a dirty-deliverable case proving no auto-commit precedes the gate. A separate fixture that writes a test-owned sentinel must prove it is preserved and surfaced, not cleaned.
5. Add an ordered mutation-map regression covering deliverable auto-commit, override persistence, arbiter persistence, transition emit, and WP persistence. The `for_review` gate must precede every applicable mutating leg.
6. Preserve explicit sync-disable/minimal-import as pre-I/O opt-outs: assert truthful skipped/unverified metadata, no workspace or subprocess activity, and no passing/verified-clean representation. Do not compare their outcome with a real enabled gate verdict.
7. Run an isolated-child SIGKILL/recovery case: terminate during the gate, then use the existing authoritative status/reconciliation read to prove the prior lane and absence of a new transition event without claiming rollback.
8. Retain fake-time cadence tests and add short synchronized real-mechanism tests for thread/process shutdown and output serialization; use events, not sleep-based races.
9. Preserve existing escape-hatch tests unchanged. Run focused tests without retries, then ruff/mypy on touched modules and the terminology architectural gate.

Timing tests use virtual/injected time and synchronization primitives, not 65-second sleeps. Short real-mechanism tests validate cleanup and serialization without using elapsed-time races.

## Complexity Tracking

No charter violation is planned. The managed helper must remain small and single-purpose; if orchestration complexity approaches the ceiling, progress formatting and observation mechanics are separated into pure/private helpers with direct tests.

## Implementation Concern Map

### Work-package atomicity rationale

The runner and CLI concerns remain one WP even though they use checkpointed commits. The exact-entry RED test cannot become green until both the canonical runner callback and CLI presentation seam exist; separating those surfaces would either leave an unapprovable red-only WP or create overlapping ownership across WPs. Review checkpoints are mandatory after the RED commit, canonical runner completion, and CLI outcome integration.

### IC-01 — Red-first observable contract

- **Purpose**: Prove the residual silent-liveness defect on the planning base and freeze the exact human/JSON contract before implementation.
- **Relevant requirements**: FR-001–FR-004, NFR-001, NFR-002, NFR-005, SC-001, SC-002, SC-005
- **Affected surfaces**: `tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py`, `contracts/pre-review-observability.md`
- **Sequencing/depends-on**: none
- **Risks**: A test that mocks below the orchestration seam or uses real 30-second waits would be vacuous or flaky.

### IC-02 — Managed gate observation

- **Purpose**: Give the canonical gate runner a polling lifecycle, typed terminal outcomes, and bounded child cleanup while accepting a presentation-only liveness callback.
- **Relevant requirements**: FR-001, FR-002, FR-006, NFR-001, NFR-004
- **Affected surfaces**: `src/specify_cli/review/pre_review_gate.py`, `src/specify_cli/cli/commands/agent/tasks_move_task.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: Cross-platform process-tree cleanup, exception propagation, accidental second timeout authority, lock release, and complexity growth.

### IC-03 — Output integrity and pre-mutation interruption

- **Purpose**: Keep JSON stdout singular, preserve typed timeout/cancellation, and ensure no pre-gate recovery or transition mutation occurs first.
- **Relevant requirements**: FR-003–FR-005, FR-007, NFR-002–NFR-004, SC-002–SC-004
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`, focused CLI acceptance fixtures
- **Sequencing/depends-on**: IC-02
- **Risks**: Rich output accidentally reaching stdout in JSON mode; broad exception handling swallowing cancellation; dirty deliverables omitted from prospective scope; child work surviving termination.

### IC-04 — Regression and governance closeout

- **Purpose**: Demonstrate delivered controls, architectural boundaries, quality gates, and tracer evidence remain intact.
- **Relevant requirements**: FR-006, NFR-004–NFR-006, SC-004, SC-005
- **Affected surfaces**: existing escape-hatch tests, targeted gate tests, `traces/`, draft PR evidence
- **Sequencing/depends-on**: IC-01–IC-03
- **Risks**: Weakening existing assertions, retry-to-green, or presenting mocked unit evidence as end-to-end proof.

## Delivery and PR Boundary

Implementation and independent review use Spec Kitty work-package workspaces. After acceptance and local Mission merge, the authorized branch may be pushed and a PR opened against `origin/main`, but the PR must remain **DRAFT**. The orchestrator must not mark it ready, enable auto-merge, merge it, or push directly to `origin/main`.
