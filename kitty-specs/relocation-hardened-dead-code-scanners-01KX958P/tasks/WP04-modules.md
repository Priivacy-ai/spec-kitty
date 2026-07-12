---
work_package_id: WP04
title: IC-MODULES — relocation-harden-or-preserve test_no_dead_modules.py
dependencies: []
requirement_refs:
- FR-011
- FR-012
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2086590"
history:
- created at planning (tasks) — modules harden-or-preserve
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_dead_modules.py
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/test_no_dead_modules.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Read [spec.md](../spec.md) FR-011/FR-012,
[plan.md](../plan.md) §IC-MODULES. **Independent of the symbol key — can run parallel with WP01.**

## Objective
Relocation-harden `test_no_dead_modules.py` IF it carries a relocatable anchor; ELSE downgrade to
explicit-preserve (byte-unchanged) and SAY SO — no unmeasured scope-add. Preserve the cross-module
`__all__` deadness, the 4 detectors, test-not-caller semantics, and the bidirectional ratchet.

## Subtasks

### T019 — assess the relocatable anchor
Inspect the module allow-list (CATEGORY_1..7 / the module-path allow-sets). Determine whether any
entry is a *relocatable* anchor (a module whose deadness survives a package-path rename) vs a pure
path-set with no relocation semantics. Record the finding.

### T020 — harden-if-relocatable ELSE downgrade-to-preserve (FR-011)
- **If a relocatable anchor exists**: harden it — a DoD battery item relocates a sanctioned dead
  module's anchor (rename its containing package path where the module stays dead) → gate green with
  0 edits AND a genuinely-dead module at the new path is still caught.
- **If NOT** (pure path-set): downgrade FR-011 to **explicit-preserve** (byte-unchanged, covered by
  FR-012) and document the downgrade in the WP + issue-matrix. Do NOT invent a relocatable anchor.

### T021 — preserve FR-012 (byte-unchanged invariants)
Confirm (and keep byte-unchanged) the cross-module `__all__` deadness detection, the 4
dynamic-dispatch detectors, test-not-caller semantics, and the bidirectional ratchet. Any change
here must be justified; the default is preserve.

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json` via
`spec-kitty agent action implement WP04 --agent <you>`. No dependencies (parallel with WP01).

## Definition of Done
- FR-011 either delivered (relocation battery green + genuinely-dead caught) OR explicitly
  downgraded-to-preserve with a documented rationale; FR-012 invariants preserved; full
  `tests/architectural/` 0-failed; ruff+mypy clean.

## Reviewer guidance (reviewer-renata, opus)
If hardened: confirm the relocation battery reds a genuinely-dead module at the new path. If
downgraded: confirm the rationale is honest (no relocatable anchor actually exists) and FR-012
invariants are byte-unchanged — resist an invented anchor.

## Activity Log
- 2026-07-11T18:54:45Z – claude:sonnet:python-pedro:implementer – shell_pid=2013062 – Assigned agent via action command
- 2026-07-11T19:08:16Z – claude:sonnet:python-pedro:implementer – shell_pid=2013062 – Ready (PRESERVE): no relocatable anchor — _ALLOWLIST pure frozenset[str] exact dotted paths; FR-011→explicit-preserve, FR-012 byte-unchanged; file 2 passed, ruff+mypy clean, full arch green.
- 2026-07-11T19:08:46Z – claude:opus:reviewer-renata:reviewer – shell_pid=2086590 – Started review via action command
- 2026-07-11T19:18:27Z – user – shell_pid=2086590 – Review PASSED (reviewer-renata opus): verified _ALLOWLIST is pure frozenset[str] of exact dotted paths — no relocatable anchor (marker cats 4/5 empty); FR-011 downgrade-to-preserve correct, not lazy; test_no_dead_modules.py 0-diff (blob SHA identical), FR-012 invariants byte-unchanged (4 caller patterns + test-not-caller + bidirectional ratchet); file 2 passed. Matrix schema-drift (Notes->Scope) reconciled.
