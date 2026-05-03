# Feature Specification: 3.2.0 Workflow Reliability Blockers

**Feature Branch**: `release-320-workflow-reliability-01KQKV85`  
**Created**: 2026-05-02  
**Status**: Draft  
**Input**: User description: "Create and implement one software-dev mission for the highest-priority 3.2.0 stable-release workflow reliability blockers from `mission-state-audit-01KQHRB8`, covering issues #945, #949, #950, #951, #952, #953, #904, and verification of #944."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trust Status Transitions (Priority: P1)

An agent executing a work-package transition needs every successful transition command to leave an observable, durable event so downstream implement, review, merge, and dashboard flows all agree on the work-package state.

**Why this priority**: If state mutation success can be reported without an event, every later workflow step can make a decision from a false state.

**Independent Test**: A focused workflow fixture can run a transition command from the repository root and from a worktree/subagent context, then verify that each successful response has a corresponding status event and that missing event persistence returns a non-zero result with a precise diagnostic.

**Acceptance Scenarios**:

1. **Given** a planned work package and a valid transition request, **When** the transition command reports success, **Then** the expected event is present in the mission status event log and the materialized state reflects the new lane.
2. **Given** an event write or readback failure, **When** the transition command completes, **Then** it fails loudly, names the missing transition evidence, and does not allow callers to treat the mutation as successful.
3. **Given** an implement or review command is backgrounded, interrupted, or slow, **When** the workflow resumes or is inspected, **Then** work packages are not stranded in `claimed` without an actionable recovery state.

---

### User Story 2 - Review the Correct Work (Priority: P1)

A reviewer needs every generated review prompt and diff command to identify the correct repository, mission, work package, worktree, branch, and base reference, even when multiple missions or repositories are active at the same time.

**Why this priority**: A reviewer acting on the wrong prompt or reconstructed branch name can approve or reject unrelated work.

**Independent Test**: Concurrent review prompt fixtures can create review requests for two repos or missions and assert that prompt paths are collision-proof, prompt metadata self-identifies the requested work, and generated diff instructions use canonical mission state.

**Acceptance Scenarios**:

1. **Given** two concurrent missions or repos request reviews, **When** prompts are generated, **Then** each prompt has a unique per-repo, per-mission, per-work-package, per-invocation location.
2. **Given** a generated prompt names a different repo, mission, work package, or worktree than the requested review, **When** the reviewer dispatch step validates it, **Then** dispatch fails closed before any review begins.
3. **Given** a mission slug begins with `mission-`, **When** review diff instructions are generated, **Then** they use canonical state references rather than reconstructed slug conventions.

---

### User Story 3 - Enforce Active Work Ownership (Priority: P1)

An implementer working through sequential work packages in a shared lane needs file ownership checks to follow the active work package, not a stale work package that previously occupied the lane.

**Why this priority**: Stale ownership can either block legitimate work or allow changes outside the current work package's scope.

**Independent Test**: A shared-lane fixture can move from one work package to another with disjoint owned files and prove the guard uses the currently active work package's ownership set.

**Acceptance Scenarios**:

1. **Given** a shared lane has completed one work package and started another, **When** an ownership guard runs, **Then** it validates changed files against the active work package's `owned_files`.
2. **Given** guard context is stale or ambiguous, **When** the guard cannot prove the active work package, **Then** it reports a guard-context problem distinct from a true scope violation.

---

### User Story 4 - Preserve Parseable Successful Commands (Priority: P2)

An agent or script consuming command output needs successful local mutations to remain parseable and non-fatal, even if final SaaS or sync cleanup reports a recoverable problem after the local state is already durable.

**Why this priority**: Red failure output or corrupted JSON after a successful local mutation can cause automation to retry, misclassify, or abandon a valid workflow step.

**Independent Test**: A fixture can force a final-sync failure after a successful local mutation and assert that command status, stdout, stderr, and JSON output preserve the local success contract while surfacing explicit non-fatal sync diagnostics.

**Acceptance Scenarios**:

1. **Given** a local state mutation succeeds and final sync fails, **When** the command exits, **Then** the local success remains machine-readable and the sync issue is marked non-fatal.
2. **Given** a JSON command surface is requested, **When** non-fatal sync diagnostics exist, **Then** stdout remains valid JSON and diagnostics appear only in an explicit field or on stderr according to the command contract.
3. **Given** repeated sync-lock or interpreter-shutdown messages occur in one invocation, **When** diagnostics are rendered, **Then** duplicate messages are collapsed so the operator sees one actionable summary.

---

### User Story 5 - Recover Safely from Merge and Review Inconsistency (Priority: P2)

A release operator needs merge, mission-review, and ship workflows to detect unsafe local branch state and stale rejected review artifacts before claiming a mission is ready for release.

**Why this priority**: A diverged `main` or contradictory review artifact can invalidate release signoff even when work-package lanes look approved or done.

**Independent Test**: A merge/ship preflight fixture can simulate local `main` divergence and stale rejected review-cycle frontmatter, then assert deterministic remediation before release signoff.

**Acceptance Scenarios**:

1. **Given** local `main` has diverged from `origin/main`, **When** merge or ship preflight runs, **Then** the workflow blocks unsafe continuation and provides a deterministic path to a focused PR branch based on mission-owned changes.
2. **Given** a work package is `approved` or `done` but its latest review artifact still says `verdict: rejected`, **When** mission-review or ship signoff runs, **Then** the workflow warns hard or fails until the contradiction is resolved.

### Edge Cases

- A transition writes frontmatter or materialized state but the event append fails or is unreadable.
- A command runs from a lane worktree whose relative paths do not resolve to the canonical mission directory.
- Two review prompts are created in the same second for different repositories or work packages.
- A mission slug already contains the `mission-` prefix and would be misparsed by string reconstruction.
- A shared lane moves from WP01 to WP04 with no overlapping owned files.
- Hosted sync is enabled but the remote service, lock file, or interpreter shutdown path fails after local persistence.
- Local `main` contains unrelated commits, missing origin commits, or both.
- The latest review-cycle artifact contradicts the canonical work-package lane.

### Domain Language *(include when terminology precision matters)*

- **Canonical terms**:
  - **Mission**: A complete Spec Kitty workflow from specify through ship for this stabilization effort.
  - **Work package**: A planned, independently reviewable unit of mission work, identified as `WP##`.
  - **Lane**: The current workflow state of a work package as represented by canonical status events and materialized views.
  - **Status event**: The durable event record that proves a work-package state transition occurred.
  - **Review prompt**: The generated reviewer instruction artifact for a specific repo, mission, work package, worktree, and invocation.
  - **Final sync diagnostic**: A non-fatal hosted sync or cleanup issue reported after successful local persistence.
- **Avoid / ambiguous synonyms**:
  - Do not use "feature" as the canonical identity for this work; use "mission".
  - Do not treat "approved", "done", and "rejected" as interchangeable review states.
  - Do not describe final sync failures as command failures when the local mutation succeeded.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Atomic transition evidence | As an agent executing a work-package transition, I want every successful transition to have a corresponding durable status event so that downstream workflow state is trustworthy. | High | Open |
| FR-002 | Loud transition failure | As an agent executing a transition, I want missing event persistence or readback to fail the command with a precise diagnostic so that no caller treats an unproven mutation as successful. | High | Open |
| FR-003 | Interrupted action recovery | As an operator verifying prior fixes, I want backgrounded, interrupted, or slow implement/review actions to avoid stranding work packages in `claimed` so that workflows remain recoverable. | High | Open |
| FR-004 | Isolated review prompt identity | As a reviewer, I want review prompts to be collision-proof and self-identifying across repo, mission, work package, worktree, branch, base ref, and invocation so that I review the intended work. | High | Open |
| FR-005 | Review prompt fail-closed validation | As a review dispatcher, I want prompt metadata mismatches to block reviewer dispatch so that wrong-repo or wrong-work-package reviews cannot proceed silently. | High | Open |
| FR-006 | Canonical review diff refs | As a reviewer, I want diff commands to use canonical mission and lane references so that slug naming edge cases cannot point review at the wrong comparison. | High | Open |
| FR-007 | Active work-package ownership | As an implementer in a shared lane, I want ownership guards to validate against the active work package's owned files so that stale lane context cannot block or permit the wrong changes. | High | Open |
| FR-008 | Guard context diagnostics | As an operator diagnosing guard output, I want stale or ambiguous guard context to be reported separately from true scope violations so that remediation is clear. | Medium | Open |
| FR-009 | Non-fatal final sync reporting | As an automation consumer, I want successful local mutations to remain successful when final sync fails non-fatally so that scripts do not retry or abort valid state changes. | High | Open |
| FR-010 | Parseable command surfaces | As an automation consumer, I want JSON/stdout command surfaces to remain parseable when diagnostics are present so that command consumers can reliably inspect results. | High | Open |
| FR-011 | Sync diagnostic deduplication | As an operator, I want repeated final-sync cleanup messages deduplicated per invocation so that logs remain actionable. | Medium | Open |
| FR-012 | Diverged main preflight | As a release operator, I want merge or ship preflight to detect local `main` divergence from `origin/main` so that unsafe release work stops before state is reconstructed manually. | High | Open |
| FR-013 | Focused PR branch path | As a release operator, I want a deterministic focused PR branch synthesis path when local `main` is not shippable so that mission-owned work can still be prepared safely. | High | Open |
| FR-014 | Review artifact consistency gate | As a mission reviewer, I want approved or done work packages to be checked against the latest review artifact verdict so that stale rejected verdicts cannot coexist silently with release-ready state. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Regression coverage | Each primary blocker issue (#945, #949, #950, #951, #952, #953, #904) and verification issue #944 MUST have at least one focused automated regression test or an explicit documented deferral before the mission can be accepted. | Testability | High | Open |
| NFR-002 | No unintended network dependence | Regression tests MUST avoid real network calls except for an explicitly scoped hosted-sync test path; external hosted behavior MUST be mocked or isolated for deterministic local runs. | Reliability | High | Open |
| NFR-003 | Local command determinism | Focused workflow fixtures MUST produce the same pass/fail result across at least three consecutive local runs on an unchanged checkout. | Reliability | High | Open |
| NFR-004 | Parseability validation | JSON command-output tests MUST validate stdout with a JSON parser and fail if non-JSON diagnostic text appears on stdout. | Compatibility | High | Open |
| NFR-005 | Diagnostic specificity | Hard-failure diagnostics for transition, prompt, ownership, branch, and review-artifact gates MUST name the mission, work package, and violated invariant when those identities are known. | Operability | Medium | Open |
| NFR-006 | Coverage quality bar | New code introduced by this mission MUST include pytest coverage for new behavior and maintain the project coverage expectation for touched areas. | Testability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Primary repo boundary | The primary implementation repo for this mission is `spec-kitty`; `spec-kitty-saas` and `spec-kitty-tracker` are context repos unless a work package explicitly scopes changes there. | Scope | High | Open |
| C-002 | SaaS sync flag on this machine | Commands that exercise SaaS, tracker, hosted auth, or sync flows during testing on this computer MUST run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Environment | High | Open |
| C-003 | Local planning root | Specify, plan, and tasks artifacts MUST be created from the `spec-kitty` repository root checkout, not a worktree. | Workflow | High | Open |
| C-004 | Canonical state over reconstruction | Workflow logic MUST prefer canonical mission, lane, and status state over reconstructed slug or path conventions. | Governance | High | Open |
| C-005 | No silent release contradictions | Mission-review and ship readiness MUST NOT silently pass when canonical state and latest review artifact verdict conflict. | Governance | High | Open |
| C-006 | Issue linkage | The mission MUST maintain traceability to parent issue #822 and blocker issues #945, #949, #950, #951, #952, #953, #904, plus verification-only issue #944. | Traceability | Medium | Open |

### Key Entities *(include if feature involves data)*

- **Mission Identity**: The canonical mission id, slug, title, base branch, and merge target for this stabilization sprint.
- **Work Package State**: The current and historical status of a work package, including event evidence and materialized lane.
- **Review Prompt Invocation**: A unique generated review request with metadata binding it to one repo, mission, work package, worktree, branch, base ref, and invocation.
- **Ownership Context**: The active work package id and its owned file set at the moment an implement, review, or commit guard runs.
- **Final Sync Diagnostic**: A structured non-fatal report about hosted sync or cleanup issues after local persistence has succeeded.
- **Release Preflight Result**: A merge/ship readiness decision that records branch divergence, suggested remediation, and review-artifact consistency.

## Assumptions & Open Questions *(include when discovery leaves documented defaults or deferred decisions)*

### Assumptions

- The mission is a `software-dev` mission because the requested outcome is focused code and test changes.
- The landing branch is `main`, based on `spec-kitty agent mission branch-context --json` reporting current branch `main`, planning/base branch `main`, merge target `main`, and `branch_matches_target: true`.
- The suggested work-package split from `start-here.md` is the intended planning shape unless `/spec-kitty.plan` finds a stronger split.
- Closed issue #944 is verification-only unless regression testing shows the fix no longer holds.
- Hosted sync behavior should be tested without real network calls except where a work package explicitly scopes a SaaS sync path and uses this machine's required `SPEC_KITTY_ENABLE_SAAS_SYNC=1` flag.

### Open Questions

- None. The provided `start-here.md` request is detailed enough to proceed without deferred clarification markers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh workflow smoke covering `init -> specify -> plan -> tasks -> implement/review -> merge -> PR` completes without manual Python status-event emission.
- **SC-002**: 100% of transition commands covered by this mission either write the expected durable event on success or return non-zero with a diagnostic naming the missing invariant.
- **SC-003**: Review prompt regression tests prove correct repo, mission, work package, and worktree identity for at least two concurrent prompt-generation scenarios.
- **SC-004**: Shared-lane ownership regression tests prove the guard uses the active work package's owned files after moving between at least two disjoint work packages.
- **SC-005**: Non-fatal final-sync failure tests prove local success output remains parseable and is not rendered as a red command failure.
- **SC-006**: Merge/ship preflight tests prove local `main` divergence is detected before unsafe release continuation and that a focused PR branch path is presented.
- **SC-007**: Mission-review or ship readiness tests prove approved/done work-package state cannot silently coexist with a latest review artifact whose verdict remains rejected.
- **SC-008**: Each linked blocker issue has either a focused fix validated by tests or an explicit deferral note before mission acceptance.
