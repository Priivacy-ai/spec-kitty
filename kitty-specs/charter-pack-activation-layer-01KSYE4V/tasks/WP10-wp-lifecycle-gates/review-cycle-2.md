---
affected_files: []
cycle_number: 2
mission_slug: charter-pack-activation-layer-01KSYE4V
reproduction_command:
reviewed_at: '2026-05-31T14:58:16Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP10
---

# WP10 Review Feedback — Cycle 1

Reviewer: `reviewer-renata` | Date: 2026-05-31

## Summary

FR-017 (finalize-tasks gate) and FR-018 (implement gate / C-006 ordering) are
fully and correctly implemented. All 7 tests pass. Ruff is clean on touched
files. Pre-existing test failures in `test_wrapper_delegation.py`,
`test_no_dead_symbols.py`, `test_move_task_git_validation_unit.py`, and
`test_planning_workflow_integration.py` pre-date WP10 and are not regressions.

One blocking issue remains: the WP's `requirement_refs` lists **FR-019** and the
Definition of Done states `CharterActivationError` must be both _defined_ **and**
_raised_ in the charter context resolution path. Currently it is only defined.

---

## Blocking Issue — FR-019: `CharterActivationError` has no production raise site

**Anti-pattern**: Dead code (item 1 of the anti-pattern checklist).

**FR-019 spec text** (spec.md §FR table):
> DRG resolution and tactic lookup through the charter module hard-fail when the
> requested artifact is not in the activated set; errors include the artifact
> identifier, the activated set, and the resolution command.

**What WP10 delivered**: `src/charter/exceptions.py` defines and exports
`CharterActivationError`. It is re-exported from `charter/__init__.__all__`.
No production code path raises it — `grep -rn "raise CharterActivationError" src/`
returns zero hits.

**What the spec says about the call-site** (T046 body):
> Wire the hard-fail guard into the DRG resolution path in `src/charter/context.py`
> (owned by WP08, so read-only for WP10).

The spec correctly prohibits WP10 from editing `context.py`. However the DoD is
explicit:

> `CharterActivationError` is defined and **raised** for deactivated artifact
> lookups in the charter context resolution path (FR-019).

This creates an ownership conflict. The resolution is one of:

**Option A — Coordinate with WP08 (preferred for this sprint):**
WP08's lane (`kitty/mission-charter-pack-activation-layer-01KSYE4V-lane-h`) wired
`filter_graph_by_activation` in `context.py:503-533` but did not add the
`CharterActivationError` guard. Since WP08 is already `approved`, the cleanest
path is to add a follow-on subtask to WP08 (or an explicit note in the merge plan
to coordinate the raise-site addition before WP10 is marked `done`).

**Option B — Add a guarded raise in WP10's owned path:**
WP10 could wire a `CharterActivationError` raise inside the two CLI gate functions
themselves (in `mission.py` or `workflow.py`) when an artifact-level deactivation
is detected in the operational context, without touching `context.py`. This is a
narrower coverage than FR-019 intends but it would give the exception a live
production caller.

**Option C — Remove FR-019 from WP10 `requirement_refs`:**
If the mission planner accepts that the raise-site is entirely WP08's
responsibility, remove FR-019 from WP10's `requirement_refs` and update
WP08's to include it explicitly (requires planner sign-off).

**Required action for re-submission**: Choose one of the three options above,
implement it, and add a test that verifies `CharterActivationError` is raised (or
that the resolution path is wired). If Option C is chosen, update the frontmatter
accordingly and note the decision in the activity log.

---

## Minor Observation (non-blocking)

`tests/architectural/test_no_dead_symbols.py` has a stale allowlist entry
`charter.invocation_context::ProjectContext` — now that WP03 has introduced
production callers, the allowlist entry should be removed. This is not WP10's
concern (WP10 did not add it and does not own that file), but is noted for
awareness.

---

## Items Verified as PASS

| Anti-pattern | Verdict | Notes |
|---|---|---|
| Dead code | FAIL (FR-019 raise site) | `CharterActivationError` defined but never raised in src/ |
| Synthetic-fixture test | PASS | Gate logic is live; deleting impl would break tests |
| Silent empty return | PASS | No silent failures in WP10-introduced code |
| FR-017 coverage | PASS | Test 1–3 cover finalize-tasks gate exhaustively |
| FR-018 coverage | PASS | Tests 4–5 cover implement gate; C-006 ordering verified |
| FR-019 coverage | FAIL | No test verifies CharterActivationError is raised |
| Frozen surface | PASS | No frozen or contract files touched |
| Locked decisions | PASS | No `--feature` flags, no terminology violations |
| Shared-file ownership | PASS | WP10 owns all 4 of its files exclusively |
| Production fragility | PASS | `typer.Exit(1)` is appropriate for CLI hard-fail |
| Terminology (charter canon) | PASS | Uses `--mission`, no `--feature` |
