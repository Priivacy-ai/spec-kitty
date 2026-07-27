# WP03 Review — Cycle 1 (reviewer-renata)

**Verdict: CHANGES REQUESTED** (2 blocking issues). The seam design, R3 decision
row, husk-spoof flips, scope fence, and 5-site migration are otherwise excellent
and correct. Both blockers are narrow and quick to fix.

---

## What is correct (no action needed)

- **Seam API (FR-005)**: `WorktreeTopology`, `classify_worktree_topology`,
  `is_registered_coord_worktree`, `read_worktree_registry`,
  `is_under_worktrees_segment` match `research-authority-seams.md` and C-SEAM-1.
  Name proposes / registry disposes is implemented faithfully; registry is
  injectable + cached frozenset; scanner reads it once per pass (no N× shelling).
- **R3 (FR-008)**: `CoordinationBranchDeleted` (subclass of `StatusReadPathNotFound`,
  `error_code=COORDINATION_BRANCH_DELETED`, actionable `next_step`). One
  `git rev-parse --verify` disambiguates R2 vs R3; non-git context correctly does
  NOT fire R3 (`_coord_branch_exists` fails closed to "present"). All 7
  decision-table pins (R1/R2/R2'/R3/R4) are real end-to-end git tests, not
  synthetic fixtures — `test_r3_never_falls_back_to_primary` directly pins
  NFR-003. R3 composes with the #1848 carve-out as designed.
- **C-SEAM-1 routing discipline**: `is_under_worktrees_segment`'s only consumer is
  `status_service._is_coordination_worktree_path`, used purely for contract-LABEL
  consistency guards (raises `StatusContractError` on label/shape mismatch) — NOT
  authority routing. No migrated site routes on the shape idiom. Routing decisions
  go through `is_registered_coord_worktree`. Correct.
- **C-002 fence**: `status_transition.py`, `aggregate.py`, `merge.py` untouched
  (verified via `git log <base>..HEAD -- <file>` — all empty).
- **NFR-001 fixture exceptions — BOTH LEGITIMATE**:
  - `test_handle_equivalence_matrix.py`: the old fixture declared
    `coordination_branch` in meta but never created the branch — an incoherent
    state that WP03's new R3 correctly rejects. Adding `git branch <coord>` models
    the real `ensure_coordination_branch` R2 contract. Valid documented exception.
  - `test_scanner.py` coord-prefer test: the old test asserted a bare (unregistered)
    `-coord` *directory* shadows primary — i.e. it pinned the husk-spoof BUG WP03
    fixes. Converting it to a registered `git worktree add` preserves the legitimate
    contract and the new `test_dashboard_husk_coord_dir_does_not_shadow_primary`
    pins the flip. This is the WP's intended "behavior-preserving except where the
    old predicate was WRONG."
- **Dead-symbols allowlist (test_no_dead_symbols.py)**: narrowly-scoped, mission-
  tagged `_CATEGORY_C_WP_IN_FLIGHT_TOPOLOGY_AUTHORITY` listing only
  `ResolvedStatusSurface` (predates WP03, opted in via `__all__`) and
  `CoordinationBranchDeleted` (caught transitively by ~13 existing
  `except StatusReadPathNotFound` handlers; by-name consumer lands in WP05). Not a
  general escape hatch. Self-expiring once WP05 lands. Acceptable.
- ruff clean on all 6 owned files; 126 seam/decision/scanner/equivalence tests +
  668 status+architectural tests + 92 emit/lifecycle/canonical-root tests all green.
- Pre-existing-failure honesty: `test_non_git_directory_raises` fails identically
  on the merge-base (tests `resolve_canonical_root`, untouched by WP03). Honest.

---

## BLOCKING ISSUE 1 — New mypy error under the CI-authoritative invocation

The `# type: ignore[misc]` on `class CoordinationBranchDeleted(StatusReadPathNotFound)`
(surface_resolver.py:104) is correct under **single-file** mypy (the `missions/`
exclude makes the base resolve to `Any` → `cannot subclass "Any" [misc]`). But the
project's CI runs the **full-package** invocation (ci-quality.yml:497):

    mypy --strict src/specify_cli src/charter src/doctrine

Under that invocation the base class IS resolvable, so the `[misc]` error does not
fire and the suppression is reported as:

    src/specify_cli/coordination/surface_resolver.py:104:
      error: Unused "type: ignore" comment  [unused-ignore]

Measured: base = 82 errors, WP03 lane = 83 errors. The delta is exactly this one
line. This violates the CLAUDE.md "zero new mypy errors and zero warnings" standard
(and the project does NOT disable `unused-ignore` — see the commented-out
`--disable-error-code` in pyproject.toml).

**Fix (verified to satisfy BOTH invocations — single-file clean AND full-package
back to 82):**

    class CoordinationBranchDeleted(StatusReadPathNotFound):  # type: ignore[misc, unused-ignore]

Update the inline rationale to note both invocations.

---

## BLOCKING ISSUE 2 — Lock-root flip (emit.py / work_package_lifecycle.py) is untested

The lock-root change is described as "canonical-root resolution for registered
worktrees — fixes lock mis-route" (a concurrency-correctness fix: two processes
anchored on one mission via different worktrees must share a lock root). The new
branch is:

    if topology in (WorktreeTopology.COORD_WORKTREE, WorktreeTopology.LANE_WORKTREE):
        return resolve_canonical_root(feature_dir)

This branch is **not exercised by any test**. Mutation test: disabling it
(`if False and ...`) in both emit.py and work_package_lifecycle.py breaks ZERO
tests (72/72 still pass). The pre-existing `test_canonical_root_when_in_worktree.py`
uses a `wt-feature` worktree that is NOT under a `.worktrees/` segment, so
`classify_worktree_topology` returns PRIMARY and the new branch is bypassed; it
exercises `resolve_canonical_root` via a different path, not the lock-root flip.

Per anti-pattern checklist item 2 and the "fixes lock mis-route" claim: a
concurrency-correctness change with no failing-if-deleted test is an unverified
behavioral change on the exact defect class this seam exists to kill.

**Fix:** add one regression test (in an owned `tests/.../test_worktree_topology*.py`
or the status emit/lifecycle suite) that:
  1. creates a real `git worktree add` UNDER `<repo>/.worktrees/<...>-coord` (or a
     lane worktree), and a `kitty-specs/<mission>` feature_dir inside it;
  2. asserts `_feature_status_lock_root(feature_dir, repo_root=None)` (and the
     `work_package_lifecycle._repo_root_for_lock` twin) returns the CANONICAL main
     repo root, NOT the worktree-local `parent.parent`;
  3. ideally asserts a primary-checkout feature_dir and the worktree feature_dir for
     the same mission resolve to the SAME lock root (the cross-context agreement
     that is the whole point of the fix).
Confirm the test FAILS when the new branch is reverted.

---

## Non-blocking note

- C-RATCHET test (`tests/architectural/test_topology_resolution_boundary.py`, FR-009)
  does not exist — but FR-009 is out of WP03 scope (WP03 = FR-005/FR-008). No action.
