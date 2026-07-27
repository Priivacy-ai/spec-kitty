# Research: Merge Done-Marking Surface Resolver

**Source**: Five-paradigm investigation via Debugger Debbie profile (invocation ID 01KTDTY8SEPEJMZQFJ2EF84W1M)
**Date**: 2026-06-06
**Issue**: https://github.com/Priivacy-ai/spec-kitty/issues/1726

---

## Finding 1: Write-Path Mechanics

**Decision**: The write path routes to the coordination branch worktree when `coordination_branch` is set in `meta.json`.

**Rationale**: `_mark_wp_merged_done` (`merge.py:223`) calls `emit_status_transition_transactional`, which reads `coordination_branch` from `meta.json` via `_identity_for_request`. When present, it opens `BookkeepingTransaction.acquire(destination_ref=coord_branch, ...)`. The transaction creates or reuses the coordination worktree at `.worktrees/<slug>-<mid8>-coord/` and writes `status.events.jsonl` inside it, then commits to the coordination branch ref (`kitty/coord/<slug>-<mid8>`). The primary checkout's `kitty-specs/<slug>/status.events.jsonl` is not touched.

**Alternatives considered**: None — this is the existing behavior being diagnosed, not a design choice.

**Key code references**:
- `src/specify_cli/coordination/status_transition.py` lines ~318/334 — routing decision
- `src/specify_cli/coordination/transaction.py` line ~598 — `BookkeepingTransaction.acquire`; line ~754 — `effective_destination_ref` override; line ~765 — `txn.feature_dir` assignment

---

## Finding 2: Read-Back Path Mechanics

**Decision**: The read-back assertion reads the primary checkout's event log file directly, never consulting the coordination branch.

**Rationale**: `_assert_merged_wps_reached_done` (`merge.py:348`) calls `get_wp_lane(feature_dir, wp_id)` where `feature_dir = resolve_feature_dir_for_mission(repo_root, mission_slug)`. `get_wp_lane` → `_require_event_log(feature_dir)` → `read_events(feature_dir)` → `Path.read_text()` on `feature_dir / "status.events.jsonl"`. This is a plain filesystem read with no git ref awareness. `feature_dir` resolves to the primary checkout path, not the coordination worktree.

**Key code references**:
- `src/specify_cli/status/lane_reader.py` line 32 — `_require_event_log`
- `src/specify_cli/status/store.py` — `read_events`: pure `Path.read_text()`
- `merge.py:1797` — assertion call site; `merge.py:1864` — `safe_commit` call site (after assertion)

---

## Finding 3: Ordering Compound

**Decision**: The assertion fires before the coordination-branch events are flushed. This makes the divergence structurally guaranteed, not timing-dependent.

**Rationale**: `_assert_merged_wps_reached_done` is at `merge.py:1797`. `safe_commit`, which would propagate coordination-branch events to the primary checkout, is at `merge.py:1864` — 67 lines later. The assertion cannot see the write under any circumstances in the current code path. The fix cannot rely on reordering `safe_commit`; it must make the assertion read from the same surface as the write.

---

## Finding 4: No Surface Resolver Exists

**Decision**: There is no existing shared abstraction for "where does the status surface live for this mission." One must be created.

**Rationale**: Both `_mark_wp_merged_done` (line 223) and `_assert_merged_wps_reached_done` (line 348) call `resolve_feature_dir_for_mission(repo_root, mission_slug)` independently. `resolve_feature_dir_for_mission` returns a `feature_dir` (the mission directory root) but does not resolve the actual events file path, and it does not account for whether the write will go through `BookkeepingTransaction` to a coordination worktree. After `resolve_feature_dir_for_mission`, the two functions diverge: one enters `emit_status_transition_transactional` (which may reroute to coordination branch); the other passes `feature_dir` directly to `get_wp_lane` (which always reads from the filesystem path as-is).

**Key code references**:
- `merge.py:223` — `_mark_wp_merged_done` uses `resolve_feature_dir_for_mission`
- `merge.py:348` — `_assert_merged_wps_reached_done` uses `resolve_feature_dir_for_mission` independently
- `src/specify_cli/coordination/status_transition.py` line 318 — coord-branch fork in `emit_status_transition_transactional`

---

## Finding 5: Full Test Gap

**Decision**: Zero merge-related test files set `coordination_branch` in any fixture. The full coverage gap is confirmed.

**Rationale**: Across 11 merge-related test files, `grep -n 'coordination_branch'` returns zero results. All tests that call both functions live monkeypatch either `emit_status_transition_transactional` or `get_wp_lane` directly — making the surface divergence invisible. Tests that exercise both functions without mocking them (T015 in `test_merge.py`, `test_merge_done_recording.py`) also omit `coordination_branch` from their fixtures.

**Best homes for regression tests**:
- `tests/specify_cli/cli/commands/test_merge.py` — T015 live-function section
- `tests/merge/test_merge_done_recording.py`

---

## Finding 6: Class Recurrence from #1589

**Decision**: This is a class recurrence. The fix for #1589 facet 3 added `coordination_branch` awareness to runtime read sites but did not propagate to the merge closeout path. No recurrence guard exists.

**Rationale**: Issue #1589 facet 3 fixed the same locate-vs-observe divergence on `move-task`, `next`, and `lane_reader`. Those fixes live in `status/lane_reader.py` and `status/uninitialized_hint.py`. The merge closeout path (`_assert_merged_wps_reached_done`) was not updated. No architectural guard prevents the same class from reappearing on new paths.

**Alternatives considered**: Re-routing the assertion to use `read_current_wp_state_transactional` (which is coordination-branch-aware). Rejected because it is heavier than needed — the assertion only needs the final lane value from the canonical surface, not the full transactional read machinery. A simple surface resolver is sufficient.

---

## Finding 7: Planning-Only Path Shares the Vulnerability

**Decision**: The planning-artifact merge path is not separate. It flows through the same done-marking loop.

**Rationale**: `_run_lane_based_merge_locked` contains a single done-marking loop at lines 1782–1797 that iterates all WPs across all lanes, including planning-only WPs. The `LanesManifest.planning_artifact_wps` field exists but is not consulted by the loop. PR #1723's planning-artifact tests are green only because they omit `coordination_branch` and mock both functions. A real planning-only mission with `coordination_branch` set would fail identically.

---

## Open Questions

None. All blocking questions were resolved by the five-paradigm investigation. The fix approach is fully determined.
