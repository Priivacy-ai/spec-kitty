---
work_package_id: WP01
title: Red-first repros (git-reducible reds only)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: fix/merge-coord-rollback-transactionality
merge_target_branch: fix/merge-coord-rollback-transactionality
branch_strategy: Planning artifacts for this mission were generated on fix/merge-coord-rollback-transactionality. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-coord-rollback-transactionality unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Red-first reproduction
assignee: ''
agent: "claude"
shell_pid: "615737"
shell_pid_created_at: "1784389369.26"
history:
- at: '2026-07-18T14:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: debugger-debbie
authoritative_surface: tests/regression/
create_intent:
- tests/regression/test_issue_2367_bake_strand.py
execution_mode: code_change
model: ''
owned_files:
- tests/regression/test_issue_2786_revert_failure_split_brain.py
- tests/regression/test_issue_2367_bake_strand.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Red-first repros (git-reducible reds only)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `debugger-debbie`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Author two **red-first** regression reproductions that fail for the *product* reason on the mission
base, and repair the permanently-red existing #2786 assertion so it can go green after the fix.

- **SC-001**: both repros RED on the mission base with the first failing assertion being the contract (not setup), GREEN on the final commit.
- **SC-006**: the *modified* `test_issue_2786_*` is RED on base and asserts `committed == working` (re-reduced from the coord ref) **after** the heal step — a bare deletion of the old assertion fails this SC.
- Both tests carry `@pytest.mark.regression` and a docstring referencing the issue (#2786 / #2367).

**CRITICAL — do NOT assert marker/doctor surfaces here.** `MergeState.pending_coord_reconcile` and
the `doctor coordination` stranded-revert finding do NOT exist yet (they land in WP02/WP03/WP04). An
assertion against them here reds with `AttributeError` — **setup-red, forbidden** by
[ADR 2026-07-17-1](../../../docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md).
Assert only **git-reducible** state (committed coord ref vs intended lane).

## Context & Constraints

- Spec: [spec.md](../spec.md) FR-001, FR-003, split-brain half of FR-002; US1 scenarios 1,3.
- Research: [research.md](../research.md) D3 (bake-path mechanism), D7 (committed-ref derivation).
- Data model: [data-model.md](../data-model.md) — the strand set = WPs this merge marked `done` that remain `DONE` on the committed coord ref.
- Charter: ATDD red-first; [testing-flakiness.md#test-run-baseline-red-gotcha](../../../docs/guides/testing-flakiness.md#test-run-baseline-red-gotcha) — classify baseline reds, don't green-wash.
- **Expected-red until WP03 lands** (single-PR landing unit). This is not a violation — it's the red-first contract.

### Code anchors (verified on base)
- `src/specify_cli/merge/executor.py` — bake strand `_record_merged_wps_done_for_merge` failure branch ≈406-408 (byte-restore-**without**-revert); revert-failure branch ≈500-514 (swallowed).
- `src/specify_cli/merge/done_bookkeeping.py:510` — `_durable_done_wps_on_coordination_ref(...)` reads `EventLogReadContract.coordination_branch_ref` → the committed-ref reduction the tests use.
- Existing harness in `tests/regression/test_issue_2786_revert_failure_split_brain.py` — reuse `_init_git_repo`, `_bootstrap_coord_mission`, `CoordinationWorkspace.worktree_path`, and its committed/working coord-event readers.

## Branch Strategy

- **Planning base branch**: `fix/merge-coord-rollback-transactionality`
- **Merge target branch**: `fix/merge-coord-rollback-transactionality` (→ consolidate → local main → PR)
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Subtasks & Detailed Guidance

### Subtask T001 – Modify the existing #2786 assertion → assert-after-heal

- **Purpose**: The on-base assertion `assert committed_lane == working_lane` (≈line 204) has **no resume step**. Under the mark-not-raise fix the committed `done` is *deliberately* stranded until repair, so that synchronous assertion can never go green → permanent red. Fix it to assert coherence **after** invoking the heal.
- **Steps**:
  1. Read the existing test end-to-end. Keep the strand-inducing setup (revert-failure injection) and the witnesses.
  2. Replace the synchronous coherence assertion with: drive the strand → assert the strand exists (committed `done`, intended `approved`) → invoke `spec-kitty merge --resume` (or the heal entry once it exists) → assert `committed_lane == working_lane` re-reduced from the coord ref.
  3. Until WP03 lands the heal, this test is RED at the post-heal assertion (the heal is a no-op) — that is the expected red.
  4. **Never** bare-delete the assertion (SC-006 / delete-the-assertion-not-the-test anti-pattern).
- **Files**: `tests/regression/test_issue_2786_revert_failure_split_brain.py`

### Subtask T002 – New #2367-B bake-strand repro (≥2-WP fixture)

- **Purpose**: Prove the bake-mid-write-set strand — a failure **inside** `_record_merged_wps_done_for_merge` after ≥1 committed `done`, hitting the ≈406-408 byte-restore-without-revert branch.
- **Steps**:
  1. Bootstrap a coord mission with a **≥2-WP** write-set (one WP that commits `done` before the injected failure = *stranded*; one that is only ever `approved` = *coherent*). **Author your OWN multi-WP bootstrap in this owned file** — the shared `_bootstrap_coord_mission` (in the #2711 harness) is hardcoded single-WP and has NO bake-loop injection hook; it is in NO WP's `owned_files`, so do NOT edit it (locality violation). Reuse only the primitive helpers `_init_git_repo` / `_git`. Inject the failure via a `_mark_wp_merged_done` `side_effect` that raises on the 2nd WP.
  2. Inject the failure inside the bake loop after the first WP's `done` commit lands (monkeypatch the per-WP emit to raise on the 2nd, or similar). Confirm it exercises the ≈406-408 branch, NOT target-advance/squash-conflict (those are revert-covered — vacuous).
  3. Assert (git-reducible): the stranded WP reduces to `DONE` on the committed coord ref while its intended lane is `approved`; the coherent WP is not stranded. RED today.
- **Files**: `tests/regression/test_issue_2367_bake_strand.py` (NEW)

### Subtask T003 – Committed-ref split-brain assertions (no marker/doctor)

- **Purpose**: Ground both tests on the committed-ref authority the fix will use, so the reds are product-reds and the ≥2-WP fixture pins the specific stranded WP.
- **Steps**:
  1. Use `_durable_done_wps_on_coordination_ref` (or the test's existing committed-event reader) to reduce the committed coord ref.
  2. Assert the stranded set equals exactly the stranded WP — establishing the contract WP02's `coord_incoherent_done_wps` must satisfy.
  3. Keep all assertions git-reducible; no import of `pending_coord_reconcile` or doctor findings.
- **Files**: both test files above.

## Definition of Done

- [ ] Both tests RED on the mission base for the product reason (verified: run on base via `PYTHONPATH="$(pwd)/src"`), not `AttributeError`/setup.
- [ ] The modified #2786 test's `merge --resume`/heal step is verified to **run and no-op (not raise)** on base — so the first failing assertion is provably the post-heal coherence contract, not infra.
- [ ] `@pytest.mark.regression` + issue-referencing docstrings on both.
- [ ] Existing #2786 test modified to assert-after-heal (not deleted); ≥2-WP fixture in the #2367 test, authored in the owned file (the unowned #2711 `_bootstrap_coord_mission` is NOT edited).
- [ ] `pytest tests/architectural/test_pytest_marker_convention.py tests/architectural/test_no_legacy_terminology.py` green.
- [ ] No production code touched (tests only).

## Reviewer Guidance

Verify the reds fail for the product reason on base (not setup); confirm no marker/doctor surface is
referenced; confirm the #2786 assertion was *modified* not deleted (SC-006); confirm the #2367
fixture is ≥2-WP with one stranded + one coherent WP and injects on the bake path.

## Activity Log

- 2026-07-18T15:21:07Z – claude – shell_pid=579351 – Assigned agent via action command
- 2026-07-18T15:42:33Z – claude – shell_pid=579351 – Red-first repros: intentionally RED until WP03 (single-PR landing unit, ADR 2026-07-17-1)
- 2026-07-18T15:42:57Z – claude – shell_pid=615737 – Started review via action command
- 2026-07-18T15:49:55Z – user – shell_pid=615737 – Review passed (renata): SC-006/007 + product-red + bake-path verified
