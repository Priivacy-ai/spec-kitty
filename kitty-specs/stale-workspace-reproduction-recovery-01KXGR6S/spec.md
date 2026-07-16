# Mission Specification: Recover Missing Lane Workspaces

**Mission Branch**: `fix/stale-workspace-reproduction`
**Created**: 2026-07-14
**Status**: Draft
**Input**: GitHub issue #2626 — stale lane-workspace metadata can make WP transitions crash or report success while leaving tracking writes uncommitted.

## Intent Summary

An operator resumes a Mission after its coordination branch has been recreated, while a persisted lane-workspace record still names a lane worktree that no longer exists. The operator must receive one truthful outcome: the canonical workspace authority safely recovers the transition and commits every tracking mutation at its owning placement, or the command refuses before mutation with an actionable recovery diagnostic. A raw filesystem exception, a misleading coordination path, or a successful transition paired with a dirty primary checkout is never acceptable. This Mission is reproduction-first: implementation is permitted only if the defect is RED on the current planning base.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stale workspace state is reproduced honestly (Priority: P1)

A maintainer needs a deterministic witness that models a persisted lane assignment whose recorded worktree directory has disappeared, then invokes the same operator entry points implicated by #2626.

**Why this priority**: The report was observed on another repository and Spec Kitty version. Current-base code truth must be established before changing an authority seam.

**Independent Test**: Build a real temporary Git repository with Mission metadata, lane assignment, coordination topology, and a stale workspace record; invoke the supported transition/review entry points and assert the full consistency boundary.

**Acceptance Scenarios**:

1. **Given** valid lane metadata whose persisted worktree path is absent, **When** the witness runs against the current planning base, **Then** it proves either a live RED defect or an already-correct outcome without mocking away workspace resolution or commit routing.
2. **Given** a transition attempt in that state, **When** observations are collected, **Then** exit/result, event-log state, materialized status, WP tracking content, commit placement, and checkout dirt are all recorded together.

---

### User Story 2 - Transition outcomes are atomic and actionable (Priority: P1)

An operator invokes `mark-status`, `move-task`, or the review action while lane metadata is stale. The command either recovers through the canonical authority and completes cleanly, or refuses before any durable transition/write with a diagnostic naming the missing workspace and a supported recovery action.

**Why this priority**: A green-looking command paired with an uncommitted tracking file creates silent state divergence and data-loss risk.

**Independent Test**: Exercise each affected entry-point family against the RED fixture and prove no outcome can combine success with an uncommitted WP mutation or partial state transition.

**Acceptance Scenarios**:

1. **Given** a recoverable missing lane worktree, **When** the command chooses recovery, **Then** all authoritative state and tracking writes are committed at their canonical placement and every relevant checkout is clean.
2. **Given** a missing lane worktree that cannot be recovered safely, **When** the command runs, **Then** it exits non-zero before mutation and identifies the stale record, missing path, and supported recovery command.
3. **Given** either outcome, **When** human and JSON output are inspected, **Then** neither reports an overall success while an auto-commit failed.
4. **Given** an unrecoverable stale workspace during review, **When** readiness fails, **Then** event-log bytes, materialized status, WP/tracking bytes, Git HEADs, locks, and porcelain remain unchanged from before the command.
5. **Given** a healthy review workspace and a COORD status commit, **When** the later PRIMARY tracking commit fails, **Then** the composite operation compensates every invocation-owned landed placement in reverse order and restores every owned ref, byte/index snapshot, lock, checkout, and staged outbound effect to its pre-command state.
6. **Given** a recoverable missing review workspace that this invocation materializes and a COORD status commit, **When** the later PRIMARY tracking commit fails, **Then** the same compensation contract applies and cleanup additionally removes only the invocation-created workspace and lock.
7. **Given** another writer advances a placement ref after an invocation-owned commit, **When** compensation evaluates its receipt, **Then** it preserves the foreign history, returns a truthful non-zero `compensation_failed` result with expected and observed SHAs, and names a supported recovery action.
8. **Given** compare-and-swap restoration succeeds but checked-out-worktree resynchronization fails, **When** the command reports its terminal result, **Then** it reports `compensation_failed`, retains the restored ref evidence plus the checkout repair diagnostic, and never reports atomic success.
9. **Given** the local PRIMARY-and-COORD composite reaches `committed`, **When** one outbound channel fails, **Then** the local result remains `committed`, that channel records retryable `dispatch_failed`, later channels still run, and no outbound failure rewrites local Git state.

---

### User Story 3 - Healthy workspace flows remain unchanged (Priority: P2)

Operators whose lane and coordination worktrees exist continue to receive the current transition, commit-placement, and structured-output behavior.

**Why this priority**: A stale-state guard must not create a second workspace resolver or perturb healthy lane topology.

**Independent Test**: Run the existing healthy lane/coord transition suites alongside the stale-state witness and prove byte-compatible public outcomes where no workspace is missing.

**Acceptance Scenarios**:

1. **Given** a healthy lane worktree and record, **When** the same commands run, **Then** transition and commit behavior remains unchanged.
2. **Given** JSON mode, **When** a stale-state refusal occurs, **Then** stdout remains one parseable document and diagnostics do not leak as unrelated stdout text.

### Edge Cases

- The recorded lane branch exists, agrees with the current lane assignment, and its worktree is absent: recovery may reattach/recreate it.
- The recorded lane branch is absent or disagrees with the current lane assignment while the stale record remains: refuse before mutation.
- The coordination worktree exists but the lane worktree does not.
- A transition has dependencies or review guards that would independently refuse it; stale-workspace handling must not bypass those guards.
- Recovery or refusal is interrupted; no subprocess, lock, partial event, or dirty tracking mutation remains.
- COORD commits successfully but the subsequent PRIMARY tracking commit refuses or fails.
- A placement ref advances after an invocation-owned commit but before compensation; the command must preserve the foreign advance and report terminal `compensation_failed` with automatic restoration declined by the expected-old CAS guard.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Current-base reproduction | The Mission MUST provide a non-fakeable current-base witness for #2626 using supported operator entry points and realistic Git/workspace state. | High | Open |
| FR-002 | Full consistency observation | The witness MUST jointly observe command result, status event log, materialized lane state, WP tracking content, commit placement, and dirt across primary, coordination, and lane checkouts. | High | Open |
| FR-003 | Reproduction-first disposition | Production code MUST change only if FR-001 is RED on the planning base; an already-correct result MUST be documented and closed without speculative implementation. | High | Open |
| FR-004 | Atomic success | A successful stale-workspace transition MUST leave all intended authoritative and tracking writes committed at canonical placement with relevant checkouts clean. | High | Open |
| FR-005 | Fail before mutation | When safe recovery is unavailable, the command MUST fail before durable mutation and MUST NOT report the transition as successful. | High | Open |
| FR-006 | Actionable diagnostics | Refusal MUST identify the stale workspace record or lane, the missing path, and a supported recovery action without exposing a raw `FileNotFoundError` or misleading path. | High | Open |
| FR-007 | Entry-point coverage | The disposition MUST cover `mark-status`, `move-task`, and the review action through each entry point's existing owning seam. Consolidation is permitted only if the RED witness proves one shared cause; the Mission MUST NOT manufacture a new cross-command resolver. | High | Open |
| FR-008 | Structured-output truth | JSON mode MUST remain one parseable stdout document whose status agrees with the durable outcome; human mode MUST make commit failure or refusal unmistakable. | Medium | Open |
| FR-009 | Recovery classification | Recovery MAY recreate or reattach a missing worktree only when the canonical lane branch exists and agrees with the current lane assignment; an absent or divergent branch MUST fail before mutation. | High | Open |
| FR-010 | Review composite placement ownership | `agent action review` MUST execute its COORD status claim and PRIMARY WP tracking mutation as one Mission Management domain operation under the canonical Mission mutation lock. The workflow caller only requests the operation and consumes its typed result; it MUST NOT own cross-placement commit or compensation policy. `mark-status` and `move-task` rows 1–8 remain frozen and outside this composite contract. | High | Open |
| FR-011 | Canonical typed receipt propagation | Each `agent action review` placement commit owner MUST return the one canonical placement-receipt type bound to the composite transaction ID and invocation ID, with destination ref, lock-held `before_sha`, committed SHA, worktree root, exact committed diff-tree paths, and event IDs where applicable. Workflow dictionaries and ref observations MUST NOT become receipt authority. | High | Open |
| FR-012 | Conditional reverse compensation | If any later `agent action review` step fails after one or more invocation-owned placements landed, Mission Management MUST compensate every landed placement in reverse commit order, including a PRIMARY commit created before staging recovery failed. Each ref restoration MUST use an atomic expected-old compare-and-swap in the canonical `ref_advance` authority and resynchronize checked-out worktrees only after CAS succeeds. | High | Open |
| FR-013 | Composite outbound boundary | SaaS emission, offline-queue writes, dossier synchronization, and every other enumerated review-transition outbound effect MUST receive zero attempts before the local composite is `committed`. After local commit, each channel records independent `dispatch_succeeded` or retryable `dispatch_failed` evidence and later channels continue under existing deferred-outbound semantics; dispatch failure MUST NOT change the local `committed` outcome. `refused`, `compensated`, and `compensation_failed` MUST have zero outbound attempts. | High | Open |
| FR-014 | Typed in-process result | The Mission Management review operation MUST return one canonical in-process `CompositeWorkflowResult` that distinguishes `committed`, `refused`, `compensated`, and `compensation_failed` and carries receipts, compensation evidence, and diagnostics. This Mission MUST NOT add a public `--json` flag or persist a result artifact. | Medium | Open |
| FR-015 | Typed post-commit failure | When a placement commit is created but caller-state recovery later fails, the canonical commit seam MUST raise a typed `PlacementCommitFailure` carrying the complete canonical `PlacementCommitReceipt` plus the recovery diagnostic. Reverse compensation MAY consume only that error-carried receipt and MUST NOT reconstruct commit ownership from `rev-parse`, ancestry, or worktree state. | High | Open |
| FR-016 | Stable attempt identity | The workflow boundary MUST mint one `invocation_id` per registered `agent action review` invocation and retain it across any internal retry. Mission Management MUST mint one `transaction_id` per composite attempt; retries mint a new transaction ID. The transaction ID MUST be unique across attempts, the `(invocation_id, transaction_id)` pair MUST identify one attempt, and both identifiers MUST be inherited unchanged by every placement receipt, failure, compensation result, and `CompositeWorkflowResult` belonging to that attempt. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Determinism | The focused stale-workspace witness MUST pass reliably across repeated local runs and avoid timing-only assertions. | Reliability | High | Open |
| NFR-002 | Platform neutrality | The fix MUST use existing platform-neutral workspace and Git abstractions and introduce no platform-specific path assumptions; new platform variants are conditional follow-ups unless the production-shaped RED witness reaches such behavior. | Portability | Medium | Open |
| NFR-003 | Quality gates | Changed code MUST pass focused pytest coverage, Ruff, and strict mypy with zero new warnings or blanket suppressions. | Maintainability | High | Open |
| NFR-004 | Diagnostic latency | A non-recoverable missing-workspace state MUST be detected before launching transition side effects and complete within 2 seconds in a local fixture. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical workspace authority | Consume the existing workspace resolver/allocation/recovery authority; do not reconstruct lane paths or create a parallel stale-record resolver at command call sites. | Architecture | High | Open |
| C-002 | Status event authority | `status.events.jsonl` remains the sole authority for lane state; WP frontmatter/activity text is tracking evidence, not an alternative transition authority. | Architecture | High | Open |
| C-003 | Placement authority | Tracking and status artifacts MUST be committed through their canonical placement/commit-router seams; never fall back to an arbitrary checkout merely because it exists. | Architecture | High | Open |
| C-004 | No silent workaround | Do not delete stale metadata, hand-commit primary-checkout files, or auto-create directories outside the supported workspace lifecycle as an implementation shortcut. | Safety | High | Open |
| C-005 | Issue boundary | #2160 and #2367 are adjacent, already-owned authority/race mechanisms; this Mission treats them as references and changes their mechanisms only if the #2626 reproduction proves the same owning seam, the plan records the fold explicitly, and ownership is coordinated. | Scope | High | Open |
| C-006 | Draft PR workflow | All changes reach `origin/main` only through a DRAFT PR; the human operator alone may mark ready or merge. | Governance | High | Open |
| C-007 | Production-shaped fixture | The required witness uses the reported relative `.worktrees/...` record with an absent directory. Malformed, outside-repository, and speculative platform-shaped records are non-goals unless discovered on the exact live path. | Scope | High | Open |
| C-008 | Resolve once where workspace is required | Each command path whose existing owner requires execution-workspace readiness MUST obtain one canonical resolved-workspace result before durable mutation and pass that result through readiness, recovery, and execution. Lifecycle helpers and call sites MUST NOT independently recompose a competing path or branch. `mark-status` is a workspace-free negative control and MUST NOT gain lane-workspace resolution. | Architecture | High | Open |
| C-009 | Mission Management composite authority | The Mission Management domain service is the sole `agent action review` composite owner and canonical lock holder. It MUST compose the existing placement resolver, `BookkeepingTransaction`, partition-aware commit router, and guarded ref/worktree resynchronization seams. This Mission explicitly authorizes extending the canonical `ref_advance` authority with expected-old CAS restoration; workflow code MUST remain a caller and MUST NOT introduce raw ref mutation or a parallel transaction mechanism. | Architecture | High | Open |
| C-010 | Compare-and-swap compensation | Compensation MUST verify that the current ref equals the receipt-owned committed SHA before restoration and MUST fail without overwriting any concurrent or foreign advance. This yields `compensation_failed`, with explicit recovery evidence, rather than the zero-delta `refused` outcome. | Safety | High | Open |
| C-011 | Terminal outcome truth | `refused` is reachable only when the complete under-lock terminal observation proves zero durable ref/byte/index/lock/path delta and zero dispatched outbound effect. Missing or unattributed receipt evidence after any ref movement is `compensation_failed` with indeterminate ownership, never `refused`. | Safety | High | Open |
| C-012 | Acceptance stimulus boundary | The frozen production-shaped witness may use repository-local Git hooks or an independent fixture-owned helper process as fault stimuli. It still MUST NOT monkeypatch a production symbol, subprocess boundary, placement/lifecycle/commit owner, or registered CLI entry point. | Testing | High | Open |
| C-013 | Receipt provenance gate | Producer provenance is enforced by a non-vacuous architectural call-site gate over concrete receipt constructors/producers, with a self-mutation test and shrink-only allowlist. End-to-end success alone MUST NOT be claimed as proof that only canonical owners produce receipts. | Architecture | High | Open |
| C-014 | Complete caller-state preservation | The pre-command snapshot and recovery boundary MUST cover every index, worktree, staged, unstaged, and untracked path that `safe_commit` may temporarily mutate, stash, restore, or expose, including unrelated sentinel paths. If any pre-existing caller state is not restored exactly, the terminal outcome is `compensation_failed` even when owned Mission paths and refs were restored. | Safety | High | Open |
| C-015 | Two-layer proof | Acceptance MUST combine (1) the registered CLI with real Git/worktrees for operator output and durable-state proof and (2) direct Mission Management real-Git integration for typed `CompositeWorkflowResult`, receipt/failure identity, compensation, and outbound evidence. Neither layer may be replaced by a public JSON result surface or production monkeypatching. | Testing | High | Open |

### Key Entities

- **Workspace record**: Persisted `.kittify/workspaces/<mission>-<lane>.json` context describing a lane assignment and expected worktree.
- **Resolved workspace**: Canonical runtime result for a WP, including execution mode, lane, branch, path, and existence state.
- **Primary placement**: Owning location/ref for `tasks.md` and WP tracking files; it is not interchangeable with status placement.
- **Coordination status placement**: Owning location/ref for status events and materialized status in coordinated topology; it does not absorb PRIMARY tracking files.
- **Transition consistency contract**: The cross-placement decision, event append, materialization, tracking write, commits, compensation/refusal, and structured result that must present one truthful outcome even though artifacts have distinct owners.
- **Recovery action**: Existing supported workspace lifecycle operation that can recreate or reconcile a missing lane worktree without fabricating authority.
- **Placement commit receipt**: The single canonical commit-owner-produced type naming its composite transaction and invocation, one destination ref, lock-held before and committed SHAs, owning worktree, exact diff-tree paths, and associated status event IDs. It is never represented by a workflow dictionary or inferred from a later ref read.
- **Composite workflow transaction**: Mission Management-owned, invocation-scoped operation that holds the canonical mutation lock, sequences the COORD and PRIMARY placements, retains exact byte/ref/index/untracked snapshots and receipts, stages enumerated outbound effects, and decides one terminal outcome.
- **Composite commit receipt**: Exact set of placement receipts required for an overall success, paired with the operation and WP identity.
- **Compensation result**: Typed evidence of the compare-and-swap restoration attempt, including expected current SHA, restored SHA, whether restoration occurred, and any actionable diagnostic.
- **Composite workflow result**: Canonical typed in-process result returned to the workflow caller, carrying terminal outcome, placement receipts, compensation evidence, terminal under-lock ref observations, outbound disposition, and diagnostics without creating a persisted result artifact.
- **Placement commit failure**: Typed post-commit error carrying the complete canonical placement receipt and caller-state recovery diagnostic when a commit exists but safe-commit recovery did not complete.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The planning-base witness produces a recorded RED or already-fixed verdict across all six consistency surfaces in FR-002.
- **SC-002**: After disposition, zero tested entry points can return success while leaving an intended tracking mutation uncommitted.
- **SC-003**: Non-recoverable stale workspace state yields a non-zero, actionable result before any event-log or WP-file mutation in 100% of focused cases.
- **SC-004**: Healthy lane and coordination regression suites remain green with no public output-contract drift.
- **SC-005**: Focused tests, Ruff, strict mypy, and required architectural/terminology guards pass before review.
- **SC-006**: In separate healthy-workspace and recoverable-workspace injections where PRIMARY fails after an invocation-owned COORD commit, successful reverse-order compensation leaves PRIMARY and COORD refs, exact owned bytes, staged patch, unstaged patch, untracked path/byte set, locks, worktree paths, porcelain, and dispatched outbound count identical to their pre-command observation.
- **SC-007**: Every successful split-placement review reports an exact PRIMARY-and-COORD receipt set whose composite transaction/invocation IDs agree, whose `before_sha` values equal the under-lock pre-commit observations, whose committed SHAs equal the terminal under-lock owning refs, whose diff-tree paths equal the intended committed paths, and whose COORD event IDs equal the appended transition events; missing, duplicate, unattributed, or mismatched evidence produces a non-zero non-success result.
- **SC-008**: Focused outbound tests prove every channel has zero attempts before local `committed`; after commit, an injected middle-channel failure records retryable `dispatch_failed`, later channels still attempt and can record `dispatch_succeeded`, and the local result remains `committed`. `refused`, `compensated`, and `compensation_failed` record zero attempts.
- **SC-009**: The receipt-producer architectural gate has a non-zero concrete floor, rejects an injected unauthorized constructor/call site, and permits only the reviewed canonical producer set.
- **SC-010**: A post-commit caller-recovery failure exposes one typed `PlacementCommitFailure` whose complete receipt drives reverse compensation; before/after proof includes unrelated staged, unstaged, and untracked sentinels and yields `compensation_failed` if any sentinel differs.
- **SC-011**: Registered-CLI real-Git tests prove output and durable state, while direct Mission Management real-Git integration proves typed results, unique/inherited attempt IDs, receipts, failures, compensation, and per-channel outbound evidence without a public JSON result contract.

## Assumptions

- Assignment plus the single claim comment on #2626 is the complete issue-thread interaction; all later evidence belongs in the DRAFT PR.
- The preferred outcome is not predetermined: safe recovery and fail-closed refusal are both acceptable when grounded in the canonical authority and an honest durable result.
- The report's original Spec Kitty 3.2.5 environment is context, not proof that the defect survives current `origin/main`.
- This request is not a bulk edit; any cross-file changes are semantic wiring/tests around one stale-workspace behavior, not a repeated identifier migration.

## Non-Goals

- A residual authority sweep for #2160 or merge-time VCS-lock/rollback work from #2367.
- Upgrade-worktree coherence from #2392, workspace-registry redesign, or a new doctor/recovery command.
- Relaxing `safe_commit` path policy, falling back to arbitrary primary-checkout commits, or redesigning generic commit-failure warnings without an exact stale-workspace RED.
- Release, version, or broad documentation work unrelated to behavior contradicted by the witness.
