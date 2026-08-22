---
work_package_id: WP01
title: 'Retire dead ExecutionMode enum #2 (governance-gate)'
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: rc3-execution-mode-consolidation-01M0GGX1
merge_target_branch: rc3-execution-mode-consolidation-01M0GGX1
branch_strategy: Planning artifacts for this mission were generated on rc3-execution-mode-consolidation-01M0GGX1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-execution-mode-consolidation-01M0GGX1 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-execution-mode-consolidation-01M0GGX1
base_commit: 047dd19f647ba86ea66a275b460d7091096340e2
created_at: '2026-08-21T17:26:21.987869+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history: []
authoritative_surface: src/mission_runtime/
create_intent: []
execution_mode: code_change
owned_files:
- src/mission_runtime/context.py
- src/mission_runtime/__init__.py
- tests/architectural/test_mission_runtime_surface.py
- docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md
tags: []
tracker_refs: []
---

## Objective

Retire the dead `mission_runtime.context.ExecutionMode` enum (enum #2) and its
entire declared surface — module `__all__`, package re-export, architectural-surface
test pin, and the ADR bullet — as a **governance-gate** change. No runtime behavior
changes: the enum has zero member consumers.

## Context

Three classes are named `ExecutionMode`; enum #2 is a dead, mis-named local duplicate
of the external `spec_kitty_events` worktree-vs-direct axis. It pairs `WORKTREE` with
`CODE_CHANGE`, and that `CODE_CHANGE` token collides in meaning with the *live*
ownership enum's `CODE_CHANGE` (which means "this WP changes code"). Removing enum #2
is the first half of eliminating the footgun (WP02 renames the live enum).

Because enum #2 is **surface-declared** (pinned by an architectural test + named in an
ADR), deleting it is a governance-gate action: the test and ADR are updated in this
same WP, not treated as collateral. This is red-first: the surface-test edit goes RED
before the deletion makes it GREEN.

**Verified dead (against `upstream/main` @ `c44b4bcf87`):** no `.WORKTREE` /
`.CODE_CHANGE` member access anywhere in `src/`;
`MissionExecutionContext.execution_mode` is `str | None` (a raw string), not this enum.

WP02 depends on this WP: once enum #2 is gone, WP02's re-drift guard ("no
`class ExecutionMode` under `src/`") turns green purely on WP02's rename.

### Subtask T001: Red-first — unpin the symbol from the surface test

**Purpose**: Make the architectural surface test express the target state (symbol
gone) BEFORE deleting the code, so the deletion is verified red→green.

**Steps**:
1. In `tests/architectural/test_mission_runtime_surface.py`, remove the
   `"ExecutionMode",` entry from the `_PUBLIC_SURFACE` list (around line 53).
2. Run the test — it MUST now FAIL (the actual `mission_runtime.__all__` still
   exports `ExecutionMode`). This is the expected red.

**Files**: `tests/architectural/test_mission_runtime_surface.py` (modify, −1 line)
**Validation**: `pytest tests/architectural/test_mission_runtime_surface.py` is RED
with a surface-mismatch assertion naming `ExecutionMode`.

### Subtask T002: Delete the class from context.py

**Purpose**: Remove the dead enum definition and its module-level export.

**Steps**:
1. Delete the `class ExecutionMode(enum.Enum): ...` block in
   `src/mission_runtime/context.py` (around line 42, incl. its docstring + members).
2. Remove the `"ExecutionMode",` entry from the `__all__` list in the same module
   (around line 359).
3. If the `import enum` becomes unused after deletion, leave it only if other symbols
   in the module still need it (check — `MissionTopology` uses `enum.Enum`, so `import
   enum` stays).

**Files**: `src/mission_runtime/context.py` (modify, remove class + `__all__` entry)
**Validation**: `git grep -n "class ExecutionMode" src/mission_runtime/` returns nothing.

### Subtask T003: Drop the package re-export

**Purpose**: Remove enum #2 from the package public surface.

**Steps**:
1. In `src/mission_runtime/__init__.py`, remove the `ExecutionMode,` import (line ~32).
2. Remove the `"ExecutionMode",` entry from the package `__all__` (line ~82).

**Files**: `src/mission_runtime/__init__.py` (modify, −2 lines)
**Validation**: `python -c "import mission_runtime; assert 'ExecutionMode' not in mission_runtime.__all__"`.

### Subtask T004: Record the retirement in the ADR

**Purpose**: Keep the canonical-surface ADR honest — enum #2 was listed as public API.

**Steps**:
1. In `docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md`:
   - Remove `"ExecutionMode"` from the `__all__` code snippet (line ~76).
   - Remove or amend the `ExecutionMode — the resolution mode ...` bullet (line ~84).
   - Add a short dated addendum (e.g. under a `## Amendments` / `## Update` heading)
     noting that mission `rc3-execution-mode-consolidation-01M0GGX1` (M7, 2026-08-21)
     retired the never-consumed `ExecutionMode` symbol from this surface; the
     worktree-vs-direct axis is owned by the external `spec_kitty_events.status.ExecutionMode`.

**Files**: `docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md` (modify)
**Validation**: `grep -n "ExecutionMode" docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md` shows only the retirement note (no live `__all__`/bullet claims).

### Subtask T005: Verify green + static gates

**Purpose**: Confirm the governance gate is green and nothing regressed.

**Steps**:
1. `pytest tests/architectural/test_mission_runtime_surface.py` → GREEN.
2. `python -c "import mission_runtime"` → no error.
3. `ruff check src/mission_runtime/` and `mypy --strict src/mission_runtime/` → clean.
4. Run any `tests/architectural/` dead-symbol/surface gates that reference the module.

**Files**: none (verification)
**Validation**: all four checks pass.

## Definition of Done

- [ ] `grep -rn "class ExecutionMode" src/mission_runtime/` returns zero.
- [ ] `mission_runtime.__all__` and `context.py __all__` no longer list `ExecutionMode`.
- [ ] `tests/architectural/test_mission_runtime_surface.py` is GREEN with the symbol removed from `_PUBLIC_SURFACE`.
- [ ] ADR-2026-06-07-1 no longer advertises `ExecutionMode` as public API and carries a dated retirement note.
- [ ] `ruff` + `mypy --strict src/mission_runtime/` clean, no new suppressions.

## Risks

- **Governance-gate scope**: forgetting the ADR or surface test leaves the gate red or the doc stale — both are owned by this WP.
- **Unused import**: after deleting the class, double-check `import enum` is still needed (it is — `MissionTopology`).

## Reviewer Guidance

- Confirm red→green: the surface test was RED after T001 and GREEN after T002/T003.
- Confirm the enum was genuinely dead (no member access) — deletion must not change any runtime path.
- Confirm the ADR edit removes the *claim* of public API, not just adds a note.

Implementation command: `spec-kitty agent action implement WP01 --agent <name>`
