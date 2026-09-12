# Mission Specification: Durable Concurrent Review-Cycle Records

**Mission Branch**: `mission/durable-concurrent-review-cycle-records`
**Created**: 2026-08-23
**Status**: Draft
**Input**: GitHub issue [#3235](https://github.com/Priivacy-ai/spec-kitty/issues/3235), confirmed by the operator after an adversarial evidence review.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Concurrent verdicts never disappear (Priority: P1)

As a reviewer, I want each verdict submission to be reported successful only when both its current-verdict fact and its referenced evidence record are durable, so concurrent reviewers cannot silently erase one another's work.

**Why this priority**: A successful response followed by missing or uncommitted reviewer evidence is silent data loss and a release-blocking integrity failure.

**Independent Test**: Submit two distinct verdicts concurrently against the same work package over at least 50 iterations using separate operating-system processes. Each iteration must finish with two complete durable records or one complete durable record plus one causally justified explicit refusal. The suite must include a deterministic concurrent case where the first automatic save releases the queue within 10 seconds and no independent state-machine rule forbids the second submission; both submissions must then finish durably, proving that the second writer actually waits in line.

**Acceptance Scenarios**:

1. **Given** a work package ready for a verdict, **When** two reviewers submit distinct verdicts concurrently and both operations report success, **Then** both evidence records are durably retained and each successful result resolves to its own record.
2. **Given** the same concurrent submissions, **When** the first automatic save releases the queue within 10 seconds and no independent state-machine rule forbids the second submission, **Then** both operations finish durably with distinct evidence records.
3. **Given** the same concurrent submissions, **When** queue acquisition exceeds 10 seconds or an independently valid state-machine rule refuses one submission, **Then** exactly one operation may succeed and the other returns an explicit, causally evidenced refusal that cannot be mistaken for success.
4. **Given** two operations that both report success, **When** the durable state is inspected after both processes exit, **Then** neither record is missing, uncommitted, duplicated into the other's slot, or reachable only from transient working-tree state.

---

### User Story 2 - Failures are explicit and recoverable (Priority: P2)

As an operator, I want a commit collision or persistence failure to be reported accurately and leave a retryable state, so I never have to infer data loss from a misleading success response.

**Why this priority**: Concurrency protection is incomplete if its losing path silently succeeds, strands an orphan, or blocks an identical retry.

**Independent Test**: Inject each known contention and persistence failure shape and verify that the operation either completes durably or refuses explicitly without leaving a false-success state.

**Acceptance Scenarios**:

1. **Given** contention over shared version-control state, **When** a verdict record cannot be committed within the bounded recovery policy, **Then** the caller receives an explicit failure and no success payload claims that record is durable.
2. **Given** an interrupted or refused verdict submission, **When** the reviewer retries the identical submission after contention clears, **Then** the retry can complete without manual deletion or repair of an orphaned record.
3. **Given** a durability failure after one side of the verdict operation has changed, **When** the operation returns, **Then** the externally readable current verdict and its referenced evidence do not disagree about whether the verdict was successfully recorded.

---

### User Story 3 - Durability is truthful across mission shapes (Priority: P3)

As a maintainer, I want the same success and refusal contract across every supported mission topology and automatic-commit mode, so changing where lifecycle evidence is stored cannot reintroduce silent loss.

**Why this priority**: Review evidence can reside on different governed surfaces; a fix that covers only one topology leaves production users exposed elsewhere.

**Independent Test**: Exercise successful and contended verdict recording across the supported topology and automatic-commit matrix, verifying the durable target and returned durability signal in every cell.

**Acceptance Scenarios**:

1. **Given** any supported mission topology with automatic commit enabled, **When** a verdict reports success, **Then** its evidence record is committed to the governed lifecycle-evidence destination and the current-verdict event points to that record.
2. **Given** automatic commit is explicitly disabled, **When** a verdict is recorded, **Then** the result clearly distinguishes the sanctioned non-committed mode from durable success.
3. **Given** a protected target branch or coordination topology, **When** the system selects a different evidence destination, **Then** durability is measured from the actual destination rather than inferred from configuration.

---

### Edge Cases

- Both processes allocate distinct record numbers but race while committing them.
- One process encounters a shared-index refusal while the other has already completed.
- A commit operation returns a non-success status without raising an exception.
- A persistence component raises after the evidence file is written but before the overall verdict operation completes.
- A process terminates after allocating or writing a record but before durability is confirmed.
- The same reviewer retries byte-identical feedback after an explicit refusal.
- Two reviewers submit opposing verdicts against the same work package at nearly the same time.
- The evidence destination differs between single-branch, lane, coordination, and lane-with-coordination topologies.
- Automatic commit is disabled intentionally and must not be mislabeled as durable persistence.
- A durability pointer exists but its evidence record is absent from the committed destination.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Truthful successful recording | As a reviewer, I want a successful verdict response to guarantee that its current-verdict fact and referenced evidence record are both durable, so success never conceals evidence loss. | High | Open |
| FR-002 | Explicit concurrency refusal | As a reviewer, I want a concurrent submission that times out after 10 seconds or is independently forbidden by the state machine to return an explicit, causally identified refusal, so ordinary contention waits in line while a real inability to complete tells me to retry. | High | Open |
| FR-003 | Distinct concurrent records | As an auditor, I want two successful concurrent submissions to retain two distinct evidence records, so neither reviewer overwrites or impersonates the other. | High | Open |
| FR-004 | Accurate durability reporting | As an operator, I want human and machine-readable results to distinguish durable success, explicit refusal, and intentionally non-committed operation, so automation never infers durability from configuration alone. | High | Open |
| FR-005 | Recoverable failure state | As an operator, I want a refused or interrupted submission to leave no orphan that blocks an identical retry, so recovery needs no manual repository repair. | High | Open |
| FR-006 | Authority coherence | As a maintainer, I want the current-verdict authority and the referenced evidence record to agree about completed submissions, so consumers never observe a successful verdict pointing to unavailable evidence. | High | Open |
| FR-007 | Topology-complete behavior | As a maintainer, I want the same durability contract across all supported mission topologies and automatic-commit modes, so placement changes cannot weaken review integrity. | Medium | Open |
| FR-008 | Production-path regression proof | As a maintainer, I want the concurrency acceptance test to exercise the real reviewer entry point and fail when production serialization or record commitment is removed, so a synthetic test cannot report false confidence. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Concurrency durability bar | Across at least 50 iterations with at least two concurrent operating-system processes, 100% of reported successes retain their distinct current-verdict facts and committed evidence records; every non-completing writer returns an explicit refusal. | Reliability | High | Open |
| NFR-002 | Zero silent loss | Fault-injection coverage for every observed failure shape produces zero successful responses with a missing or uncommitted evidence record. | Reliability | High | Open |
| NFR-003 | Responsive recording | A single uncontended verdict recording, including durable persistence, completes in under 2 seconds in the existing performance harness. | Performance | Medium | Open |
| NFR-004 | Cross-platform behavior | The production durability contract passes on Linux, macOS, and Windows; platform-specific stress harness limitations must not weaken production behavior. | Compatibility | Medium | Open |
| NFR-005 | Mutation-sensitive proof | The acceptance suite must fail when either production event serialization or evidence-record commitment is independently disabled, with at least one negative control for each protection. | Quality | High | Open |
| NFR-006 | Targeted quality gates | All affected tests pass with at least 90% changed-line coverage, and touched production files report zero new lint or strict type-checking findings. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Preserve authority split | The event-sourced status record remains authoritative for which verdict is current; the review-cycle artifact remains authoritative for the reviewer's evidence content. | Architecture | High | Open |
| C-002 | No lock across version-control subprocess | New serialization must not hold an inter-process status lock across a version-control subprocess invocation. | Reliability | High | Open |
| C-003 | No green-washing | The issue-pinned concurrency test must not be weakened, skipped, quarantined, marked expected-failure, or redefined to permit successful-but-uncommitted evidence. | Process | High | Open |
| C-004 | Real entry point | Acceptance evidence must drive the production reviewer command surface rather than manually constructing authoritative events or applying a test-only lock. | Quality | High | Open |
| C-005 | No version prescription | This mission assigns no release or patch version; release sequencing remains an operator decision. | Process | Medium | Open |
| C-006 | Existing placement governance | Durable evidence must land on the destination selected by the existing governed placement rules; the mission must not introduce a second placement authority. | Architecture | High | Open |

### Key Entities

- **Current verdict**: The authoritative answer to which verdict currently governs a work package, including reviewer identity, verdict value, and a reference to its evidence.
- **Review-cycle evidence record**: The durable, versioned record of what the reviewer reported, including prose, affected files, reproduction guidance, reviewer identity, and cycle identity.
- **Verdict submission result**: The caller-visible outcome distinguishing durable success, explicit refusal, and an intentionally non-committed mode.
- **Explicit refusal**: A non-success outcome that names why durability was not achieved and permits a deterministic retry; it is never encoded as success plus a warning.

### Domain Language

- **Verdict** means the current status fact; **evidence record** means the reviewer's preserved content. Do not use either term as a synonym for the other.
- **Durable success** means both the current-verdict fact and its referenced evidence record have reached their governed durable destinations.
- **Best-effort render** must not describe an evidence record that a successful verdict result promises to preserve.
- **Committed** refers to durable inclusion in the governed version-control destination, not mere presence in a working directory.

## Scope

### In Scope

- Concurrent verdict recording against the same mission and work package.
- Truthful durability signaling for both human and machine consumers.
- Failure recovery for shared-index contention, incomplete commit results, and interruptions around evidence persistence.
- Production-path stress and mutation-sensitive regression coverage.
- All supported mission topologies and automatic-commit modes.

### Out of Scope

- Replacing the event-sourced current-verdict authority.
- Changing review policy, verdict vocabulary, reviewer permissions, or work-package lane semantics except where an explicit refusal is required for durability.
- Reorganizing unrelated version-control or status infrastructure.
- Assigning a release version or publishing a release.

## Assumptions and Dependencies

- Issue #3235 remains an open P0 contract; the later event-log authority mission did not supersede it.
- Issue #3235 is assigned to `robertDouglass`; the mission claim is evidenced by [the tracker comment](https://github.com/Priivacy-ai/spec-kitty/issues/3235#issuecomment-5387211052) and the mission issue matrix.
- The accepted review-cycle placement decision remains binding: review-cycle artifacts are lifecycle evidence placed through existing governed rules.
- `main` is the eventual merge target, while planning occurs on `mission/durable-concurrent-review-cycle-records`.
- Existing event-log locking is retained unless evidence shows it must change to satisfy this mission.
- The existing deliberate red-first reproduction is the starting acceptance signal and must be corrected through production behavior rather than assertion changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across at least 50 iterations with two or more concurrent operating-system processes, every iteration produces either two distinct durable verdict-and-evidence pairs or one durable pair plus one causally proven 10-second queue-timeout or independently valid state refusal; at least one deterministic concurrent round in which the queue clears within 10 seconds and state policy permits both submissions produces two durable pairs.
- **SC-002**: Across the tested concurrency run, zero operations report durable success while their referenced evidence is absent, uncommitted, overwritten, or reachable only from transient working-tree state.
- **SC-003**: Each observed contention and persistence-failure shape produces an explicit refusal within the existing command timeout, and the identical retry succeeds after contention clears without manual cleanup.
- **SC-004**: The production-path concurrency test turns red when production event serialization is disabled and independently turns red when evidence-record commitment is disabled.
- **SC-005**: Every supported mission topology and automatic-commit matrix cell returns a truthful durability classification and stores successful evidence at the governed destination.
- **SC-006**: A single uncontended verdict recording, including durable persistence, completes in under 2 seconds.
- **SC-007**: All functional requirements have production-path acceptance coverage, and the affected quality gates finish with zero new failures attributable to the mission.
