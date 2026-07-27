---
verdict: approved
reviewer: reviewer-renata
cycle: 2
mission_slug: single-planning-surface-authority-01KVPR00
wp_id: WP07
cycle_number: 2
reviewed_at: '2026-06-22T18:30:00Z'
reproduction_command: 'PWHEADLESS=1 python3 -m pytest tests/specify_cli/missions/test_is_committed_coord_aware.py tests/integration/test_p0_pinning_regressions.py tests/specify_cli/cli/commands/agent/test_mission_planning_entry.py -q'
---

# WP07 cycle-2 — APPROVED (FR-011 `is_committed` collapse; genuine single-surface unification)

Reviewed through the binding UNIFICATION lens: success = `is_committed` now consults the ONE
canonical read-resolved surface with the multi-surface OR + #7 workaround GONE — NOT cell-for-cell
parity with the retired 3-leg OR.

## 1. UNIFICATION (primary gate) — PASS

`is_committed` (`_substantive.py:301`) is reduced to a SINGLE check: tracked AND present at `HEAD`
of the git surface the file physically lives on (derived from `file_path` via the existing
`_git_commit_check_context`). Verified the OR is genuinely DELETED, not refactored-but-retained:

- The `placement` / `target_branch` / `primary_repo_root` params are GONE from the signature.
- Leg 1 (coord-ref) and Leg 3 (primary-target-branch / FR-005 #7) blocks are DELETED; the body is
  now `head_hit = _head_carries_path(...); return head_hit`.
- `_ref_carries_path` is REMOVED from src entirely (`grep -rn _ref_carries_path src/` → none; it
  survives only as a *test-local* reconstruction helper for the parity assertion).
- `_substantive.py` no longer imports `CommitTarget`/`CommitTargetKind`/`routes_through_coordination`
  and no longer re-derives topology (`grep` → none).
- Net deletion: `_substantive.py` + `mission.py` = 52 ins / 116 del (≈64 net LOC removed; consistent
  with randy's −94 once added doc-comments are netted). `is_committed` complexity is now ~3
  branch-points (well under 15).
- Sole non-test caller `mission.py:2130` simplified to `is_committed(spec_file, repo_root,
  diagnostics=...)` — the in-scope sole-caller co-change.

## 2. NOT PARITY-CHASING (the #7 tests) — PASS (genuine removal)

The #7/FR-005 leg behaviour is genuinely REMOVED, not contorted to preserve a removed quirk:

- The old quirk-pinning tests are DELETED, not re-keyed to preserve old behaviour:
  `test_coord_placement_file_on_coord_branch_returns_true`,
  `test_coord_placement_file_on_both_branches_returns_true` (the OR-logic test),
  `test_coord_placement_nonexistent_branch_falls_back_to_head`,
  `test_flattened_placement_uses_head_check`, `test_primary_placement_uses_head_check`.
- EVERY `is_committed(...)` call in the test now uses the collapsed signature — no `placement=`,
  no `target_branch=`. The removed params are gone from every assertion.
- The decisive anti-parity-chasing evidence: `test_spec_uncommitted_on_primary_surface_returns_false`
  asserts the exact scenario the #7 leg existed to RESCUE (primary path + coord-only spec) now
  returns **False** — the new unified reality, the OPPOSITE of the removed quirk. A parity-chaser
  would have contrived this to stay True; randy pinned it to False.
- The `test_is_committed_fr011_parity` 6-cell test reconstructs the retired OR *on the same
  read-resolved spec the caller feeds* and asserts equivalence. It is correctly framed as
  equivalence DOCUMENTATION (cycle-1 explicitly requested "ADD a PARITY assertion"), not as the
  gate. It does NOT re-pin the standalone #7-leg false-negative rescue (that combination is
  unreachable because the read path never feeds primary-path-with-coord-only-spec).

## 3. LOAD-BEARING INVARIANTS (#1718, #1848) — PASS (witnessed live)

- **#1848 coord-deleted — never reached, source re-verified independently.**
  `CoordinationBranchDeleted(StatusReadPathNotFound)` confirmed subclass
  (`surface_resolver.py:167`). `_find_feature_directory` (`mission.py:1168`) calls
  `resolve_handle_to_read_path`; at `:1175` `except StatusReadPathNotFound → raise ActionContextError`.
  The setup-plan call site `:2073` `except (ValueError, ActionContextError) → Exit(1)` fires BEFORE
  `is_committed` at `:2130`. LIVE repro: a mission declaring a coordination_branch whose ref was
  never created raises `CoordinationBranchDeleted` from `resolve_handle_to_read_path(require_exists
  =True)` — confirmed `is_committed` is never reached. Switching to the read surface cannot regress
  coord-deleted.
- **#1718 create-window — resolves PRIMARY → True, witnessed live.** Built the topology
  (coord branch declared+exists, worktree unmaterialised, spec on primary HEAD); read path
  resolved to the PRIMARY dir (`.worktrees` not in path); `is_committed` returned True with
  diagnostics showing a SINGLE surface checked (`HEAD:...spec.md: hit`) — not a 3-leg OR.

## 4. LIVE EVIDENCE — PASS

Both load-bearing cells reproduced live in throwaway repos (not "code looks right"):
create-window read→primary→True; coord-deleted read-raises-before-is_committed. The materialized
COORD + SINGLE_BRANCH + LANES cells are covered by the green parametrized parity test.

## 5. FR-005 (T036) + sweep — PASS (within WP07 scope)

The two WP07-owned decision sites in `mission.py` (`_planning_commit_worktree:768`,
`_enforce_analysis_report_write_preflight:863`) now route through `routes_through_coordination(...)`
instead of `.kind is COORDINATION`. Repo-wide sweep: the only surviving `.kind is COORDINATION`
*decision* read inside WP07's surfaces is canonical (inside `routes_through_coordination` itself,
`context.py:131`). NOTE (non-blocking, cross-WP boundary): `tasks.py:359`
(`_planning_review_base` review-currency) still uses a direct `.kind is COORDINATION` — that is a
DIFFERENT FR-005 site, NOT in WP07's owned diff, and is out of this WP's scope. Flagged for the
orchestrator; not a WP07 defect.

## 6. GATES — PASS

- ruff: clean on all three diff-scoped files.
- mypy: clean on `_substantive.py`.
- complexity: `is_committed` ≈3 (≤15).
- no suppressions added to production code (the test's `# noqa: BLE001` mirrors the retired
  caller's intentional broad catch in the reconstruction helper — narrow, justified).
- tests: WP07 file 12/12 pass; P0 pinning regressions 8/8; mission planning entry 9/9.
- working tree clean (stash-check: no uncommitted divergence).

## Known pre-existing (orchestrator, not WP07 defects)

WP01 `test_public_surface_matches_contract` symbol gap and WP02 dead-symbol debt — per prompt,
handled at pre-merge.

## Verdict

**APPROVED.** This is genuine single-surface unification: the multi-surface OR and the #7/FR-005
workaround are deleted (net −64 LOC, helper removed), `is_committed` consults the one read-resolved
surface, and the removed quirk is NOT re-pinned (the rescue scenario now correctly returns False).
The two load-bearing invariants (#1718 create-window, #1848 coord-deleted) are preserved — both
witnessed on live repros, the coord-deleted short-circuit re-verified at the source. Cycle-1
re-work feedback fully addressed.
