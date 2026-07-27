---
work_package_id: WP08
review_cycle: 1
verdict: changes_requested
reviewer: reviewer-renata
reviewed_commit: 5a159f1150b4ea516168c4bf464dad86856cfade
mission: execution-context-unification-01KTPKST
requirement_refs:
- FR-006
- FR-007
---

# WP08 Review — Cycle 1 — CHANGES REQUESTED

## Summary

The merge half (FR-007) and the flattened-`CommitTarget.kind` work (T028) are
correct and behavior-preserving. The retrospect status-**event** surface
(#1735) was genuinely re-routed through `resolve_status_surface`. **However the
#1771 half of FR-006 — "no gitignored writes" — was not implemented and was not
honestly carved out as a tracked follow-up.** That is the literal substance of
issue #1771 and an explicit, named acceptance criterion of FR-006 / IC-07 / the
WP08 objectives and T026. This blocks approval.

## Blocking Issue 1 — FR-006 #1771 (gitignored retrospect record write) unmet

**What FR-006 requires (spec.md line 32; plan.md IC-07 line 148; this WP's
Objectives + T026):** retrospect read/write to the canonical surface with
**"no gitignored writes (#1735/#1771)."**

**What #1771 actually is:** `spec-kitty retrospect create` writes the
retrospective *record* to `.kittify/missions/<mission_id>/retrospective.yaml`,
and `.kittify/missions/` is in `.gitignore` (`.gitignore:61`). The record is
therefore silently discarded on checkout/clone and is not committable without
`git add -f`. The issue's Expected Behavior is to relocate the record to a
tracked home (e.g. `kitty-specs/<slug>/retrospective.yaml`).

**What WP08 changed:** only the `status.events.jsonl` read/commit *surface*
(the #1735 half), via the new `_canonical_events_path` → `resolve_status_surface`
at retrospect.py:90/160/400/812. The record-write path is untouched:
`write_gen_record` (`src/specify_cli/retrospective/writer.py:474-475`) and
`_canonical_record_path` (`retrospect.py:85-87`) still target
`.kittify/missions/<id>/retrospective.yaml` — still gitignored. The auto-commit
at retrospect.py:403 stages `[record_path, events_path]`, but `record_path` is
gitignored, so the original #1771 bug is fully intact.

**Why the deferral is not acceptable as-is:**
- #1771 is one of the two issues FR-006 was authored to drain (#1735 + #1771).
  The "no gitignored writes" clause names exactly this defect. Shipping only
  #1735 while the commit message labels the work "(#1735/#1771)" mislabels
  coverage rather than achieving it.
- There is no test anywhere asserting the #1771 behavior (a `git check-ignore`
  / committable-location assertion). The "no gitignored writes" criterion is
  wholly untested as well as unimplemented (anti-pattern checklist #4: FAIL for
  this FR half).
- No tracker follow-up was filed and no carve-out was recorded in spec/plan; the
  activity log simply folds #1771 into the #1735 sentence.

**How to fix (pick one, per the issue's Expected Behavior):**
1. Relocate the record write to a tracked location (the issue suggests
   `kitty-specs/<slug>/retrospective.yaml`), routed through the canonical
   surface so it matches the status-event side; **or**
2. Narrow the `.gitignore` rule so `retrospective.yaml` under
   `.kittify/missions/` is tracked while ephemeral runtime state stays ignored.

Add a test that fails today and passes after the fix (e.g. assert the resolved
record path is NOT git-ignored / lands under a tracked dir).

**If the operator decides the relocation is genuinely out of scope for this
mission**, that is a scope-amendment decision: amend FR-006 in spec.md to drop
the "no gitignored writes" clause and re-scope #1771 to a separate tracked
mission, then re-submit. Do not approve FR-006 as "met" while #1771 is open.

The ~450/705-test retrospect surface confirms the relocation is non-trivial —
but non-trivial is not out-of-scope. The risk is real; the requirement is also
real and explicitly named.

## Verified PASS (no action needed)

- **T028 flattened `CommitTarget.kind` (behavior-preserving):** the new
  `FLATTENED` classification (resolution.py:414) changes no existing decision.
  Both consumers (`implement.py:481`, `agent/mission.py:544`) branch only on
  `kind is CommitTargetKind.COORDINATION`; PRIMARY and FLATTENED share the
  identical non-coord path, and both call sites document this intent.
- **Parity flip legit:** `test_flattened_topology_commit_target_kind` xfail
  removed and now PASSES; the only remaining xfail is
  `test_runtime_lifecycle_action_parity` (F-008), as claimed. 20 passed, 1
  xfailed.
- **T027 merge no-op is genuine (not work-avoidance):** merge.py already
  consumes `resolve_status_surface` at 343/512/2087 and `path_is_under_worktrees`
  / `compose_meta_json_path` at 579/908/911/958 — strangled in by WP02-07. No
  parallel coord-path re-derivation remains.
- **#1735 status-surface routing:** the 3 retrospect sites (completed-check,
  create, backfill) route through `_canonical_events_path` →
  `resolve_status_surface`; fallback is structured
  (`except (FileNotFoundError, ValueError)` → primary feature dir), documented.
- **Merge-state machine NOT regressed:** `tests/merge tests/lanes/test_merge.py
  tests/lanes/test_recovery_post_merge.py` = 224 passed (excluding the 2
  pre-existing-cycle-blocked collection files).
- **Pre-existing circular import confirmed:**
  `core.dependency_graph → status → uninitialized_hint → detect_cycles` blocks
  isolated collection of `test_ci_coverage_regressions.py` and
  `test_conflict_classifier.py`. WP08 touched none of these modules; the same
  import line exists at WP07 HEAD (d9b3a9a22). Pre-existing, not WP08-caused,
  no runtime impact.
- **Gates:** `ruff` clean, `mypy` clean on the 2 changed source files;
  terminology guard passes; no `--feature` introduced.
- **Anti-patterns:** dead code (PASS — `_canonical_events_path` has 3 callers),
  silent empty return (PASS — structured documented fallback), frozen surface
  (PASS), shared-file ownership (PASS — diff is single-lane lane-h).

## Verdict

CHANGES REQUESTED. Fix Issue 1 (#1771 gitignored record write) or formally
re-scope FR-006, then re-submit.
