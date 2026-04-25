# Tasks: Runtime Extraction Remediation

**Mission**: `runtime-extraction-remediation-01KPX9DT`
**Mission ID**: `01KPX9DTTAADZW59PV51PQN658`
**Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
**Generated**: 2026-04-23

---

## Overview

Fixes the two blocking findings from the post-merge review of mission #95 (`runtime-mission-execution-extraction-01KPDYGW`) and one medium-risk gap, enabling the runtime extraction branch to merge to `main`.

- **WP01** (CRITICAL): Register `src/runtime` in `pyproject.toml` — the package is currently not importable in installed environments
- **WP02** (HIGH): Revert 6 upgrade migration files from `runtime.*` paths to `specify_cli.runtime.*` shim paths — they cause `MigrationDiscoveryError` in installed environments
- **WP03** (MEDIUM): Migrate 4 residual source callers from shim paths to canonical `runtime.*` paths — missed by mission #95 WP09

**Total**: 9 subtasks across 3 WPs. WP01 and WP02 are independent and can run in parallel. WP03 depends on WP01.

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add `"src/runtime"` to `packages` list in `pyproject.toml` | WP01 | No | [D] |
| T002 | Verify `from runtime import PresentationSink` succeeds in installed environment | WP01 | No | [D] |
| T003 | Run full test suite; confirm zero new failures | WP01 | No | [D] |
| T004 | Apply 7 import reversions across 6 migration files (see plan.md table) | WP02 | No | [D] |
| T005 | Run `spec-kitty upgrade` / `pytest tests/upgrade/`; confirm no `MigrationDiscoveryError` | WP02 | No | [D] |
| T006 | `rg` scan confirms zero `runtime.*` imports remain in `src/specify_cli/upgrade/` | WP02 | No | [D] |
| T007 | Apply 5 import migrations across 4 residual source callers (see plan.md table) | WP03 | No | [D] |
| T008 | `rg` scan confirms only shim directories retain `specify_cli.runtime.*` imports in `src/` | WP03 | No | [D] |
| T009 | Run full test suite + `spec-kitty next --help` smoke test | WP03 | No | [D] |

---

## Work Packages

---

### WP01 — Register `src/runtime` in `pyproject.toml`

**Priority**: Critical (blocking — fixes DRIFT-1 from post-merge review)
**Estimated prompt size**: ~220 lines
**Profile**: `python-pedro`
**Dependencies**: None

**Goal**: Add `"src/runtime"` to `pyproject.toml`'s `packages` list so the runtime package is discoverable by hatchling in all install modes. Verify the import works and the test suite is unaffected.

**Subtasks**:
- [x] T001 Add `"src/runtime"` to `packages` list in `pyproject.toml` (WP01)
- [x] T002 Verify `from runtime import PresentationSink` succeeds in installed environment (WP01)
- [x] T003 Run full test suite; confirm zero new failures (WP01)

**Implementation sketch**:
1. Open `pyproject.toml`, find the `packages` list in `[tool.hatch.build.targets.wheel]`, add `"src/runtime"` in the same format as existing entries
2. Verify with `python -c "from runtime import PresentationSink, StepContractExecutor, ProfileInvocationExecutor; print('OK')"`
3. Run `pytest tests/ --ignore=tests/auth -q` and verify count ≥ pre-WP baseline

**Risks**: `pyproject.toml` format must exactly match existing entries. Do NOT touch the `version` field (C-001).

**Prompt file**: `tasks/WP01-register-runtime-package.md`

---

### WP02 — Revert upgrade migration imports to shim paths

**Priority**: High (blocking — fixes DRIFT-2 from post-merge review)
**Estimated prompt size**: ~250 lines
**Profile**: `python-pedro`
**Dependencies**: None (independent of WP01)

**Goal**: Revert 7 import lines across 6 migration files from `runtime.*` canonical paths back to `specify_cli.runtime.*` shim paths. Migration modules are version-pinned and must remain importable in environments where `runtime` is not yet on `sys.path`.

**Subtasks**:
- [x] T004 Apply 7 import reversions across 6 migration files (WP02)
- [x] T005 Run `spec-kitty upgrade` and/or `pytest tests/upgrade/`; confirm no `MigrationDiscoveryError` (WP02)
- [x] T006 `rg` scan confirms zero `runtime.*` imports in `src/specify_cli/upgrade/` (WP02)

**Implementation sketch**:
1. Apply each reversion from the mapping table in `plan.md` — pure string replacements, no logic changes
2. Run `pytest tests/upgrade/ -q` to confirm
3. Run `rg "from runtime\." src/specify_cli/upgrade/` — expected: zero matches

**Risks**: Only change the import lines listed in the plan table. Any other change to a migration file risks corrupting version-pinned behaviour.

**Prompt file**: `tasks/WP02-revert-migration-imports.md`

---

### WP03 — Migrate 4 residual source callers to canonical paths

**Priority**: Medium (non-blocking but eliminates DeprecationWarning noise and closes the occurrence-map gap from mission #95)
**Estimated prompt size**: ~240 lines
**Profile**: `python-pedro`
**Dependencies**: WP01 (canonical paths safe only after `src/runtime` is registered)

**Goal**: Migrate 5 import lines across 4 source files from `specify_cli.runtime.*` shim paths to `runtime.*` canonical paths. Three of the 5 imports are lazy (inside function bodies) — read each file carefully before editing.

**Subtasks**:
- [x] T007 Apply 5 import migrations across 4 residual source callers (WP03)
- [x] T008 `rg` scan confirms only shim directories retain `specify_cli.runtime.*` in `src/` (WP03)
- [x] T009 Run full test suite + `spec-kitty next --help` smoke test (WP03)

**Implementation sketch**:
1. Apply each migration from the mapping table in `plan.md`
2. Run `rg "from specify_cli\.(next|runtime)" src/ -l` — expected: only files under `src/specify_cli/next/` and `src/specify_cli/runtime/`
3. Run `pytest tests/ --ignore=tests/auth -q` and `spec-kitty next --help`

**Risks**: Three of the 5 imports are lazy (inside function bodies). Read each file before editing to find the exact location.

**Prompt file**: `tasks/WP03-migrate-residual-callers.md`

---

## Dependency Graph

```
WP01 (pyproject.toml fix) ──────────────────────────────────► WP03 (residual callers)
WP02 (migration revert)   ── logically independent ───────────────────────────────────
```

**Lane note**: WP01 and WP02 are logically independent but share lane-a in the lane system. `spec-kitty implement WP02` will not activate until WP01 is committed to the lane worktree. WP02 does NOT need to wait for WP01 to be approved — it can proceed as soon as WP01's commit lands.

## Success Criteria Summary

| SC | Spec criterion | WP | Gate |
|---|---|---|---|
| SC-1 | `from runtime import PresentationSink` works in non-editable install | WP01 | T002 | [D] |
| SC-2 | `spec-kitty upgrade` without `MigrationDiscoveryError` | WP02 | T005 | [D] |
| SC-3 | Test suite stable (zero new failures) | WP01+WP03 | T003+T009 |
| SC-4 | No residual shim-path callers outside shim dirs | WP03 | T008 | [D] |
| SC-5 | DRIFT-1 and DRIFT-2 cleared | WP01+WP02 | SC-1+SC-2 |
