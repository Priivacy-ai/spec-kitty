# "Done" Means Review-Complete, Not Merged to Target

**Filename:** `2026-02-04-21-done-means-review-complete-not-merged.md`

**Status:** Accepted (supersedes ADR-18)

**Date:** 2026-02-04

**Deciders:** Robert Douglass

**Technical Story:** Corrects a fundamental semantic error in ADR-18 where "done" lane was conflated with "merged to target branch". In production, this caused `implement` to branch from the target branch (missing the dependency's code) instead of from the dependency's WP branch.

---

## Context and Problem Statement

ADR-18 ("Auto-Detect Merged Single-Parent Dependencies") established that when a dependency WP's lane is "done", the `implement` command should branch from the target branch because "the work is already there." This was wrong.

**The actual workflow:**

```
1. WP01 implemented in worktree on branch `025-feature-WP01`
2. WP01 passes review → lane set to "done"
3. WP01 worktree cleaned up, but branch `025-feature-WP01` persists
4. WP01's code is NOT in the target branch (e.g., 2.x)
5. Merging WP branches into target happens later via `spec-kitty merge`
```

**What ADR-18 assumed:**

```
"done" lane → WP merged to target → branch deleted → branch from target
```

**What actually happens:**

```
"done" lane → review complete → branch still exists → branch from WP branch
```

**The bug this caused (three locations in implement.py):**

1. **Validation step:** When base WP was "done", validation was skipped entirely (`pass`) instead of verifying the WP branch exists.
2. **Create workspace step:** When base WP was "done", the code branched from the target branch (which doesn't contain the WP's code) instead of from the WP's branch.
3. **Multi-parent auto-merge:** When all dependencies were "done", the code short-circuited to branch from target instead of creating a merge base from the WP branches.

**Real-world impact:** Feature 025-cli-event-log-integration. WP02 depended on WP01 (done). `implement WP02` branched from `2.x` which did NOT contain WP01's event infrastructure code. The workspace was missing all of WP01's work.

## Decision Drivers

* **Semantic correctness** - "done" is a lane status meaning review-complete, not a git operation
* **Separation of concerns** - Lane management (kanban) is separate from branch management (git)
* **Feature-level merge** - `spec-kitty merge` is the command that merges WP branches to target; `implement` should not assume this has happened
* **Branch persistence** - WP branches persist after review (per ADR-9: cleanup at merge, not at review)
* **Data integrity** - Branching from target loses the dependency's code entirely

## Considered Options

* **Option 1:** "Done" means review-complete; branch from WP's branch (correct semantics)
* **Option 2:** "Done" means merged to target; branch from target (ADR-18's position, incorrect)
* **Option 3:** Add a separate "merged" lane to distinguish review-complete from merged

## Decision Outcome

**Chosen option:** "Option 1: Done means review-complete; branch from WP's branch", because the lane status tracks review workflow, not git operations. Merging is a separate operation performed by `spec-kitty merge` at the feature level.

### Lane Lifecycle (Authoritative)

```
planned → doing → for_review → done
                                  ↓
                    (branch persists, worktree may be cleaned up)
                                  ↓
                    spec-kitty merge (feature-level operation)
                                  ↓
                    WP branches merged to target, then deleted
```

### Implementation Rules

1. **When base WP is "done":** Branch from `{feature_slug}-{base_wp_id}` (the WP's branch, which contains the implementation code).
2. **When all multi-parent dependencies are "done":** Create merge base from their WP branches (not from target).
3. **Validation:** When base WP is "done", verify its branch exists. Error if branch was prematurely deleted.
4. **Never assume "done" means code is in target.** Only `spec-kitty merge` puts code in target.

### Consequences

#### Positive

* **Correct code inheritance** - Dependent WPs get their dependency's actual implementation
* **Clean separation** - Lane status (review workflow) decoupled from git operations (merge)
* **No data loss** - Branching from WP branch guarantees the dependency's code is present
* **Consistent model** - Same branching logic whether dependency is "doing" or "done"
* **Feature-level merge preserved** - `spec-kitty merge` remains the single point of truth for target integration

#### Negative

* **Branch must persist** - WP branches cannot be deleted until feature-level merge completes
* **Contradicts ADR-18** - Requires superseding a recently accepted ADR
* **Slightly more complex** - Must look up WP branch name rather than defaulting to target

#### Neutral

* **ADR-9 unaffected** - ADR-9 says "cleanup at merge" which means feature-level merge, consistent with this ADR
* **ADR-15 updated** - Multi-parent all-done case now creates merge base from WP branches instead of branching from target

### Confirmation

Validated by:
- Integration tests in `test_merged_dependency_workflow.py` (4 tests covering single-parent done, multi-parent all-done, parallel dependents, and in-progress regression)
- All 1967 tests pass with the corrected implementation
- Real-world fix for Feature 025 workflow

## Pros and Cons of the Options

### Option 1: "Done" = review-complete, branch from WP branch (CHOSEN)

"Done" is purely a review/kanban status. The WP's branch persists and contains the implementation. Dependent WPs branch from it.

**Pros:**
* Semantically correct (lane tracks review, not git state)
* No data loss (dependency's code always available)
* Consistent with `spec-kitty merge` being the merge operation
* Consistent with ADR-9 (branches persist until feature merge)

**Cons:**
* WP branches accumulate until feature merge (minor disk/ref overhead)
* Must handle edge case where branch was prematurely deleted

### Option 2: "Done" = merged to target, branch from target (ADR-18)

Assumes that when a WP is "done", its code has been merged to the target branch.

**Pros:**
* Simpler logic (just use target branch)
* No need to look up WP branch name

**Cons:**
* **Factually wrong** - "done" does not mean merged; `spec-kitty merge` does that
* **Causes data loss** - Branching from target misses the dependency's code entirely
* **Breaks real workflows** - Proven broken in Feature 025

### Option 3: Add a separate "merged" lane

Add a new lane after "done" to explicitly track when code reaches target.

**Pros:**
* Unambiguous (each state has one meaning)
* Could enable workflows that distinguish review-complete from integrated

**Cons:**
* Adds complexity to the kanban model
* `spec-kitty merge` operates on features, not individual WPs, making per-WP "merged" lane awkward
* Over-engineering for the current workflow

## More Information

**Supersedes:** ADR-18 ("Auto-Detect Merged Single-Parent Dependencies")

ADR-18's core error was equating `lane == "done"` with "merged to target branch." This conflation led to three bugs in `implement.py` where the code branched from the target branch (missing the dependency's work) instead of from the WP's implementation branch.

**Related ADRs:**
- **ADR-9:** Worktree Cleanup at Merge - Establishes that branches persist until feature-level merge. Consistent with this ADR.
- **ADR-15:** Merge-First Suggestion for Multi-Parent - Updated to create merge base from WP branches, not from target.

**Key principle:** Lane status tracks review workflow. Git operations (merge to target) are performed by `spec-kitty merge` at the feature level. These are independent concerns.

**Version:** 0.13.22 (bugfix)
