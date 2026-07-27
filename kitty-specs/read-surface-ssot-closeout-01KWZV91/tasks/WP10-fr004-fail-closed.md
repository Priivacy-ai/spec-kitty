---
work_package_id: WP10
title: FR-004 fail-closed fix (orchestrator_api/commands.py)
dependencies: []
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2575049"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/orchestrator_api/
create_intent:
- tests/specify_cli/orchestrator_api/test_commands_fail_closed.py
execution_mode: code_change
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/orchestrator_api/test_commands_fail_closed.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-004, C-005), `plan.md`. **Append to `traces/*.md`.**

## Objective

Fix the residual fail-closed fallback at `orchestrator_api/commands.py` (~@1452): an
`ActionContextError` must raise/propagate a **structured error**, never silently fall back to
`CommitTarget(ref=current_branch)`. Red-first (C-005).

## Context

- This file is **FR-004-only** — NOT a Thread-B collision (its `json.loads` @~1343 parses
  `--evidence-json`, unrelated to meta.json; do not route it).
- The offending construct: `except ActionContextError:` → `return ..., CommitTarget(ref=current_branch)`
  (~@1439/@1452). A resolver failure must not degrade to the current branch (a shadow write path).

## Subtasks

### T032 — Red-first
Add `tests/specify_cli/orchestrator_api/test_commands_fail_closed.py`: force an `ActionContextError`
and assert (currently RED) that a structured error propagates rather than a
`CommitTarget(ref=current_branch)` fallback. Prove red pre-fix.

### T033 — Fail-closed
Replace the fallback with a structured raise (reuse the existing `PlacementResolutionRequired` /
`core.errors` structured-error surface — do NOT invent a new one). No `allow_missing`-style silent
degrade. ruff/mypy clean; complexity ≤15.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP10 --agent <name>`.

## Definition of Done
- [ ] Red-first proven; `ActionContextError` now raises a structured error.
- [ ] No `CommitTarget(ref=current_branch)` fallback remains; @~1343 evidence-json parse untouched.
- [ ] ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Confirm the fallback is gone and replaced with a structured raise (fail-closed). Verify the red-first
test. Confirm the evidence-json `json.loads` was NOT touched (not a meta read).

## Activity Log

- 2026-07-08T07:31:24Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Assigned agent via action command
- 2026-07-08T07:46:19Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Ready: red-first fail-closed, structured raise, ruff/mypy clean
- 2026-07-08T07:47:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=2575049 – Started review via action command
- 2026-07-08T07:58:17Z – user – shell_pid=2575049 – Review passed (renata, opus): FR-004 fail-closed via PlacementResolutionRequired, red-first 3 tests RED->green, scope-clean, 22 tests green, ruff/mypy clean. Stale checkout-grammar ratchet seed correctly removed.
