---
work_package_id: WP03
title: LC-6 workspace-context tombstone on merge/cancel
dependencies: []
requirement_refs:
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: fix/session-reaper-and-tmp-leak-hygiene
merge_target_branch: fix/session-reaper-and-tmp-leak-hygiene
branch_strategy: Planning artifacts for this mission were generated on fix/session-reaper-and-tmp-leak-hygiene. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/session-reaper-and-tmp-leak-hygiene unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
agent: "claude"
shell_pid: "649917"
history:
- 'Created by planner for #1842 tasks phase'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/test_workspace_context_tombstone.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/merge/executor.py
- src/specify_cli/status/emit.py
- src/specify_cli/coordination/status_transition.py
- .kittify/workspaces/059-*.json
- .kittify/workspaces/060-*.json
- tests/specify_cli/test_workspace_context_tombstone.py
role: implementer
tags: []
task_type: implement
---

# WP03 – LC-6 workspace-context tombstone on merge/cancel

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-005, C-004) + `plan.md` (IC-03) + `research.md` (LC-6 row).

## Objective
Tombstone `.kittify/workspaces/<slug>-*.json` when a mission completes merge or is cancelled, and remove the 14 committed orphans (merged 059/060). **Add only the tombstone — preserve all other merge/cancel semantics (C-004).**

## Context (post-spec/plan squad, verified)
- Writers of `.kittify/workspaces/*.json`: `workspace/context.py:305 save_context`, from `lanes/implement_support.py:127,167` AND `lanes/recovery.py:732`. (NOT `context/resolver.py:270`, which writes the separate `.kittify/runtime/contexts/` MissionContext surface.)
- `cleanup_orphaned_contexts` gates on `worktree_path.exists()` → **no-op on cancel while the worktree lives**. `delete_context(repo_root, workspace_name)` has **zero external callers** today.
- **Cancel emit path (post-tasks squad, verified):** `move-task --to canceled` → `ports.coord.commit_status` → **`emit_status_transition_transactional`** (`coordination/status_transition.py:713`). `tasks_transition_core` is a pure decision core (no emit); `emit.emit_status_transition` fires ONLY on the non-coordination **fallback** (:729). On **coord topology** (this leak's target case — per-lane contexts) it uses `_prepare_event` + `txn.append_event` — so a hook in `emit.py` alone **NEVER fires for a real coord mission**.
- `delete_context(repo_root, workspace_name)` is a **pure `unlink`** (no worktree gate) → **order-independent** (used for both cancel and merge); `cleanup_orphaned_contexts` is the worktree-gated find-path (no-op while the worktree lives) — do NOT use it here.

## Changes
- **T011** — pin the seam: the tombstone must hook **`emit_status_transition_transactional`** (`coordination/status_transition.py`) covering **BOTH** the coord-topology branch (after `_prepare_event`/`append_event`) AND the non-coord fallback (:729) — NOT `emit.py` alone (never fires for a coord mission). Confirm the lane worktree persists through cancel (so it's testable).
- **T012** — **cancel** hook on `emit_status_transition_transactional` (both branches): when the `canceled` transition leaves **all lane WPs terminal** (mirror `status/doctor.py`'s `all(wp.lane in {done, canceled})` — the context is per-lane, cancel is per-WP), map WP→lane `workspace_name` (slug + lane_id) and call targeted `delete_context(repo_root, workspace_name)`.
- **T013** — **merge-completion** hook in `merge/executor.py`: at completion call targeted `delete_context(repo_root, workspace_name)` for the mission's lane workspace_names. Since `delete_context` is a pure unlink, it is **order-independent** — no "after worktree removal" ordering constraint.
- **T014** — remove the 14 committed orphans (`.kittify/workspaces/059-*.json`, `060-*.json`) for the already-merged 059/060.
- **T015** — `tests/specify_cli/test_workspace_context_tombstone.py`: a mission that merges leaves no `.kittify/workspaces/*.json` orphan; a fully-cancelled mission leaves none; the tombstone is a no-op for a still-active mission; merge/cancel behavior otherwise unchanged. **The cancel test MUST use a coord-topology mission (coordination_branch set)** — a flat/fallback mission routes through the different `emit.emit_status_transition` path and would give a false green.

## Red-first / DoD
- [ ] Cancel hook on `emit_status_transition_transactional` (coord + fallback branches) fires for a **coord-topology** mission (proven: without it, a cancelled coord mission leaves an orphan → test reds); uses targeted `delete_context`.
- [ ] Merge hook uses targeted `delete_context` (order-independent — no worktree-removal ordering); a merged mission leaves no orphan.
- [ ] The 14 committed 059/060 orphans removed; `git ls-files .kittify/workspaces/ | wc -l` drops by 14.
- [ ] `PWHEADLESS=1 uv run pytest tests/specify_cli/test_workspace_context_tombstone.py tests/specify_cli/merge/ -q` green (scope as needed); merge/cancel semantics unchanged.
- [ ] `ruff` + `mypy --strict` clean; no new suppressions.

## Commit
`git add -A && git commit -m "fix(#1842): tombstone workspace-context JSON on merge/cancel + remove 059/060 orphans"`

## Reviewer Guidance
Confirm the cancel hook gates on all-lane-terminal (not per-WP) and uses targeted `delete_context` (not the worktree-gated `cleanup_orphaned_contexts`). Confirm the merge hook is ordered AFTER worktree removal. Confirm C-004 (no other merge/cancel behavior changed) — the central `emit_status_transition` hub must not regress other transitions.

## Activity Log

- 2026-07-06T19:16:29Z – claude – shell_pid=649917 – Assigned agent via action command
- 2026-07-06T19:50:49Z – claude – shell_pid=649917 – Moved to for_review
- 2026-07-06T20:02:16Z – user – shell_pid=649917 – Moved to approved
