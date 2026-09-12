---
affected_files:
- path: src/mission_runtime/__init__.py
- path: src/mission_runtime/write_target_degrade.py
- path: src/specify_cli/events/decision_log.py
- path: src/specify_cli/git/bookkeeping_commit.py
- path: tests/architectural/test_mission_runtime_surface.py
- path: tests/mission_runtime/test_write_target_degrade.py
- path: tests/architectural/test_no_write_side_rederivation.py
- path: tests/regression/test_birth_cutover.py
cycle_number: 3
mission_slug: placement-port-residuals-closure-01KYDEF0
reproduction_command: PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest tests/mission_runtime/test_write_target_degrade.py tests/architectural/test_mission_runtime_surface.py tests/architectural/test_no_write_side_rederivation.py tests/regression/test_birth_cutover.py::test_coord_seed_commit_targets_coord_branch_via_real_placement_port tests/retrospective/test_retrospective_durable_home_coord.py tests/retrospective/test_home_resolution_single_authority.py -q
reviewed_at: '2026-07-27T04:32:46Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP04
---

# WP04 Review — Cycle 3: APPROVED

Independent re-review of the re-implemented WP04. Cycle-1 REJECTED because the
migrated `bookkeeping_commit._resolve_bookkeeping_commit_target` raised
`ActionContextError` when `branch is None` *before* attempting resolution,
breaking the reachable fail-open post-merge retrospective path. The current
committed state on lane-d fixes this cleanly. All checks below were run by me
from the lane-d worktree.

## Issue 1 (cycle-1 BLOCKER) — RESOLVED: resolve-first semantics restored

`resolve_write_target_or_degrade` (`src/mission_runtime/write_target_degrade.py:65-120`)
attempts placement resolution FIRST whenever `_mission_meta_exists` is true,
returning the placement-port target regardless of `degrade_ref` (including when
`degrade_ref is None`). The fail-closed raise fires ONLY when resolution has
genuinely failed AND `degrade_ref is None` (lines 108-119). No upfront raise.

`bookkeeping_commit._resolve_bookkeeping_commit_target`
(`src/specify_cli/git/bookkeeping_commit.py:177-198`) is a clean one-line
passthrough to the helper (`degrade_ref=branch`) — no premature raise.

## Degrade policies preserved (NOT flattened)

- **decision_log fail-OPEN:** `_resolve_default_target`
  (`src/specify_cli/events/decision_log.py:121-141`) passes a concrete
  `degrade_ref=destination_ref` (never `None`) → an unresolvable mission
  degrades to the caller's coord ref, never raises.
- **bookkeeping fail-CLOSED:** passes `degrade_ref=branch` (may be `None`) → an
  unresolvable mission with no branch raises `ActionContextError`.

The two policies live at the call sites (via the `degrade_ref` value), not in
the shared helper — correct.

## Reachable production path verified

`post_merge/retrospective_terminus.py:245-251` calls `commit_merge_bookkeeping`
with NO `branch=` argument (defaults `None`), inside a fail-open try/except.
With resolve-first, a resolvable mission (post-merge/close, meta.json present)
now returns the placement-port target and commits — it does NOT hit the
upfront raise the cycle-1 impl had. The new pin
`TestBookkeepingCommitResolvesFirstOnBranchNone::test_branch_none_with_resolvable_mission_returns_placement_target`
asserts `resolve_placement_only` is called once AND its target object reaches
`safe_commit` — this test would FAIL on a raise-first implementation
(commit_merge_bookkeeping would raise before resolution).

## Evidence I ran (lane-d worktree)

- `tests/mission_runtime/test_write_target_degrade.py` — PASS
- `tests/architectural/test_mission_runtime_surface.py` — 7/7 PASS
  (`__all__` == `_PUBLIC_SURFACE` lockstep including the new
  `resolve_write_target_or_degrade` entry)
- `tests/architectural/test_no_write_side_rederivation.py` — PASS
- `tests/regression/test_birth_cutover.py::test_coord_seed_commit_targets_coord_branch_via_real_placement_port`
  — PASS
- `tests/retrospective/test_retrospective_durable_home_coord.py` (+
  `test_home_resolution_single_authority.py`) — 10 PASS (the fail-open
  retrospective terminus path)
- Combined core batch: 42 passed.

## MR-1 lockstep + SC-004

- `__init__.__all__` == `_PUBLIC_SURFACE` (surface test 7/7).
- Exactly ONE `def _mission_meta_exists` in `src/` — the extracted helper
  (`write_target_degrade.py:123`). The two verbatim clones are gone (SC-004,
  asserted by `TestScenario004VerbatimCloneRemoval` AST test).

## Out-of-owned collateral — acceptable rationale-backed leeway

WP04's diff also touches two files outside `owned_files`, both genuinely
required by the consolidation (revert-and-red holds):

1. `tests/regression/test_birth_cutover.py` — the monkeypatch spy target moved
   from `bookkeeping_commit.resolve_placement_only` to
   `mission_runtime.write_target_degrade.resolve_placement_only`, because
   `bookkeeping_commit` no longer imports `resolve_placement_only` (confirmed:
   it now imports only `resolve_write_target_or_degrade`; remaining mentions
   are docstring-only). The old target would patch a nonexistent attribute.
2. `tests/architectural/test_no_write_side_rederivation.py` (WP03's file) — 4
   `_CHECKOUT_GRAMMAR_ALLOW_LIST_SEED` descriptors pointing at the
   `CommitTarget(ref=...)` constructions that used to live in
   `_resolve_default_target` / `_resolve_bookkeeping_commit_target` were
   DELETED; those constructions no longer exist at the call sites (moved into
   the helper), so the live-staleness contract would red if they remained.

Both edits carry in-file coordination notes. Region separation confirmed vs
WP03's approved edits to the same two files:
- `test_no_write_side_rederivation.py`: WP03 @ ~506-523
  (`_PINNED_BOUNDARY_SANCTIONED_PREFIXES`), WP04 @ ~809-830
  (`_CHECKOUT_GRAMMAR_ALLOW_LIST_SEED`) — disjoint.
- `test_birth_cutover.py`: WP03 @ ~605-627
  (`test_birth_then_migration_..._idempotent`), WP04 @ ~827-885
  (`test_coord_seed_commit_targets_coord_branch_via_real_placement_port`) —
  disjoint, different functions.
No clobber. This is acceptable rationale-backed leeway (the no-overlap guard
holds), not an ownership violation.

## Gates

- `ruff check` on owned files — All checks passed.
- `mypy` on owned source files (`write_target_degrade.py`, `decision_log.py`,
  `bookkeeping_commit.py`) — clean. The single reported error
  (`src/runtime/next/_internal_runtime/schema.py:29`) is pre-existing on the
  mission base branch, is not an owned file, and is not in the diff — does not
  count against WP04.

## Verdict

APPROVED. The cycle-1 blocker is genuinely fixed (resolve-first, policies not
flattened), the reachable retrospective path is proven green, MR-1/SC-004 hold,
and the out-of-owned collateral is justified, disjoint, and coordination-noted.
