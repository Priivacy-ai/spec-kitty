# Implementation Plan: Recover Missing Lane Workspaces

**Branch**: `fix/stale-workspace-reproduction` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)
**Input**: GitHub issue #2626 and the reviewed Mission specification

## Summary

Preserve the approved production-shaped witness and its frozen rows 1–8, then finish the four RED `agent action review` rows through one Mission Management-owned composite operation. The workflow boundary resolves readiness once and mints one invocation ID; Mission Management holds the canonical mutation lock, mints one transaction ID per attempt, commits COORD status and PRIMARY tracking through their existing owners, and returns one typed in-process result. Exact canonical receipts—not observed ref movement—authorize success and reverse compensation. A typed post-commit failure carries its receipt; expected-old CAS restoration lives in the canonical ref-advance authority; every safe-commit-affected caller-state path is preserved. Local commit precedes independent best-effort outbound delivery. The registered CLI and direct Mission Management real-Git layers jointly prove the contract.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer CLI, Git CLI/subprocess boundary, `mission_runtime` placement seam, Mission Management status aggregate/lifecycle service, `BookkeepingTransaction`, partition-aware commit router, `safe_commit`, canonical ref-advance authority
**Storage**: Repository files (`meta.json`, `lanes.json`, persisted workspace JSON, status JSONL/materialization, Markdown tracking) and Git refs/worktrees
**Testing**: Frozen registered-CLI witness `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`; direct Mission Management real-Git integration for typed results; focused transaction/router/ref-advance/safe-commit tests; receipt-producer architectural gate
**Target Platform**: Linux, macOS, and Windows 10+ through existing platform-neutral Git/path abstractions
**Project Type**: Python CLI monorepo
**Performance Goals**: Non-recoverable stale workspace refused before side effects within 2 seconds in the focused fixture
**Constraints**: ATDD RED first; no patches over resolver/commit/status seams; no arbitrary primary fallback; no direct `origin/main` push; PR remains DRAFT
**Scale/Scope**: One issue and one review-only composite path. `mark-status` and `move-task` rows 1–8 stay frozen; WP04 expands in place with no WP/lane/topology recomputation.

## Charter Check

- **Canonical authority**: PASS if workspace resolves once and PRIMARY tracking remains separate from COORD status. No command-local path reconstruction.
- **Domain ownership**: PASS only when Mission Management owns the composite operation and canonical lock; workflow is a request/result adapter.
- **ATDD first**: PASS only after a test-only RED commit reproduces a current-base defect. Already-green arms receive characterization evidence, not speculative production changes.
- **Tiered rigor**: Critical workflow mutation requires real-Git CLI proof, focused seam tests, independent review, and architectural gates.
- **Tracker hygiene**: #2626 is assigned and claimed; `issue-matrix.md` marks it as the sole addressed issue. No adjacent ticket is activated by this amendment.
- **Git/PR discipline**: Planning stays on `fix/stale-workspace-reproduction`; implementation uses resolved lane workspaces; PR #2641 remains DRAFT and the operator merges.
- **Campsite/terminology**: New branches receive tests; no suppressions, legacy Mission terminology, or unrelated cleanup.

## Project Structure

### Documentation

```text
kitty-specs/stale-workspace-reproduction-recovery-01KXGR6S/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── issue-matrix.md
├── disposition-matrix.md
├── contracts/stale-workspace-transition-contract.md
└── tasks.md

docs/adr/3.x/
└── 2026-07-14-2-cross-partition-workflow-transaction.md
```

### Source and tests

```text
src/specify_cli/
├── cli/commands/agent/
│   ├── tasks_mark_status.py
│   ├── tasks_move_task.py
│   ├── workflow.py
│   └── workflow_executor.py
├── coordination/
│   ├── types.py
│   ├── transaction.py
│   ├── status_transition.py
│   ├── outbound.py
│   └── commit_router.py
├── git/
│   ├── commit_helpers.py
│   └── ref_advance.py
├── status/
│   ├── review_transaction.py
│   └── work_package_lifecycle.py
├── sync/local_commit.py
├── workspace/context.py
└── lanes/lifecycle_sync.py

tests/
├── agent/test_workflow_review_lane_gate.py
├── architectural/test_review_receipt_producer_gate.py
├── specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py
├── specify_cli/cli/commands/test_workspace_husk_resolution_1833.py
├── specify_cli/coordination/
│   ├── test_commit_router_partition.py
│   ├── test_status_transition.py
│   ├── test_transaction.py
│   ├── test_outbound.py
│   └── test_types.py
├── specify_cli/git/
│   ├── test_commit_helpers.py
│   └── test_ref_advance.py
├── specify_cli/sync/test_local_commit.py
└── specify_cli/status/test_review_transaction.py
```

**Structure Decision**: Add `status/review_transaction.py` as the Mission Management composite domain service, consistent with the accepted execution-state domain ADR. Keep placement, COORD transaction, PRIMARY routing, safe commit, and ref resynchronization in their existing authorities. `coordination/types.py` owns the one canonical class `PlacementCommitReceipt`; the existing public/internal name `CommitReceipt` becomes a compatibility type alias to that exact class identity, not a subclass, wrapper, second dataclass, or second constructor authority. Workflow remains a thin registered-command adapter. WP04 expands in its existing lane-d; do not add WP05, edit `lanes.json`, or run mutating task finalization.

## Complexity Tracking

No charter violations are planned.

## Implementation Concern Map

IC-01 through IC-06 are immutable reviewed historical state. WP01–WP03 approvals,
the disposition rows, test-only witness commit `980eae6a9`, remediation commit
`eaff3130c`, and both WP04 review artifacts are inputs, not work to reactivate. The
amendment begins at IC-07. No instruction below authorizes edits to rows 1–8, WP02,
WP03, or any adjacent-ticket mechanism.

### IC-01 — Real persisted-context witness

- **Historical outcome (immutable)**: Approved production-shaped witness and reviewed disposition; do not rerun as a planning decision or edit frozen rows.
- **Preserved evidence**: Approved witness commit/blob, registered argv, six-surface observations, and reviewer reference.

### IC-02 — Disposition gate and ownership matrix

- **Historical outcome (immutable)**: The committed authoritative matrix assigns rows 9–12 to WP04 and freezes rows 1–8; do not amend its ownership decisions.
- **Preserved evidence**: Committed disposition matrix and case-by-case frozen-witness Charter exception.

### IC-03 — Task-command and placement remediation

- **Historical outcome (immutable)**: WP02 is independently approved; task-command behavior and its tests are not amendment owners.
- **Preserved evidence**: Test-only RED, production GREEN, exact approved witness blob, and independent review.

### IC-04 — Review readiness before claim

- **Historical outcome (immutable)**: Readiness-before-claim and invocation-owned workspace cleanup from the preserved WP04 implementation remain the starting base.
- **Preserved evidence**: `980eae6a9`, `eaff3130c`, cleanup/ownership tests, and review cycles 1–2.

### IC-05 — Lifecycle missing-authority diagnostics

- **Historical outcome (immutable)**: WP03 is an approved no-op; its lifecycle owners remain unchanged.
- **Preserved evidence**: Byte-identical owner hashes and approved lifecycle verification.

### IC-06 — Cross-surface regression evidence

- **Historical outcome (immutable baseline)**: Approved regression evidence defines the floor; amendment validation may rerun it but may not reinterpret or weaken it.
- **Preserved evidence**: Full witness, focused suites, Ruff, strict mypy, and architectural/terminology gates recorded by prior reviews.

### IC-07 — Mission Management review composite

- **Purpose**: Own `agent action review` COORD status plus PRIMARY tracking as one locked domain attempt and return `CompositeWorkflowResult`.
- **Relevant requirements**: FR-004, FR-010, FR-014, FR-016, C-009, C-011
- **Affected surfaces**: new `src/specify_cli/status/review_transaction.py`, `status/work_package_lifecycle.py`, `coordination/status_transition.py`, workflow caller adapters
- **Sequencing/depends-on**: IC-04 readiness; precedes all durable review mutation
- **Design**: Workflow mints `invocation_id` once. Mission Management mints unique `transaction_id` per attempt, holds the existing Mission mutation lock through terminal ref/state observation, stages outbound effects, and invokes existing placement owners. No public JSON flag or persisted result artifact.
- **Lock order**: acquire the review workspace/resource lock first; then the sole `status.locking.feature_status_lock`; then Git worktree/index locks. `BookkeepingTransaction` is the transaction scope under the already-held feature lock, not a distinct lock. The receipt-returning lower status seam consumes that open scope and MUST NOT reacquire the feature lock. Expected-old ref CAS runs while the feature lock is held; CAS still protects against foreign Git writers outside that lock. No new composite lock is introduced.
- **Risks**: Violating this order can deadlock or double-commit. Tests assert acquisition order and that the lower status seam does not reacquire the feature lock.

### IC-08 — Canonical receipt and post-commit failure propagation

- **Purpose**: Make one owner-produced `PlacementCommitReceipt` the only success/compensation authority and preserve it when a commit exists but caller-state recovery fails.
- **Relevant requirements**: FR-011, FR-015, C-013, C-014
- **Affected surfaces**: `coordination/types.py`, `transaction.py`, `status_transition.py`, `commit_router.py`, `git/commit_helpers.py`, receipt-producer architectural gate
- **Sequencing/depends-on**: IC-07 transaction/attempt identity
- **Design**: The final state has `PlacementCommitReceipt` as the sole class and `CommitReceipt = PlacementCommitReceipt` preserving exact class identity. Receipt contains invocation/transaction IDs, destination ref, lock-held `before_sha`, commit SHA, worktree, committed diff-tree paths, and event IDs. `PlacementCommitFailure` carries the complete receipt plus recovery diagnostics. Wave A temporarily preserves the byte-compatible legacy `CommitReceipt` class as a distinct constructor while adding the future data types; B1 atomically switches the alias only with migration of every canonical producer/adapter. The final shrink-only producer-gate baseline includes the migrated legacy/current producers and new Git-to-coordination adapter sites; no workflow producer is permitted.
- **Git evidence seam**: `safe_commit` gains an additive composite-deferral mode returning Git-owned generic pending `LocalCommit` plus post-commit caller-recovery evidence. Default non-composite behavior remains byte-compatible. Git modules do not import `coordination.types`; placement owners adapt Git evidence into the canonical coordination receipt/failure.
- **Risks**: `safe_commit` temporarily touches unrelated caller index/worktree state. Snapshot and verify every affected staged, unstaged, and untracked path, including unrelated sentinels.

### IC-09 — Reverse expected-old compensation

- **Purpose**: Restore every invocation-owned landed placement in reverse order after later failure without erasing foreign history.
- **Relevant requirements**: FR-012, C-010, C-014
- **Affected surfaces**: `git/ref_advance.py`, `coordination/transaction.py`, Mission Management composite service, focused real-Git tests
- **Sequencing/depends-on**: IC-08 receipts/failures
- **Design**: Extend the canonical ref-advance module with expected-old CAS restore. CAS uses receipt `commit_sha` as expected old and `before_sha` as replacement; checked-out worktrees resynchronize only after CAS. A mismatch, incomplete caller-state restore, or post-CAS resync failure yields `compensation_failed` with repair evidence.
- **Risks**: Ref restoration can succeed before resync fails. Preserve both facts and never relabel the result compensated.

### IC-10 — Post-commit outbound and two-layer proof

- **Purpose**: Separate local atomicity from best-effort delivery and prove both public and typed contracts.
- **Relevant requirements**: FR-013, C-012, C-015, SC-008, SC-011
- **Affected surfaces**: `coordination/outbound.py`, `BookkeepingTransaction.defer_outbound` and `_run_deferred_outbound`, `sync/local_commit.py`, configured capture-sink adapters, frozen CLI witness, direct real-Git integration, architectural gate
- **Sequencing/depends-on**: IC-07 through IC-09
- **Design**: Composite staging includes LocalCommit persistence/send alongside SaaS, offline queue, and dossier effects. Zero persistence/send attempts occur before local `committed`; all staged effects are discarded for non-success. After commit, each real adapter records `dispatch_succeeded` or retryable `dispatch_failed`, and later channels continue. A configured file-backed/offline/local capture sink injects a failing middle channel and proves a later channel succeeds. Registered CLI proves output/durable state; direct Mission Management integration proves typed results, IDs, receipts, failures, compensation, sentinels, and channel evidence.
- **Risks**: Treating delivery failure as transaction failure would attempt unsafe rollback after externally visible delivery. Keep local outcome committed and surface retryable per-channel diagnostics.

## Execution Strategy

### Preserved and rejected evidence

Start from preserved `980eae6a9`, `eaff3130c`, and the two approved WP04 review
artifacts. IC-01–IC-06 and rows 1–8 remain immutable historical evidence. Rejected
commits `7e8f6f579`, `52d5f02ab`, and scaffold `98ccc4dc` are retained in Git history only as
non-authorizing discovery evidence: their code, test expectations, green results,
and producer assumptions do not satisfy any amendment gate and MUST NOT be copied
forward as reviewed design. `98ccc4dc` is specifically rejected because switching
`CommitReceipt` to the expanded exact alias before migrating
`BookkeepingTransaction.commit` breaks the existing canonical transaction producer.
Its defect MUST be remediated test-first in the corrected Wave A sequence before B1;
neither its commit nor an incidental green may authorize implementation. Before the
corrected Wave A, one test-only correction commit MAY
replace or delete test scaffolding introduced by those rejected commits. That
correction commit cannot edit production, relax a preserved assertion, or claim RED
evidence; its name-status and assertion/fixture audit become part of the handoff.

### Wave A — API, type, and port discovery

1. Land a test-only API/type/port and rejected-scaffold-remediation RED commit. It
   specifies the full future `PlacementCommitReceipt`, typed
   `PlacementCommitFailure`, composite result vocabulary, Mission Management entry
   signature, owner ports, producer/import boundaries, and a regression proving the
   existing `BookkeepingTransaction.commit` constructor remains byte-compatible and
   usable during Wave A. Wave A explicitly does **not** assert exact alias identity or
   authorize the alias switch. It contains no implementation and does not attempt a
   composite transaction.
2. Land a separate runtime-mutation-free scaffold commit limited to exactly:
   - `src/specify_cli/coordination/types.py`: data-only
     full `PlacementCommitReceipt` and data-only `PlacementCommitFailure`, while
     preserving the existing legacy `CommitReceipt` class, fields, constructor,
     behavior, and class identity byte-compatible and distinct from
     `PlacementCommitReceipt`;
   - `src/specify_cli/status/review_transaction.py`: enums, frozen dataclasses,
     protocols, the public entry signature, and
     `CompositeImplementationUnavailable`.
3. The Wave A entry implementation immediately raises
   `CompositeImplementationUnavailable` before acquiring a resource/status/Git lock,
   invoking a placement owner, reading or moving a ref, staging/releasing outbound,
   or entering a retry. It MUST NOT return a terminal composite result. Wave A adds
   no `__init__.py` export, workflow wiring, Git/status/router/outbound call, hidden
   fallback, or compatibility execution path. Its only green evidence is API/type/
   import/producer shape, legacy transaction-producer regression, distinct interim
   class identities, plus proof that the unavailable sentinel is mutation-free. The
   final FR-011 exact-alias outcome is unchanged but deferred wholly to B1.

### Wave B — vertical semantic slices

Each slice is exactly two ordered commits: its test-only RED commit first, then its
behavior commit. Before starting the next slice, rerun every prior slice and keep it
GREEN. A behavior commit may implement only the boundary exposed by its immediately
preceding RED; broad horizontal implementation of a later slice is prohibited.
Production owners are never monkeypatched. Repository hooks and independent fixture
helpers are stimuli only: they coordinate or inject the external condition, while
assertions must observe the real named production owner and boundary.

Every filesystem mutation probe MUST be isolated from the real lane/repository.
Scanners and architectural gates used by these tests accept an explicit root/path.
The fixture copies the declared committed preimage plus only the minimal required
package tree and configuration into a collision-safe unique temporary root, injects
the unauthorized producer/import/signature mutation only in that disposable copy,
runs the gate against the explicit temporary root, and proves rejection. Cleanup
deletes the temporary root; unique naming and cleanup remain safe under overlapping
processes. Because parallel probes share no mutable paths, they require no
serialization lock. Assert the canonical source hash equals the declared committed
preimage both before and after every probe. The real production bytes are never
modified, so assertion failure, process crash, SIGKILL, overlapping gates, and normal
parallel readers cannot observe injected bytes. Shared-lane in-place mutation plus a
lock/`finally` restore is prohibited and is not interruption-safety evidence.

1. **B1 — first-terminal foundation**
   - Test-only RED: pin the entire minimum contract required before any truthful local
     terminal result can exist:
     - real PRIMARY and COORD owner paths yielding the exact two-receipt committed set;
     - complete refused observation under the held status lock with zero durable delta,
       zero receipts, and zero lower-seam commit calls;
     - missing COORD receipt, wrong COORD hash, duplicate destination, mismatched
       invocation/transaction IDs, unattributed movement, and every other negative
       receipt/identity case resolving to `compensation_failed`;
     - invocation/transaction identity inherited unchanged by the result and every
       receipt/evidence item;
     - real resource lock, `feature_status_lock`, lifecycle seam, and Git-lock entry/
       exit order, one outer status-lock acquisition, no lower-seam reacquisition, and
       no implicit lower-seam commit;
     - named outbound intents, including Git-owned pending `LocalCommit` persistence/
       send evidence, staged before the first durable mutation with explicit
       per-channel result disposition: committed marks them releasable only after the
       local terminal result, while refused/non-success discards or suppresses them and
       records zero persistence/send/delivery attempts;
     - additive composite deferral leaves default non-composite safe-commit and
       `LocalCommit` behavior byte-compatible.
     - the final FR-011 switch `CommitReceipt is PlacementCommitReceipt`, migration of
       **all** existing canonical receipt producers/adapters to the expanded constructor,
       the current `BookkeepingTransaction.commit` producer regression, the final
       non-vacuous shrink-only AST producer set, and both complete PRIMARY and COORD
       success adapters. The RED must prove the alias switch cannot pass independently
       of the complete producer migration.
     Instrument the real boundaries. On the Wave A unavailable path, assert zero lock,
     owner, ref, lower-seam commit, outbound, and retry calls. The initial B1 RED MAY
     fail at `CompositeImplementationUnavailable`; no committed/refused expectation is
     accepted as GREEN until every item above is pinned.
   - Behavior: implement only that foundation: prepare, the additive Git-owned deferred
     `LocalCommit` evidence mode, pre-mutation named-channel staging/disposition,
     canonical resource→feature-status→Git lock order, real owner invocation, both
     complete canonical PRIMARY and COORD success Git-evidence→receipt adapters,
     atomic migration of every existing canonical producer/adapter to the full
     `PlacementCommitReceipt` constructor, and only then in the same commit replace the
     legacy class with exact `CommitReceipt = PlacementCommitReceipt`. There MUST be no
     intermediate commit where the alias has switched but any legacy constructor call
     remains. Finish the non-vacuous shrink-only producer allowlist in this same
     behavior commit, plus receipt/identity/result evaluation and typed
     `committed`, `refused`, or indeterminate `compensation_failed` outcomes. **B1
     wholly and solely owns the exact-alias switch, complete producer migration, final
     producer set, and both success adapters.** The lifecycle seam consumes the
     already-held status lock and transaction without reacquisition or implicit commit.
     No retry, compensation, persistence/send, or delivery executes in B1; it creates
     and disposes only pending evidence, and non-success always records zero attempts.
2. **B2 — post-commit Git evidence adaptation and caller-state recovery**
   - Test-only RED: drive the real Git commit seam through a post-commit caller-state
     recovery failure and require the placement owner to raise
     `PlacementCommitFailure` carrying the complete canonical receipt and recovery
     diagnostic. Assert unrelated staged/unstaged/untracked bytes and modes plus the
     complete index and worktree patches. A repository-local hook may inject the
     recovery condition and record a reached marker; the test observes the real Git
     and placement-owner return/raise path.
   - Behavior: add the generic Git post-commit evidence needed by the placement owner,
     caller-state capture/restore, and the Git-evidence→`PlacementCommitFailure`
     adapter with complete error-receipt propagation. **B2 wholly and solely owns typed
     post-commit failure and its adaptation/propagation.** Git remains
     coordination-type-free. B3–B5 may
     rerun this contract only as regression evidence; they MUST NOT introduce a new
     adapter, alternate receipt construction path, or fresh RED for this behavior.
3. **B3 — canonical expected-old CAS and post-CAS resynchronization**
   - Test-only RED: exercise `git/ref_advance.py` directly with real refs/worktrees.
     Prove success with the expected old OID, foreign-advance refusal without ref or
     worktree overwrite, and checked-out-worktree resync only after successful CAS.
     An independent helper performs the foreign advance at the prescribed concurrent
     barrier; an expected-old transaction hook obstructs resync only after CAS. Both
     tests name and reach the real ref-advance boundary.
   - Behavior: implement the canonical expected-old CAS and post-CAS worktree-resync
     primitive before any composite compensation consumes it. Return exact ref/restored
     worktree/repair evidence; never force-update over a foreign OID. These tests remain
     Git-authority tests and do not claim composite reverse compensation yet.
4. **B4 — composite reverse compensation**
   - Test-only RED, after B3 is GREEN: cover both composite compensation
     paths. First, a conditional PRIMARY Git hook reaches and refuses only the named
     real owner commit before PRIMARY lands but after COORD has landed, requiring
     compensation of the landed COORD receipt. Second, reuse B2's already-GREEN
     post-commit caller-state failure and error-carried PRIMARY receipt as regression
     infrastructure after both placements land. Prove the composite consumes that
     exact error-carried receipt without `rev-parse`, ancestry, porcelain, or other
     reconstruction, then compensates in strict PRIMARY→COORD order. Both scenarios
     assert exact terminal refs, caller state, resources, and
     `compensated`/`compensation_failed` repair evidence through the already-GREEN B3
     ref-advance primitive. Instrument the real outer `feature_status_lock` and prove
     the same continuously held lock instance spans every reverse-order CAS, every
     successful-CAS worktree resync, and terminal ref/caller-state observation. Assert
     the PRIMARY→COORD trace contains no lock release, second acquisition, or
     lower-seam reacquisition between those boundaries.
   - Behavior: implement receipt-driven reverse compensation for invocation-owned
     landed placements by composing B2 receipt propagation with B3 expected-old CAS
     and resync while the one outer feature-status lock remains continuously held
     through terminal observation. Caller-state mismatch is always
     `compensation_failed`. B4 adds no adapter. No private ref mutation, receipt
     reconstruction, duplicate
     Git-evidence adapter, or modification to B1/B2 adapter behavior is
     permitted.
5. **B5 — retry and post-commit per-channel delivery**
   - Test-only RED: through direct typed inputs/outputs and real owner evidence where
     applicable, cover exactly one retryable condition, named in this plan
     `RetryablePreDurablePrepareConflict`. The prepare port may raise it only before
     any resource/status/Git lock, placement-owner or ref operation, durable delta,
     receipt, pending outbound evidence, compensation state, or channel attempt.
     Prove workflow invokes Mission Management exactly once with the resolved identity
     and `invocation_id`. Mission Management alone catches and retries only this private
     exception: the next internal attempt reuses the same `invocation_id`, receives a
     fresh `transaction_id`, and begins with empty receipt, compensation,
     pending-outbound, channel, resource-ownership, and owner-invocation state. Assert
     no ID, receipt, owner call, counter, disposition, diagnostic, or other evidence
     from the failed prepare attempt leaks into the next attempt or terminal result.
     Also cover no outbound attempt before local commit or on any non-success, and a
     real middle-channel failure followed by a later-channel success. Use typed evidence
     and explicit per-owner/per-channel counters; do not add ready/release/done barriers.
     B1 deferred `LocalCommit` evidence, staging/disposition, zero-attempt behavior,
     success receipts, and default non-composite compatibility plus B2 complete
     error-receipt propagation are regression-only, never new REDs. Explicitly prove
     `committed`, `refused`, `compensated`, `compensation_failed`, every post-lock
     failure, and every post-durable failure are returned/raised once and never retried.
   - Behavior: add the private prepare-port exception
     `RetryablePreDurablePrepareConflict` inside Mission Management, its
     single-condition private retry loop, and post-commit per-channel delivery only.
     Workflow invokes the service once and never owns a retry loop. The exception does
     not extend or alter the four-value terminal vocabulary. For each internal attempt,
     Mission Management mints a fresh `transaction_id` and attempt context, runs prepare
     validation before resource creation/attachment or any resource/review/status/Git
     lock, and catches only that private conflict. On retry it retains only
     `invocation_id`; every receipt/compensation/outbound/channel/resource/owner
     collection is newly empty. After prepare succeeds, no retry boundary remains:
     Mission Management creates/attaches invocation-owned resources as needed, acquires
     resource/review lock → `feature_status_lock` → Git locks, and proceeds once. Every
     terminal, post-lock, and post-durable outcome returns/raises without retry. Consume
     B1's already-GREEN pending `LocalCommit` and named-channel evidence after local
     `committed`; do not alter its deferral, staging, discard/suppress, or compatibility
     behavior. Git never imports coordination receipt types.

An intentional RED after B1 is valid only after the test reaches its named real
production boundary. Deterministic `ready`, `release`, and `done` marker files or pipe
barriers are required **only** for B3 cases with an actually concurrent independent
foreign writer or synchronized post-CAS obstruction; their payloads include the
invocation/transaction IDs when present, destination ref, and relevant OIDs. Pure
receipt/identity evaluation plus `LocalCommit` deferral/staging/disposition (B1),
retry/post-commit delivery behavior (B5), and
non-concurrent hook failures use direct typed inputs/outputs, real owner evidence where
applicable, and simple reached markers—never artificial concurrency barriers. A
failure at `CompositeImplementationUnavailable` after B1, fixture setup, an unobserved
stimulus, or a monkeypatched substitute does not authorize implementation. The final
aggregate run MUST show every B1–B5 boundary and applicable
stimulus marker reached,
all earlier slices GREEN, the registered-CLI and direct Mission Management real-Git
layers GREEN, the receipt-producer gate and IC-06 regression floor GREEN, and PR
#2641 still DRAFT. WP04 remains the only active package; do not refinalize task or
topology state.

## Acceptance Witness Matrix

**Test module**: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`

| Entry point | Exact argv | Required starting state |
|---|---|---|
| `mark-status` | `agent tasks mark-status T001 --status done --mission <slug> --json` | `tasks.md` contains pending T001; stale lane context exists but must remain irrelevant |
| `move-task` | `agent tasks move-task WP01 --to for_review --mission <slug> --agent codex --json` | WP01 is `in_progress`, subtasks complete, implementation commit present, dependencies satisfied |
| `agent action review` | `agent action review WP01 --agent codex --mission <slug>` | WP01 is `for_review`, implementation commit present, coordination topology/status materialized |

Each argv runs against healthy, matching-branch/missing-worktree, branch-absent, and divergent-context rows as applicable. Rows 1–8 and the reviewed fixture/observation harness remain byte-frozen. Review rows retain the test-only `980eae6a9` desired contract and gain real-Git fault stimuli through repository-local hooks or an independent fixture helper, never production monkeypatching. Before/after ref OIDs, exact bytes, staged/unstaged patches, untracked path/byte/mode sets, locks, worktrees, porcelain, commit diff-tree paths, and outbound attempt counts are observed under the Mission lock where applicable.

The direct Mission Management integration uses the same real repositories and worktrees to inspect `CompositeWorkflowResult`, invocation/transaction inheritance, canonical receipts, `PlacementCommitFailure`, compensation results, and per-channel delivery evidence. It does not introduce a public JSON surface.

The `move-task --skip-pre-review-gate` escape hatch may be retained only as a separately labelled negative-control row. It cannot satisfy the ordinary `move-task` acceptance row because it returns before workspace resolution.

## Readiness and Compensation Protocol

1. **Classify without mutation**: workflow reconciles persisted context with the current lane assignment and branch inventory into one resolved ready/recoverable/unavailable/divergent identity and mints one invocation ID.
2. **Invoke Mission Management once; prepare internally**: workflow passes that resolved identity and invocation ID in one service call. Mission Management is the sole canonical owner of the private `RetryablePreDurablePrepareConflict` loop. It mints a fresh transaction ID and empty attempt context, then runs prepare validation before any resource/worktree creation or attachment, any resource/review/status/Git lock, owner/ref operation, durable delta, receipt, pending outbound evidence, or channel attempt. Only that private pre-durable conflict is caught; an internal retry retains only invocation ID and rebuilds every other field empty.
3. **Acquire resources and locks after successful prepare**: only after the current attempt's prepare succeeds may Mission Management create/attach a recoverable worktree or other invocation-owned resource and record ownership. It then acquires, in order, the resource/review lock → sole outer `feature_status_lock` → Git worktree/index locks. No retry boundary exists from this point onward.
4. **Open the durable attempt**: under those locks, snapshot all safe-commit-affected caller state, stage named outbound and pending `LocalCommit` evidence before mutation, and invoke the existing placement owners. Every terminal, post-lock, and post-durable failure is observed once and never retried.
5. **Commit with canonical receipts**: COORD status and PRIMARY WP tracking remain physically partitioned and commit through existing owners. Each owner returns the same canonical receipt type; post-commit caller recovery failure raises `PlacementCommitFailure` carrying that receipt.
6. **Compensate in reverse**: on later failure, consume only owner-produced or error-carried receipts, newest first. Expected-old CAS restoration happens in `ref_advance`; resync follows successful CAS. Restore exact caller state and invocation-owned workspace/lock resources.
7. **Observe terminal local state under lock**: exact receipt set yields `committed`; zero delta yields `refused`; exact restoration yields `compensated`; any unattributed movement, CAS/resync failure, or caller-state mismatch yields `compensation_failed`.
8. **Deliver after commit**: only local `committed` unlocks best-effort per-channel outbound. Delivery failure remains diagnostic/retryable and does not alter the local result.

## Rejected Alternatives

- **Fallback commit in the primary checkout**: placement, not directory availability, owns artifacts.
- **One global stale-workspace wrapper**: commands have distinct owners and workspace requirements.
- **Rollback-first design**: readiness can be established before mutation; compensation is a last resort.
- **Observed-ref receipts**: movement proves neither producer nor compensation ownership; rejected in favor of owner-produced typed receipts and typed post-commit failure.
- **Workflow-owned transaction/dictionaries**: violates Mission Management ownership and duplicates policy; workflow remains a caller.
- **Outbound inside local atomicity**: a later delivery failure cannot safely retract earlier external delivery; rejected in favor of post-commit per-channel evidence.
- **Add WP05/refinalize topology**: would recompute live lanes and risk #2644; fold the operator-authorized owner expansion into WP04 in place.
- **Delete/rewrite stale context automatically**: disagreement is an authority conflict, not implicit permission.
- **Activate adjacent-ticket work**: rejected; the amendment is limited to the reviewed `agent action review` composite gap.

## Post-Design Charter Re-check

PASS: the design preserves canonical authorities, uses RED-first evidence, keeps one-issue scope, assigns new branches focused tests, and retains the DRAFT/operator-only landing boundary.

## Risks and Rollback

- **Nested-lock/deadlock risk**: Mission Management is the sole outer lock holder; receipt-returning lower seams accept the active transaction instead of reacquiring the same lock.
- **Lock-order invariant**: workspace/resource → feature-status → Git worktree/index. `BookkeepingTransaction` operates inside the already-held feature-status scope; there is no separate transaction or composite lock. Expected-old CAS remains under the feature lock.
- **Type-identity drift risk**: Wave A deliberately retains distinct interim class identities so legacy producers remain valid. B1 makes `CommitReceipt` an alias to `PlacementCommitReceipt` atomically with every producer/adapter migration, and the architectural gate rejects either half of that switch in isolation.
- **Caller-state loss risk**: preflight captures full relevant-worktree staged, unstaged, and untracked state, including unrelated sentinels. Any mismatch blocks `compensated`.
- **Foreign-ref risk**: expected-old CAS preserves foreign history. CAS refusal is `compensation_failed`, never a forced reset.
- **Post-CAS resync risk**: record restored ref plus failed checkout path and supported repair; do not conceal the split outcome.
- **Outbound duplication risk**: no attempts before local commit; per-channel retry evidence is explicit and delivery failures do not trigger Git rollback.
- **LocalCommit leakage risk**: composite mode defers both sync-state persistence and send; default safe-commit and non-composite LocalCommit behavior remain unchanged.
- **Implementation rollback**: before Mission landing, revert WP04 code commits as a unit while retaining the immutable witness and planning evidence. Runtime compensation never uses broad `git reset --hard`, deletes persisted workspace authority, or rewrites a ref without receipt-bound expected-old CAS.
