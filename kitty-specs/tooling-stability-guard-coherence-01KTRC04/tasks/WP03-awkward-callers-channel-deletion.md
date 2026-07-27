---
work_package_id: WP03
title: Awkward callers + five-channel deletion
dependencies:
- WP02
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T15:46:07.790561+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase 1 - Spine
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "283416"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/events/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/upgrade.py
- src/specify_cli/events/decision_log.py
- src/specify_cli/core/mission_creation.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Awkward callers + five-channel deletion

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match if none assigned.

---

## Objectives & Success Criteria
Finish the guard strangle: convert the context-less callers, fold the remaining privilege channels into
`GuardCapability`, then **DELETE all five channels** and flip WP01's xfail repros.
- The 3 awkward callers convert (the 4th — `agent/mission.py` planning paths — is WP05's).
- The bool/file-content/env channels FOLD into asserted capabilities (incl. the `allow_protected_branch_in_test_mode=True` **production** call sites in agent/workflow.py + agent/mission.py and the ~8-module bool propagation — those param-threading edits are expected out-of-map edits with one-line rationale; the FILES' ownership stays with their WPs, your change is mechanical param removal).
- **Done when:** the five channels are gone (`_is_protected_branch_exception`, `_is_completed_op_record_exception`, `_test_mode_allows_protected_branch`, both bool params, prefix constants, env privilege hatches — keep ONLY the documented operator escape hatch, named in the guard docstring); WP01's 5 xfails flip to passing refusal tests; this mission's own commits still work.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-008), plan.md (IC-02), data-model.md (channel-consolidation + deletions ledger), contracts/ (C-GUARD-2 per-channel refusals), research/plan-review-debugger-debby.md (RISK-1/RISK-2), research/plan-review-python-pedro.md (awkward-caller analysis)}`.
- **Strangler order (C-004):** convert → prove WP01 suite green → delete. Channel deletion lands ONLY after every prefix/bool consumer is on a capability. Never in a WIP commit.
- **Self-hosting (debby RISK-2):** this repo's own WP/status commits run through the guard you're deleting channels from. Before the deletion commit: run the WP01 suite + a live `spec-kitty agent tasks status` smoke. **Escape hatch:** document the operator env hatch (the one explicitly retained) in `commit_guard`'s docstring + this WP's activity log. If you wedge your own commit path, STOP and report — do not force.
- `git/commit_helpers.py` is WP02-owned: your deletion edits there are **sequential** (dep WP02) coordinated out-of-map edits — record the rationale line. Same for the `=True` call-site removals in agent/workflow.py / agent/tasks.py (WP02-owned) and agent/mission.py (WP05-owned — coordinate: remove only the bool param usage, not the planning-path logic).

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T009 — `upgrade.py` (no mission context)
- The upgrade flow runs outside any mission. Construct a FLATTENED `CommitTarget` for the current branch and assert `GuardCapability.upgrade_bookkeeping`. Its old prefix reliance (`chore: apply spec-kitty upgrade changes`) must become irrelevant (message is just a message).

### T010 — `decision_log.py` + `mission_creation.py`
- `decision_log.py` crosses the runtime_bridge boundary — resolve its CommitTarget from the surface that calls it (pass it in; do not re-derive inside). `core/mission_creation.py` runs pre-spec (mission dir just created): destination = the branch `create` reports; capability `standard` (it commits to a non-protected planning destination, or relies on WP05's placement when protected — coordinate, don't duplicate).

### T011 — Fold the bool/file-content channels
- Replace `allow_protected_branch_in_test_mode=…` with `capability=GuardCapability.test_mode` at the sites that genuinely need it (audit each `=True` production site — pedro/alphonso flagged agent/workflow.py + agent/mission.py; decide per site whether it should be `merge_bookkeeping`/`test_mode` or was masking a placement bug now fixed by WP02). Same for `allow_completed_op_on_protected_branch` → `merge_bookkeeping`. The op-record FILE-content check is replaced by the caller asserting its capability.

### T012 — DELETE the five channels + flip xfails
- Remove: `_is_protected_branch_exception` + prefix constants, `_is_completed_op_record_exception`, `_test_mode_allows_protected_branch`, both bool params (full ~8-module propagation), env privilege hatches (except the ONE documented operator escape hatch), and WP02's compat shim if still present. Flip WP01's 5 `xfail(strict=True)` repros to plain passing refusal tests (remove markers).

### T013 — Self-hosting verification
- After deletion: run the full WP01 suite + commit a trivial change via `spec-kitty safe-commit --to-branch fixups/code-engine-stabilization` from this repo to prove the dogfood path works; document the escape hatch.

## Definition of Done
- `rg "_is_protected_branch_exception|allow_protected_branch_in_test_mode|allow_completed_op_on_protected_branch|_is_completed_op_record_exception"` → zero hits in src/; WP01 suite fully green (0 xfail); `ruff`+`mypy` clean; own-commit smoke passes.

## Risks & Mitigations
- *Wedging the dogfood commit path* → suite + smoke BEFORE the deletion commit; escape hatch documented; STOP-don't-force.
- *A flow losing privilege silently* → T011's per-site audit; the WP01 invariants assert legitimate flows still work.

## Review Guidance
- Recommended: **architect-alphonso sign-off** (no privilege-channel residue — grep; capability assignments justified per site) + **reviewer-renata**. The per-channel refusal tests (former xfails) are the acceptance evidence.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10 – python-pedro (lane-c) – T009-T013 complete (strangler: convert → prove 5-xfail → delete → 0-xfail).
  - **T009** upgrade.py: FLATTENED CommitTarget + `UPGRADE_BOOKKEEPING`; message-prefix reliance retired.
  - **T010** mission_creation.py: CommitTarget(PRIMARY) + `STANDARD`; decision_log.py takes a CommitTarget passed IN
    from runtime_bridge (topology-correct COORDINATION/FLATTENED), no internal re-derivation.
  - **T011** per-site capability decisions: executor op-record → `MERGE_BOOKKEEPING` (file-content + bool channels gone);
    workflow.py x2 → `TEST_MODE`; coordination thread (types/policy/transaction WP02-owned + status_transition WP07 +
    bootstrap) → `capability` param defaulting to `STANDARD` (coord/lane branch is non-protected) — policy.py now defers
    the protected decision to `commit_guard.evaluate` (C-GUARD-1) instead of a parallel bool+env check; mission.py (WP05)
    bool-usage-only → `TEST_MODE`; safe_commit_cmd (WP04) dropped redundant `=False`.
  - **T012** deleted all five channels; grep gate `rg "_is_protected_branch_exception|allow_protected_branch_in_test_mode|
    allow_completed_op_on_protected_branch|_is_completed_op_record_exception" src/` → ZERO hits. 5 xfail repros flipped to
    passing refusal tests (WP01 suite 9 passed / 0 xfailed).
  - **Escape hatch (retained):** `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` is the ONE documented operator escape hatch
    (solo-fork operators who own `main`). It is consumed ONLY by the legacy `assert_not_protected_branch` pre-check in
    `git/commit_helpers.py` and NEVER reaches `commit_guard.evaluate`; it is named in commit_guard's module docstring.
    The deleted env hatch was `SPEC_KITTY_TEST_MODE` (its commit-privilege use is removed; tests assert `TEST_MODE` capability).
  - **T013** self-hosting: `spec-kitty safe-commit --to-branch fixups/code-engine-stabilization` from the PRIMARY checkout
    landed a trivial bookkeeping probe via the unmodified path ("Requested files committed"); probe reverted to keep the
    target clean. Real proof is the WP01 suite (9/0). ruff clean; no new mypy errors.
  - **Scoped deferral:** the `target`/`destination_ref` two-arg compat shim in safe_commit is RETAINED — out-of-mission
    string callers (merge.py, implement.py, orchestrator) still pass `destination_ref=`; retiring it needs their
    conversion, beyond WP03's owned scope. The DoD grep gate does not require it.
- 2026-06-10T20:48:46Z – user – shell_pid=156252 – Five privilege channels DELETED (FR-008): _is_protected_branch_exception+prefix consts, _is_completed_op_record_exception+op-record file-content channel, _test_mode_allows_protected_branch, both safe_commit bools, SPEC_KITTY_TEST_MODE commit-privilege. commit_guard.evaluate is sole authority (C-GUARD-1); coordination policy.py now defers to it. Per-site capability folds: upgrade=UPGRADE_BOOKKEEPING, op-record=MERGE_BOOKKEEPING, workflow/mission test escapes=TEST_MODE, mission_creation=STANDARD, coord-thread default=STANDARD. Retained ONE operator escape hatch SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS (pre-check only). WP01 suite 9 passed/0 xfailed; coordination+git+events+upgrade suites green; grep gate zero hits; ruff clean; no new mypy. T013 dogfood safe-commit proved unmodified path. Scoped deferral: target/destination_ref compat shim retained (out-of-mission string callers).
- 2026-06-10T20:49:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=283416 – Started review via action command
- 2026-06-10T20:54:28Z – user – shell_pid=283416 – Review passed (incl. architect-alphonso sign-off): Crown residue grep ZERO hits for the 4 deleted-channel symbols; surviving SPEC_KITTY_TEST_MODE uses are all legit non-commit (version isolation x2, hook-retire allowlist string, 2 pre-existing pre-flight UX guards from #1387 — not the deleted channel). WP01 suite 9 passed/0 xfailed (markers removed, plain refusal tests). Capability audit clean: upgrade=FLATTENED+UPGRADE_BOOKKEEPING, mission_creation=PRIMARY+STANDARD, decision_log=CommitTarget passed-in (no re-derive), workflow x2=TEST_MODE (target_branch normally-unprotected; honest test-only escape, not masking placement bug), op-record=MERGE_BOOKKEEPING. policy.py is genuine C-GUARD-1 consolidation (delegates to commit_guard.evaluate, zero residual env/bool). Escape hatch SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS pre-check-only + documented in commit_guard docstring. destination_ref shim deferral ACCEPTED (still used by implement.py/merge.py, out of owned scope, documented; WP10 ratchet/follow-up should allowlist or convert). Gates: git/git_ops/upgrade 802 passed, commit_guard+pre-commit-guard 20 passed, coordination policy+#1348 11 passed, ruff clean, mypy 2 pre-existing _get_current_build_id no-any-return confirmed on base (no NEW). 2 test_wrapper_delegation failures confirmed lane-worktree-environmental (implement-from-worktree refusal; 5 pass from primary).
