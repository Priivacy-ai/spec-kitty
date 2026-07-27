---
affected_files: []
cycle_number: 1
mission_slug: reliability-papercut-sweep-01KWD0V5
reproduction_command:
reviewed_at: '2026-06-30T22:38:36Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
---

# WP03 Review Feedback — reliability-papercut-sweep-01KWD0V5 (cycle 1)

**Verdict: changes requested (1 blocking finding).** The primary contract is strong; one
secondary path re-introduces the exact phantom-efficacy class this WP exists to eliminate.

## What passes (verified independently)

- **Efficacy red-first (PRIMARY anti-laziness anchor) — PASS.** Reverting the two production
  files to pre-fix and re-running the new tests yields RED for the right reason:
  `test_coord_health_recovery_efficacy_missing_worktree` fails because the finding has no
  `extra['recovery_args']` and `doctor workspaces --fix` cannot recreate a worktree. The test
  is genuine efficacy, not existence: it *executes* `git worktree add` from `recovery_args`,
  asserts the worktree now exists, and re-runs `_check_coordination_worktree_health` to assert
  doctor reports `ok`. `never_created → flatten` and the `#1890` secondary existence invariant
  are both correct and RED-on-pre-fix.
- **16 golden re-pins — HONEST, not masking.** 20 golden tests genuinely fail pre-WP03 on
  click 8.4.2: `get_command(app)` returns `typer.core.TyperGroup`/`TyperOption`, which no longer
  subclass `click.Group`/`click.Option` (`isinstance` is False). The duck-type `_is_option_param`
  matches options without over-matching `Argument`s (verified on live instances), and the
  load-bearing exact-equality assertions (`registered == FROZEN_SUBCOMMANDS`, `len == 16`,
  `actual == EXPECTED_OPTIONS[name]`) are unchanged. Clean topology-aware re-pin.
- ruff + mypy clean on owned production files; C901 clean (complexity ≤ 15); 334 doctor tests pass.

## Blocking finding

**B1 — The stale-behind-tip recovery makes an unverified efficacy claim (the very
phantom-efficacy class #2240/#1890 targets), and its ~37-line execution path is untested.**

The new `COORDINATION_WORKTREE_STALE` finding recommends:
> "Run `spec-kitty doctor workspaces --fix` to refresh it (fast-forwards stale coord worktrees)."

But no test proves that following this recommendation actually resolves the stale state.
`_refresh_stale_coord_worktrees` + `_coord_worktree_needs_refresh` in
`_workspace_husk_doctor.py` (the code that performs the `git merge --ff-only`) are entirely
uncovered (lines 153-177, 193-205; 77% module coverage, the gap is exactly the refresh path).
Existing husk tests only hit the empty-result early return.

This is asymmetric with the missing-worktree case, which sets the bar correctly (execute the
recovery, assert the state is resolved). For the stale case you have **diagnosis-only** coverage
(`test_coord_health_warns_stale_coord_worktree` asserts the STALE *finding* is emitted) but
**no efficacy/execution** coverage. Per DIR-041 and the mission thesis ("a recommendation must
perform what it claims, not just exist"), and to avoid a new-code-coverage hole at the Sonar
gate, the fast-forward execution needs a focused efficacy test.

### Fix (small, mirrors the existing missing-worktree efficacy test)

Add a test that:
1. Materialises a coord worktree, advances the coord branch tip, and rolls the worktree HEAD
   back one commit (you already have this exact setup in
   `test_coord_health_warns_stale_coord_worktree`).
2. Invokes the recovery path — call `_refresh_stale_coord_worktrees(repo_root)` directly (or
   drive `doctor workspaces --fix`) and assert the returned outcome for that worktree is
   `"refreshed"`.
3. Asserts the state is resolved: the worktree HEAD now equals the branch tip, and a follow-up
   `_check_coordination_worktree_health` no longer emits `COORDINATION_WORKTREE_STALE`.

Optionally also cover the `already_current` / `failed` (diverged) branches so the helper's
new branches are exercised. That closes the efficacy gap and the coverage hole together.

No other issues. Anti-pattern checklist: dead code N/A (all new helpers wired), synthetic-fixture
PASS (efficacy test drives real production path), silent-empty-return PASS (None returns are
documented "no finding" cases), frozen-surface PASS, ownership PASS (shared `_coordination_doctor.py`
with WP02 noted per C-002, WP02 merged first), fragility PASS (no bare raises; `--ff-only` reports
`failed` not raise).
