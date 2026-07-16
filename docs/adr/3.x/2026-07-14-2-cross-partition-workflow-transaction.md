---
title: 'Cross-partition review mutation is one Mission Management transaction'
status: Proposed
date: '2026-07-14'
---
# Cross-partition review mutation is one Mission Management transaction

**Filename:** `2026-07-14-2-cross-partition-workflow-transaction.md`

**Status:** Proposed

**Date:** 2026-07-14

**Deciders:** Operator, Architect Alphonso, Reviewer Renata

**Technical Story:** [GitHub issue #2626](https://github.com/Priivacy-ai/spec-kitty/issues/2626)

---

## Context and Problem Statement

`agent action review` changes two canonical partitions: COORD owns status events and
materialization; PRIMARY owns the WP tracking file. The current lifecycle path commits
COORD before PRIMARY but exposes only the event, discarding the transaction receipt.
Later code can observe ref movement but cannot prove which invocation owns it or safely
compensate it. A PRIMARY failure can therefore leave a partial durable transition or be
misreported as atomic success.

The accepted domain model assigns status and WP lifecycle to Mission Management. The
workflow command is an adapter, not a second transaction owner. The solution must retain
existing placement, transaction, commit-router, safe-commit, and ref-resync authorities;
preserve unrelated caller state; and keep outbound delivery from corrupting local
atomicity.

## Decision Drivers

* One canonical owner for a logical review claim.
* Owner-produced evidence instead of inferred ref movement.
* Exact preservation of caller Git state and foreign history.
* Real-Git proof through both registered CLI and domain-service layers.
* Review-only remediation that leaves frozen task-command behavior unchanged.

## Considered Options

* Keep sequential commits and infer ownership from final refs.
* Put transaction/compensation policy in the workflow command.
* Add a new composite lock and a second receipt model around existing seams.
* Make Mission Management own a receipt-driven composite operation.
* Replace both commits with a new Git plumbing implementation.

## Decision Outcome

**Chosen option:** "Mission Management owns a receipt-driven composite operation",
because it preserves the established domain and placement authorities while supplying
the missing ownership and compensation evidence.

Mission Management holds the existing `status.locking.feature_status_lock` across local
mutation and terminal observation; no composite lock is added. Lock order is fixed:
review workspace/resource lock, feature-status lock, then Git worktree/index locks.
`BookkeepingTransaction` is the transaction scope inside the already-held feature-status
lock, not another lock. Lower status seams consume that open scope without reacquiring
the feature lock. Ref CAS occurs under the feature lock, while its expected-old
predicate protects against foreign Git writers.

Workflow mints one invocation ID across internal retry; Mission Management mints one
transaction ID per attempt. COORD and PRIMARY continue through their existing commit
owners, which return the sole class `PlacementCommitReceipt`. Existing `CommitReceipt`
is a compatibility alias to that class identity, not another type or constructor
authority. A commit-created recovery failure carries the complete receipt in typed
`PlacementCommitFailure`. A shrink-only architectural gate baselines reviewed
legacy/current and new adapter producer sites before production changes.

`safe_commit` gains an additive composite-deferral mode returning Git-owned pending
`LocalCommit` and post-commit recovery evidence; its default behavior does not change.
Git never imports coordination receipt types. Placement owners adapt generic Git
evidence into canonical receipts/failures.

On later failure, Mission Management compensates landed placements in reverse order.
The canonical ref-advance module gains expected-old CAS restoration; worktrees resync
only after CAS. Missing receipts, foreign advancement, incomplete caller-state restore,
or resync failure produce `compensation_failed`, never a reconstructed receipt or
destructive reset.

SaaS, offline queue, dossier, LocalCommit persistence/send, and other outbound effects
receive zero attempts until the local composite is `committed`; non-success discards
them. Channels then run independently through existing
`BookkeepingTransaction.defer_outbound` best-effort semantics and record
success/failure evidence; delivery failure does not stop later channels or change the
local committed outcome.

### Consequences

#### Positive

* Success and compensation have attributable, typed evidence for both partitions.
* Foreign history and unrelated staged, unstaged, and untracked caller state are
  preserved by construction.
* Workflow becomes thinner and Mission Management ownership becomes explicit.
* Receipt compatibility preserves class identity while removing duplicate producer
  authority.

#### Negative

* The lifecycle/status seams must expose receipts without breaking compatibility
  callers, and safe-commit recovery must retain complete post-commit evidence.
* Compensation can restore a ref before checkout resync fails; that split must remain
  visible as `compensation_failed` with operator repair guidance.
* Lock ordering and additive deferred-commit mode require direct regression coverage.

#### Neutral

* PRIMARY and COORD remain separate commits and canonical artifact homes.
* This decision applies only to `agent action review`; `mark-status` and `move-task`
  retain their reviewed behavior.
* Default non-composite safe-commit and LocalCommit behavior remains unchanged.

### Confirmation

The decision is confirmed when immutable reviewed rows 1–8 remain unchanged; the frozen
registered-CLI real-Git witness proves output and durable state; direct Mission
Management real-Git integration proves lock order, typed results, IDs, receipts,
failures, reverse compensation, caller-state sentinels, and per-channel delivery
evidence; and a test-only-RED, non-vacuous architectural gate restricts receipt
producers with a shrink-only baseline and self-mutation test.

Deterministic proof uses a conditional PRIMARY hook, foreign-COORD helper, post-commit
caller-recovery-conflict hook, and post-CAS resync obstruction, each with an asserted
stimulus marker. A configured file-backed/offline/local capture sink proves a failing
middle channel does not prevent later success. An adapter test proves one invocation ID
survives internal retry while transaction IDs differ.

## Pros and Cons of the Options

### Infer ownership from final refs

**Pros:** Minimal code change.

**Cons:** Cannot attribute movement or authorize compensation; false success remains
possible.

### Workflow-owned transaction

**Pros:** Close to the registered command.

**Cons:** Duplicates Mission Management policy and encourages workflow-owned receipt
dictionaries and raw Git recovery.

### Mission Management receipt-driven composite

**Pros:** Aligns with the accepted bounded context, reuses canonical seams, and provides
typed success/failure/compensation evidence.

**Cons:** Requires additive internal contracts across lifecycle, coordination, commit,
and ref-resync modules.

The chosen form deliberately uses the existing feature-status lock and fixed lock order,
one receipt class with a compatibility alias, Git-owned generic deferred commit
evidence, and placement-owned adaptation. These constraints prevent the chosen option
from becoming a new lock, receipt, or Git authority.

### New composite lock and second receipt model

**Pros:** Could isolate the new workflow behind bespoke types and synchronization.

**Cons:** Creates competing lock order and constructor authority, complicates legacy
adoption, and makes deadlock and receipt-identity drift more likely. Rejected in favor
of the existing feature-status lock plus an exact compatibility alias.

### New multi-ref Git plumbing

**Pros:** Could prepare and move multiple refs as one lower-level operation.

**Cons:** Replaces mature safe-commit and placement authorities, broadens scope, and
creates a second commit mechanism.

## More Information

* Mission: `stale-workspace-reproduction-recovery-01KXGR6S`
* Governing predecessors: `2026-05-01-1-atomic-work-package-start-lifecycle.md`,
  `2026-06-03-1-execution-state-domain-model.md`, and
  `2026-06-24-1-kind-and-topology-aware-artifact-placement.md`
