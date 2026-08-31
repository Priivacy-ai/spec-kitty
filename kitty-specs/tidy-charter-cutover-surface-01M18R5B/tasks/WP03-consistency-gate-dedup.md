---
work_package_id: WP03
title: 'Simplify: one shared DRG load + fail-closed wrapper for the 3 consistency gates (#3808)'
dependencies: []
requirement_refs:
- FR-004
- FR-005
- NFR-001
planning_base_branch: spec/tidy-charter-cutover-surface
merge_target_branch: spec/tidy-charter-cutover-surface
branch_strategy: Planning artifacts for this mission were generated on spec/tidy-charter-cutover-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/tidy-charter-cutover-surface unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tidy-charter-cutover-surface-01M18R5B
base_commit: 917d2b379810fb9c8686ad32a92132f633f30deb
created_at: '2026-08-30T20:42:48.941862+00:00'
subtasks:
- T008
- T009
- T010
- T011
phase: Phase 1
history: []
authoritative_surface: src/charter/activation/consistency_check.py
create_intent: []
execution_mode: code_change
mission_id: 01M18R5BMJSQBT1ZN68WSR4X6Q
owned_files:
- src/charter/activation/consistency_check.py
- tests/charter/test_consistency_check.py
tags: []
tracker_refs: []
---

# WP03 — Simplify: one shared DRG load + fail-closed wrapper for the 3 consistency gates (#3808)

**Priority**: P2 · **Concern**: IC-03 · **Requirements**: FR-004, FR-005, NFR-001 (behavior-preserving)
**Owned files**: `src/charter/activation/consistency_check.py`, `tests/charter/test_consistency_check.py`
**Dependencies**: none (independent lane)

## Goal
`run_consistency_check` runs three always-on gates that each independently call
`load_validated_graph(repo_root)` (and two also build a `DoctrineService`) — the DRG is
loaded 3× per run — behind three near-identical `try/except → (verification_errors,
suggestions)` shapes. Collapse to **one shared load + one parameterized fail-closed wrapper**,
with **byte-identical verdicts**.

## Context
- Gates: `_check_enforcement_lattice`, `_check_decision_documentation_on_implement`,
  `_check_unreconciled_tensions` (all in `charter/activation/consistency_check.py`).
- NOT a change to what the gates *decide* — dedup + single graph load only (issue #3808 non-goals).
- This module was just relocated by #3807; edit it at its `charter/activation/` home.

## Subtasks
- **T008** — Characterization tests first: in `tests/charter/test_consistency_check.py`, add
  focused tests exercising each gate's **pass and fail arms** directly, capturing current
  verdicts (the before/after parity baseline). Add a spy/count assertion for the DRG load count.
- **T009** — Extract one shared helper: "load graph + build doctrine service once, or raise on
  drift", passed into the three gates so the graph loads **once** per `run_consistency_check`.
- **T010** — Extract one parameterized fail-closed wrapper (message-stem + target-list +
  coherent-fold flag) backing the three gate checks; keep each gate's distinct literals.
- **T011** — Prove parity: the three gates produce byte-identical verdicts on the shipped
  corpus before/after; DRG loaded exactly once. Keep complexity ≤15; `ruff`/`mypy` clean.

## Acceptance (SC-003, NFR-001)
- DRG loaded once (down from 3×), one `DoctrineService` built, shared across the three gates.
- Enforcement-lattice, decision-documentation-on-implement, and unreconciled-tensions verdicts
  are identical before/after on pass and fail arms (0 diff).
- New/changed branches covered by the focused tests (Sonar new-code coverage).
