---
affected_files: []
cycle_number: 1
mission_slug: single-planning-surface-authority-01KVPR00
reproduction_command:
reviewed_at: '2026-06-22T17:44:42Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP07
---

# WP07 cycle-1 → re-work: FR-011 clean path adjudicated (investigation result)

The collapse was correctly self-blocked in cycle 1. A focused alphonso+randy investigation
+ source adjudication (orchestrator) found a CLEAN, behavior-preserving FR-011 path WITHIN
`_substantive.py` ownership. Implement it now.

## The adjudicated design (alphonso, source-verified)

`is_committed` has EXACTLY ONE non-test caller: setup-plan `mission.py:2131`, whose `spec_file`
(`= feature_dir / "spec.md"`, :2085) is ALREADY the READ-resolved surface (`feature_dir` from
`_find_feature_directory` :2064 = `resolve_handle_to_read_path(require_exists=True)`).

COLLAPSE: reduce `is_committed` (`:317-412`) from the 3-leg OR to a SINGLE-surface check —
"is `file_path` committed on the git surface it actually lives on" — using `file_path`'s own
git context (the existing `_git_commit_check_context` machinery, `:263-283`). Drop the
`placement` / `target_branch` / `primary_repo_root` params and the OR machinery; simplify the
one call site accordingly.

## Why it is behavior-preserving (per-cell, source-verified)

- SINGLE_BRANCH / LANES / flattened: read surface = PRIMARY; spec on primary HEAD → True (== OR leg 2).
- COORD materialized: read surface = COORD dir; spec on coord branch → True (== OR leg 1).
- create-window #1718 (coord declared, worktree UNMATERIALIZED): read surface = PRIMARY
  (`_resolve_not_found` / UNMATERIALIZED, `_read_path_resolver.py`); spec on primary HEAD → True
  (== OR, which is rescued by the coord-ref/HEAD legs). This is the cell that diverged for the
  WRITE placement (placement=COORD) but CONVERGES for the READ surface.
- coord-deleted #1848: `is_committed` is NEVER REACHED — `_find_feature_directory` (:2064) raises
  `CoordinationBranchDeleted` (a `StatusReadPathNotFound`) → re-raised `ActionContextError` →
  caught at :2069 → `Exit(1)`, BEFORE :2131. So switching is_committed to the read surface cannot
  regress coord-deleted (it is short-circuited upstream).

## REQUIRED co-change (the guard — non-negotiable, randy's valid point)

The envelope test `tests/specify_cli/missions/test_is_committed_coord_aware.py` is MISSING the
create-window and coord-deleted cells. ADD them, plus a PARITY assertion proving the new
single-surface check returns the SAME verdict the retired 3-leg OR did, across ALL 6 cells:
- create-window: assert single-via-read == True (spec on primary HEAD).
- coord-deleted: assert `is_committed` is NEVER REACHED at the setup-plan call site (the read
  path raises `ActionContextError`/exits first) — i.e. pin the UPSTREAM short-circuit, not an
  is_committed verdict. Witness this on a real repro.
Keep the existing #1718/#1848 P0 pins green. Remove any now-orphaned helper (`_ref_carries_path`
/ `_head_carries_path`) with grep proof, or document why it survives.

## Gate (unchanged)
Witness verdict-equivalence on a LIVE flattened + create-window repro before finalizing.
"The code looks right" is an automatic rejection. NFR-003 behavior-preserving; ruff+mypy clean;
complexity ≤15; the repo-wide FR-005 completeness sweep (only surviving `.kind is COORDINATION`
decision read is inside `routes_through_coordination`).
