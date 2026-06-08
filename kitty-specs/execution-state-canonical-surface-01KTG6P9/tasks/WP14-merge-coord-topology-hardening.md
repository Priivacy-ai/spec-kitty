---
work_package_id: WP14
title: Coordination-topology merge & path/status hardening (#1772)
dependencies:
- WP04
requirement_refs:
- FR-035
- FR-037
- FR-038
- NFR-001
- NFR-006
tracker_refs:
- '1772'
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on
  feat/execution-state-strangler. During /spec-kitty.implement this WP may
  branch from a dependency-specific base, but completed changes must merge back
  into feat/execution-state-strangler unless the human explicitly redirects the
  landing branch.
subtasks:
- T054
- T055
- T056
- T057
phase: Phase 3 - Strangle
assignee: ''
agent: "claude:sonnet:paula-patterns:implementer"
shell_pid: "3055487"
history:
- at: '2026-06-08T03:40:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (#1772 fold-in)
agent_profile: paula-patterns
authoritative_surface: 'src/specify_cli/cli/commands/merge.py'
execution_mode: code_change
model: ''
scope: codebase-wide
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/cli/commands/doctor.py
- tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP14 – Coordination-topology merge & path/status hardening (#1772)

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` (profile below), then `/spk-doctrine-semantic-compression`.

- **Profile**: `paula-patterns`
- **Role**: `implementer`

## ⚙️ Persona IC — Paula Patterns (+ Randy Reducer)

One coord-aware surface owns feature-dir/status resolution on **every** path, including merge. The merge must NOT carry a parallel `done`-status proxy for "code integrated" — gate on the real tree state. Behavior-preserving for the healthy-merge path (NFR-001); `coordination/transaction.py` internals stay untouched (NFR-006).

## Background (#1772 — P0, data integrity)

`spec-kitty merge` failed three ways on a healthy, fully-approved coordination-topology mission and, on retry, **silently produced a zero-code squash-merge while reporting success**. Root causes:

- **Bug 0 (FR-035):** finalize/recovery `git add` flows staged tracked `.worktrees/` content (precondition for the rest).
- **Bugs 1/2 (FR-036):** `candidate_feature_dir_for_mission` / `resolve_status_surface` double-resolved the coord worktree → `.worktrees/<m>-coord/.worktrees/<m>-coord/…`. **Delivered by WP04** (the canonical coord-aware resolver) — WP14 depends on it.
- **Bug 3 (FR-037):** the retry gated integration on the per-WP `done` event (already written before the abort), so it skipped all lanes and squashed zero code.
- **Bug 4 (FR-038):** post-merge validation read a `.worktrees/` path that is never tracked in a branch tree.

This WP owns the merge-flow + hygiene halves (FR-035/037/038); the resolver-correctness half (FR-036) is WP04.

## Objectives & Success Criteria

Realize **SC-011**: on a coord-topology fixture with tracked `.worktrees/` junk + pre-recorded `done` events from an aborted merge, `spec-kitty merge` integrates the real lane diffs or fails loudly (never a zero-code squash reported as success); post-merge validation reads the in-branch status path; finalize/recovery never stage `.worktrees/` and `doctor` flags pre-existing tracked `.worktrees/`.

## Subtasks

> **ATDD-first (C-011):** author + commit **T057 RED first**, before T054–T056. Reviewer verifies red→green.

### T057 — Coord-topology merge regression fixture (RED first)

**Purpose**: Reproduce #1772 in a test before fixing it.

**Steps**:
1. New `tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py`. Build a coord-topology mission fixture: `coordination_branch` in `meta.json`, ≥1 lane with real diff, tracked `.worktrees/<m>-coord/…` junk, and per-WP `done` events pre-recorded in the coord event log (simulating a prior aborted merge).
2. Assert (initially failing): merge integrates the lane diff (target tree contains the WP code), OR raises a loud structured error — never a zero-diff squash reported success.
3. Assert post-merge validation resolves the in-branch status path (no `git show <branch>:.worktrees/…`).

**Validation**: the test FAILS on current `main`/branch (proves non-vacuity), passes after T054–T056.

### T054 — No `.worktrees/` staging + doctor check (FR-035, Bug 0)

**Steps**:
1. Guard the finalize/recovery + merge staging flows so no path under `.worktrees/` is ever passed to `git add` (explicit filter; reuse the same predicate everywhere — Randy Reducer: one guard, not per-call-site copies).
2. Add a `spec-kitty doctor` check (in `cli/commands/doctor.py`) that flags tracked `.worktrees/` content with a remediation hint.

**Validation**: a finalize/recovery run with `.worktrees/` dirt stages none of it; `doctor` reports the pre-existing tracked `.worktrees/` files.

### T055 — Gate integration on tree-diff, not `done` status (FR-037, Bug 3 — data integrity)

**Steps**:
1. In `cli/commands/merge.py`, gate lane code integration on the **actual lane tree-diff** vs. the target, not the per-WP `done` event. A `done` status is NOT a proxy for "code already integrated".
2. If a squash/merge would integrate **zero** lane diffs, FAIL LOUDLY with a structured error — do not emit a success commit, and do not reset lane HEADs on a no-op.
3. Fix `_write_mission_number_to_branch` to resolve the in-branch feature dir (not a nested-worktree `meta.json`) before `git add`.

**Validation**: the retry-after-abort path (T057) integrates real code or fails; never a zero-code squash reported as success.

### T056 — In-branch post-merge validation (FR-038, Bug 4)

**Steps**:
1. In the `_assert_merged_wps_reached_done`-adjacent validation, resolve the **in-branch** status path (the tracked `kitty-specs/<m>/status.events.jsonl` in the branch tree), not a `.worktrees/` worktree path.

**Validation**: post-merge validation succeeds on a coord-topology merge without `path exists on disk, but not in <branch>` errors.

## Branch Strategy

Planning/base branch: `feat/execution-state-strangler`. Final merge target: `feat/execution-state-strangler`. Execution worktrees are allocated per the computed lane from `lanes.json`.

## Definition of Done

- T057 fixture committed RED first, then green after T054–T056.
- FR-035 / FR-037 / FR-038 satisfied; SC-011 met.
- Healthy-merge path behavior-preserved (NFR-001); `coordination/transaction.py` untouched (NFR-006).
- `ruff` + `mypy` clean, no disabled checks (NFR-007).
- Depends on WP04 having landed the FR-036 single coord-aware resolver.

## Reviewer Guidance

- Verify T057 is non-vacuous (fails without the fixes).
- Confirm FR-037 truly gates on tree-diff — try the "all WPs already done, zero diff" path and confirm it fails loudly rather than emitting a success squash.
- Confirm no `.worktrees/` path can reach `git add` and the `doctor` check fires on tracked `.worktrees/`.
- Confirm FR-036 is consumed from WP04's resolver, not re-implemented here.

## Activity Log

- 2026-06-08T11:21:33Z – claude:opus:paula-patterns:implementer – shell_pid=3002487 – Started implementation via action command
- 2026-06-08T11:42:16Z – claude:opus:paula-patterns:implementer – shell_pid=3002487 – Ready for review: FR-035/037/038 + ATDD T057 (RED->green, non-vacuous), healthy-merge preserved (NFR-001), transaction.py untouched (NFR-006), FR-036 consumed from WP04
- 2026-06-08T11:43:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=3026288 – Started review via action command
- 2026-06-08T11:55:35Z – user – shell_pid=3026288 – Moved to planned
- 2026-06-08T11:56:21Z – claude:sonnet:paula-patterns:implementer – shell_pid=3055487 – Started implementation via action command
