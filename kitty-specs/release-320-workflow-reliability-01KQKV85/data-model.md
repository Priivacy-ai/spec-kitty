# Data Model: 3.2.0 Workflow Reliability Blockers

## Mission Identity

**Purpose**: Bind every workflow action to the correct mission.

**Fields**:

- `mission_id`: Canonical immutable ULID.
- `mission_slug`: Human-readable mission slug.
- `feature_dir`: Absolute mission artifact directory.
- `planning_base_branch`: Branch used for planning artifacts.
- `merge_target_branch`: Final landing branch.
- `repo_root`: Absolute repository root checkout.

**Validation rules**:

- Command dispatch must reject ambiguous mission selectors.
- Generated review prompts must include mission identity and fail validation if it does not match the requested mission.
- Branch names must come from resolved command payloads or mission metadata, not reconstructed slug strings.

## Work Package State

**Purpose**: Represent the durable lifecycle of a work package.

**Fields**:

- `work_package_id`: Stable `WP##` identifier.
- `from_lane`: Previous lane, when known.
- `to_lane`: Requested target lane.
- `event_id`: Durable status event identity.
- `event_path`: Absolute path to `status.events.jsonl`.
- `materialized_lane`: Lane produced by reducing the event log.
- `actor`: Agent or command actor.
- `evidence`: Structured proof such as review verdict or merge reference.

**Validation rules**:

- A transition command may report success only after the expected event is appended and can be read back.
- Materialized state must agree with the appended event after readback.
- Missing event evidence is a hard transition failure, not a warning.
- `claimed` recovery verification must cover backgrounded, interrupted, and slow implement/review actions.

**State transitions**:

```
planned -> claimed -> in_progress -> for_review -> in_review -> approved -> done
```

Additional lanes `blocked` and `canceled` remain governed by existing transition rules.

## Review Prompt Invocation

**Purpose**: Ensure reviewers act on the correct work.

**Fields**:

- `invocation_id`: Unique prompt-generation identity.
- `repo_root`: Absolute repository root.
- `mission_id`: Canonical mission id.
- `mission_slug`: Mission slug.
- `work_package_id`: `WP##`.
- `lane_worktree`: Absolute lane worktree path, when applicable.
- `mission_branch`: Mission branch/ref from canonical state.
- `lane_branch`: Lane branch/ref from canonical state.
- `base_ref`: Canonical diff base ref.
- `prompt_path`: Absolute prompt artifact path.
- `created_at`: Timestamp.

**Validation rules**:

- Prompt paths must be unique across repo, mission, work package, and invocation.
- Dispatcher must compare requested context with prompt metadata before launching a reviewer.
- Any repo, mission, work package, worktree, or ref mismatch fails closed.
- Diff instructions must use `base_ref`, `mission_branch`, and `lane_branch` from canonical state.

## Ownership Context

**Purpose**: Scope file changes to the active work package.

**Fields**:

- `active_work_package_id`: Work package being implemented, reviewed, or committed.
- `lane_id`: Shared lane/workspace identifier.
- `owned_files`: Glob patterns from the active work package.
- `staged_files`: Files being checked by the guard.
- `context_source`: Source used to resolve active work package.

**Validation rules**:

- Guards must resolve active work package at invocation time.
- Guard output must distinguish `scope_violation` from `stale_or_ambiguous_context`.
- In a shared lane, moving from one work package to another must change the ownership set used by the guard.

## Final Sync Diagnostic

**Purpose**: Preserve local command success while reporting non-fatal hosted sync cleanup failures.

**Fields**:

- `local_result`: Success or failure of the local mutation.
- `sync_result`: Success, skipped, or non-fatal failure.
- `diagnostic_code`: Stable diagnostic category.
- `message`: Human-readable diagnostic.
- `stderr_rendered`: Whether diagnostic was rendered to stderr.
- `json_field`: Optional JSON field name when the command contract allows diagnostics in JSON.
- `dedupe_key`: Per-invocation duplicate suppression key.

**Validation rules**:

- If `local_result` is success and `sync_result` is non-fatal failure, stdout must remain parseable.
- Non-fatal diagnostics must not use red command-failure styling.
- Duplicate diagnostics with the same dedupe key should render once per invocation.

## Release Preflight Result

**Purpose**: Prevent unsafe merge/ship signoff.

**Fields**:

- `local_target_branch`: Actual local target branch, `main` for this mission.
- `remote_tracking_branch`: Remote branch used for divergence comparison.
- `ahead_count`: Local commits not on remote.
- `behind_count`: Remote commits not local.
- `diverged`: Whether both local and remote have unique commits.
- `focused_pr_branch`: Deterministic branch name or synthesis path when local target is unsafe.
- `review_artifact_status`: Consistency result for latest review artifact verdicts.

**Validation rules**:

- Diverged local target branch blocks unsafe merge/ship continuation.
- Remediation must name a deterministic focused PR branch path.
- Approved or done work packages cannot silently pass if the latest review artifact verdict is `rejected`.

## Invariants

- Local success requires durable local evidence.
- Canonical mission identity wins over path, slug, or branch reconstruction.
- Active work-package context wins over lane-level stale context.
- Hosted sync cannot invalidate already durable local mutation success unless the local command contract explicitly says sync is part of the mutation.
- Release readiness requires consistency between state, review evidence, and branch safety.
