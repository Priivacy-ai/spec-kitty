---
cycle_number: 1
wp_id: WP02
mission_slug: specify-protected-primary-coherence-01KVMBD6
reviewer_agent: claude:opus:reviewer-renata:reviewer
verdict: rejected
reviewed_at: '2026-06-21T08:30:00+00:00'
affected_files: []
---

# WP02 Review — Cycle 1 — REQUEST CHANGES

Reviewer: reviewer-renata (claude:opus). Diff isolated against WP01 tip
(`kitty/mission-specify-protected-primary-coherence-01KVMBD6-lane-a`).

The core extraction is correct and the de-god collapse is real (not relocated).
Two blocking issues remain: dead code left behind by the collapse, and a
toothless "negative" test that violates the WP's own anti-fakeable reviewer gate.

---

## What is verified GOOD (live evidence)

- **T027 de-god (the load-bearing one): PASS.** `grep -c 'safe_commit('
  src/specify_cli/cli/commands/agent/mission.py` → **0** (only a `# noqa: F401`
  re-export shim at :58). All three former inline tails now genuinely delegate:
  `:2379` (gap-analysis), `:2422` (generator-config), `:3850` (finalize-tasks)
  call `commit_for_mission(...)`. `_commit_to_branch` (:1163) and record-analysis
  (:1946) also route through it. C-001 "both directions" satisfied: the
  duplication was REMOVED, not relocated.
- **T006: PASS.** `commit_for_mission` reuses `resolve_placement_only` +
  `CoordinationWorkspace.resolve` — no parallel materializer.
- **T007/T028: PASS.** `spec-commit` is registered in
  `cli/commands/__init__.py::register_commands` (:228, mirrors safe-commit),
  NOT in `specify_cli/__init__.py`. Verified live: `register_commands(app)` →
  `spec-commit` present.
- **B-1: PASS.** Entrypoint derives `mission_slug` (path or `--mission`),
  resolves `ProtectionPolicy`, calls the router; slug-from-path covered by
  `test_spec_commit_slug_derived_from_path`.
- **T014: PASS.** `assert_not_protected_branch` fully removed from mission.py;
  record-analysis routes its report commit through `commit_for_mission`
  (materialize-then-retry).
- **T017: PASS.** L1 test rewritten to assert exit 0 + report written + router
  called + NO `PROTECTED_BRANCH_REFUSED`.
- **Adjacent test fixes: legitimate.** `test_feature_finalize_bootstrap.py` /
  `test_mission_planning_entry.py` repoint spies from `safe_commit` /
  `_resolve_planning_placement` to the new `commit_for_mission` boundary (a true
  consequence of the extraction, not regression masking). `test_wrapper_delegation.py`
  patches `is_worktree_context=False` for CWD-invariance — defensible isolation fix.
- ruff + mypy clean on all new/changed src; complexity ≤ 15; no `--feature`
  regression; terminology guard passes; 307 passed / 2 xfailed.

---

## BLOCKING ISSUES

### Issue 1 (BLOCKING — anti-pattern checklist item 1: dead code)
The T027 collapse orphaned two helpers in
`src/specify_cli/cli/commands/agent/mission.py` that are now called by NO
production code, test, or external module:

- **`_try_advance_primary_ref` (mission.py:1018, ~75 lines).** Had 4 live callers
  on the WP01 base (lane-a :1281/:2468/:2519/:3981); this WP removed all 4 (the
  router uses its own `_try_advance_ref`). Zero callers remain in `src/` or `tests/`.
- **`_safe_commit_empty_changeset_error` (mission.py:984).** Had 1 live caller on
  base (lane-a :1264); now zero (the router uses its own `_is_empty_changeset_error`).

Both are dead code introduced by this diff.

**Fix:** delete both functions (and any now-unused imports they pulled in, e.g. the
`ref_advance` imports local to `_try_advance_primary_ref`). If either is intended
as a re-export shim for an external caller, name that caller and add a regression
test importing it — otherwise remove.

### Issue 2 (BLOCKING — T009 step 6 / anti-fakeable reviewer gate)
`tests/coordination/test_commit_router.py::test_negative_stubbed_materialiser_causes_wrong_result`
does NOT fail when the materializer is a no-op. The WP requires a negative variant
that "FAILS if the materializer is stubbed (would catch a no-op fix)." This test's
own docstring claims that property but the assertions don't deliver it:

- Line 286: `assert result.status in {"committed", "unchanged", "no_op_wrong_surface"}`
  accepts 3 of 4 possible statuses — it cannot fail on outcome.
- Line 289: `assert result.placement_ref == "kitty/mission-x-ABCD1234"` is always
  true, because `commit_for_mission` sets `placement_ref=placement.ref` from the
  mocked `coord_target` regardless of which surface the artifact actually landed on.

The test stubs `_materialise_coord_worktree` to RETURN THE PRIMARY PATH
(`return tmp_path, (artifact,)`) — i.e. it simulates exactly the broken no-op
materializer the gate must catch — and the test PASSES. Confirmed by running it in
isolation: `1 passed`.

**Fix:** make the negative variant actually distinguish coord-surface from
primary-surface and FAIL on the stub. Options: (a) commit to a real temp git repo
with a real coord worktree and assert the artifact is reachable on the coord branch
but NOT staged on the primary HEAD; or (b) have the stub return an empty/absent
path tuple and assert `status == "no_op_wrong_surface"` (so a working materializer
→ committed, a no-op stub → no_op_wrong_surface — a real discriminator). Today's
assertion set is non-discriminating and must be tightened.

---

## Non-blocking note
- The entrypoint test `test_spec_commit_protected_materialises` stubs
  `commit_for_mission` at the command level, so it proves only "router called with
  protected policy," and `test_protected_coord_placement_materialises` stubs
  `_materialise_coord_worktree`. Full real-coord-worktree e2e is deferred to WP07
  per the prompt — acceptable for WP02's narrow scope, but it means Issue 2 is the
  ONLY in-WP guard that the materializer is load-bearing. That is exactly why
  Issue 2 must be fixed here, not deferred.

---

## Change list to clear this review
1. Delete `_try_advance_primary_ref` and `_safe_commit_empty_changeset_error`
   from mission.py (+ now-unused imports). Re-run ruff to confirm no F811/unused.
2. Rewrite `test_negative_stubbed_materialiser_causes_wrong_result` so a no-op /
   primary-returning materializer makes the test FAIL (real coord-branch assertion
   or a no_op_wrong_surface discriminator).
3. Re-run: `PWHEADLESS=1 pytest tests/coordination/ tests/specify_cli/cli/commands/test_spec_commit_cmd.py tests/specify_cli/cli/commands/agent/` + ruff + mypy.
