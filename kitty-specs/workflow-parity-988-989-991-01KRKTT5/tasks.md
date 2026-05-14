# Tasks: Workflow Parity Fixes 988/989/991

**Mission**: workflow-parity-988-989-991-01KRKTT5
**Branch**: `fix/workflow-parity-988-989-991`
**Plan**: [plan.md](plan.md)

## Subtask Index

| ID    | Description                                                                 | WP    | Parallel |
|-------|-----------------------------------------------------------------------------|-------|----------|
| T001  | Add `ClaimablePreview` dataclass + `preview_claimable_wp()` helper           | WP01  | [P]      |
| T002  | Wire `next --json` payload to populate `wp_id` + `selection_reason`         | WP01  |          |
| T003  | Regression test: `next --json` exposes claimable wp_id (#988)                | WP01  |          |
| T004  | Add `LIGHTWEIGHT_REVIEW_MISSING_BASELINE` + `LEGACY_MISSION_DEAD_CODE_SKIP` diagnostic codes | WP02 | [P] |
| T005  | Update `scan_dead_code()` to fail-hard on modern missions with null baseline | WP02 |          |
| T006  | Regression test: lightweight review fails missing baseline on modern mission (#989) | WP02 |          |
| T007  | Extract `run_review_artifact_consistency_preflight()` helper                 | WP03  | [P]      |
| T008  | Invoke preflight in `merge --dry-run` path (human + JSON output)             | WP03  |          |
| T009  | Regression test: `merge --dry-run` emits `REJECTED_REVIEW_ARTIFACT_CONFLICT` (#991) | WP03 |          |

## Work Packages

### WP01 — `next --json` claimability parity (#988)

**Goal**: Make `spec-kitty next --json` expose the same WP that `agent action implement` would claim.

**Priority**: P1 — operator/agent loop trust.

**Independent test**: Given a mission with at least one claimable WP, `spec-kitty next --json` includes a non-null `wp_id`; given a mission with no claimable WPs, it includes a non-null `selection_reason`.

**Included subtasks**:
- [ ] T001 Add `ClaimablePreview` dataclass + `preview_claimable_wp()` helper in `src/specify_cli/next/`
- [ ] T002 Wire `next --json` payload (`Decision.to_dict()` + `_print_decision`) to invoke the helper and emit `wp_id` and `selection_reason`
- [ ] T003 Add regression test `tests/next/test_next_claimable_payload.py` asserting the new payload shape

**Implementation sketch**:
1. Introduce `ClaimablePreview` and side-effect-free `preview_claimable_wp(feature_dir, *, mission_meta)` in `src/specify_cli/next/discovery.py` (or extend existing module).
2. Inside the `next` decision builder, when `mission_state == "implement"` and `preview_step == "implement"`, call the helper and merge `wp_id` + `selection_reason` into the decision dict.
3. Add a regression test exercising two scenarios (claimable, not claimable).

**Parallel opportunities**: T001 is independent of T002/T003. T003 depends on T001+T002.

**Dependencies**: none.

**Prompt**: [tasks/WP01-next-json-claimability.md](tasks/WP01-next-json-claimability.md)

**Estimated prompt size**: ~280 lines.

---

### WP02 — Lightweight review dead-code parity (#989)

**Goal**: Modern missions with `baseline_merge_commit: null` must fail lightweight review with a structured diagnostic rather than silently passing.

**Priority**: P1 — release-evidence integrity.

**Independent test**: Given a modern mission (with `mission_id` in `meta.json`) and `baseline_merge_commit: null`, `spec-kitty review --mode lightweight` exits non-zero with `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`. Legacy missions (no `mission_id`) still pass with `LEGACY_MISSION_DEAD_CODE_SKIP` tag.

**Included subtasks**:
- [ ] T004 Add `LIGHTWEIGHT_REVIEW_MISSING_BASELINE` and `LEGACY_MISSION_DEAD_CODE_SKIP` to `src/specify_cli/cli/commands/review/_diagnostics.py`
- [ ] T005 Update `scan_dead_code()` in `src/specify_cli/cli/commands/review/_dead_code.py` to branch on `mission_id` presence + `baseline_merge_commit`
- [ ] T006 Add regression test `tests/specify_cli/cli/commands/review/test_dead_code_baseline.py`

**Implementation sketch**:
1. Add the two diagnostic codes.
2. Modify `scan_dead_code()` to:
   - If `baseline_merge_commit` populated → run existing scan (no change).
   - Elif `mission_id` populated → return structured failure with `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`.
   - Else → preserve historical skip but tag with `LEGACY_MISSION_DEAD_CODE_SKIP`.
3. Wire the structured failure through the review verdict so the CLI exit code reflects the failure.
4. Add regression test covering all three branches.

**Parallel opportunities**: T004 is independent of T005/T006. T005 depends on T004; T006 depends on T005.

**Dependencies**: none.

**Prompt**: [tasks/WP02-lightweight-review-baseline.md](tasks/WP02-lightweight-review-baseline.md)

**Estimated prompt size**: ~320 lines.

---

### WP03 — Merge dry-run review-artifact gate parity (#991)

**Goal**: `spec-kitty merge --dry-run` must invoke the same review-artifact consistency gate as real merge, surfacing `REJECTED_REVIEW_ARTIFACT_CONFLICT` in both human and JSON output.

**Priority**: P1 — release readiness signal trust.

**Independent test**: Given a mission with `WP01` lane `approved` and a `rejected` latest review-cycle artifact, `spec-kitty merge --mission <slug> --dry-run --json` exits non-zero with `REJECTED_REVIEW_ARTIFACT_CONFLICT` in the JSON payload, and human output names the conflict.

**Included subtasks**:
- [ ] T007 Extract `run_review_artifact_consistency_preflight()` helper used by both real merge and dry-run
- [ ] T008 Invoke the preflight in the dry-run path (human + JSON output)
- [ ] T009 Add regression test `tests/specify_cli/cli/commands/test_merge_dry_run_review_artifact.py`

**Implementation sketch**:
1. Extract the existing real-merge invocation of `find_rejected_review_artifact_conflicts()` into a single helper that returns a structured result.
2. Call the helper from the `merge --dry-run` path before computing the preview; on detection, emit the diagnostic to the chosen output (human or JSON) and exit non-zero.
3. Confirm `tests/post_merge/test_review_artifact_consistency.py` and `tests/merge/test_merge_post_merge_invariant.py` stay green.
4. Add regression test for the dry-run path.

**Parallel opportunities**: T007 is independent of T008/T009. T008 depends on T007; T009 depends on T008.

**Dependencies**: none.

**Prompt**: [tasks/WP03-merge-dry-run-review-artifact.md](tasks/WP03-merge-dry-run-review-artifact.md)

**Estimated prompt size**: ~320 lines.

## MVP Scope

Each of WP01, WP02, WP03 is independently shippable. Recommended order: WP03 → WP01 → WP02 (per start-here.md execution order — WP03 is most concrete, WP01 needs payload understanding, WP02 has the most policy nuance).

## Parallelization

All three WPs touch disjoint code paths:
- WP01 owns `src/specify_cli/next/` + `src/specify_cli/cli/commands/next_cmd.py` payload edits.
- WP02 owns `src/specify_cli/cli/commands/review/`.
- WP03 owns `src/specify_cli/cli/commands/merge.py` + `src/specify_cli/post_merge/review_artifact_consistency.py`.

They can run in parallel across three lanes if needed; in this mission they are executed sequentially by a single agent.
