# Separate Feature Planning Branch from Merge Target

**Filename:** `2026-03-20-1-separate-feature-planning-branch-from-merge-target.md`

**Status:** Accepted

**Date:** 2026-03-20

**Deciders:** Robert Douglass

**Technical Story:** Reworks the PR-265 branch-contract change after finding that overloading `target_branch` broke feature creation, planning artifact validation, and status commits.

---

## Context and Problem Statement

ADR-13 introduced `target_branch` as the branch where status commits should land. ADR-14 then made that field explicit in `meta.json`, and ADR-17 allowed the target branch to be created later when a feature was first implemented.

That model worked as long as `target_branch` meant one thing: the branch the completed feature eventually merges into.

PR-265 tried to solve a real problem by making planning artifacts live on a dedicated per-feature branch. However, it reused `target_branch` for that new role. That conflated two separate concepts:

1. The branch that owns planning and status artifacts during feature development
2. The branch that the finished feature eventually merges into

The result was internally inconsistent behavior:

* `create-feature --target-branch 2.x` could leave planning artifacts on the wrong branch
* `implement` started enforcing that planning artifacts must already be committed on the merge target
* existing recovery paths could claim success on the feature branch while still committing on the caller's branch
* delayed creation of a future merge target (ADR-17) was at risk because feature creation now tried to branch from a target that might not exist yet

The architectural question is: how should Spec Kitty represent feature-local planning state without losing the existing meaning of `target_branch`?

## Decision Drivers

* **One field, one meaning** - Branch metadata must not overload multiple roles
* **Preserve merge semantics** - Merge/orchestrator code already treats `target_branch` as final integration target
* **Planning integrity** - Specs, plans, tasks, and status mutations must live on a durable per-feature branch
* **Backward compatibility** - Existing features without `feature_branch` must still work
* **ADR-17 compatibility** - Future merge targets may not exist when a feature is created
* **Explicit metadata** - The branch contract must stay visible in `meta.json`

## Considered Options

* **Option 1:** Reuse `target_branch` for both planning and final merge
* **Option 2:** Replace `target_branch` with `feature_branch` everywhere
* **Option 3:** Keep `target_branch` for final merge and add `feature_branch` for planning/status

## Decision Outcome

**Chosen option:** "Option 3: Keep `target_branch` for final merge and add `feature_branch` for planning/status", because it solves the planning-branch problem without breaking the established merge contract.

### Consequences

#### Positive

* **Clear branch contract** - `target_branch` means final merge target, `feature_branch` means planning/status branch
* **Planning commands become deterministic** - `create-feature`, `setup-plan`, `finalize-tasks`, task status changes, and workflow status updates all use the feature planning branch
* **Merge flow stays compatible** - existing merge code can keep treating `target_branch` as the integration destination
* **ADR-17 stays valid** - if the merge target does not exist yet, the feature branch is created from the current branch and `created_from_branch` records that bootstrap point
* **Backward compatible** - planning-branch resolution falls back to legacy metadata when `feature_branch` is missing

#### Negative

* **Metadata grows again** - `meta.json` now needs `feature_branch` in addition to `target_branch`
* **More branch concepts to explain** - users and prompts must distinguish planning branch from merge target
* **Legacy helper names may lag** - some internal function names still refer to "target branch" while enforcing planning-branch behavior

#### Neutral

* **`created_from_branch` becomes meaningful** - it records where the feature planning branch was actually forked from
* **Status artifacts move with planning artifacts** - branch-local planning state now advances on the feature branch instead of the merge target
* **Legacy features degrade safely** - missing `feature_branch` falls back to `target_branch`, then the detected primary branch

### Confirmation

We confirmed this decision by:

* reproducing the original PR-265 regressions where planning and merge branches were conflated
* updating `create-feature` so explicit merge targets can differ from the feature planning branch
* adding regression tests for explicit target branches, missing target branches, and failed existing-branch checkout recovery
* updating `implement` to validate planning artifacts against `feature_branch`
* verifying task/workflow planning-state commands run from the feature planning branch

## Pros and Cons of the Options

### Option 1: Reuse `target_branch` for both roles

Make `target_branch` represent both planning/status state and final merge destination.

**Pros:**

* Minimal schema change
* Superficially simple
* Keeps one branch field in metadata

**Cons:**

* Conflates two separate responsibilities
* Breaks merge/orchestrator assumptions
* Makes planning validation incorrect for features targeting `2.x`, `3.x`, or other non-current merge branches
* Conflicts with delayed target creation from ADR-17

### Option 2: Replace `target_branch` with `feature_branch` everywhere

Drop `target_branch` and make all flows reason about a single feature branch.

**Pros:**

* Very clear planning model
* Simplifies status/planning routing

**Cons:**

* Loses explicit final merge destination
* Requires major changes to merge, preflight, and orchestrator code
* Breaks existing metadata and tooling contracts

### Option 3: Separate `feature_branch` from `target_branch` (CHOSEN)

Use one explicit branch for planning/status state and one explicit branch for final merge.

**Pros:**

* Preserves existing merge semantics
* Makes planning/status routing explicit
* Compatible with legacy metadata and delayed target creation
* Matches the actual workflow: plan on feature branch, merge into target branch

**Cons:**

* Adds another metadata field
* Requires prompt/template updates
* Requires careful documentation to avoid user confusion

## More Information

**Implementation:**

* `src/specify_cli/core/feature_detection.py`
* `src/specify_cli/cli/commands/agent/feature.py`
* `src/specify_cli/cli/commands/agent/tasks.py`
* `src/specify_cli/cli/commands/agent/workflow.py`
* `src/specify_cli/cli/commands/implement.py`

**Tests:**

* `tests/specify_cli/test_cli/test_agent_feature.py`
* `tests/specify_cli/test_core/test_create_feature_branch.py`
* `tests/specify_cli/core/test_feature_detection.py`
* `tests/specify_cli/test_implement_command.py`

**Related ADRs:**

* **Supersedes ADR-13**: Target Branch Routing for Status Commits
* **Clarifies ADR-14**: Explicit Metadata Fields Over Implicit Defaults
* **Preserves ADR-17**: Auto-Create Target Branch on First Implement
