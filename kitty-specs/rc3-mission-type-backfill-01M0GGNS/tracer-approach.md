# Tracer — Approach / Execution Notes (M0 mission_type backfill)

Seeded at planning; append as the approach evolves.

## Program ordering (BLUF)
- M0 is a **program gate**: must land AND run against real projects **before** M3 (#3596/#3598,
  typo/typeless `mission_type` hard-fails) and M5 (#3598, legacy `mission` resolution dropped)
  reach them. Backfilling `mission_type` first is what makes the combined M3+M5 change non-breaking.

## Phase plan
1. Spec finalization (harden LIGHT spec, resolve open decision) → squad #1.
2. Plan (command surface, gate reuse, idempotency, composition w/ backfill-identity) → squad #2.
3. Tasks + finalize → squad #3.
4. Implement/review (red-first per AC; implement=sonnet, review=opus).
5. Closeout (merge → clean history → rebase → docs/changelog → draft PR; operator merges).

## WP01 — DONE (implement=sonnet, review=opus)
- backfill_mission_type.py + tests: 19 passed, ruff+mypy clean, complexity 8/5/4. Red-first evidence
  captured (ModuleNotFoundError → green). Committed on lane-a.
- Opus review: APPROVE — probed the real `MissionTypeProfileRepository.for_project` (research/software-dev
  resolve on a bare repo, sofware-dev does not) confirming R-4 predicate is activation-independent and the
  R-4 test is non-tautological. Applied nits: hoist double canonical call + drop `-O`-stripped assert;
  added `test_present_but_blank_mission_type_left_untouched` (deferred typeless left byte-identical).
- Shared-worktree hazard (flagged by implementer, zero net effect): a stale `spec-kitty-safe-commit` stash
  popped add/add conflicts in WP task md; resolved --ours (current squad-folded content), dropped stale stash.

## WP02 + WP03 — DONE (implement=sonnet, review=opus)
- WP02 (migrate backfill-mission-type command): 6 CLI tests green + campsite M1/M2 folds (one
  _NO_PROJECT_ROOT const, reused flag constants); opus APPROVE. Applied help-text fix (command-specific
  --mission/--json help — the reused _MISSION_HELP over-promised mid8/mission_id selector resolution the
  slug-only backend doesn't honor).
- WP03 (gate regression + cross-authority + AC-5): 4 tests green; opus APPROVE with the STRONG check —
  reviewer monkeypatched the writer predicate to registered∧roster and confirmed AC-5 flips RED, proving
  the profile-resolution predicate is genuinely pinned (not vacuous). All 29 mission tests green.
