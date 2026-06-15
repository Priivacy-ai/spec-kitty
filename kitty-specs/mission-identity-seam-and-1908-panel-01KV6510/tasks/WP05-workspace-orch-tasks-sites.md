---
work_package_id: WP05
title: Route workspace/orchestrator/tasks worktree + compose sites
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-005
- FR-009
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
phase: Phase 2 - Route call sites
assignee: ''
agent: claude
shell_pid: '1073121'
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/workspace/
create_intent:
- tests/specify_cli/workspace/test_context_worktree_routing.py
execution_mode: code_change
owned_files:
- src/specify_cli/workspace/context.py
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/workspace/test_context_worktree_routing.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – workspace/orchestrator/tasks routing

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, claude).

---

## Objectives & Success Criteria
Route the remaining worktree-dir name-guesses + the hand-rolled compose in `agent/tasks.py` through
the WP01 seam. Read [spec.md](../spec.md) FR-005/FR-001/FR-003, paula F-1.

**Done when:** byte-identical names; `tasks.py:844` no longer hand-rolls the `endswith(f"-{mid8}")`
dedup (delegates to the seam compose); tests green.

## Context & Constraints
- **Depends on WP01.** TDD-first. Only the 3 named files + the new test. Byte-identical names.
- **CRITICAL byte-identical rule (squad):** worktree f-strings here are `{slug}-{lane}` (no mid8) and
  `{mission}-{wp}` (legacy WP form, :771). Route as `worktree_path(..., mission_id=None, …)` /
  `worktree_dir_name(...)` so WP01's legacy-faithful grammar reproduces them EXACTLY — do NOT add
  `mission_id` where the old f-string lacked it. Watch the **assign-then-join indirection**
  (`workspace_name = f"{slug}-{lane}"` two lines above a `.worktrees / workspace_name`) — route the
  COMPOSE, not just the literal join (WP09's ratchet checks for this). Assert against WP01's golden table.
- `agent/tasks.py:844` = `mission_slug if mission_slug.endswith(f"-{mid8}") else f"{mission_slug}-{mid8}"`
  — this is the #1949 idempotent-compose reinvented inline (the recurrence shape WP09 bans); replace
  with the seam's compose / `mission_dir_name`.
- `agent/tasks.py` also has the `--mission`/`feature` selector code from the #1797 work — leave that
  untouched; only the worktree (:1333) + compose (:844) + mid8-caller sites change.

## Subtasks
### T021 [P] — `workspace/context.py:310/811/847/867` (incl. assign-then-join)
Route the four `.worktrees/...` worktree-dir constructions through `worktree_path(...)`. Note :310/
:811/:867 build a `workspace_name = f"…"` variable before joining — route the compose itself
(`worktree_dir_name`), not merely the final `Path` join, so no name-guess survives indirection.

### T022 [P] — `orchestrator_api/commands.py:475` AND `:771` (squad-added)
Route BOTH worktree-dir constructions through `worktree_path(...)`: `:475`
(`f"{mission_slug}-{lane.lane_id}"`) and the previously-unrouted `:771`
(`f"{mission}-{wp}"`, legacy WP-based form). Use `worktree_dir_name`/`worktree_path` with the same
inputs the old f-string had. ALSO route this file's `mid8_from_slug` value-use (≈:254) to the seam's
`resolve_mid8` (FR-004 in-place-demotion fallout — WP05 owns this file).

### T023 — `agent/tasks.py:1333` (worktree) + `:844` (compose) + mid8 callers
Route the `-lane-a`/worktree construction at :1333 through the seam; replace the inline idempotent
compose at :844 with the seam's `mission_dir_name`/`worktree_dir_name` so the dedup lives only in the
seam. Route this file's `mid8_from_slug` value-uses (≈:819/:840/:3929) to `resolve_mid8`.

### T024 — Tests + gates
Create `tests/specify_cli/workspace/test_context_worktree_routing.py` asserting byte-identical names
(against WP01's golden table) for the routed sites. `ruff`+`mypy`; `PWHEADLESS=1 pytest
tests/specify_cli/workspace/ -q` plus a quick `tests/specify_cli/cli/commands/agent/` run for the
tasks.py change.
- [ ] context.py (incl. indirection) + orchestrator_api :475 AND :771 + tasks.py :1333/:844 routed;
  [ ] tasks.py:844 delegates to seam (no inline endswith dedup); [ ] mid8_from_slug callers in
  orchestrator_api + tasks.py routed to resolve_mid8; [ ] byte-identical names vs golden table;
  [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.

## Definition of Done
All sites routed; inline compose removed; names unchanged; tests green.

## Reviewer Guidance
Confirm no worktree name-guess or inline mid8-dedup remains in these 3 files; the #1797 selector
code in tasks.py is untouched; names byte-identical.
