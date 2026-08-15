---
work_package_id: WP05
title: Narrow the drift gates to structural invariants + canonical snapshot
dependencies:
- WP02
requirement_refs:
- FR-012
planning_base_branch: mission/modular-per-package-ci
merge_target_branch: mission/modular-per-package-ci
branch_strategy: Planning artifacts for this mission were generated on mission/modular-per-package-ci. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/modular-per-package-ci unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
phase: Phase 3 - Gate reshape
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- tests/specify_cli/regression/test_twelve_agent_parity.py
- tests/specify_cli/skills/test_command_renderer.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 – Narrow the drift gates

**Implements**: FR-012; SC-005. IC-05. **Depends on WP02** (regen proven equivalent first).

## Goal

Replace the 144+24 byte-grid assertions with **structural invariants + one canonical snapshot** per suite, so a
one-line source edit stops fanning out to ~14 fixture failures. The gate tests already carry maintainer TODOs
proposing exactly this (`test_twelve_agent_parity.py:26-37`, `test_command_renderer.py:19-30`).

## Scope

- `test_twelve_agent_parity.py`: keep structural invariants (agent count == 12, per-agent file count ==
  `len(CANONICAL_COMMANDS)`, arg-placeholder presence, no orphan baseline dirs) + ONE canonical rendered
  command snapshot (e.g. `specify` for one representative agent). Drop the full per-(agent,command) byte grid.
- `test_command_renderer.py`: keep the path/render invariants + ONE canonical `SKILL.md` snapshot; drop the full
  per-(agent,command) byte grid.
- Remove the now-unreferenced fixtures ONLY as part of the same change, or keep a single canonical fixture per
  suite. Coordinate file removal with WP06 re-homing (do not orphan a fixture a marker oracle still expects).
- Preserve real drift-detection: a genuinely wrong render must still fail the canonical snapshot + invariants.

## ATDD / red-first (C-008)

- **T001 (RED first)**: a test that injects a deliberately-wrong render and asserts the narrowed gate still
  catches it (proves narrowing didn't lose coverage). RED if the narrowed gate would pass a bad render.
- **T002**: churn-reduction assertion — a one-line source-prompt edit touches ≤ 1 canonical snapshot (SC-005).

## Validation surface (targeted)

```bash
PWHEADLESS=1 pytest tests/specify_cli/regression/test_twelve_agent_parity.py tests/specify_cli/skills/test_command_renderer.py -q
```

## Acceptance (SC-005)

- After narrowing, a one-line source edit requires regenerating ≤ 1 canonical snapshot instead of ~14 files; no
  drift-detection coverage lost.
