---
work_package_id: WP01
title: 'Foundation: sync_active() seam + #2801 clean-cut + freeze baselines'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-009
- FR-016
planning_base_branch: spike/3799-sync-deactivation-3798-accept-hermetic
merge_target_branch: spike/3799-sync-deactivation-3798-accept-hermetic
branch_strategy: Planning artifacts for this mission were generated on spike/3799-sync-deactivation-3798-accept-hermetic. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spike/3799-sync-deactivation-3798-accept-hermetic unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history:
- at: '2026-08-29T11:58:38Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent:
- tests/core/test_sync_active.py
- tests/architectural/census/sync_deactivate_collect_baseline.txt
- tests/architectural/census/sync_deactivate_test_census.txt
execution_mode: code_change
owned_files:
- src/specify_cli/core/saas_sync_config.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/review/test_pre_review_gate_*.py
- tests/core/test_sync_active.py
- tests/architectural/census/sync_deactivate_collect_baseline.txt
- tests/architectural/census/sync_deactivate_test_census.txt
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission plan.md "Post-plan squad corrections (BINDING)" section and the relevant contracts/ file — they are authoritative over this prompt where they conflict.

## Objective

Lay the foundation the whole mission keys on:

1. Introduce the **single canonical arming predicate** `sync_active()` in `src/specify_cli/core/saas_sync_config.py` (T001).
2. **Clean-cut #2801**: the pre-review regression gate reads only its own dedicated env `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` and stops honoring the sync toggles entirely; rewrite its tests (T002).
3. **Freeze the collection baseline** for opt-in parity (NFR-004) — this MUST happen now, before any `skipif` or conftest flip exists, because today's HEAD *is* the opt-in baseline (T003).
4. **Freeze the file census** — a frozen sorted SET of the sync-coupled test file paths that WILL carry `skipif` (the WP05 target list) for FR-013 (T004).

This WP is the sole unblocker: WP02, WP03, WP04, WP06, WP07 all depend transitively on the seam and/or the frozen baselines. Land it first.

## Context

Authoritative sources (read them, do not re-derive from this prompt):

- **plan.md → "Post-plan squad corrections (BINDING)"** — items 1, 4, 5 govern this WP.
- **contracts/sync-active-seam.md** — the exact predicate body, its location rationale (import cycle), and INV-1..INV-4.
- **contracts/pre-review-gate-env.md** — the #2801 before/after and INV-1..INV-4.
- **data-model.md** — the 8-row truth table (derived, not stored; env-only, no migration).
- **spec.md** — FR-002 (seam), FR-009 (gate decouple), NFR-004 (collect parity), FR-013 (census), C-007/C-008, SC-002/SC-004.

Key facts confirmed against current code by the post-plan squad (BINDING item 4):

- `first_set_sync_disable_env()` lives at `core/env.py:73`.
- `is_saas_sync_enabled()` lives at `core/saas_sync_config.py:37`.
- The pre-review gate consumer is `tasks_move_task.py:993` (`_mt_pre_review_gate_env_disable_reason`), and its `first_set_sync_disable_env` import at `tasks_move_task.py:120` is that function's SOLE use — so removing the sync-toggle read is a clean removal, not a partial one.

**Why the predicate lives in `saas_sync_config.py`, not `env.py`** (BINDING item 1): `saas_sync_config` already imports `is_truthy` from `env`. Defining `sync_active()` in `env.py` with a top-level `saas_sync_config` import would create the cycle `env → saas_sync_config → env` and fail at first import. `saas_sync_config.py` depends one-way on `env`, so it can import `first_set_sync_disable_env` freely.

> Note: `occurrence_map.yaml` still names `core/env.py` in a couple of places. The BINDING plan correction and `contracts/sync-active-seam.md` supersede it — the predicate goes in `core/saas_sync_config.py`. Flag the drift; do not follow the stale reference.

## Per-Subtask Guidance

### T001 — Add `sync_active()` + 8-row truth-table unit tests

**Steps**
1. In `src/specify_cli/core/saas_sync_config.py`, add:
   ```python
   def sync_active() -> bool:
       """True iff the legacy sync surface is armed. Machine-level arming only —
       NOT per-project egress consent (see sync/egress.py). Disable/minimal-import wins."""
       return is_saas_sync_enabled() and first_set_sync_disable_env() is None
   ```
   Import `first_set_sync_disable_env` from `.env` (one-way dependency — safe). `is_saas_sync_enabled` is already defined in this module at :37.
2. Write `tests/core/test_sync_active.py` covering **all 8 truth-table rows** from `data-model.md` / spec truth table. `E`=`SPEC_KITTY_ENABLE_SAAS_SYNC`, `D`=`SPEC_KITTY_SYNC_DISABLE`, `M`=`SPEC_KITTY_SYNC_MINIMAL_IMPORT`; expected `sync_active = E AND NOT (D OR M)`:

   | E | D | M | sync_active |
   |---|---|---|-------------|
   | 0 | 0 | 0 | inactive |
   | 1 | 0 | 0 | active |
   | 1 | 1 | 0 | inactive |
   | 1 | 0 | 1 | inactive |
   | 1 | 1 | 1 | inactive |
   | 0 | 1 | 0 | inactive |
   | 0 | 0 | 1 | inactive |
   | 0 | 1 | 1 | inactive |

   Use `monkeypatch.setenv` / `monkeypatch.delenv(..., raising=False)` to set each combination; assert the boolean. Parametrize for compactness.

**Files**: `src/specify_cli/core/saas_sync_config.py`, `tests/core/test_sync_active.py`.

**Validation**: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m pytest tests/core/test_sync_active.py -q` — all 8 rows green (the env var here just proves the harness; each parametrized case sets its own env). Confirm `INV-3` (truth table) and `INV-4` (single definition — no other module re-implements the predicate; sites import `sync_active`).

### T002 — #2801 clean-cut of the pre-review gate

**Steps**
1. In `src/specify_cli/cli/commands/agent/tasks_move_task.py`, rewrite `_mt_pre_review_gate_env_disable_reason` (~:993) to read **only** `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`. It must no longer call `first_set_sync_disable_env()`.
2. Remove the now-dead `first_set_sync_disable_env` import at :120 (confirmed sole use). Do not remove any other import.
3. Rewrite `tests/review/test_pre_review_gate_*.py` to the new env:
   - Assert the gate is **skipped** only when `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` is set (INV-2).
   - Assert setting/unsetting `SPEC_KITTY_SYNC_DISABLE` / `SPEC_KITTY_SYNC_MINIMAL_IMPORT` / `SPEC_KITTY_ENABLE_SAAS_SYNC` has **no** effect on the gate (INV-3) — this is the load-bearing #2801 assertion.
   - Keep/confirm the INV-1 case: a failing gate condition on a bare install (sync inactive) BLOCKS the `for_review` transition.

**Files**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`, `tests/review/test_pre_review_gate_*.py`.

**Validation**: `.venv/bin/python -m pytest tests/review/ -k pre_review_gate -q` green. Cross-check `contracts/pre-review-gate-env.md` INV-1..INV-4 and C-004 (gate never weakened) / FR-016 (the new flag is a gate flag, not a sync flag).

### T003 — Freeze the `--collect-only` opt-in baseline (NFR-004)

**Chicken-and-egg (BINDING item 5a)**: today's HEAD conftest forces `SPEC_KITTY_ENABLE_SAAS_SYNC=1` ON for the whole suite, so HEAD *is* the opt-in baseline. Once WP04 de-masks conftest and WP05 lands `skipif`, that baseline is gone. Capture it NOW.

**Steps**
1. Run:
   ```
   SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m pytest tests/sync tests/specify_cli/sync --collect-only -q
   ```
2. Capture the **non-skipped** node-IDs (strip the summary line and any `[skip]` entries) into `tests/architectural/census/sync_deactivate_collect_baseline.txt`, one node-id per line, **sorted**, deterministic. This is the WP07 T020 comparison target.

**Files**: `tests/architectural/census/sync_deactivate_collect_baseline.txt` (new).

**Validation**: the file is non-empty and sorted; re-running the collect command yields an identical set (order-independent). Reuse the shape from `tests/architectural/test_ci_collection_completeness.py` / `_gate_coverage.py` for how node-ids are normalized.

### T004 — Freeze the FR-013 file census (frozen SET, not a count)

**BINDING item 5b**: a *count* would let a rename mask a deletion. Freeze a **sorted SET of file paths** that WILL carry `skipif` — the WP05 target list.

**Steps**
1. Compute the sorted set of sync-coupled test file paths that WP05 will gate, from `occurrence_map.yaml → tests_fixtures` and `spec.md FR-011`: `tests/sync/**` (187), `tests/specify_cli/sync/**` (7), `tests/delivery/**`, `tests/cli/commands/test_sync_*.py`, `tests/status/` fanout modules, `tests/dossier/test_snapshot_emit.py`, `tests/stress/test_concurrent_emits.py`, `tests/integration/test_offline_queue_overflow.py`, plus #2809's `tests/**/test_daemon_sync_disable_env.py` and `tests/**/test_strict_json_stdout.py` (only the two named tests' files).
2. Write the repo-root-relative paths, one per line, sorted, into `tests/architectural/census/sync_deactivate_test_census.txt`.

**Files**: `tests/architectural/census/sync_deactivate_test_census.txt` (new).

**Validation**: file is non-empty, sorted, deduplicated, repo-root-relative. This is the FROZEN_SET that WP06's census test loads and compares against the live skipif-carrying set. Cross-check `tests/architectural/test_sync_env_census.py` for the census-file shape convention.

## Branch Strategy

- Planning base branch == merge target branch == `spike/3799-sync-deactivation-3798-accept-hermetic`; `branch_strategy: already-confirmed`.
- Do NOT hand-create a worktree. `spec-kitty implement WP01` allocates the execution workspace from the computed lane in `lanes.json` (`resolve_workspace_for_wp`). Consume the resolved path; never reconstruct `.worktrees/...`.
- This is the foundation WP (deps `[]`) — it must merge before the dependent WPs can validate against the seam.

## Test Strategy

- **Test-first / red-first (DIR-034)**: for T001 write the 8-row truth table first (red — `sync_active` does not yet exist), then add the predicate. For T002 rewrite the gate tests to the new-env contract first (red on old code), then apply the clean cut.
- **ruff + mypy clean**, complexity ≤ 15. `sync_active()` is a one-line boolean — trivially under the ceiling. Do not add `# noqa` / `# type: ignore`.
- **Targeted pytest only — never the full suite** (the full run takes ~1h and breaks the session). Run only the node-ids listed under each subtask's Validation.
- **Env footguns**: use `.venv/bin/python -m pytest`, never `uv run` (it re-syncs and destroys the hand-built `.venv`). Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to exercise the opt-in path where a subtask calls for it (T003 baseline capture).
- Baseline `.txt` artefacts (T003/T004) are data, not code — no ruff/mypy, but they must be deterministic (sorted, stable).

## Definition of Done

- `sync_active()` exists in `core/saas_sync_config.py`; 8-row truth table green (**FR-002**, INV-3/INV-4, C-008).
- Pre-review gate reads only `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`; sync toggles proven inert against it; tests rewritten (**FR-009**, C-004, SC-002, contracts/pre-review-gate-env.md INV-1..INV-4).
- `sync_deactivate_collect_baseline.txt` frozen from HEAD opt-in collect (**NFR-004** foundation for SC-004 / WP07 T020).
- `sync_deactivate_test_census.txt` frozen as a sorted SET of the WP05 target files (**FR-013** foundation for WP06).
- ruff + mypy clean; targeted tests green.

## Risks

| Risk | Mitigation |
|------|------------|
| Placing `sync_active()` in `env.py` re-introduces the import cycle | BINDING item 1 — it MUST live in `saas_sync_config.py`; a quick `python -c "import specify_cli.core.saas_sync_config"` smoke confirms no cycle. |
| Missing a second consumer of `first_set_sync_disable_env` when cutting #2801 | Squad confirmed `tasks_move_task.py:120` is the sole *behavioral* pre-review consumer; name-only enumerators are untouched. Grep before deleting the import. |
| Baseline captured AFTER a skipif or conftest flip is wrong forever | Capture T003/T004 on clean HEAD, before any other WP work; this WP owns them so ordering is guaranteed. |
| Census as a count hides rename-masked deletion | Freeze a SET of paths, not a count (BINDING item 5b). |

## Reviewer Guidance

- Confirm `sync_active()` is defined once, in `saas_sync_config.py`, and that WP02's sites will *import* it rather than re-implement (INV-4).
- Confirm the pre-review gate no longer references any sync toggle anywhere in `tasks_move_task.py`, and that the removed import at :120 was genuinely dead.
- Confirm the two `.txt` baselines are sorted, deterministic, repo-root-relative, and were captured on HEAD (not post-skipif). Spot-check a handful of node-ids in the collect baseline exist today.
- Verify no full-suite run was used to produce the baseline beyond the targeted `--collect-only` on `tests/sync` + `tests/specify_cli/sync`.
