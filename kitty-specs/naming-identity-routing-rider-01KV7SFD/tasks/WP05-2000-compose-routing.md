---
work_package_id: WP05
title: '#2000 compose-routing via dir-name seam'
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: feat/naming-rider-3-2-1
merge_target_branch: feat/naming-rider-3-2-1
branch_strategy: Planning artifacts for this mission were generated on feat/naming-rider-3-2-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/naming-rider-3-2-1 unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1901873"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent:
- tests/specify_cli/core/test_2000_compose_routing.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/mission_creation.py
- src/specify_cli/core/worktree.py
- tests/specify_cli/core/test_2000_compose_routing.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read `spec.md` (FR-005), `plan.md` (IC-03), and `scope-review/priti-ticket-focus.md` (#2000's real
file list).

## Objective

Route the two hand-rolled **compose** sites (#2000) through the canonical `mission_dir_name` /
`worktree_dir_name` seam functions. The defect is the *compose* (these already call mid8); routing through
the seam removes 2 of the bare `mid8`/`_mid8` callers entirely. Depends on WP01.

## Context

Per `scope-review/priti-ticket-focus.md`, #2000's real sites are:
- `core/mission_creation.py:321` — `mission_slug_formatted = f"{human_slug}-{_mid8(mission_id)}"`
- `core/worktree.py:367` / `:370` — `branch_name = f"{human_slug}-{_mid8(mission_id)}"` (+ the worktree
  dir compose nearby)

These are exactly the `<human>-<mid8>` grammar that `mission_dir_name` / `worktree_dir_name` already
compose canonically. Routing eliminates the inline f-string + the bare `_mid8` call.

## Subtasks

### T017 — Byte-parity tests FIRST
Create `tests/specify_cli/core/test_2000_compose_routing.py` pinning the current composed dir/branch
names for representative slugs (with/without embedded mid8, legacy NNN-). Must pass before & after.

### T015 — `core/mission_creation.py:321`
Replace the inline `f"{human_slug}-{_mid8(mission_id)}"` with the canonical `mission_dir_name(...)` seam
call. Confirm byte-identical output.

### T016 — `core/worktree.py:367/370`
Replace the inline composes with `worktree_dir_name(...)` (and the branch compose via the appropriate
seam function). Removes the 2 bare callers. Confirm byte-identical output.

## ⚠️ Post-tasks remediation (binding — see tasks-review/POST-TASKS-SYNTHESIS.md)

- **Lands BEFORE WP01.** Use the already-public seam functions; do not reference `_mid8`.
- **The mid8 derivation MOVES, it is not "removed":** `mission_dir_name(slug, *, mid8: str)` /
  `worktree_dir_name(...)` take a mid8 **string**. So `mission_creation.py` still derives the mid8 — via
  `resolve_mid8("", mission_id=…)` — and passes it to `mission_dir_name`. The win is that the
  hand-rolled `f"{human_slug}-{…}"` *compose* is replaced by the canonical seam function; the derivation
  is routed through `resolve_mid8`. Update the DoD: "the inline f-string compose is gone; the mid8 comes
  from `resolve_mid8`."
- **Byte-parity (anti-gaming):** the T017 tests assert the composed dir/branch names against **frozen
  literals captured from HEAD before any edit**.

## Branch Strategy
Base/merge target: `feat/naming-rider-3-2-1`. Worktree from `lanes.json`.

## Definition of Done
- [ ] Both composes routed through the seam; no inline `<human>-<mid8>` f-string or bare `_mid8` remains
      in these files.
- [ ] Composed dir/branch names byte-identical (NFR-001); byte-parity tests green.
- [ ] `ruff`/`mypy` clean on diff; complexity ≤ 15; no suppressions.

## Risks / reviewer guidance
- **Reviewer:** these are worktree/branch CREATE paths — a byte-parity miss here would create
  mis-named worktrees/branches. Verify the seam produces the exact same name the inline compose did,
  including the NNN-strip / embedded-mid8 dedup behavior.
- Do NOT touch `branch_naming.py` (WP01 owns it) or the ratchet test (WP02 owns it).

## Activity Log

- 2026-06-16T12:21:43Z – claude:sonnet:python-pedro:implementer – shell_pid=1871119 – Assigned agent via action command
- 2026-06-16T12:27:38Z – claude:sonnet:python-pedro:implementer – shell_pid=1871119 – Routed mission_creation/worktree composes through the seam; byte-parity frozen-literal tests green; ruff+mypy clean.
- 2026-06-16T12:28:26Z – claude:opus:reviewer-renata:reviewer – shell_pid=1901873 – Started review via action command
- 2026-06-16T12:31:58Z – user – shell_pid=1901873 – Review passed: #2000 composes routed via mission_dir_name; byte-parity tests use HEAD-frozen literals + cross-check all slug shapes (plain/embedded-mid8/legacy NNN-); scope clean (only 3 owned files); branch_naming.py + ratchet test untouched; no _mid8/bare mid8 callers remain; ruff+mypy clean.
