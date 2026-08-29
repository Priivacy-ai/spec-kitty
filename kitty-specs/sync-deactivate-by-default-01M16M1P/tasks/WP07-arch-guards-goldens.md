---
work_package_id: WP07
title: Arch guards + goldens + NFR-004 parity
dependencies:
- WP01
- WP02
- WP05
requirement_refs:
- FR-014
planning_base_branch: spike/3799-sync-deactivation-3798-accept-hermetic
merge_target_branch: spike/3799-sync-deactivation-3798-accept-hermetic
branch_strategy: Planning artifacts for this mission were generated on spike/3799-sync-deactivation-3798-accept-hermetic. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spike/3799-sync-deactivation-3798-accept-hermetic unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
history:
- at: '2026-08-29T11:58:38Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/deactivation/test_collect_parity_nfr004.py
execution_mode: code_change
owned_files:
- tests/architectural/test_saas_sync_gate_selection_invariance.py
- tests/architectural/test_sync_writer_census.py
- tests/architectural/test_sync_env_census.py
- tests/characterization/test_sync_cli_safe.py
- tests/deactivation/test_collect_parity_nfr004.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission plan.md "Post-plan squad corrections (BINDING)" section and the relevant contracts/ file — they are authoritative over this prompt where they conflict.

## Objective

Update the meta arch guards and PR#3570 goldens to assert the new default-off / no-op contract (**updated, not skipped** — FR-014), rewrite the two that currently FIGHT default-off, and add the NFR-004 collection-parity guard.

- **T018** — rewrite the two guards that FIGHT default-off: `test_saas_sync_gate_selection_invariance.py::test_flag_is_set_at_collection_time` (:45) and `test_sync_writer_census.py` (:804 census-cannot-grow).
- **T019** — env-census frozen set gets the `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` literal; add an inactive-path arm to the `test_sync_cli_safe.py` golden.
- **T020** — NFR-004 parity: opt-in `--collect-only` node-ids == the WP01 baseline (diff = 0).

## Context

Authoritative sources:

- **plan.md → BINDING** items 10 (`test_flag_is_set_at_collection_time` asserts enable=="1" collection-wide → rewrite to the default-unset contract) and 11 (`test_sync_writer_census.py:804` census-cannot-grow must admit `sync_active()` as a new decision path; `test_sync_env_census.py` add the `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` literal; `test_sync_cli_safe.py` golden self-pins enable=1 and stays green → ADD an inactive-path arm; `test_egress_consent_boundary` / `test_sync_no_early_bind` / `test_sync_two_authority` are NEUTRAL — do not touch).
- **spec.md** — FR-014 (update guards + goldens to the deactivated/no-op contract, not skipped), NFR-004 / SC-004 (opt-in collection parity, diff = 0).
- **contracts/sync-active-seam.md** — `sync_active()` is a new decision/grant path (relevant to the writer census).

**Why these two FIGHT default-off** (BINDING item 10/11):
1. `test_flag_is_set_at_collection_time (:45)` asserts the enable flag `== "1"` collection-wide — after WP04 the default is unset, so this guard is now false by construction. Rewrite it to assert the **default-unset** contract (the flag is NOT forced on by default; opt-in sets it).
2. `test_sync_writer_census.py (:804)` is a "census cannot grow" guard — but `sync_active()` is a legitimately NEW decision/grant path. Update the census to admit it (grow by exactly the sanctioned addition), not reject it.

**Neutral guards — DO NOT TOUCH**: `test_egress_consent_boundary`, `test_sync_no_early_bind`, `test_sync_two_authority`. They remain valid under the new contract.

**NFR-004 without a second full run** (SC-004): compare `--collect-only` node-ids under opt-in against the WP01 baseline file — a collection diff, not a re-execution.

## Per-Subtask Guidance

### T018 — Rewrite the two guards that fight default-off

**Steps**
1. `tests/architectural/test_saas_sync_gate_selection_invariance.py` — rewrite `test_flag_is_set_at_collection_time` (:45): instead of asserting `SPEC_KITTY_ENABLE_SAAS_SYNC == "1"` collection-wide, assert the **default-unset contract** — the flag is absent/unset by default (post-WP04), and is set only under the opt-in CI job. Keep the guard's intent (collection-time posture is well-defined), flipped to the new default.
2. `tests/architectural/test_sync_writer_census.py` — update the `:804` census-cannot-grow expectation so `sync_active()` is admitted as a sanctioned new decision/grant path. The census should grow by exactly this addition (not be defeated wholesale).

**Files**: `tests/architectural/test_saas_sync_gate_selection_invariance.py`, `tests/architectural/test_sync_writer_census.py`.

**Validation**: `.venv/bin/python -m pytest tests/architectural/test_saas_sync_gate_selection_invariance.py tests/architectural/test_sync_writer_census.py -q` → green under the default-off posture. Confirm the writer census still FAILS if an *unsanctioned* new writer/gate is added (don't neuter it).

### T019 — Env-census literal + golden inactive-path arm

**Steps**
1. `tests/architectural/test_sync_env_census.py` — add the new `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` literal to the frozen set of recognized env vars (introduced by #2801 / FR-009). This keeps the env-census guard aware of the new gate flag.
2. `tests/characterization/test_sync_cli_safe.py` — the PR#3570 golden self-pins `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and thus stays green as-is. **ADD an inactive-path arm** (per FR-014) that exercises the deactivated/no-op contract: with sync inactive, the sync CLI reports inactive / no-ops rather than performing sync work. Keep the existing opt-in arm green; add the new arm.

**Files**: `tests/architectural/test_sync_env_census.py`, `tests/characterization/test_sync_cli_safe.py`.

**Validation**: `.venv/bin/python -m pytest tests/architectural/test_sync_env_census.py tests/characterization/test_sync_cli_safe.py -q` → both arms green. Confirm the env-census reds if `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` is removed from the frozen set (guard still bites).

### T020 — NFR-004 collection-parity guard

**Steps**
1. Create `tests/deactivation/test_collect_parity_nfr004.py`.
2. Run (or shell out to) `--collect-only` under `SPEC_KITTY_ENABLE_SAAS_SYNC=1` over `tests/sync` + `tests/specify_cli/sync`, capture the non-skipped node-ids, normalize/sort.
3. Load the WP01 baseline from `tests/architectural/census/sync_deactivate_collect_baseline.txt`.
4. Assert the two sets are **equal (diff = 0)** — proving no previously-green test is newly skipped under opt-in (opt-in parity). On mismatch, print `newly-skipped: ...` / `unexpected: ...`.
5. This must NOT trigger a second full execution — collection only (SC-004 wording: "verified without a second full execution"). Complexity ≤ 15 (extract a collect helper).

**Files**: `tests/deactivation/test_collect_parity_nfr004.py` (new).

**Validation**: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m pytest tests/deactivation/test_collect_parity_nfr004.py -q` → green (diff = 0). Depends on WP05 having landed the skipif (so the opt-in path is the one being verified); coordinate ordering — run this after WP05 or gate it to compare only what exists.

## Branch Strategy

- Planning base branch == merge target branch == `spike/3799-sync-deactivation-3798-accept-hermetic`; `branch_strategy: already-confirmed`.
- `spec-kitty implement WP07` allocates the execution worktree from the computed lane in `lanes.json`.
- WP07 depends on WP01 (baseline + seam) and WP02 (gating to validate). WP08 depends on WP07.

## Test Strategy

- **Test-first / red-first (DIR-034)**: T018's two guards are RED against the default-off posture before the rewrite (they assert the old forced-on contract). Rewrite them to the new contract. T020's parity guard is written against the WP01 baseline.
- **Updated, not skipped (FR-014)**: never skip these guards to make them pass — rewrite them to assert the new contract. Do not touch the three neutral guards.
- Keep the writer census still able to catch *unsanctioned* growth (don't defeat it while admitting `sync_active()`).
- **NFR-004 is collection-only** — a `--collect-only` diff, never a second full run (SC-004).
- **ruff + mypy clean**, complexity ≤ 15 (extract collect/load helpers).
- **Targeted pytest only**; never the full suite. **Env footguns**: `.venv/bin/python -m pytest`, never `uv run`; `SPEC_KITTY_ENABLE_SAAS_SYNC=1` for the parity + golden opt-in arms.

## Definition of Done

- `test_flag_is_set_at_collection_time` rewritten to the default-unset contract (**FR-014**, BINDING item 10).
- `test_sync_writer_census.py:804` admits `sync_active()` as a sanctioned decision path, still catches unsanctioned growth (**FR-014**, BINDING item 11).
- `test_sync_env_census.py` frozen set includes `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` (**FR-014**).
- `test_sync_cli_safe.py` gains an inactive-path arm; opt-in arm still green (**FR-014**).
- Three neutral guards untouched.
- NFR-004 collection-parity guard green (opt-in node-ids == WP01 baseline, diff = 0) (**NFR-004/SC-004**).
- ruff + mypy clean.

## Risks

| Risk | Mitigation |
|------|------------|
| Skipping a guard instead of rewriting it | FR-014 is explicit: updated, not skipped. |
| Defeating the writer census while admitting sync_active() | Grow the census by exactly the sanctioned addition; verify it still reds on an unsanctioned writer. |
| Touching a neutral guard and breaking it | Leave `test_egress_consent_boundary` / `test_sync_no_early_bind` / `test_sync_two_authority` alone (BINDING item 11). |
| NFR-004 guard triggers a second full run | Collection-only diff against the WP01 baseline file (SC-004). |
| Parity guard run before WP05 lands skipif | Order after WP05, or compare only existing node-ids. |

## Reviewer Guidance

- Confirm the two fighting guards were REWRITTEN (assert the new default-off/no-op contract), not skipped or deleted.
- Confirm the writer census still catches an unsanctioned new writer (not neutered).
- Confirm the three neutral guards are untouched in the diff.
- Confirm `test_sync_cli_safe.py` keeps its opt-in arm green AND adds an inactive-path arm.
- Confirm the NFR-004 guard compares `--collect-only` node-ids against the WP01 baseline file (no second full run) and reds on a diff.

---
## Post-tasks squad correction (BINDING)
**Dependency add: WP07 also depends on WP05.** T020 (NFR-004 collection-parity) is vacuous until WP05's skipif exists — before then the opt-in and default collections are identical and the test verifies nothing. Sequence T020 AFTER WP05 lands. (Implement WP07's T018/T019 arch-guard rewrites — which only need WP01+WP02 — first if parallelizing, but T020 waits on WP05.)
