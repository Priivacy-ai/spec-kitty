# Mission Specification: Observable Pre-Review Gate

**Mission**: `implement-review-loop-recovery-01KXG2TD`
**Mission ID**: `01KXG2TDVPTZSYY58E578T5RX3`
**Type**: software-dev
**Status**: Draft
**Claimed implementation issue**: [#2573](https://github.com/Priivacy-ai/spec-kitty/issues/2573), limited to the residual default pre-review path described below

## Purpose

**TL;DR**: Make the default pre-review gate observably alive and interruption-safe without corrupting machine-readable output.

The exact entry point `spec-kitty agent tasks move-task WP## --to for_review` still runs its real pre-review test gate synchronously and without continuing liveness feedback. The underlying test process can run for up to 300 seconds, leaving a human operator unable to distinguish useful work from a hang. The existing skip flag, environment escape hatch, initial notice, and sync-disable handling were already delivered by commit `35f3a2206`; this Mission must preserve, not reimplement, those behaviors.

This Mission covers only the default non-skipped gate execution in human-output and JSON-output modes, plus interruption during the gate phase before transition mutation begins.

## Intent Summary

- **Primary actor**: a maintainer or orchestration agent moving one work package to `for_review`.
- **Trigger**: `spec-kitty agent tasks move-task WP## --to for_review` reaches the default real pre-review gate without a skip or escape hatch.
- **Desired outcome**: a human can see continuing liveness, a machine receives one valid JSON document, and a pre-mutation timeout or catchable cancellation leaves no transition residue.
- **Invariant**: before the gate has completed successfully, interruption must not create or materialize a work-package transition.
- **Boundary**: this is not a universal command-output, status-routing, workspace-resolution, or synchronization redesign.

## User Scenarios & Testing

### Scenario 1 — Human-output liveness

- **Actor**: a maintainer running the exact entry point in its normal human-output mode.
- **Trigger**: the real pre-review gate continues beyond its initial notice.
- **Outcome**: the maintainer receives an initial progress indication within 2 seconds and periodic liveness at intervals no greater than 30 seconds until the gate returns.
- **Exception**: if the gate finishes in under 30 seconds, no artificial delay or redundant heartbeat is required; the final result remains truthful.

### Scenario 2 — JSON-output integrity

- **Actor**: an orchestration agent invoking the exact entry point in JSON mode.
- **Trigger**: the real pre-review gate runs long enough that progress information is relevant.
- **Outcome**: standard output contains exactly one parseable JSON document. Progress is conveyed only through a channel that cannot corrupt that document or through final structured gate metadata.
- **Exception**: a gate timeout or failure still produces one parseable JSON result describing the gate outcome; human-oriented progress prose never appears alongside the JSON document on standard output.

### Scenario 3 — Timeout before transition mutation

- **Actor**: a maintainer whose real pre-review gate reaches its time bound.
- **Trigger**: timeout occurs while the command is still in the gate phase and before any transition mutation.
- **Outcome**: the work package remains in its prior state and the result identifies the timeout.
- **Exception**: the timeout leaves no new event-log append, materialized status change, work-package tracking mutation, placement commit, or Spec Kitty-owned checkout dirtiness. Files written independently by invoked tests are preserved and surfaced, never destructively cleaned by transition recovery.

### Scenario 4 — Catchable cancellation before transition mutation

- **Actor**: a maintainer cancelling the command with an interruption the process can catch.
- **Trigger**: cancellation arrives during the gate phase and before transition mutation.
- **Outcome**: the command terminates with a truthful cancellation result and the work package remains in its prior state.
- **Exception**: an uncatchable process kill is not promised in-process rollback; subsequent recovery or reconciliation must be able to establish the authoritative state.

### Scenario 5 — Delivered controls remain honest

- **Actor**: a maintainer using the already-delivered skip, escape-hatch, or sync-disable behavior.
- **Trigger**: one of those existing controls is active.
- **Outcome**: its planning-base behavior remains unchanged, and disabling synchronization cannot manufacture a passing pre-review verdict.
- **Exception**: this regression scenario does not require changes to other synchronization paths or a new control.

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | In human-output mode, the default real pre-review run for `spec-kitty agent tasks move-task WP## --to for_review` MUST show an initial progress indication within 2 seconds of entering the gate phase. | Confirmed |
| FR-002 | While that human-mode gate remains active, the command MUST provide a liveness indication at least once every 30 seconds until the gate completes, times out, or is cancelled. | Confirmed |
| FR-003 | In JSON mode, the command's standard output MUST contain exactly one parseable JSON document for success, gate failure, timeout, or catchable cancellation. | Confirmed |
| FR-004 | JSON-mode progress MUST use a channel that cannot corrupt standard-output JSON or MUST be represented in the final structured gate metadata; this requirement establishes no universal output contract for other commands. | Confirmed |
| FR-005 | A timeout or catchable cancellation during the gate phase before transition mutation MUST preserve the prior work-package state and report that no transition was applied. | Confirmed |
| FR-006 | The planning-base skip flag, environment escape hatch, initial notice, and sync-disable behavior delivered by `35f3a2206` MUST remain behaviorally unchanged; disabling synchronization MUST NOT turn a failing, unavailable, timed-out, or cancelled gate into a passing gate result. | Confirmed |
| FR-007 | An uncatchable process kill during the pre-mutation gate phase MUST have a deterministic recovery or reconciliation outcome that can establish whether authoritative state changed, without claiming in-process rollback. | Confirmed |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|---|---|---|---|
| NFR-001 | Human liveness latency | Initial progress appears within 2 seconds; consecutive liveness indications are no more than 30 seconds apart during a gate lasting at least 65 seconds. | Confirmed |
| NFR-002 | JSON integrity | Across success, failure, timeout, and catchable-cancellation acceptance cases, 100% of standard-output payloads parse as exactly one JSON document with no leading or trailing progress prose. | Confirmed |
| NFR-003 | Pre-mutation interruption cleanliness | For every timeout and catchable-cancellation fixture, there are 0 new event-log appends, 0 materialized status changes, 0 WP tracking mutations, 0 placement commits, and 0 Spec Kitty-owned dirty paths in planning, coordination, or lane checkouts. Test-owned writes are excluded from the zero-residue claim, preserved, and surfaced without destructive cleanup. | Confirmed |
| NFR-004 | Explicit skip honesty | In 100% of explicit sync-disable and minimal-import cases, the command reports a truthful skipped/unverified gate outcome, touches no gate workspace or subprocess, and never represents the result as passing or verified clean. | Confirmed |
| NFR-005 | Red-first proof | At least one acceptance test for the residual liveness defect is RED on the Mission planning base and GREEN after implementation; its failing-test commit precedes and is separate from every implementation commit. | Confirmed |
| NFR-006 | Regression containment | Targeted tests covering the delivered `35f3a2206` controls and this Mission's exact entry point pass with 0 retries and 0 newly weakened assertions. | Confirmed |

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Scope is limited to the default, non-skipped real pre-review gate reached by `spec-kitty agent tasks move-task WP## --to for_review`, in human-output and JSON-output modes. | Fixed |
| C-002 | The skip flag, environment escape hatch, initial notice, and sync-disable handling from `35f3a2206` are delivered baseline behavior, not implementation scope. | Fixed |
| C-003 | Atomicity claims apply only to timeout and catchable cancellation during the gate phase before transition mutation begins. | Fixed |
| C-004 | SIGKILL and equivalent uncatchable termination do not carry an in-process rollback guarantee; only deterministic recovery or reconciliation is required. | Fixed |
| C-005 | Standard-output JSON integrity is required only for this exact entry point and mode; the Mission MUST NOT define a universal CLI output contract. | Fixed |
| C-006 | The Mission makes no promises about invocation from arbitrary checkouts, canonical root resolution, placement routing redesign, or workspace recreation. | Fixed |
| C-007 | The first implementation work package MUST begin with a separately committed acceptance test proven RED on the planning base before implementation starts. | Fixed |
| C-008 | The specification defines observable outcomes only; progress transport, process control, code structure, and recovery architecture remain plan decisions. | Fixed |
| C-009 | Interruption recovery MUST NOT reset, restore, or otherwise destructively clean operator or test-owned checkout changes. | Fixed |

## Success Criteria

| ID | Criterion | Measure |
|---|---|---|
| SC-001 | A human can distinguish a long-running real gate from a hang. | During an acceptance run lasting at least 65 seconds, initial progress appears within 2 seconds and no liveness gap exceeds 30 seconds. |
| SC-002 | Machine-readable output remains machine-safe. | Success, failure, timeout, and catchable-cancellation runs each emit exactly one standard-output JSON document that parses without preprocessing. |
| SC-003 | Pre-mutation interruption leaves no workflow residue. | Timeout and catchable-cancellation acceptance runs satisfy every zero-residue facet enumerated in NFR-003. |
| SC-004 | Existing escape and synchronization controls remain honest. | Planning-base regression cases remain green, and every explicit sync-disable/minimal-import case reports a truthful skip without workspace or subprocess activity. |
| SC-005 | The defect is demonstrated non-vacuously. | A separately committed test fails on the planning base because ongoing human liveness is absent, then passes after implementation without weakening its timing assertions. |

## Issue Traceability and Code-Truth Disposition

| Issue | Disposition | Requirements / evidence |
|---|---|---|
| [#2573](https://github.com/Priivacy-ai/spec-kitty/issues/2573) | Sole claimed issue, narrowed to the residual synchronous/non-streaming default pre-review path with a 300-second subprocess timeout. | FR-001–FR-007; NFR-001–NFR-006; SC-001–SC-005 |
| [#2549](https://github.com/Priivacy-ai/spec-kitty/issues/2549) | Fixed on the planning base. Placement-routing tests are green; facet B was delivered by `8612ee788`. Regression context only. | No delivery requirement or success criterion. |
| [#2570](https://github.com/Priivacy-ai/spec-kitty/issues/2570) | Frictions 1 and 3 were delivered by `e7cab2693` and `dd83e5b6f`. Regression context only. | No delivery requirement or success criterion. |
| [#2626](https://github.com/Priivacy-ai/spec-kitty/issues/2626) | Removed from this Mission. The current review-missing-workspace path is fixed; the mark-status/move-task residual is unproven and belongs in a separate reproduction-first future Mission. | No delivery requirement or success criterion. |

## Key Entities and Domain Language

- **Mission**: the canonical unit of governed delivery.
- **Work package (WP)**: the unit being moved to `for_review`.
- **Pre-review gate phase**: the interval in which the real pre-review check runs before any transition mutation begins.
- **Human-output mode**: interactive command output intended to communicate progress and outcome to a person.
- **JSON-output mode**: command output in which standard output must be one machine-parseable JSON document.
- **Liveness indication**: evidence that the real gate remains active; it is not a passing verdict.
- **Catchable cancellation**: an interruption the running process can observe and handle before termination.
- **Authoritative state**: the persisted Mission state used to determine whether a transition occurred.

## Assumptions

- The code-truth audit and convergent post-spec squad findings supplied for this revision are authoritative for planning-base disposition.
- The existing initial notice does not satisfy ongoing liveness for a gate that can remain silent for several minutes.
- A gate can be exercised long enough to validate heartbeat cadence without changing its actual pass/fail semantics.
- Recovery semantics for uncatchable termination may use existing authoritative-state reconciliation; the plan will determine the appropriate bounded design.

## Non-Goals

- Reimplementing or redesigning the skip flag, environment escape hatch, initial notice, or sync-disable behavior delivered by `35f3a2206`.
- Delivering any #2549 or #2570 facet.
- Delivering #2626 without a separate reproduction-first Mission.
- A universal CLI progress, logging, JSON, or error-output contract.
- Root/worktree resolver redesign, any-checkout routing promises, placement authority redesign, or workspace lifecycle repair.
- Changing the 300-second gate bound merely to hide the lack of liveness.
- Guaranteeing in-process rollback after SIGKILL or equivalent uncatchable termination.
- Prescribing modules, APIs, threading, subprocess control, progress transport, or implementation structure during specification.
