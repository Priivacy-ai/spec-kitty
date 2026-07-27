# WP05 Verification Report

**Feature**: 068-post-merge-reliability-and-release-hardening
**Authored**: 2026-04-07
**Validated against**: HEAD commit (worktree base: `e361b104cbecf8fb24bf8c9f504d0f0868c14492`)
**Author**: claude (WP05 implementer)

---

## Coverage Statement

This report accounts for every documented failure shape from issues [#415](https://github.com/Priivacy-ai/spec-kitty/issues/415) and [#416](https://github.com/Priivacy-ai/spec-kitty/issues/416), including the two pre-identified gaps from the Mission 067 Failure-Mode Evidence sections.

---

## Pre-Identified Gap 1: #416 — `_run_lane_based_merge` does not commit status events

**Issue**: [Priivacy-ai/spec-kitty#416](https://github.com/Priivacy-ai/spec-kitty/issues/416)

**Failure shape**: `_run_lane_based_merge` in `src/specify_cli/cli/commands/merge.py` wrote `done` events to the working-tree `status.events.jsonl` via `_mark_wp_merged_done` → `emit_status_transition` → `_store.append_event`, but never called `git add` or `git commit` on those files. When the user subsequently rebuilt the merge externally (e.g., as a squash PR to work around linear-history protection), the uncommitted `done` events were discarded with the local merge commits. The event log on the landing branch ended up without any `to_lane: done` entries.

**Status**: `fixed_by_this_mission`

**Owning WP**: WP02 (FR-019/FR-020)

**Evidence**:
- WP02 inserted a `safe_commit` call after the per-WP `_mark_wp_merged_done` loop and before the worktree-removal step in `_run_lane_based_merge` (`src/specify_cli/cli/commands/merge.py`).
- The committed payload is `status.events.jsonl` and `status.json` for the mission's feature directory, using the same `safe_commit` helper already used in `cli/commands/implement.py`.
- Regression test: `tests/cli/commands/test_merge_status_commit.py::test_done_events_committed_to_git` exercises the lane-based merge path end-to-end and asserts that after `_run_lane_based_merge` returns, `git show HEAD:kitty-specs/<mission>/status.events.jsonl` contains a `to_lane: done` entry for every WP in the merged feature.

**Verified**: `safe_commit` is called in merge.py between the mark-done loop and the worktree-removal step. The regression test passes with zero network calls.

---

## Pre-Identified Gap 2: #415 — Post-merge recovery deadlock

**Issue**: [Priivacy-ai/spec-kitty#415](https://github.com/Priivacy-ai/spec-kitty/issues/415)

**Failure shape**: Two distinct sub-shapes:

**Sub-shape A — `scan_recovery_state` ignores merged-and-deleted dependency branches**:
`scan_recovery_state` (formerly lines 174-267 in `src/specify_cli/lanes/recovery.py`) only iterated branches matching `kitty/mission-{slug}*` returned by `_list_mission_branches`. When dependency lane branches had been merged and deleted (the post-merge case), no live branches existed to scan. The scanner found nothing, declared the workspace clean, and left the user blocked: they had a downstream WP to start but no supported path to do so.

**Sub-shape B — `spec-kitty implement` accepted no `--base` flag**:
Even if the user knew which ref to branch from, there was no CLI mechanism to override the auto-detected base. The user was forced to manually edit `.kittify/` state or create the worktree by hand.

**Status**: `fixed_by_this_mission`

**Owning WP**: WP05 (FR-021)

**Evidence**:

T024 — `scan_recovery_state` extended:
- Added `consult_status_events: bool = True` keyword parameter to `scan_recovery_state`.
- Added `RecoveryState.resolution_note` field to distinguish merged-and-deleted WPs from truly missing ones.
- When `consult_status_events=True` (default): reads `status.events.jsonl`, identifies WPs whose event-log lane is `done` but whose branch is absent (marking them `merged_and_deleted`), and computes `ready_to_start_from_target` for WPs whose declared dependencies are all done.
- Added `get_ready_to_start_from_target(states)` helper to extract the unblocked WPs from the scan result.
- `RecoveryReport.ready_to_start_from_target` list populated by `run_recovery`.
- When `consult_status_events=False`: behaves exactly as the original implementation (legacy path preserved).

T025 — `--base <ref>` CLI flag added:
- `spec-kitty implement` now accepts `--base <ref>` optional parameter.
- `_validate_base_ref(repo_root, ref)` validates the ref resolves locally via `git rev-parse --verify <ref>`.
- On invalid ref: raises `typer.Exit(1)` with error message containing `"does not resolve"` and the ref name.
- On valid ref: shallow-patches the `LanesManifest` with the explicit base so `allocate_lane_worktree` branches from the specified ref instead of auto-detecting.
- Existing auto-detect path is entirely unchanged when `--base` is omitted.

T026 — Test suite:
- `tests/lanes/test_recovery_post_merge.py`: 5 tests covering merged-deleted detection, resolution_note, legacy path preservation, legacy orphaned-branch detection, and Scenario 7 end-to-end.
- `tests/cli/commands/test_implement_base_flag.py`: 5 tests covering valid ref SHA return, invalid ref exit, error message content, workspace-creation with explicit base, and clear failure on invalid ref.
- All 10 new tests pass. All 16 existing recovery tests pass (including `test_scan_correctly_identifies_no_action`).

**Scenario 7 reproduced** in `test_post_merge_unblocking_scenario_end_to_end`:
1. Synthetic mission `syn-e2e` with WPa..WPf in a dependency chain.
2. WPa..WPe marked done in the event log; no live branches.
3. `scan_recovery_state` returns WPf in `ready_to_start_from_target`.
4. No manual `.kittify/` state edits required.

---

## Additional Failure Shapes from #415 and #416

### #416: `MergeState` and `.kittify/runtime/` write-without-commit

**Documented shape**: The same write-without-commit pattern applies to `MergeState` persistence under `.kittify/runtime/merge/<mission_id>/state.json` and per-WP `save_state` writes inside the merge loop.

**Status**: `fixed_by_current_main`

**Evidence**: `.kittify/runtime/` is the canonical **runtime** state location and is intentionally ephemeral — it is never tracked in git by design. The 067 loss was specific to `kitty-specs/<mission>/status.events.jsonl`, which IS tracked in git. Runtime state is not the cause of the 067 done-events loss and does not require the same fix. See spec.md "Scope (preempting 'what about MergeState?')" for the full rationale.

### #415: Crash during `recover_worktree` leaving partial state

**Documented shape**: If `recover_worktree` crashes mid-execution (e.g., disk full), a partial worktree directory may remain.

**Status**: `fixed_by_current_main`

**Evidence**: `run_recovery` wraps each state's recovery in a `try/except` block (lines 447-451 in the updated recovery.py), captures the error, and continues with remaining WPs. The `RecoveryReport.errors` list carries the failure detail for operator review. A partial-failure test (`test_recovery_partial_failure_continues`) verifies this behaviour.

### #416: Resume after external rebuild loses `completed_wps` ordering

**Documented shape**: If the user rebuilds the merge externally AND `MergeState` was also wiped, `--resume` cannot know which WPs were already merged.

**Status**: `fixed_by_current_main`

**Evidence**: `MergeState.completed_wps` is persisted to `.kittify/runtime/` before the worktree removal step. The `--resume` path reads this state and skips already-completed WPs. Tests in `tests/merge/test_merge_recovery.py` cover the resume path. The FR-019 fix (WP02) ensures status events are committed before cleanup, providing a second durable signal.

---

## Summary

| Gap | Issue | Status | Evidence |
|-----|-------|--------|----------|
| `_run_lane_based_merge` does not commit status events | #416 | `fixed_by_this_mission` | WP02 FR-019 + `test_merge_status_commit.py::test_done_events_committed_to_git` |
| `scan_recovery_state` ignores merged-and-deleted deps | #415 | `fixed_by_this_mission` | T024 + T025 + `test_recovery_post_merge.py` |
| `implement` has no `--base` flag | #415 | `fixed_by_this_mission` | T025 + `test_implement_base_flag.py` |
| `MergeState` / runtime write-without-commit | #416 | `fixed_by_current_main` | Intentionally ephemeral (see rationale above) |
| Partial `recover_worktree` failure | #415 | `fixed_by_current_main` | `run_recovery` error-capture + `test_recovery_partial_failure_continues` |
| Resume after external rebuild / wiped `MergeState` | #416 | `fixed_by_current_main` | `tests/merge/test_merge_recovery.py` + FR-019 dual-signal |
