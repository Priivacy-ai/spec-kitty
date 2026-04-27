---
work_package_id: WP05
title: Adapters wrapping existing modules
dependencies: []
requirement_refs:
- FR-024
planning_base_branch: main
merge_target_branch: main
branch_strategy: Worktree branch derived from lanes.json by spec-kitty implement; final merge target is main.
subtasks:
- T017
- T018
- T019
- T020
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/compat/_adapters/
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/compat/_adapters/__init__.py
- src/specify_cli/compat/_adapters/version_checker.py
- src/specify_cli/compat/_adapters/gate.py
- src/specify_cli/compat/_adapters/detector.py
- tests/architectural/test_compat_shims.py
priority: P0
tags: []
---

# WP05 — Adapters wrapping existing modules

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP05 --agent <name>` from `lanes.json`.

## Objective

Wrap the three legacy compatibility surfaces (`core.version_checker`, `migration.gate`, `upgrade.detector`) as private adapters under `compat/_adapters/`. The adapters are pure re-exports — they introduce **no new behavior** and **no logic**. The planner (WP06) and CLI surfaces (WP08, WP09) consume the adapters; existing call sites continue to import from the legacy paths and keep working.

The architectural test in this WP enforces the "no logic in adapters" property so future drift is caught at PR time.

## Context

- Spec: C-008 (single authority), FR-024 (planner emits structured plan).
- Plan: §"Engineering Alignment" Q1-A — wrap existing modules as private adapters.
- Data model: [`data-model.md`](../data-model.md) §6 (Migration of existing call sites).
- Existing modules: `src/specify_cli/core/version_checker.py` (260 LOC), `src/specify_cli/migration/gate.py` (70 LOC), `src/specify_cli/upgrade/detector.py` (74 LOC).

## Subtasks

### T017 — `compat/_adapters/version_checker.py`

**Steps**:
1. Create `src/specify_cli/compat/_adapters/__init__.py` (empty).
2. Create `src/specify_cli/compat/_adapters/version_checker.py`:
   - One-line module docstring naming the wrapped module.
   - Import the public symbols from `specify_cli.core.version_checker` and re-export them. Use explicit `from … import X, Y, Z` plus `__all__ = [...]`. No wildcard imports.
   - Add a `# adapter:no-logic` marker comment that the architectural test grep-asserts.

**Files**: `src/specify_cli/compat/_adapters/__init__.py`, `src/specify_cli/compat/_adapters/version_checker.py`.

**Validation**: `from specify_cli.compat._adapters import version_checker; assert version_checker.SOMETHING is core.SOMETHING`.

### T018 — `compat/_adapters/gate.py`

**Steps**:
1. Create `src/specify_cli/compat/_adapters/gate.py`:
   - Re-export `check_schema_version`, `_EXEMPT_COMMANDS` (plus any other public symbol from `specify_cli.migration.gate`).
   - `# adapter:no-logic` marker.
   - Document in the docstring that WP07 will replace `migration.gate` with a thin shim that delegates to `compat.planner`. Until WP07 lands, this adapter exposes today's behavior.

**Files**: `src/specify_cli/compat/_adapters/gate.py`.

**Validation**: re-export round-trip test.

### T019 — `compat/_adapters/detector.py`

**Steps**:
1. Create `src/specify_cli/compat/_adapters/detector.py`:
   - Re-export `UpgradeDetector` (and any other public class/function from `specify_cli.upgrade.detector`).
   - `# adapter:no-logic` marker.

**Files**: `src/specify_cli/compat/_adapters/detector.py`.

**Validation**: round-trip test.

### T020 — Architectural test: shims contain only delegation

**Steps**:
1. `tests/architectural/test_compat_shims.py`:
   - For each adapter file (`compat/_adapters/version_checker.py`, `compat/_adapters/gate.py`, `compat/_adapters/detector.py`):
     - Read the file as text.
     - Assert the `# adapter:no-logic` marker is present.
     - Parse with stdlib `ast`. Walk the module:
       - Allow: module docstring, `from … import …` statements, `__all__ = [...]` assignment, `# adapter:no-logic` comment.
       - Disallow: `def`, `class`, `if`, `for`, `while`, `try`, attribute assignment beyond `__all__`.
     - If anything else appears, fail the test with a clear message naming the offending node and line.
2. The test is the **invariant** that protects future maintainers from quietly putting logic in an adapter and breaking the "single source of truth" property (C-008).

**Files**: `tests/architectural/__init__.py` (if not created by WP04), `tests/architectural/test_compat_shims.py`.

**Validation**: `pytest tests/architectural/test_compat_shims.py -v` green. Add a deliberately-broken adapter file in a test fixture (`tests/architectural/_fixtures/`) and confirm the test fails on it (positive test of the test).

## Definition of Done

- [ ] Three adapter files exist with `# adapter:no-logic` marker.
- [ ] Each adapter re-exports the legacy module's public symbols and nothing else.
- [ ] Architectural test passes for all three adapters.
- [ ] Architectural test would fail for an adapter with stray logic (verified via fixture).
- [ ] `mypy --strict` clean for all three adapters.
- [ ] `ruff check` clean.
- [ ] No legacy module is modified in this WP. (WP07 modifies `migration/gate.py` later.)

## Risks

- Some legacy modules may not declare `__all__`. The adapter explicitly enumerates the symbols it re-exports — read each legacy module and pick the public surface (no leading underscore).
- If the architectural test's AST walker is overly strict and accidentally rejects valid imports (e.g. `from typing import TYPE_CHECKING` blocks), tighten the allow-list rather than loosening the rejection.

## Reviewer Guidance

1. **No logic**: confirm each adapter is just imports + `__all__` + the marker comment. Less than 30 lines each.
2. **Symbol fidelity**: every public symbol in the legacy module is exposed through the adapter; nothing is hidden silently.
3. **Test rigor**: the architectural test rejects a known-bad fixture, not just passes on the real adapters.
4. **Documentation**: each adapter docstring names the wrapped module and references this WP.

## Implementation command

```bash
spec-kitty agent action implement WP05 --agent <name>
```
