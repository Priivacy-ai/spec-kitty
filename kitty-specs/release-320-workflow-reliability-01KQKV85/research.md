# Research: 3.2.0 Workflow Reliability Blockers

## Decision: Treat local status events as the success source of truth

**Rationale**: Issue #945 shows that command success without a matching `status.events.jsonl` event makes all downstream lane, review, merge, and dashboard state suspect. The existing status package already has event append, read, reducer, materialization, and work-package lifecycle helpers. The lowest-risk plan is to add post-write readback checks around transition commands rather than create a new state system.

**Alternatives considered**:

- Trust frontmatter or materialized snapshots after transitions. Rejected because the mission's invariant is event persistence, and snapshots are derived state.
- Add a second audit log for transition success. Rejected because it duplicates the canonical event log and increases reconciliation burden.

## Decision: Verify #944 through interrupted-action fixtures, not new workflow semantics by default

**Rationale**: #944 is linked as verification-only. The plan should prove that backgrounded, interrupted, or slow implement/review commands do not strand work packages in `claimed`. If the fixture fails, the implementation work becomes a focused correction to lifecycle recovery; otherwise it remains regression coverage.

**Alternatives considered**:

- Rework claimed-state lifecycle preemptively. Rejected because the issue is closed and broad lifecycle rewrites increase release risk.

## Decision: Make review prompt files invocation-specific and self-validating

**Rationale**: Issue #949 requires collision-proof prompt generation across concurrent missions and repos. Storing prompts under a path keyed by repo identity, mission id or slug, work package id, and invocation id prevents collisions. Embedding metadata lets the dispatcher fail closed if the file content does not match the requested review.

**Alternatives considered**:

- Continue writing predictable temporary prompt names. Rejected because concurrent reviews can overwrite or reuse stale content.
- Rely on file paths only. Rejected because copied or stale files can still be dispatched accidentally.

## Decision: Generate review diffs from canonical state

**Rationale**: Issue #950 is a branch/ref identity problem. Slugs that begin with `mission-` can break reconstructed naming conventions. The plan requires diff commands to use mission metadata, lane/workspace context, and resolved branch contract data instead of string reconstruction.

**Alternatives considered**:

- Patch the slug reconstruction rules. Rejected because future slug edge cases would keep creating variants of the same bug.

## Decision: Resolve active work-package ownership at guard time

**Rationale**: Issue #951 shows shared lanes can retain stale ownership context from a previous work package. The guard must resolve the active work package for the current invocation, then read that work package's `owned_files`. If active context is missing or contradictory, report a guard-context error instead of a scope violation.

**Alternatives considered**:

- Store one lane-level ownership set. Rejected because sequential work packages in one lane can legitimately own disjoint files.
- Disable ownership enforcement in shared lanes. Rejected because it loses an important safety guard.

## Decision: Separate local mutation success from final-sync diagnostics

**Rationale**: Issue #952 requires successful local state changes to remain parseable and non-fatal when final SaaS/sync cleanup fails. The plan keeps local mutation exit status tied to local durability and renders sync cleanup issues as structured diagnostics on stderr or explicit JSON fields.

**Alternatives considered**:

- Treat any sync failure as command failure. Rejected because it makes durable local success look like failure and breaks automation.
- Suppress sync diagnostics. Rejected because operators still need visibility into hosted sync issues.

## Decision: Add merge/ship preflight for diverged local `main`

**Rationale**: Issue #953 requires detecting divergence before an agent reconstructs branches manually. The plan adds a preflight result that compares the local target branch with its remote tracking branch and, when unsafe, offers a deterministic focused PR branch path based on mission-owned changes.

**Alternatives considered**:

- Let Git fail during merge or push. Rejected because the user-facing problem is late, ambiguous failure.
- Always force agents to manually create a branch. Rejected because the requirement asks for a deterministic path.

## Decision: Gate approved/done state against latest review artifact verdict

**Rationale**: Issue #904 requires preventing silent contradiction between work-package lane state and latest `review-cycle-N.md` frontmatter. The plan adds a consistency check before mission-review/ship signoff so stale `verdict: rejected` artifacts are either corrected or block release readiness.

**Alternatives considered**:

- Ignore review artifacts after lane state changes. Rejected because stale rejected artifacts are part of the release evidence trail.
- Rewrite old review artifacts automatically. Rejected unless the implementation can prove the latest artifact is stale and produce an audit note; a hard warning or failure is safer.

## Decision: Keep testing local and deterministic

**Rationale**: The mission needs reliable regression tests for release blockers. Tests should use temporary repositories, mission fixtures, monkeypatched sync clients, and local command runners. Commands that exercise sync behavior on this computer must include `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, but external services should be mocked unless a work package explicitly scopes a hosted integration path.

**Alternatives considered**:

- Use the dev SaaS deployment for all sync tests. Rejected because network state would make release-blocker regression tests flaky.
