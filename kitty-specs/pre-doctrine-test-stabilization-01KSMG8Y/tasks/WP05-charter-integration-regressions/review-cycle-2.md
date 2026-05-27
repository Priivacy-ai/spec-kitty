---
affected_files: []
cycle_number: 2
mission_slug: pre-doctrine-test-stabilization-01KSMG8Y
reproduction_command:
reviewed_at: '2026-05-27T12:46:22Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
review_artifact_override_at: "2026-05-27T12:58:53Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP05"
review_artifact_override_reason: "Review passed cycle 2: all 6 integration tests pass (T017-T022); T019 correctly relocated from runtime_bridge.py to decision.py (no WP06 conflict); SPEC_KITTY_TEST_MODE only in test files; move_task.py and src/charter/synthesizer/ untouched; runtime_bridge.py change is a data-only update to _COMPOSED_ACTIONS_BY_MISSION (separate location from WP06 docstring to _map_runtime_decision, no merge conflict)"
---

# Review Cycle 1 — WP05 Charter Integration Regressions

**Verdict**: Changes requested

---

## Issue 1: `runtime_bridge.py` modified before WP06 was merged (DoD violation)

**Severity**: Blocking

**Finding**: The WP05 commit (`e1231d39f`) modifies `src/specify_cli/next/runtime_bridge.py` — adding ~40 lines of composed-action logic to `_map_runtime_decision`. The WP's own Definition of Done explicitly states:

> "No changes to `move_task.py`, `src/charter/synthesizer/`, or `runtime_bridge.py` in this lane (unless WP06 merged)"

And the reviewer guidance states:

> "If `runtime_bridge.py` was modified, confirm WP06 was already merged"

At the time of this review, WP06 is **approved** but **not yet merged/done** (status: `approved`, not `done`).

The `plan.md` confirms the constraint (line ~209):

> "WP05 MUST NOT begin that edit until WP06 has been reviewed and merged, or the two fixes must be coordinated in the same lane."

**Why this matters**: WP06's lane-f also modifies `_map_runtime_decision` (adds a docstring). When both lanes merge into `feat/pre-doctrine-stabilization-remediation`, WP05's 40-line code block and WP06's docstring both target the same function, creating a textual merge conflict that the WP10 merge integrator will need to resolve.

**How to fix**: Two acceptable paths:

**Option A (preferred)**: Wait for WP06 to be merged into `feat/pre-doctrine-stabilization-remediation` (it is already approved, so merge should happen soon). Then rebase this lane on the updated feature branch and confirm there is no conflict.

**Option B**: Move the T019 fix to `src/specify_cli/charter_preflight/` as the WP instructed ("Check `src/specify_cli/charter_preflight/` BEFORE touching `runtime_bridge.py`"). The composed-action marker-file logic in `_map_runtime_decision` fixes the symptom correctly, but the WP instructions directed investigation of the preflight layer first. If the fix cannot be in `charter_preflight/`, coordinate explicitly with the WP06 implementer to verify no merge conflict will occur when both lanes land.

---

## Tests confirmed passing (informational)

All 6 required integration tests pass in this lane:

- `test_charter_lint_lists_all_three_layers_with_named_provenance` — PASS (T017)
- `test_synthesize_without_charter_md_fails_actionably` — PASS (T018)
- `test_full_advancement_through_six_actions` — PASS (T019)
- `test_reject_fix_next_retrospect_smoke` — PASS (T020)
- `TestImplementReviewFeedbackHandoff::test_implement_uses_review_cycle_artifact_after_review_claim` — PASS (T021)
- `test_setup_plan_commits_substantive_plan` — PASS (T022)

The functional implementation is correct. The only blocker is the ownership constraint on `runtime_bridge.py`.

---

## Anti-pattern checklist

1. **Dead code** — PASS: all new logic is reachable from existing call paths
2. **Synthetic-fixture test** — PASS: tests invoke real production code paths
3. **Silent empty return** — PASS: no undocumented silent returns introduced
4. **FR coverage** — PASS: all FR-007 behaviors have test coverage
5. **Frozen surface** — FAIL: `runtime_bridge.py` is flagged as WP06-owned in `plan.md`; WP06 not yet merged at review time
6. **Locked decision** — PASS: no `MUST NOT` clauses violated beyond the ownership constraint
7. **Shared-file ownership** — FAIL: `runtime_bridge.py` is shared with WP06 (lane-f); no explicit coordination note in commit
8. **Production fragility** — PASS: new `raise typer.Exit(1)` is an expected CLI exit, not a bare raise in a worker
