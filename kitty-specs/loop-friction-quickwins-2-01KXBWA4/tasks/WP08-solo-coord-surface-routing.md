---
work_package_id: WP08
title: Solo PR-bound coord mission — route empty-coord surface cleanly to primary (#2533 consequence)
dependencies: []
requirement_refs:
- C-002
- FR-011
- NFR-005
tracker_refs:
- '2533'
- '2160'
planning_base_branch: feat/loop-friction-quickwins-2
merge_target_branch: feat/loop-friction-quickwins-2
branch_strategy: Planning artifacts for this mission were generated on feat/loop-friction-quickwins-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/loop-friction-quickwins-2 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-loop-friction-quickwins-2-01KXBWA4
base_commit: 5d3b7ebc7bec34415f3dd5f4413630457ca93812
created_at: '2026-07-12T21:35:36.400231+00:00'
subtasks:
- T029
- T030
- T031
- T032
phase: Coord-lane recovery
agent: claude
shell_pid: '1484725'
shell_pid_created_at: '1783892074.19'
history:
- at: '2026-07-12T19:30:00Z'
  actor: claude
  action: Added post-tasks per operator (#2533 latest comment). Consequence-only fix; derivation revisit deferred to a follow-up.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/surface_resolver.py
create_intent:
- tests/coordination/test_surface_resolver_solo_coord_primary.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/surface_resolver.py
- tests/coordination/test_surface_resolver_coord_empty_warning.py
- tests/coordination/test_surface_resolver_solo_coord_primary.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 — Solo PR-bound coord mission routes empty-coord surface cleanly to primary

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objectives & Success Criteria

A solo PR-bound `--start-branch` mission (topology `coord`, no lanes, mission dir never populated on the
coordination branch) must resolve its status surface cleanly to PRIMARY as an EXPECTED route — not trip the
loud "stale, split-brain status surface" fallback that today reads as an error and drives a manual flatten.
The split-brain is killed **by construction** (read surface == write placement == PRIMARY), not merely muted.

- **SC (#2533)**: for a solo PR-bound coord mission, the first lane/status transition resolves to PRIMARY without emitting `_COORD_EMPTY_FALLBACK_WARNING` and without requiring a manual flatten.
- **SC (same-path, D4)**: the WRITE placement (`placement_seam().write_target(STATUS_STATE)`) and the READ surface (`resolve_status_surface`) resolve to the SAME path (both PRIMARY) for the solo-empty case.
- **SC (true-positive, NFR-005)**: a coord mission WITH lanes whose coord worktree is unexpectedly empty STILL warns (the warning's genuine signal is preserved).

## Context & Constraints — coordination-aware (C-002)

**Scope decision (operator, from #2533 latest comment):** fix the **CONSEQUENCE**, not the derivation. The
`if pr_bound: return COORD` derivation in `mission_create.py` (#2581, pinned by
`test_create_pr_bound_on_non_primary_branch_still_defaults_to_coord`) STAYS. A separate follow-up issue will
revisit whether solo PR-bound `--start-branch` should derive `single_branch`. **Do NOT touch the derivation
or that test in this WP.**

**The bug (#2533):** the status event log is a COORD-partition artifact routed toward the coordination
branch, while `spec.md`/`plan.md`/`tasks.md` are PRIMARY-partition on the feature branch. For a solo mission
nothing populates the mission dir on the coord branch → the coord worktree strands empty → the first lane
transition hits `resolve_status_surface_with_anchor`'s `CoordState.EMPTY` arm and emits the split-brain
WARNING before falling back to PRIMARY.

**Canonical seam to extend (alphonso D4 — do NOT fork):**
- `resolve_status_surface_with_anchor` @ `coordination/surface_resolver.py:603` — the READ-surface authority.
- The `CoordState.EMPTY` arm @ `:796-804` (already RETURNS primary; today it also logs `_COORD_EMPTY_FALLBACK_WARNING` @ `:112`).
- Reuse the existing `probe_coord_state` / `_effective_surface_topology` (@ `:544`) / `_husk_is_authoritative_surface` (@ `:508`) signals. **Do NOT add a parallel `pr_bound`-sniffing branch** (that would be a second `_husk_is_authoritative_surface`).

**KEEP invariants (hard):**
- **K-4 boundary**: this WP owns the READ surface ONLY. Do NOT touch `tasks_move_task.py`, `_mt_resolve_status_placement_ref`, or `placement_seam().write_target(STATUS_STATE)` — WP07 freezes the WRITE placement. WP08 does not own `tasks_move_task.py`.
- Re-verify line-anchors against live code before editing (they were read live but confirm).
- No `# noqa`/`# type: ignore`; ruff + mypy clean; complexity ≤15.

Depends on nothing (disjoint files from WP07). Coordinates with WP07 semantically (boundary rule below).
Plan: IC-08. Spec: FR-011. Issue: #2533.

## WP07 ↔ WP08 boundary rule (from the SSOT lens)

1. **WRITE placement authority** = `placement_seam().write_target(STATUS_STATE)` — owned/frozen by WP07 (K-4). WP08 must not touch it.
2. **READ surface authority** = `resolve_status_surface_with_anchor` — owned by WP08 (only the `CoordState.EMPTY` arm). WP07 must not touch `surface_resolver.py`.
3. **Agreement (owned by WP08's T030)**: for a solo PR-bound coord mission, read surface == write placement == PRIMARY. Prove it — do not mask a mismatch.

## Branch Strategy

- **Planning base branch / Merge target**: feat/loop-friction-quickwins-2

## Subtasks & Detailed Guidance

### Subtask T029 — Clean primary route for the legitimate solo-empty case

- **Steps**: In the `CoordState.EMPTY` arm of `resolve_status_surface_with_anchor`, recognize the legitimate
  solo/no-lanes case (mission dir never materialized on coord, no lanes registered) using the resolver's
  existing signals (`probe_coord_state` / `_effective_surface_topology` / lanes registry). Route to PRIMARY as
  an EXPECTED outcome without emitting `_COORD_EMPTY_FALLBACK_WARNING`. Do not add a `pr_bound` branch.
- **Files**: `src/specify_cli/coordination/surface_resolver.py`.

### Subtask T030 — Same-path agreement regression (kill split-brain by construction)

- **Steps**: New `tests/coordination/test_surface_resolver_solo_coord_primary.py`: build a solo PR-bound coord
  mission fixture (coord branch minted, mission dir NOT on coord, no lanes). Assert the READ surface
  (`resolve_status_surface`) and the WRITE placement (`placement_seam().write_target(STATUS_STATE)` — READ it,
  do not mutate its module) resolve to the SAME PRIMARY path. This is the D4 boundary pin.
- **Files**: the new test file.

### Subtask T031 — Preserve the warning's true signal

- **Steps**: A coord mission WITH lanes (or an expected-populated coord) whose coord worktree is
  unexpectedly empty STILL emits `_COORD_EMPTY_FALLBACK_WARNING`. Differentiate legitimate-solo-empty
  (expected → clean primary) from unexpected-empty (still warns).
- **Files**: `src/specify_cli/coordination/surface_resolver.py`.

### Subtask T032 — Update existing warning test

- **Steps**: Update `tests/coordination/test_surface_resolver_coord_empty_warning.py` for the new behavior:
  legitimate-solo-empty no longer warns; unexpected-empty still does.
- **Files**: `tests/coordination/test_surface_resolver_coord_empty_warning.py`.

## Definition of Done

- Solo-empty coord routes cleanly to primary (no split-brain warning, no manual flatten); unexpected-empty still warns.
- Same-path regression proves read surface == write placement == PRIMARY.
- Derivation + #2581 test UNTOUCHED. `surface_resolver.py` only; `tasks_move_task.py` untouched.
- `PWHEADLESS=1 uv run pytest tests/coordination/test_surface_resolver_coord_empty_warning.py tests/coordination/test_surface_resolver_solo_coord_primary.py -q` green; `ruff` + `mypy` clean.

## Risks & Reviewer Guidance

- **Risk (highest)**: muting the READ warning while the WRITE still targets coord would MASK the split-brain (reads never see writes) — reviewer verifies T030 proves same-path, not just "no warning".
- **Risk**: a `pr_bound`-sniffing branch re-derives topology (2nd authority) — reviewer rejects it; the fix uses the resolver's existing coord-state/lanes signals.
- **Risk**: over-broadening → a genuine split-brain stops warning — reviewer verifies T031.
