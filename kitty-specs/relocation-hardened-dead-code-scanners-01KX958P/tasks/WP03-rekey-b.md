---
work_package_id: WP03
title: WP-REKEY-B — dangling ratchet + body-sensitivity (single-owner 2/2)
dependencies:
- WP02
requirement_refs:
- FR-008
- FR-013
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2531502"
history:
- created at planning (tasks) — re-key B (chain 2/2)
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_dead_symbols.py
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/test_no_dead_symbols.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Read [spec.md](../spec.md) FR-008 +
DoD (b,d,g,j-gate), [plan.md](../plan.md) §IC-REKEY WP-REKEY-B, [research.md](../research.md) D-4.
**SAME OWNER of `test_no_dead_symbols.py` as WP02 — you are chain 2/2, SEQUENTIAL after WP02's
approval. C-003 is honored because you never run concurrently with WP02.**

## Objective
Add the third ratchet direction (tier-specific dangling detector) reconciled with body-sensitivity
to ONE signal, and the remaining bite battery items (b,d,g) + the gate-side DoD-j 0-false-red —
all through the PRODUCTION `_compute_offenders`/stale path.

## Subtasks

### T015 — third dangling-entry ratchet, tier-specific (FR-008)
The existing shrink-only ratchet fires only on "gained a caller"; relocation silently orphans an
entry AND false-reds at the new location. Add a dangling detector:
- **content-tier** entry: `(bare_name, body_hash)` → resolves to ZERO live `__all__` locations → red/prune.
- **module_path-tier** entry: `(bare_name, module_path)` → no live `__all__` decl → red/prune.

### T016 — body-sensitivity ONE-signal reconciliation
Editing a dead symbol's body changes its `body_hash` → the key no longer matches. Reconcile with
T015 so a body edit yields **exactly one** signal (offender-refresh), NOT an ambiguous
offender+prune double-flag. Test this explicitly — it is the subtle correctness point.

### T017 — bite battery (b,d,g) through the production path (FR-013)
(b) a relocated-but-WIRED content-tier symbol stays green [document the dead-relocated false-red
carve-out for the module_path subset]; (d) a wired allow-listed symbol reds the stale ratchet
(body-independent); (g) a dangling entry reds the new ratchet — BOTH tiers; and the body-edit →
one-signal case. All through `_compute_offenders`/stale.

### T018 — gate-side DoD-j 0-false-red (FR-013)
The gate-level 0-false-red for AnnAssign-whitespace + single-alias relocation, through the
production path (the unit-level key-invariance probe lives in WP01's `test_symbol_key.py`; C-007
requires the gate-level proof too — a unit-only (j) is the self-validation loophole).

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json` via
`spec-kitty agent action implement WP03 --agent <you>` (branches from WP02's approved base —
sequential same-owner).

## Definition of Done
- Tier-specific dangling ratchet reds on both tiers; body edit → exactly one signal; bite (b,d,g)
  + gate-side DoD-j through the production path; full `tests/architectural/` 0-failed; ruff+mypy clean.
- `known_modules`/`_record_*_edges`/`_imports_by_target` still BYTE-UNCHANGED.

## Reviewer guidance (reviewer-renata, opus)
Confirm the dangling check is TIER-SPECIFIC (content = body_hash→0; module_path = (name,module)→0)
and that a body edit produces ONE signal, not offender+prune. Confirm (b,d,g,j-gate) run through
`_compute_offenders`/stale (C-007), not a standalone fn.

## Activity Log
- 2026-07-11T20:56:08Z – claude:sonnet:python-pedro:implementer – shell_pid=2459236 – Started implementation via action command
- 2026-07-11T21:22:57Z – claude:sonnet:python-pedro:implementer – shell_pid=2459236 – Ready: tier-specific dangling ratchet (content=body_hash->0, module_path=(name,module)->0); body edit -> ONE signal; bite (b,d,g) through production path; gate-side DoD-j 0-false-red; full arch 0-failed; C-005 byte-unchanged
- 2026-07-11T21:23:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=2531502 – Started review via action command
