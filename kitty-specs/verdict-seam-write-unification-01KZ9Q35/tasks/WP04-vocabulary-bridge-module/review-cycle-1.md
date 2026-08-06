---
affected_files: []
cycle_number: 1
mission_slug: verdict-seam-write-unification-01KZ9Q35
reproduction_command:
reviewed_at: '2026-08-05T23:23:23Z'
reviewer_agent: user
verdict: rejected
wp_id: WP04
---

# WP04 Review — Cycle 1 — REJECTED (one blocking finding)

Reviewer: reviewer-renata (claude). The bridge, D-PLAN-14 safety, the guard's
red-first + anti-evasion design, and the sweep's behaviour-preservation are all
solid. One blocking finding only; the fix is small and does **not** touch the
bridge's public API, so WP05 is unaffected.

## Blocking — Anti-pattern checklist #1 (dead code): two new public symbols with zero callers

Two symbols added by the sweep have **no production or test consumer** and are
not re-exported from `status/__init__.py` (verified by grep across `src/` and
`tests/`):

1. `src/specify_cli/status/models.py:101` — `EVENT_VERDICTS: frozenset[str] =
   verdict_vocab.event_verdicts()`. Only self-references (line 101 + the two
   `# see EVENT_VERDICTS above` comments). The `ReviewApproval.verdict` /
   `ReviewResult.verdict` fields it claims to document remain bare `str`, so the
   constant constrains nothing.
2. `src/specify_cli/status/reducer.py:519` — `ReviewResultLookup.is_recognized_verdict`.
   An advisory property explicitly "never used to reject or rewrite," with no
   caller anywhere.

**Root cause.** `status/models.py` and `status/reducer.py` were **not**
inline-equivalence *code* sites at WP04's base: models.py mentioned the
`rejected`/`changes_requested` pair only in **comments** (lines 221/274),
reducer.py only in a **docstring** (line 249). AST co-occurrence of both
literals is `False` for each at base, so the guard's negative (absence) check
never flagged either — only the positive (import+call) list `_SWEPT_MODULES`
requires them, and that list comes from the plan's IC-02b "9 inline sites"
count, which evidently swept up comment/docstring-only mentions. To pass the
positive check on two modules that have no verdict-mapping path, the sweep
attached a decorative module-constant and an unused property. That is dead code,
and it also blunts the positive check's own anti-evasion intent (a token call,
not genuine adoption).

**Remediation — pick one (bridge public API unchanged either way; WP05 safe):**

- **(A, preferred)** Drop `status/models.py` and `status/reducer.py` from
  `_SWEPT_MODULES` in `tests/architectural/test_verdict_vocab_single_source.py`
  (the AST negative check already covers them for free — neither co-occurs the
  literal pair in code), and delete the two dead symbols. Reconcile the plan's
  "7 owned sweep sites" → 5 genuine sites and flag the IC-02b count to the
  planner/orchestrator so the guard's positive list means "modules that
  genuinely map verdicts."
- **(B)** Make the adoption load-bearing instead: have
  `ReviewApproval.verdict` / `ReviewResult.verdict` actually validate/type
  against the bridge vocabulary (a real consumer of `EVENT_VERDICTS`), and give
  `is_recognized_verdict` a real production consumer — so neither symbol is dead.

## Non-blocking note (no action required)

- The D-PLAN-14 end-to-end test `test_arbiter_override_does_not_synthesize_an_
  approved_review_result_event` exercises `_apply_annotation_delta`, which has
  no path to `review_result`, so it is non-vacuous only as a reducer slot-
  separation invariant. The load-bearing D-PLAN-14 refusal is carried non-
  vacuously by `test_emission_event_verdict_refuses_override_values` (raises on
  both override values; would green if the bridge mapped them). This is fine as
  shipped — just noting the end-to-end test is the weaker of the pair.

## Verified PASS (scope of the bounce is narrow)

- **D-PLAN-14 refusal**: `emission_event_verdict` refuses `arbiter_override` /
  `approved_after_orchestrator_fix` (raises `ValueError`); directly and non-
  vacuously tested. The full four-value `to_event_verdict` (display/render) maps
  both overrides → `approved` as intended, kept out of the emission path.
- **Guard red-first + not gameable**: 30/30 green now. Red-first = 8 failures by
  construction (7 positive-check params, none imported the bridge at base; +1
  negative check flagging `sync/emitter.py` and `proof/events.py`, the only two
  base AST co-occurrences among the seven). Anti-evasion synthetic proofs all
  pass: line-split still reds the negative check (module-level AST), a same-named
  fake local object and an import-without-call both red the positive check.
- **Sweep behaviour-preserving** (byte-identical accepted sets): sync/emitter
  `{approved,changes_requested,rejected,commented,unknown}` unchanged;
  proof/events Literal union unchanged + a validator that never rejects what the
  annotation accepts; orchestrator_api `event_verdicts()`=={approved,
  changes_requested}; retrospective `is_changes_requested(x)`==`x=="changes_
  requested"`; tasks_move_task approved/rejected via emission helper (hardcoded
  valid constants — cannot raise in prod). No circular import (all 8 modules
  import cleanly; retrospective lazy import documented).
- **Allowlist**: exactly `{review/cycle.py, post_merge/review_artifact_
  consistency.py}`, named and non-vacuous (both still inline the equivalence
  today, asserted by `test_allowlisted_modules_still_carry_the_equivalence_today`).
- **Owned-files/census**: exactly the 9 owned files touched;
  `test_verdict_seam_census.py` untouched and 25/25 green.
- **ruff** clean on all 9 files; **mypy --strict** clean on the bridge. The one
  mypy `no-any-return` at `tasks_move_task.py:1935` is **pre-existing** (#3223;
  identical at base line 1930, in `_mt_shell_pid_baseline`, unrelated to the
  sweep — the 5-line comment merely shifted it).
- **Pre-existing failures verified, not introduced**: #3220 (`test_reducer.py`
  `status_phase` meta-fixture) reproduces with reducer.py reverted to base;
  the two `test_issue_2684_subtask_completion_event_sourced` failures reproduce
  with tasks_move_task.py reverted to base (environmental sync/config); #3224
  (baseline venv missing `hatchling`) explains the gate's spurious "1 new
  failure" advisory.
