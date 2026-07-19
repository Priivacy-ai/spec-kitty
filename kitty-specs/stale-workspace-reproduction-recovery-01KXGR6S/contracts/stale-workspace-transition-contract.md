# Stale Workspace Transition Contract

## Inputs

- One canonical reconciled workspace classification produced from persisted context, current lane assignment, and branch inventory for entry points that require workspace readiness. `mark-status` does not resolve a lane workspace.
- Entry-point identity: `mark-status`, `move-task`, or `agent action review`.
- Pre-command snapshots for status, tracking files, refs/commit path sets, locks/paths, and checkout porcelain.
- For `agent action review` only, one Mission Management-owned, invocation-scoped composite transaction that holds the canonical Mission mutation lock and retains canonical placements, exact pre-command snapshots, staged outbound effects, and invocation-owned resources until the terminal result is observed under lock. `mark-status` and `move-task` rows 1–8 remain frozen outside this contract.

## Classification

| State | Contract |
|---|---|
| Workspace and agreeing lane branch exist | Proceed through existing healthy path. |
| Worktree absent; agreeing lane branch exists | Existing lifecycle may reattach/recreate, then proceed atomically. |
| Worktree and branch absent | Refuse before durable mutation with missing path/lane and supported recovery. |
| Persisted context disagrees with current lane assignment | Refuse before durable mutation; do not choose authority implicitly. |

## Entry-point Delta Matrix

| Entry point | Successful stale-record handling | Refusal |
|---|---|---|
| `mark-status` | PRIMARY tasks tracking commit only; no status/lane/worktree delta | Zero durable delta; structured non-zero result if its own commit cannot land |
| `move-task` | Expected status event/materialization plus PRIMARY WP commit; all owning refs clean | Zero durable delta when workspace readiness is required and unavailable; never success plus commit warning |
| `agent action review` | Workspace ready first, then claim/status and WP evidence at their canonical placements; current placement is measured, not presumed | No claim event, WP mutation, ref movement, lock, created path, or dirt; invocation-owned recovery resources are compensated on later failure |

## Receipt Contract

Each placement commit owner returns the one canonical typed receipt bound to the
composite transaction ID and invocation ID. It contains its destination ref, lock-held
`before_sha`, committed SHA, owning worktree, exact committed diff-tree paths, and
status event IDs where applicable. Split-placement success requires an exact receipt
set for PRIMARY and COORD, with every committed SHA equal to the terminal owning ref
observed while the canonical lock remains held.

The registered workflow boundary mints `invocation_id` exactly once. Mission Management
mints `transaction_id` exactly once for each composite attempt; a retry gets a new
transaction ID while retaining the invocation ID. The transaction ID is unique across
attempts, the `(invocation_id, transaction_id)` pair identifies one attempt, and both
IDs are inherited unchanged by every receipt, post-commit failure, compensation
result, and terminal result in that attempt.

The lifecycle/status layer must propagate the real receipt produced by its
`BookkeepingTransaction`; callers may not synthesize COORD ownership from
`rev-parse`, commit ancestry, dirty-state observations, or workflow-owned dictionaries.
Missing or unattributed receipt evidence after any ref movement is indeterminate
`compensation_failed`, not `refused`. Receipt producer provenance is enforced by a
non-vacuous architectural call-site gate with a concrete floor, self-mutation test, and
shrink-only allowlist.

If a commit is created but canonical safe-commit caller-state recovery fails, the
commit owner raises typed `PlacementCommitFailure`. It carries the complete canonical
`PlacementCommitReceipt` plus the primary recovery diagnostic and known unrecovered
paths. Reverse compensation may consume only this error-carried receipt; it may not
reconstruct one from `rev-parse`, ancestry, reflog, diff, or porcelain.

## Conditional Compensation

If a later step fails after one or more invocation-owned placement commits landed,
Mission Management compensates every landed placement in reverse commit order. This
includes a PRIMARY commit created before safe-commit staging recovery failed. Every
restoration uses an atomic expected-old compare-and-swap extension in the canonical
`ref_advance` authority: expected current SHA is the receipt's committed SHA and the
new SHA is its `before_sha`. Checked-out worktrees are resynchronized only after CAS
succeeds; workflow code performs neither raw ref mutation nor compensation policy.

Successful compensation restores every owned ref, exact file bytes/existence,
the complete relevant-worktree staged binary patch, unstaged binary patch, untracked
path/byte/mode set, lock, created worktree path, and checkout porcelain to the
under-lock pre-command snapshot. This includes unrelated sentinel paths that
`safe_commit` may temporarily stash, restore, mutate, or expose. Cleanup remains
idempotent and may remove only resources recorded as invocation-owned; any non-owned
caller-state mismatch yields `compensation_failed`.

If the current ref no longer equals the receipt's committed SHA, compensation fails
without erasing the foreign advance. The command returns non-zero with terminal
`compensation_failed` evidence containing the destination ref, expected SHA, observed
SHA, pre-commit SHA, and supported operator recovery action. It never reports atomic
success or fabricates a compensated receipt. A post-CAS worktree resynchronization
failure is also `compensation_failed`; the result preserves the successful ref-restore
evidence and provides an explicit checkout repair diagnostic.

`refused` is terminal only when the under-lock terminal observation proves zero ref,
file-byte, staged, unstaged, untracked, lock, path, and dispatched-outbound delta. It
is never used for unattributed movement, partial compensation, or resync failure.

## Outbound Contract

Mission Management stages SaaS emission, offline-queue writes, dossier sync, and every
other enumerated review-transition outbound effect until the exact local composite
receipt set is `committed`. No channel is attempted before that boundary. After local
commit, channels run independently in registration order under the existing
best-effort deferred-outbound semantics: each records `dispatch_succeeded` or retryable
`dispatch_failed`, failure does not stop later channels, and the local terminal outcome
remains `committed`. `refused`, `compensated`, and `compensation_failed` have zero
outbound attempts.

The workflow caller consumes one typed in-process `CompositeWorkflowResult` carrying
the terminal outcome, canonical receipts, compensation evidence, terminal under-lock
ref observations, outbound disposition, and diagnostics. This contract adds neither a
public `--json` flag nor a persisted result artifact.

## Contract Examples

| Scenario | Required result |
|---|---|
| Healthy review succeeds | Exact PRIMARY and COORD receipts; transaction/invocation IDs agree; before/final SHAs, diff-tree paths, and event IDs match; relevant checkouts clean; staged outbound dispatches; result is `committed`. |
| Recoverable review succeeds | Same receipt contract as healthy; invocation-created workspace/lock ownership is recorded and retained for the active reviewer; result is `committed`. |
| Unavailable or divergent workspace | Refusal before either placement receipt exists; all six observation surfaces unchanged. |
| Healthy workspace: COORD commits, then PRIMARY fails | Reverse compensation restores every landed placement and exact staged/unstaged/untracked state; outbound is discarded; result is non-zero `compensated`. |
| Recoverable workspace: COORD commits, then PRIMARY fails | Same compensation proof plus removal of only the invocation-created workspace/lock; result is non-zero `compensated`. |
| PRIMARY commit is created, then safe-commit staging recovery fails | PRIMARY and earlier COORD receipts are compensated in reverse order; exact pre-command state returns; result is non-zero `compensated`. |
| PRIMARY commit exists but an unrelated staged/untracked sentinel is not restored | The typed failure carries the complete PRIMARY receipt; reverse compensation runs, but caller-state mismatch makes the result `compensation_failed`. |
| Foreign COORD advance precedes compensation | Foreign history is preserved; no destructive restoration; structured result is non-zero `compensation_failed` with expected/observed SHAs and recovery guidance. |
| CAS restores a ref, then worktree resync fails | Result is non-zero `compensation_failed`; restored-ref evidence and explicit checkout repair guidance are retained; outbound remains suppressed. |
| Ref movement lacks an owner-produced receipt | Ownership is indeterminate; result is non-zero `compensation_failed`, never `refused`; ref inspection alone cannot satisfy the receipt contract. |
| Local composite commits and one outbound channel fails | Local result remains `committed`; failed channel records retryable `dispatch_failed`; later channels continue and record their own evidence. |

## Test Prohibitions

The acceptance witness may not monkeypatch any production symbol, Git/subprocess call, root/target discovery, placement resolution, lifecycle sync, commit/status path, or CLI entry point. It may use canonical fixture serialization, environment isolation, cache clearing, repository-local Git hooks, and an independent fixture-owned helper process as fault stimuli before or during the registered Typer invocation with a real temporary Git repository and genuine Git worktrees. Hooks/helpers must not replace or intercept a production owner; they may only make a real Git operation fail or advance a fixture ref externally.

Acceptance requires two complementary real-Git layers. The registered CLI layer proves
operator-visible output and all durable ref/file/index/worktree/outbound-attempt state.
Direct Mission Management integration proves the in-process `CompositeWorkflowResult`,
attempt-ID inheritance and uniqueness, canonical receipts, typed post-commit failure,
reverse compensation, caller-state sentinels, and per-channel outbound evidence. No
public JSON result option or persisted result artifact is introduced for either layer.

## Disposition Record

Every entry-point × workspace-state row records baseline SHA, exact argv, prerequisites, classification, RED/GREEN, all six before/after surfaces, reached owner, and `stop`/`continue`. Production changes are authorized only for RED/continue rows.

If the review WP/status bundle is proven to land on the wrong authority, the row is a #2160-adjacent residual. The Mission records that relationship before implementation and uses the repository's canonical partition-aware commit seam; it does not claim that the current review coordination transaction already provides that behavior and does not close #2160.

## Output

- Human mode: unmistakable success or actionable refusal; commit failure is never buried under overall success.
- JSON mode: exactly one parseable stdout document whose success/error agrees with durable state.
