# Merge-First Suggestion for Completed Multi-Parent Dependencies

**Filename:** `2026-01-29-15-merge-first-suggestion-for-completed-dependencies.md`

**Status:** SUPERSEDED by [ADR-21: "Done" Means Review-Complete, Not Merged](2026-02-04-21-done-means-review-complete-not-merged.md)

**Date:** 2026-01-29

**Deciders:** Robert Douglass

**Technical Story:** Enhances ADR-4's auto-merge behavior with proactive guidance when all multi-parent dependencies are completed, preventing auto-merge conflicts by suggesting merge-first workflow.

---

> **DEPRECATED** - This ADR recommended merging completed dependencies to the target branch before implementing the dependent WP. This was based on the incorrect assumption that "done" means the work should go to the target branch. In reality, "done" means review-complete; WP branches persist and are NOT merged to target until `spec-kitty merge` runs at the feature level.
>
> **What changed:** The `--force` flag now creates a merge base directly from the WP branches (whether "doing" or "done"), without merging anything to the target branch first. The conflict detection logic from this ADR is still used, but the recommended workflow ("merge to main first") is no longer correct.
>
> **See [ADR-21](2026-02-04-21-done-means-review-complete-not-merged.md) for the corrected position.**

---

## Context and Problem Statement

ADR-4 established auto-merge for multi-parent dependencies (e.g., WP04 depends on WP01, WP02, WP03). However, real-world testing (~/tmp Feature 001) revealed a problematic scenario:

**What happened:**
```
1. WP01, WP02, WP03 all completed (in "done" lane)
2. Each modified .gitignore independently
3. Agent ran: spec-kitty implement WP04
4. Auto-merge attempted: WP01 + WP02 + WP03
5. FAILED: .gitignore add/add conflicts
6. Agent manually merged each WP to main
7. Then started WP04 from main
```

**The pattern:**
- When dependencies are **in progress** (doing/for_review), auto-merge makes sense (combine work-in-progress)
- When dependencies are **completed** (done lane), auto-merge is **risky** (likely conflicts on shared files)

**Question:** Should we detect when all multi-parent dependencies are complete and suggest merging them to main **before** implementing the dependent WP?

## Decision Drivers

* **Conflict prevention** - Completed WPs likely modified shared files (.gitignore, package.json, etc.)
* **User experience** - Agents got stuck with auto-merge failures (trial-and-error)
* **Workflow clarity** - Merge-first vs auto-merge have different use cases
* **Agent guidance** - LLMs need explicit recommendations, not trial-and-error
* **ADR-4 enhancement** - Build on auto-merge, don't replace it
* **Backward compatibility** - Existing workflows must still work

## Considered Options

* **Option 1:** Detect all-done and suggest merge-first (error + guidance)
* **Option 2:** Attempt auto-merge, fall back on conflict (reactive)
* **Option 3:** Always require manual merge for multi-parent (strict)
* **Option 4:** Status quo (auto-merge always, user handles conflicts)

## Decision Outcome

**Chosen option:** "Option 1: Detect all-done and suggest merge-first", because:
- Proactive (detects problem before attempting)
- Educational (explains why merge-first is safer)
- Flexible (--force override for auto-merge if needed)
- Agent-friendly (clear guidance, not trial-and-error)
- Prevents common failure mode (all-done + auto-merge = conflicts)

### Consequences

#### Positive

* **Proactive guidance** - Detects problem before attempting auto-merge
* **Clear workflow** - Agent knows to run merge command first
* **Conflict control** - Merge conflicts resolved in structured manner
* **Prevents confusion** - No trial-and-error with auto-merge failures
* **Explicit choice** - Agent can choose merge-first or --force auto-merge
* **ADR-4 enhancement** - Auto-merge still available for work-in-progress scenarios

#### Negative

* **Extra step** - Must run merge command before implement
* **Two commands** - merge then implement (instead of one)
* **Code complexity** - Adds detection logic to implement command
* **User decision** - Agent must choose between merge-first and --force

#### Neutral

* **Detection trigger** - Multi-parent + all done → suggest merge
* **Override mechanism** - --force flag bypasses suggestion
* **Error message** - Blocks implement, suggests merge command
* **Still automatic** - If not all done, auto-merge proceeds normally

### Confirmation

We validated this decision by:
- ✅ 7 tests for dependency detection logic
- ✅ check_dependency_status() correctly identifies all-done scenarios
- ✅ get_merge_strategy_recommendation() provides clear guidance
- ✅ implement command blocks with actionable error message
- ✅ ~/tmp WP04 scenario would now get clear guidance upfront

## Pros and Cons of the Options

### Option 1: Detect all-done and suggest merge-first (CHOSEN)

Pre-flight check before auto-merge. If all dependencies done, error with suggestion.

**Pros:**
* Proactive detection (before failure)
* Clear guidance (suggests exact command)
* Explains trade-offs (merge-first vs auto-merge)
* Prevents common failure mode
* Agent-friendly (no trial-and-error)

**Cons:**
* Extra step (two commands instead of one)
* Code complexity (detection logic)
* Requires --force to override

### Option 2: Attempt auto-merge, fall back on conflict (status quo)

Try auto-merge, if fails, guide user to manual merge.

**Pros:**
* Works for non-conflicting cases
* No pre-flight overhead
* Simpler code (no detection)

**Cons:**
* Reactive (fails first, then suggests)
* Trial-and-error experience
* Wastes time on predictable failures
* Confusing for agents (did it fail or not?)

### Option 3: Always require manual merge

Block multi-parent entirely, force user to merge first.

**Pros:**
* No surprises (never attempts auto-merge)
* Explicit control over all merges

**Cons:**
* Loses auto-merge benefits for work-in-progress
* Too restrictive (many WPs could auto-merge cleanly)
* Breaks existing workflows

### Option 4: Status quo (auto-merge always)

Always attempt auto-merge for multi-parent, let git handle it.

**Pros:**
* No changes needed
* Works for non-conflicting cases

**Cons:**
* Predictable failures (all-done + shared files = conflict)
* No guidance (agent stuck)
* Poor UX (trial-and-error)

## More Information

**Implementation:**
- `src/specify_cli/core/dependency_resolver.py` (new module)
  - `check_dependency_status()` - Detects if all deps done
  - `get_merge_strategy_recommendation()` - Suggests workflow
  - `predict_merge_conflicts()` - Future: dry-run prediction
- `src/specify_cli/cli/commands/implement.py` - Pre-flight check integration
- `src/specify_cli/missions/software-dev/command-templates/tasks.md` - Updated guidance

**Tests:**
- `tests/integration/test_auto_merge_dependencies.py` (7 tests)
- All scenarios validated: all-done, partial-done, single-parent, multi-parent

**Decision Logic:**
```
IF multi-parent AND all dependencies in "done" lane:
  → Suggest: spec-kitty merge --feature <slug>
  → Block: Cannot proceed without --force
  → Explain: Merge-first avoids conflicts

ELSE IF multi-parent AND any dependency doing/for_review:
  → Proceed: Auto-merge (combine work-in-progress)

ELSE IF single-parent:
  → Suggest: Use --base flag
```

**Related ADRs:**
- ADR-4: Auto-Merge Multi-Parent Dependencies (original design)
- ADR-13: Target Branch Routing (status commits advance target, causing staleness)

**Enhances:** ADR-4 (auto-merge still works, now with smart guidance)

**Version:** 0.13.8 improvement (agent guidance enhancement)
