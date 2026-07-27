---
affected_files: []
cycle_number: 1
mission_slug: mission-identity-seam-and-1908-panel-01KV6510
reproduction_command:
reviewed_at: '2026-06-15T20:34:35Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
review_artifact_override_at: "2026-06-15T20:50:41Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP02"
review_artifact_override_reason: "Cycle-1 re-review APPROVED (reviewer-renata). --skip-review-artifact-check: rejected review-cycle-1.md is the PRIOR cycle artifact, addressed by c1 commit 3bc51f512. --force: benign kitty-specs drift on lane-b checkout (status authority is the coord worktree; lane diverges from merged mission branch) — NOT a code defect. VERIFIED: teardown merge.py:2786 routed via worktree_path(mission_id=_baseline_mission_id @L2400) — byte-identical to WP03 allocator for embedded slug (zero churn), KEEPS mid8 for un-embedded NNN- (TestWorktreeTeardownSeamRouting, real seam). resolve_branch_name in _check_mission_branch: embedded->identical+no warning (#1978 intact), legacy NNN->identical legacy+EXACTLY ONE one-shot DeprecationWarning, modern->BranchIdentityUnresolved (fail-closed). mission_branch_name_required RETAINED at pure-composer sites. Zero residual kitty/mission-{slug} f-strings in 3 files. Dead-symbols: resolve_branch_name+worktree_path cleared; residual flags = WP09 allowlist + WP01 cross-lane, not WP02 defects. ruff/mypy clean; 55 tests green; no new suppressions; tests/architectural untouched; scope clean. #1978 stays fixed."
---

# WP02 review feedback — cycle 1 (two additions surfaced by WP09's ratchet)

Your cycle-0 work is APPROVED-quality and stays (the 3 false-compose sites + runtime_bridge mid8
callers + collateral preflight tests are all correct). Two additions:

## 1. Route the worktree-teardown name-guess (`cli/commands/merge.py:2786`) — LIVE DEFECT
In the `--remove-worktree` teardown loop:
```python
wt_path = main_repo / ".worktrees" / f"{mission_slug}-{lane.lane_id}"
```
This guesses `<slug>-<lane>` with NO mid8. For a mid8-era mission the on-disk worktree is
`<slug>-<mid8>-lane-x`, so this silently fails to find/remove it. Route it through the WP01 seam:
`worktree_path(main_repo, mission_slug, mission_id=<the resolved _preflight_mission_id>, lane_id=lane.lane_id)`.
- **CRITICAL byte-identical caveat:** the OLD f-string had no mid8. If you pass a real `mission_id`
  you CHANGE the path (now includes `-mid8`). That is the *intended fix* here — the old name was the
  BUG (it didn't match the on-disk worktree the allocator created via the seam in WP03). So passing
  the real `mission_id` is correct: it now matches the allocator's `worktree_path(..., mission_id=…)`.
  Add a regression: a mid8-embedded mission's teardown resolves the SAME path the allocator created.
  (If `mission_id` is genuinely unavailable in that scope, resolve it the same way the preflight does,
  i.e. `_preflight_mission_id`.)

## 2. Wire `resolve_branch_name` into the preflight branch search (FR-004 + dead-symbol)
WP01 added `resolve_branch_name(slug, *, mission_id)` — the canonical-first / legacy-failover-with-
one-shot-deprecation-warning resolver (the operator's explicitly-requested behavior). It currently has
**no caller** (flagged dead by `test_no_dead_symbols`). It belongs on the branch-RESOLUTION/search
path. Where the preflight composes the expected mission branch to check existence (the
`_check_mission_branch` expected-branch computation you already touched), use `resolve_branch_name`
instead of (or in front of) `mission_branch_name_required`:
- Canonical (declared mission_id / embedded slug) → same branch as today, NO warning.
- Legacy `NNN-`/bare → resolves with the one-shot deprecation warning (FR-004 intent).
- Modern-unresolvable → still raises `BranchIdentityUnresolved` (fail-closed preserved).
This makes the symbol live, satisfies FR-004's "canonical-first, legacy-failover" rule on a real path,
and keeps your #1978 fix intact (embedded slugs resolve identically). Its test seams
`reset_legacy_failover_warning` / `LEGACY_FAILOVER_SUPPRESS_ENV` become exercised too.
- Add/extend a test proving: embedded slug → no warning + correct branch; legacy slug → exactly one
  deprecation warning + correct legacy branch; the #1978 embedded-preflight case still passes.

## Acceptance for cycle 1
- `merge.py:2786` routed; a mid8-mission teardown resolves the allocator-created worktree path (regression).
- `resolve_branch_name` wired on the preflight search path; FR-004 warning behavior tested;
  `test_no_dead_symbols` no longer flags `resolve_branch_name`/`reset_legacy_failover_warning`/
  `LEGACY_FAILOVER_SUPPRESS_ENV`.
- `pytest tests/merge/ tests/lanes/` green; the #1978 embedded-preflight + fail-closed contracts intact.
- ruff/mypy clean on changed lines; no suppressions.
