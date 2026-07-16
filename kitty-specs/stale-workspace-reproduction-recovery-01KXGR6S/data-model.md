# Data Model: Stale Workspace Recovery

## Entities

### PersistedWorkspaceContext

- `mission_slug`, `mission_id`, `wp_id`, `lane_id`
- recorded `worktree_path` and `branch_name`
- `lane_wp_ids` and execution mode
- provenance timestamp/version where present

Invariant: a record is evidence, not proof that its path or branch still exists.

### CurrentLaneAssignment

- lane identifier and WP membership from canonical lane metadata
- expected branch identity
- coordination topology/branch

Invariant: disagreement with persisted context is an authority conflict, not permission to choose whichever path exists.

### ResolvedWorkspace

- canonical path, branch, lane, execution mode, resolution kind, existence/readiness
- relationship to persisted context and current lane assignment

Invariant: resolved once before mutation and passed unchanged through readiness, recovery, and command execution.

### ArtifactPlacement

- PRIMARY: `tasks.md` and WP tracking files
- COORD status: event log and materialized status under coordinated topology
- owning ref/worktree and commit result

Invariant: physical placement remains partitioned; a transaction cannot move a PRIMARY file into COORD to simplify rollback.

### TransitionObservation

- exit/result envelope
- event-log and materialized-state before/after
- tracking-file bytes before/after
- ref HEADs and committed path sets before/after
- lock/path existence before/after
- checkout porcelain before/after

Invariant: success requires all intended deltas and clean placement; refusal requires zero durable deltas.

### PlacementCommitReceipt

- composite transaction ID and invocation ID
- destination ref and owning worktree root
- `before_sha` captured by the commit owner under the canonical Mission mutation lock before mutation
- `commit_sha` returned by the successful canonical commit seam
- exact paths derived from the committed diff tree and associated event IDs, when status events are present

Invariant: this is the one canonical placement-receipt type. Its reviewed commit
owners are the only producers; a workflow dictionary or later `rev-parse` observation
cannot create, complete, or substitute for it. Producer provenance is guarded by a
non-vacuous architectural call-site gate, not inferred from end-to-end behavior.

### PlacementCommitFailure

- complete canonical `PlacementCommitReceipt` for the commit that was created
- typed primary/caller-state recovery diagnostic
- unrecovered staged, unstaged, worktree, or untracked paths when known

Invariant: this failure exists only after the canonical commit owner has produced a
real commit and receipt but caller-state recovery did not complete. Reverse compensation
consumes this embedded receipt directly; no observer may recreate it from Git state.

### CompositeWorkflowTransaction

- Mission, WP, operation, workflow-minted invocation ID, and Mission Management-minted transaction ID
- canonical PRIMARY and COORD placements
- under-lock pre-command ref observations
- exact owned file bytes plus staged binary patch, unstaged binary patch, and untracked path/byte snapshots
- lock, path, and porcelain snapshots for owned surfaces
- invocation-owned workspace and lock resources
- ordered canonical placement receipts
- staged SaaS, offline-queue, dossier, and other enumerated outbound effects

Invariant: the Mission Management domain service owns the cross-placement decision and
holds the canonical Mission mutation lock across both commits and terminal ref
observation. Workflow is only a caller. The transaction produces exactly one terminal
outcome: `committed`, `refused`, `compensated`, or `compensation_failed`.
The invocation ID is minted once at the registered workflow boundary and remains
stable across internal retries. The transaction ID is minted once per Mission
Management attempt and is unique across retries. Their pair identifies one attempt,
and both identifiers flow unchanged through that attempt's receipts, failures,
compensation results, and terminal result.

### CompositeCommitReceipt

- operation and WP identity
- composite transaction ID and invocation ID
- exact tuple of required `PlacementCommitReceipt` values
- terminal composite outcome

Invariant: `committed` requires one receipt for every required placement, no duplicate
destination refs, and equality between every receipt `commit_sha` and its final owning
ref. A partial or inferred receipt set cannot represent success.

### CompensationResult

- destination ref
- receipt-owned expected current SHA
- pre-commit SHA requested for restoration
- whether compare-and-swap restoration occurred
- actionable diagnostic when restoration was refused or failed

Invariant: restoration is permitted only while the destination ref still equals the
receipt's `commit_sha`. A foreign or concurrent advance is preserved and yields
`compensation_failed`, never a destructive reset or false success.

### CompositeWorkflowResult

- terminal outcome: `committed`, `refused`, `compensated`, or `compensation_failed`
- composite transaction ID, invocation ID, Mission, WP, and operation identity
- exact placement receipts and reverse-ordered compensation results
- terminal ref observations captured while the canonical lock is still held
- staged/dispatched/discarded/suppressed outbound disposition by named channel
- operator diagnostics and supported recovery action where applicable

Invariant: this is a typed in-process domain result, not a public CLI `--json` contract
and not a persisted Mission artifact. `refused` requires proof of zero durable and
outbound delta. Ref movement without an attributable canonical receipt is terminal
`compensation_failed` with indeterminate ownership.

### WorkingStateSnapshot

- exact bytes and existence bit for every Mission-owned file and every caller-state path `safe_commit` may temporarily mutate, stash, restore, or expose
- complete relevant-worktree `git diff --cached --binary` staged patch, including unrelated sentinels
- complete relevant-worktree `git diff --binary` unstaged patch, including unrelated sentinels
- sorted relevant-worktree untracked path set with each path's bytes and mode, including unrelated sentinels
- lock identities, workspace path ownership, and porcelain

Invariant: pre-command capture and terminal comparison occur while Mission Management
holds the canonical mutation lock. Compensation restores only invocation-owned deltas
and preserves all pre-existing caller state byte-for-byte, including unrelated staged,
unstaged, and untracked sentinels. Any mismatch yields `compensation_failed`.

### StagedOutboundEffects

- SaaS event emission
- offline-queue write
- dossier synchronization
- any other explicitly enumerated review-transition fanout

Each channel records `attempted`, terminal `dispatch_succeeded` or `dispatch_failed`,
and retryable diagnostic evidence. Effects are staged in memory until local
`committed`. Only then are channels attempted independently in registration order;
failure does not stop later channels and does not change the local committed result.
`refused`, `compensated`, and `compensation_failed` have zero attempts.

## Relationships

`PersistedWorkspaceContext` is reconciled with `CurrentLaneAssignment` to produce one `ResolvedWorkspace`. The workflow boundary mints one invocation ID and requests Mission Management, which mints one transaction ID and opens the `CompositeWorkflowTransaction` under the canonical lock. It captures `WorkingStateSnapshot`, stages `StagedOutboundEffects`, then commits state events to COORD and WP tracking to PRIMARY through their existing owners. Each owner returns the canonical `PlacementCommitReceipt`; a post-commit recovery error returns `PlacementCommitFailure` carrying that same complete receipt. Their exact receipt set forms a `CompositeCommitReceipt` only after every expected placement succeeds. A later failure consumes all invocation-owned receipts in reverse order to produce `CompensationResult` values. The workflow caller receives only the terminal typed `CompositeWorkflowResult`; outbound channels run separately after local `committed`.

## Composite Transaction State

| State | Required evidence | Allowed next state |
|---|---|---|
| prepared | readiness established; under-lock refs and exact working state captured; outbound staged; no placement receipt | committing, refused |
| committing | Mission mutation boundary held; zero or more owner-produced receipts | committed, compensating |
| committed | exact required receipt set; terminal under-lock refs match receipt SHAs; complete caller state restored; outbound becomes eligible for independent best-effort dispatch | terminal local result |
| refused | zero receipt/ref/byte/index/lock/path delta and zero outbound dispatch proved under lock | terminal |
| compensating | later placement failed; every landed invocation-owned receipt processed in reverse order with expected-old CAS before resync | compensated, compensation_failed |
| compensated | owned refs plus all caller bytes/staged/unstaged/untracked/locks/paths/porcelain equal the pre-command observation; outbound has zero attempts | terminal |
| compensation_failed | receipt missing/unattributed after movement, CAS refused, restoration failed, or post-CAS resync failed; foreign history preserved where applicable; outbound suppressed and diagnostic records terminal evidence | terminal, operator recovery |

## State Classification

| Branch agrees/exists | Worktree exists | Classification | Allowed action |
|---|---|---|---|
| yes | yes | ready | proceed |
| yes | no | recoverable husk | reattach/recreate, then proceed |
| no | no | unavailable authority | refuse before mutation |
| disagrees | any | divergent authority | refuse before mutation |
