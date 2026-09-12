---
work_package_id: WP04
title: Lazy-import ratchet + source-side laundering guard
dependencies:
- WP01
requirement_refs:
- FR-006
- NFR-006
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 2 - Enforcement
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_runtime_charter_doctrine_boundary.py
create_intent:
- tests/architectural/fixtures/doctrine_boundary/
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- tests/architectural/test_runtime_charter_doctrine_boundary.py
- tests/architectural/fixtures/doctrine_boundary/
role: implementer
tags: []
tracker_refs:
- '2986'
wp_code: WP04
---

# Work Package Prompt: WP04 — Lazy-import ratchet

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and apply its initialization, boundaries, directives,
and tactics. State which you applied.

## Objective

Add the sibling architectural guard that closes the in-function/lazy `doctrine.*` reach-through
(invisible to the current module-level ratchet) and the first-party re-export laundering path.
Lands **red-first** with a full baseline seeded at WP01's census; WP05–07 shrink it. Closes the
runtime→doctrine half of #2986 (FR-006, SC-003).

## Context & Constraints

- The current test walks only `tree.body` (module-level). Confirmed 0 module-level vs 70 lazy
  doctrine imports today — the whole reach-through surface is invisible.
- **Use a parent-tracking recursive descent, NOT bare `ast.walk`.** `ast.walk` flattens the tree
  and loses the enclosing-block context needed to (a) skip `if TYPE_CHECKING:` imports and (b)
  distinguish module-level from nested. Track `(depth, under_TYPE_CHECKING)`.
- **The laundering rule is SOURCE-side:** assert no `src/specify_cli/doctrine/*` module lists a
  doctrine-origin symbol in its `__all__`. A consumer-side check is impossible — `from
  specify_cli.doctrine.config import load_pack_registry` (laundered) and `... import
  assert_pack_local_paths_exist` (genuine first-party) are byte-identical syntax.
- Keep the existing module-level ratchet's empty baseline intact (do not fold lazy files into it).

## Subtasks

### T017 — Sibling ratchet (recursive descent)
- Add `test_runtime_has_no_new_lazy_doctrine_imports`. Match absolute `doctrine`/`doctrine.*` with
  `ImportFrom.level == 0`, at any depth, excluding `TYPE_CHECKING` blocks and the enumerated
  management surface (from WP01). Share the file-walk + exempt filter with the existing test.

### T018 — Only-shrink frozenset baseline
- Seed `_LAZY_BASELINE_ALLOWLIST` from WP01's census (the ~29 true-runtime-lazy files). Assert
  two directions: a new violator (not allowlisted) fails; a stale entry (migrated file still
  listed) fails. This is what makes WP05–07 provably shrink it.

### T019 — Source-side laundering guard
- Assert no `src/specify_cli/doctrine/*` module's `__all__` contains a symbol it imported
  `from doctrine…`. Seed a baseline for `config.py` if it still launders at WP04 time (WP05
  closes it, forcing the stale-entry eviction).

### T020 — Fixtures + limits note  [P]
- Add fixtures under `tests/architectural/fixtures/doctrine_boundary/`: a doctrine import inside
  `if TYPE_CHECKING:` (must NOT be flagged) and one inside a nested function (must be flagged).
- Document the disposition of bare `import doctrine` (metadata introspection, `codex.py`),
  aliased imports, and the static-AST blind spot for dynamic imports (`importlib`, 0 today).

## Branch Strategy

Base + merge target `feat/doctrine-public-api-surface`; worktree per lane. Implement via
`spec-kitty agent action implement WP04 --agent <name>` (after WP01).

## Definition of Done

- [ ] Sibling ratchet uses parent-tracking descent; TYPE_CHECKING fixture NOT flagged, nested-fn IS.
- [ ] Only-shrink baseline seeded; both failure directions proven by fixtures.
- [ ] Source-side laundering guard in place; ≤ 3 s runtime (NFR-006).
- [ ] Limits (bare/aliased/dynamic import) documented.

## Risks & Reviewer Guidance

- **Risk**: `ast.walk` shorthand → cannot exclude TYPE_CHECKING or tell module-level from nested.
  Reviewer: confirm a recursive descent with depth tracking, and run the two fixtures.
- **Reviewer**: confirm the laundering rule is source-side, not a hardcoded `resolve_org_roots`
  blocklist (which would miss future laundered symbols).
