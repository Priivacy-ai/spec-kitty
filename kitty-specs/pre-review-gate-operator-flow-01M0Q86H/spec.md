# Mission Specification: Responsive Pre-Review Gate Operator Flow

**Mission Branch**: `fix/pre-review-gate-operator-flow`
**Created**: 2026-08-23
**Status**: Ready for Planning
**Input**: Resolve [GitHub issue #2573](https://github.com/Priivacy-ai/spec-kitty/issues/2573) for the 3.2.6 stabilization release.

## Intent Summary

Operators and orchestrators submitting a work package for review need an observable, bounded operation rather than a silent multi-minute wait. The pre-review gate remains an atomic prerequisite to the lane transition, while an explicit and visible skip mechanism provides a caller-selected recovery path. Newly detected regressions warn by default, with blocking available as an explicit project policy. Timeout or cancellation leaves the transition unapplied, sync-disable controls prevent implicit daemon startup, and a scope that cannot reasonably fit within the transition budget is refused promptly with guidance to select the explicit skip or a bounded scope. Asynchronous gate execution is outside this Mission.

## User Scenarios & Testing

### User Story 1 - Submit Work for Review Without Ambiguous Waiting (Priority: P1)

As an operator or orchestrator, I want review submission to report that validation is active and continue reporting progress so that I can distinguish healthy work from a hung command.

**Why this priority**: The original defect causes callers to kill a healthy but silent process, creating workflow damage while trying to recover.

**Independent Test**: Invoke the public `move-task --to for_review` command with a controlled validation run lasting longer than two progress intervals and verify prompt start feedback, at least two continuing progress signals, and one final outcome.

**Acceptance Scenarios**:

1. **Given** a work package ready to enter `for_review`, **When** its pre-review validation takes longer than one progress interval, **Then** the caller sees that validation is running and receives continuing progress until completion.
2. **Given** validation completes successfully or with a non-blocking regression warning, **When** the result is finalized, **Then** the work package enters `for_review` exactly once.
3. **Given** validation times out or is canceled, **When** the command terminates, **Then** the work package remains in its prior lane and no partial transition is reported as successful.
4. **Given** the resolved candidate-head scope cannot fit within the effective transition budget, **When** review submission evaluates that scope, **Then** it refuses before starting the candidate-head run and names both supported recovery choices: explicit skip or a bounded scope.
5. **Given** a scope with no deterministic budget classification, **When** it runs under the existing timeout and times out, **Then** the caller receives diagnostic evidence identifying the unknown classification, normalized scope identity and targets, configured budget, observed elapsed time, and unchanged lane state so maintainers can evaluate a future metadata update.

---

### User Story 2 - Use an Explicit Recovery Escape Hatch (Priority: P2)

As an operator or automation caller, I want to select the supported skip control explicitly when the environment cannot support the gate so that workflow progress does not require killing the command or bypassing lifecycle tooling.

**Why this priority**: A supported escape hatch prevents unsafe direct event emission and makes exceptional behavior visible and auditable.

**Independent Test**: Submit a work package with the explicit skip control and verify that no validation subprocess starts, the transition completes, and both human and structured output identify the skip and its reason.

**Acceptance Scenarios**:

1. **Given** an explicit per-invocation skip, **When** a work package is submitted for review, **Then** the gate does not run and the result clearly records that it was skipped.
2. **Given** a truthy `SPEC_KITTY_SYNC_DISABLE` or `SPEC_KITTY_SYNC_MINIMAL_IMPORT`, **When** review submission and implicit daemon startup are considered, **Then** neither starts the disabled work and the effective variable name is visible.
3. **Given** no skip or disable control, **When** review submission starts, **Then** the gate runs by default.

---

### User Story 3 - Preserve Configurable Regression Severity (Priority: P3)

As a project maintainer, I want newly detected regressions to warn by default while retaining an explicit blocking policy so that existing projects do not receive an unplanned enforcement change.

**Why this priority**: The stabilization release should fix the operator-flow defect without silently changing established review-admission policy.

**Independent Test**: Exercise the same new-regression verdict under default and blocking configurations and verify that the former transitions with a warning while the latter refuses the transition.

**Acceptance Scenarios**:

1. **Given** the default policy and a newly detected regression, **When** validation finishes, **Then** the caller receives a warning and the work package enters `for_review`.
2. **Given** an explicitly configured blocking policy and a newly detected regression, **When** validation finishes, **Then** the caller receives a blocking result and the prior lane is preserved.
3. **Given** either policy, **When** the gate is interrupted or times out, **Then** the lane transition is not applied.

### Edge Cases

- Validation completes at the same instant the observed deadline expires; a completion observed before the deadline uses its verdict, while an expired deadline observed first produces one timeout outcome and no transition.
- An explicit skip and a blocking policy are both present; explicit skip wins, no gate verdict is manufactured, and the skip is reported.
- Both sync-disable variables are truthy; `SPEC_KITTY_SYNC_DISABLE` is the reported reason because it is first in the canonical control order, and no disabled work starts.
- Structured-output mode emits one final JSON document with gate metadata and no intermediate progress documents; continuing heartbeat output is required only in human-facing mode.
- Catchable cancellation or timeout occurs after validation creates byproducts; the owned process tree is reaped, the prior lane remains authoritative, and transactional byproducts are restored where the command enrolled them.
- The parent command is terminated by an uncatchable hard kill; lane/event state must remain unchanged, but orphan-process reaping is not promised by this Mission.
- Implicit sync-daemon startup is disabled while an operator explicitly requests daemon management; this Mission governs only implicit startup during the review-submission flow.
- An unclassified scope times out; the system reports it as a classification candidate but does not automatically promote one machine's timeout into deterministic oversized-scope metadata.

## Domain Language

- **Pre-review gate**: Validation performed before admitting a work package to `for_review`.
- **Atomic transition**: The lane change is either applied once after the gate permits it or not applied at all; no half-applied success is observable.
- **Skip**: An explicit, visible decision not to run the gate for one invocation or under an established process-wide disable control.
- **Regression warning**: A failure present in the candidate-head scope but absent from the gate's comparison baseline, classified by the canonical pre-review verdict as new failures and reported without blocking under the default policy.
- **Blocking policy**: An explicit project setting that turns a regression warning into refusal of the lane transition.
- **Progress signal**: Human-facing evidence that the gate is still active; it is not a gate verdict or an additional structured-output document.
- **Effective transition budget**: The configured timeout available to complete the candidate-head validation leg launched by one review-submission transition. The comparison baseline is captured earlier in the implementation workflow and is input to this command, not a second leg launched by `move-task`.
- **Bounded scope**: A selected validation scope whose required legs are eligible to complete within the effective transition budget.
- **Budget classification candidate**: Diagnostic evidence from an unclassified scope that timed out and may justify a later, reviewed update to deterministic gate-budget metadata; it is not an automatic classification.

## Requirements

### Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Observable human-mode execution | The public review-submission command MUST announce that the gate is running, emit continuing human-facing progress while it remains active, and report one final outcome. Structured-output mode MUST retain one final JSON document containing gate metadata rather than emitting intermediate JSON documents. | High | Open |
| FR-002 | Atomic review admission | The system MUST apply the `for_review` transition only after the gate permits progression or an explicit skip applies; timeout, catchable cancellation, or a blocking verdict MUST preserve the prior lane. | High | Landed—verify |
| FR-003 | Explicit per-invocation skip | A caller explicitly selecting the supported per-invocation skip MUST bypass gate execution, and the final result MUST identify the skip and reason in human and structured output. | High | Landed—verify |
| FR-004 | Process-wide disable consistency | Truthy `SPEC_KITTY_SYNC_DISABLE` and `SPEC_KITTY_SYNC_MINIMAL_IMPORT` controls MUST suppress gate execution and implicit sync-daemon startup without suppressing an operator's explicit daemon-management request. | High | Landed—verify |
| FR-005 | Warn-by-default severity | A canonical new-failures verdict MUST warn and permit review admission by default; an explicit project policy MUST be able to make the same verdict block admission. | High | Landed—verify |
| FR-006 | Achievable interruption contract | Timeout and catchable cancellation MUST terminate and reap the command-owned validation process tree and MUST NOT report or persist a successful transition. Abrupt parent death MUST preserve lane/event integrity; cleanup of processes orphaned by an uncatchable hard kill is outside this Mission. | High | Landed—verify |
| FR-007 | Control and outcome precedence | The system MUST apply this precedence: explicit per-invocation skip; otherwise the first truthy disable control in canonical order (`SPEC_KITTY_SYNC_DISABLE`, then `SPEC_KITTY_SYNC_MINIMAL_IMPORT`); otherwise run the gate and apply its verdict under warn/block policy. A completion observed before its deadline uses the completed verdict; an expired deadline observed first produces timeout and no transition. | High | Landed—verify |
| FR-008 | Existing-flow compatibility | Review submission without skip, disable, timeout, cancellation, oversized scope, or a new regression MUST retain its existing successful lane-transition behavior. | High | Landed—verify |
| FR-009 | Oversized-scope refusal | Before starting candidate-head validation, a scope classified as unable to fit within the effective transition budget MUST be refused promptly without applying the transition and MUST name the explicit skip and bounded-scope recovery choices. It MUST NOT be converted into an automatic skip. | High | Open |
| FR-010 | Unknown-budget timeout evidence | When a scope with no deterministic budget classification times out, the final human and structured outcomes MUST identify the classification as unknown, include the normalized scope identity and selected targets, report both configured budget and monotonic-clock observed elapsed time, confirm that the lane remained unchanged, and identify the evidence as a candidate for a reviewed metadata update. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Initial feedback | Human-facing callers MUST receive a gate-start indication within 1 second of gate execution beginning. | Usability | High | Landed—verify |
| NFR-002 | Public-entry heartbeat cadence | While validation remains active, the public human-facing `move-task --to for_review` entry point MUST emit progress at least once every 30 seconds. | Usability | High | Open |
| NFR-003 | Transition integrity | Across success, warning, blocking, timeout, cancellation, abrupt-parent-death, skip, disable, and oversized-scope paths, zero paths may apply more than one transition or report success when the transition was not applied. | Reliability | High | Landed—verify |
| NFR-004 | Skip-path boundedness | The explicit skip path MUST perform no validation wait and start no validation subprocess. | Performance | Medium | Landed—verify |
| NFR-005 | Cross-platform evidence | POSIX process-tree behavior MUST have a real-process integration test; Windows process-tree behavior MUST have deterministic unit coverage of the Windows tree-termination contract and run in Windows CI where that job is available. | Compatibility | High | Open |
| NFR-006 | Scenario traceability | Every acceptance scenario, precedence combination, and named interruption race MUST map to a specific automated test; structured-output assertions are required for every final outcome. | Quality | High | Open |
| NFR-007 | Budget-eligible completion | A representative bounded candidate-head scope MUST complete review admission within the configured transition budget, while an oversized-scope fixture MUST be refused within 2 seconds before the candidate-head subprocess starts. | Performance | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No asynchronous redesign | This Mission MUST NOT move review admission into a background job or introduce a pending-review lane/state. | Scope | High | Accepted |
| C-002 | Preserve default severity | This Mission MUST NOT change newly detected regressions from warn-by-default to block-by-default. | Compatibility | High | Accepted |
| C-003 | Preserve lifecycle vocabulary | This Mission MUST use the existing canonical work-package lane vocabulary and MUST NOT introduce alternate status authorities. | Architecture | High | Accepted |
| C-004 | Stabilization scope | Existing #2573 behavior already present in the checkout MUST be verified and preserved; implementation changes are limited to demonstrated gaps required for the accepted behavior. | Release | High | Accepted |
| C-005 | No direct workflow bypass | Recovery MUST remain available through supported Spec Kitty controls; direct event emission or manual lane-state editing is not an accepted solution. | Governance | High | Accepted |
| C-006 | Preserve structured-output framing | `--json` MUST remain a single final JSON document. This Mission MUST NOT introduce NDJSON, mixed stdout framing, or a machine-progress stream. | Compatibility | High | Accepted |
| C-007 | No automatic budget learning | Runtime observations MUST NOT mutate, promote, or persist deterministic oversized-scope classifications automatically; classification changes require an explicit reviewed source change. | Determinism | High | Accepted |

## Assumptions and Dependencies

- The current checkout already contains partial #2573 remediation: a one-shot start notice, low-level progress-callback support, explicit gate skipping, disable-control handling, atomic transition ordering, and bounded timeout/catchable-cancellation cleanup. Continuing heartbeat delivery is not wired through the public command path, so it remains open work.
- Dogfood evidence attached to #2573 records 8 timeouts in 8 invocations and a selected architectural scope taking about 26 minutes per leg; the Mission must prove both a budget-eligible success path and prompt oversized-scope refusal.
- The canonical lane transition and event surfaces remain authoritative.
- The comparison baseline is captured earlier by the implementation workflow; this Mission does not add baseline capture to `move-task` or widen progress guarantees to that earlier command.
- Release execution places #2573 downstream of #3127. Implementation may be prepared independently, but release-ready finalization requires #3127 merged, this branch rebased onto the resulting `main`, and trustworthy required checks rerun.
- Existing projects may intentionally choose warning or blocking behavior; this Mission preserves that compatibility boundary.
- The issue's broader asynchronous redesign remains deferred and requires a separate architectural decision if revived.
- The Mission depends on the existing pre-review validation and sync-daemon control surfaces but does not change hosted SaaS contracts.

## Out of Scope

- Background or asynchronous execution of the pre-review gate.
- A new `review_gate_pending` lane or other lifecycle state.
- Changing the test selection strategy except where needed to prove an accepted requirement.
- General review-cycle authority unification tracked outside #2573.
- General daemon lifecycle redesign or explicit daemon-management commands.
- Cleanup of subprocesses orphaned by uncatchable parent `SIGKILL`; that broader process-reaping concern remains tracked by #2762.
- A streamed machine-progress protocol or any change from the existing single-document `--json` response.
- Changing regression severity to block-by-default.
- Automatic learning or mutation of deterministic scope-budget metadata from local or CI timing history.

## Success Criteria

### Measurable Outcomes

- **SC-001**: An exact public-entry human-mode acceptance test observes start feedback within 1 second and at least two timed heartbeat emissions during a controlled run lasting more than 60 seconds.
- **SC-002**: In every timeout and catchable-cancellation test, the owned process tree terminates and the work package remains in its prior lane; an abrupt-parent-death integration test separately proves lane/event state is unchanged without claiming orphan cleanup.
- **SC-003**: For the explicit skip and each canonical disable variable, exact public-entry tests prove that no validation subprocess or implicit daemon start occurs and that the effective reason appears in human output and final structured metadata.
- **SC-004**: The same new-regression fixture transitions with a warning under default policy and refuses the transition under explicit blocking policy.
- **SC-005**: A representative bounded candidate-head scope completes validation and review admission within its effective transition budget; an oversized-scope fixture is refused within 2 seconds before candidate-head validation starts and receives both recovery choices.
- **SC-006**: Explicit daemon-management tests remain green when either disable variable is set, proving the controls suppress only implicit startup.
- **SC-007**: A traceability matrix names at least one specific automated test for every acceptance scenario, precedence combination, and named interruption race in FR-001 through FR-010.
- **SC-008**: No asynchronous job, pending-review state, alternate status authority, direct workflow bypass, or multi-document structured-output protocol is introduced.
- **SC-009**: An exact public-entry timeout test for an unknown-budget scope proves that human output and the single final JSON document carry the normalized scope identity, selected targets, configured budget, controlled-clock observed elapsed time, unknown classification, unchanged-lane result, and reviewed-update guidance without changing the deterministic metadata source.

## Definition of Done

- A traceability matrix maps every acceptance scenario, precedence combination, and interruption race to a specific automated acceptance or regression test; one shared smoke test cannot discharge unrelated paths.
- Current behavior is reproduced from the public review-submission entry point before any gap is changed.
- Any implementation change demonstrates red-first evidence against the Mission's planning base branch and green evidence after the change.
- The exact public entry point proves continuing human-mode liveness; structured mode proves one final JSON document for warning, blocking, skipped, disabled, oversized, timed-out, and canceled outcomes.
- Exact-entry tests separately exercise `SPEC_KITTY_SYNC_DISABLE` and `SPEC_KITTY_SYNC_MINIMAL_IMPORT`, plus the explicit daemon-management exception.
- POSIX real-process and Windows tree-termination evidence meet NFR-005 without claiming cleanup after uncatchable parent death.
- A POSIX real-CLI abrupt-parent-death test waits until candidate-head validation is running, kills the parent, and independently proves no lane/event transition was appended; it deliberately makes no orphan-cleanup assertion.
- Issue #2573 is re-evaluated against the verified behavior; asynchronous redesign remains durably deferred in that issue unless a separate follow-up issue supersedes it.
- Every operational unknown-budget timeout observed during delivery is immediately and durably appended to the Mission's `traces/approach.md` with `provenance: operational`, scope identity, targets, configured budget, observed elapsed time, and environment context. Synthetic timeout fixtures remain test evidence and are not added to the metadata-review queue. Before acceptance, `retrospective-handoff.md` inventories the durable entries or explicit absence; after merge, canonical `retrospective.yaml` records whether any scope should be proposed for deterministic oversized classification and records a follow-up owner or explicit no-action conclusion.
- The pre-accept release handoff records an executable `waiting_upstream` resume point when #3127 is not merged. #2573 is not marked release-ready until #3127 has merged, the Mission branch has been rebased onto the resulting `main`, and required checks—including the existing Windows job where available—have been rerun on that base.
