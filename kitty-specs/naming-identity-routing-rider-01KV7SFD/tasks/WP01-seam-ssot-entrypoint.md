---
work_package_id: WP01
title: 'Seam SSOT entrypoint: demote mid8 → _mid8'
dependencies:
- WP03
- WP04
- WP05
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/naming-rider-3-2-1
merge_target_branch: feat/naming-rider-3-2-1
branch_strategy: Planning artifacts for this mission were generated on feat/naming-rider-3-2-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/naming-rider-3-2-1 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1982786"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent:
- tests/specify_cli/lanes/test_branch_naming_ssot_entrypoint.py
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/branch_naming.py
- tests/specify_cli/lanes/test_branch_naming_ssot_entrypoint.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so you work in-character with the right
governance scope and boundaries:

```
/ad-hoc-profile-load python-pedro
```

Then read this mission's `spec.md`, `plan.md` (IC-05), and `data-model.md` for full context.

## Objective

Make the **failover-aware `resolve_mid8` the single public mid8 door**, and demote bare `mid8()` to an
internal `_mid8`. This is the foundation WP — WP03/WP04/WP05 route to this final shape, so it must land
first. **You are the SOLE editor of `src/specify_cli/lanes/branch_naming.py`.**

This realizes the operator decision (FR-010, option b): the 3.2.0 canonical-first / legacy-failover
mechanic becomes the SSOT entrypoint; bare slicing is internal-only.

## Context

`branch_naming.py` today exposes both `mid8(mission_id)` (raises on short/None) and
`resolve_mid8(mission_slug, *, mission_id)` (declines → `""`, "name proposes, authority disposes"). Six
bare `mid8()` callers exist; 3 are internal to this module (lines ~206/257/473), 3 are external (handled
by WP04/WP05, not here). See `research.md` and `data-model.md`.

## Subtasks

### T001 — Rename `mid8` → `_mid8` (private) + update internal callers
- Rename `def mid8(` → `def _mid8(` at `branch_naming.py:122`.
- Update the 3 internal callers in this module: `~:206` (`suffix = f"-{mid8(mission_id)}"`),
  `~:257` (`mission_branch_name`), `~:473` (`lane_branch_name`) → call `_mid8`.
- Do NOT change `_mid8`'s behavior (still raises `ValueError` on short/None). It stays the internal
  primitive.

### T002 — Make `resolve_mid8` the sole public door
- Remove `mid8` from `__all__`; ensure `_mid8` is not exported. `resolve_mid8` (and
  `resolve_transaction_mid8`, `resolve_mission_branch`) are the public surface.
- Confirm the mission-id-only contract: `resolve_mid8("", mission_id=full_id)` must equal the old
  `mid8(full_id)` (empty slug ⇒ no embedded tail ⇒ returns `mission_id[:8]`). Add a test asserting this
  equivalence so WP04's mission-id-only callers can rely on it.

### T003 — Preserve the failover machinery verbatim
- Leave `resolve_transaction_mid8`, `resolve_mission_branch`, `_emit_legacy_failover_warning`, the
  one-shot `_legacy_failover_warned` guard, and `reset_legacy_failover_warning` (test seam) intact.
- Do not weaken the one-shot `DeprecationWarning` semantics.

### T004 — Behavioral tests (function over form)
Create `tests/specify_cli/lanes/test_branch_naming_ssot_entrypoint.py`:
- `resolve_mid8` declines (`""`) with no `mission_id`; returns `mission_id[:8]` with one; declared
  identity governs over a divergent slug tail (pin existing behavior — byte-parity).
- `resolve_mid8("", mission_id=full)` == `full[:8]` (the mission-id-only equivalence).
- `_mid8` raises on short/None (internal contract).
- The one-shot legacy-failover warning fires once; `reset_legacy_failover_warning` re-arms it.
- Composed names (`mission_branch_name`, `worktree_dir_name`, `lane_branch_name`) are byte-identical to
  current output for representative slugs (with/without embedded mid8, legacy NNN-).

## ⚠️ Post-tasks remediation (binding — see tasks-review/POST-TASKS-SYNTHESIS.md)

- **This WP now lands LAST** (depends on WP03/WP04/WP05). They migrate every *external* `mid8` caller to
  `resolve_mid8` first, so demoting `mid8`→`_mid8` + de-exporting is safe (no cross-lane ImportError).
- **DoD gate (prevents the F-1 build-break):** before de-exporting `mid8`, run
  `git grep -nE "import[^#]*\bmid8\b|branch_naming\.mid8\b" -- src/ | rg -v "_mid8|resolve_mid8|mid8_from_slug"`
  and confirm **zero external importers of the public `mid8` remain**. If any remain, STOP — the owning
  WP must route it first.
- **Byte-parity (anti-gaming):** composed-name tests assert against **literals captured from HEAD before
  any edit** (hard-coded RHS), never `resolve_mid8(x) == resolve_mid8(x)`.

## Branch Strategy
Planning/base branch: `feat/naming-rider-3-2-1`. Final merge target: `feat/naming-rider-3-2-1`. The
execution worktree for this WP is allocated from `lanes.json` (computed by finalize-tasks).

## Definition of Done
- [ ] `mid8` is private (`_mid8`); not in `__all__`; 3 internal callers updated.
- [ ] `resolve_mid8` is the only public mid8 door; mission-id-only equivalence holds + tested.
- [ ] Failover machinery + one-shot warning + reset seam preserved.
- [ ] Behavioral tests green; composed names byte-identical (NFR-001).
- [ ] `ruff` + `mypy` clean on the diff; complexity ≤ 15; no suppressions.

## Risks / reviewer guidance
- **Reviewer (reviewer-renata):** confirm no public `mid8` remains importable; confirm byte-parity tests
  actually compare composed output (not just the slice); confirm the one-shot warning + reset seam intact.
- The whole mission depends on this shape — be conservative; this is a rename + visibility change, not a
  behavior change.

## Activity Log

- 2026-06-16T12:44:41Z – claude:opus:python-pedro:implementer – shell_pid=1948414 – Assigned agent via action command
- 2026-06-16T13:01:54Z – claude:opus:python-pedro:implementer – shell_pid=1948414 – mid8 demoted to _mid8; resolve_mid8 sole public door; 3 internal callers updated (lines 213/264/480). DoD gate GREEN: zero external importers of public mid8 across src/ AND tests/ (AST-verified). Scope-review missed ONE importer -- coordination/status_transition.py (in no WP owned_files): its 'mid8 = _seam_mid8(mission_id)' pre-derivation was redundant (resolve_transaction_mid8 cascade already does mission_id[:8]; proven byte-equal) so DELETED -- this was the F-1 build-breaker the LANDS-LAST ordering exists to prevent. Also migrated 4 test modules (test_branch_naming_human_slug, test_2000_compose_routing, test_colliding_mission_flow, tests/tasks/conftest) mid8->_mid8 (golden-value helper usage). Failover machinery + one-shot DeprecationWarning + reset_legacy_failover_warning seam intact verbatim. Byte-parity tests use HEAD-captured literals (anti-gaming). Rebased onto feat/naming-rider-3-2-1 (plan.md add/add resolved to integration version). 298 affected-suite tests + 784-module import smoke green; ruff+mypy+C901 clean on diff (no NEW errors; pre-existing status_transition no-any-return x6 + branch_naming StructuredError-Any artifacts confirmed identical on base); no suppressions.
- 2026-06-16T13:03:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=1982786 – Started review via action command
- 2026-06-16T13:06:21Z – user – shell_pid=1982786 – Review passed: mid8 demoted to _mid8 (sole public door resolve_mid8); 3 internal callers + failover machinery intact; AST scan confirms ZERO external public-mid8 importers (incl. the missed multi-line coordination/status_transition.py importer, routed byte-equal via resolve_transaction_mid8, no #1900 scope creep); HEAD-literal byte-parity tests; ruff+mypy clean (pre-existing only).
