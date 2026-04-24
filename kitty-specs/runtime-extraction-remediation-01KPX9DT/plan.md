# Implementation Plan: Runtime Extraction Remediation

**Branch contract**: planning branch `kitty/mission-runtime-mission-execution-extraction-01KPDYGW` → merge target `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
**Date**: 2026-04-23
**Spec**: [./spec.md](./spec.md)
**Mission ID**: `01KPX9DTTAADZW59PV51PQN658` · **mid8**: `01KPX9DT`
**Trackers**: [#612 — Extract runtime/mission execution](https://github.com/Priivacy-ai/spec-kitty/issues/612)
**Unblocks**: `runtime-mission-execution-extraction-01KPDYGW` merge to `main`
**Parent review**: [`docs/development/mission-095-post-merge-review.md`](../../docs/development/mission-095-post-merge-review.md)

---

## Summary

Three small work packages fix two blocking findings and one medium-risk gap identified by the post-merge review of mission #95. All changes are minimal and surgical — no new abstractions, no semantic behaviour changes.

**WP01**: Register `src/runtime` in `pyproject.toml` and verify the package is importable in non-editable installs. One-line change plus test verification.

**WP02**: Revert 6 upgrade migration files from `runtime.*` canonical paths back to `specify_cli.runtime.*` shim paths. Migrations are version-pinned; they must remain importable in any environment, including those where `runtime` is not yet on `sys.path`. After this WP, `spec-kitty upgrade` works without `MigrationDiscoveryError`.

**WP03**: Migrate 4 residual source callers from `specify_cli.runtime.*` shim paths to `runtime.*` canonical paths. These files were missed by mission #95's WP09. They are safe to migrate once WP01 registers the package.

**Sequencing**: WP01 and WP02 are independent and can run in parallel. WP03 depends on WP01.

---

## Technical Context

**Language/Version**: Python 3.11+ (existing requirement)
**Primary Dependencies**: hatchling (build backend), pytest (test runner), rg/ripgrep (verification)
**Storage**: Filesystem only — `pyproject.toml` and Python source files
**Testing**: pytest (existing test suite); `rg` scan for import-path verification
**Target Platform**: Developer machines and CI (Linux, macOS). Non-editable install environment for acceptance test.
**Project Type**: Single project, Python package
**Performance Goals**: N/A — correctness fix only
**Constraints**: C-001 (no version bump), C-002 (migration modules use shim paths), C-003/C-004 (no changes to `src/runtime/` or shim dirs)
**Scale/Scope**: 11 files total — 1 pyproject.toml, 6 migration files (revert), 4 source callers (migrate)

---

## Charter Check

*GATE: Must pass before Phase 0 research.*

| Directive / Policy | Applies? | Compliance plan |
|---|---|---|
| **C-001** (no pyproject version bump) | Yes | Only `packages` list modified; `version` field untouched |
| **C-002** (migration modules use shim paths) | Yes | WP02 explicitly reverts to `specify_cli.runtime.*` shim paths |
| **C-003/C-004** (no changes to `src/runtime/` or shim dirs) | Yes | WP01/WP02/WP03 touch only `pyproject.toml`, migration files, and 4 source callers |
| **NFR-002** (zero new test failures) | Yes | WP01 T003 and WP03 T009 run full test suite as acceptance gate |

**Gate status**: PASS. No charter conflicts.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/runtime-extraction-remediation-01KPX9DT/
├── spec.md          # Mission spec (complete)
├── plan.md          # THIS FILE
├── checklists/
│   └── requirements.md
└── tasks/           # Populated by /spec-kitty.tasks
```

### Source Code (files touched by this mission)

```
pyproject.toml                                    # WP01: add "src/runtime" to packages list

src/specify_cli/upgrade/compat.py                 # WP02: revert runtime.* → specify_cli.runtime.*
src/specify_cli/upgrade/migrations/
├── m_2_0_6_consistency_sweep.py                  # WP02: revert
├── m_2_0_7_fix_stale_overrides.py               # WP02: revert
├── m_2_1_3_restore_prompt_commands.py            # WP02: revert
├── m_2_1_4_enforce_command_file_state.py         # WP02: revert
└── m_3_1_2_globalize_commands.py                 # WP02: revert

src/specify_cli/cli/commands/agent/status.py      # WP03: migrate to canonical
src/specify_cli/migration/rewrite_shims.py        # WP03: migrate to canonical
src/specify_cli/mission.py                        # WP03: migrate to canonical
src/specify_cli/state/doctor.py                   # WP03: migrate to canonical
```

---

## Phase 0: Research — All Unknowns Resolved

No research required. All facts established from the review report and code inspection (2026-04-23).

### Confirmed import mapping — WP02 (revert migration files)

| File | Current `runtime.*` import (broken) | Correct `specify_cli.runtime.*` import |
|---|---|---|
| `compat.py` | `from runtime.discovery.home import get_kittify_home` | `from specify_cli.runtime.home import get_kittify_home` |
| `m_2_0_6_consistency_sweep.py` | `from runtime.orchestration.doctor import check_stale_legacy_assets` | `from specify_cli.runtime.doctor import check_stale_legacy_assets` |
| `m_2_0_7_fix_stale_overrides.py` | `from runtime.discovery.home import get_package_asset_root` | `from specify_cli.runtime.home import get_package_asset_root` |
| `m_2_0_7_fix_stale_overrides.py` | `from runtime.orchestration.migrate import SHARED_ASSET_DIRS, SHARED_ASSET_FILES` | `from specify_cli.runtime.migrate import SHARED_ASSET_DIRS, SHARED_ASSET_FILES` |
| `m_2_1_3_restore_prompt_commands.py` | `from runtime.discovery.home import get_kittify_home, get_package_asset_root` *(lazy)* | `from specify_cli.runtime.home import get_kittify_home, get_package_asset_root` |
| `m_2_1_4_enforce_command_file_state.py` | `from runtime.discovery.home import get_kittify_home, get_package_asset_root` *(lazy)* | `from specify_cli.runtime.home import get_kittify_home, get_package_asset_root` |
| `m_3_1_2_globalize_commands.py` | `from runtime.discovery.home import get_kittify_home` | `from specify_cli.runtime.home import get_kittify_home` |

### Confirmed import mapping — WP03 (migrate residual callers)

| File | Current `specify_cli.runtime.*` import | Correct `runtime.*` canonical import |
|---|---|---|
| `cli/commands/agent/status.py` | `from specify_cli.runtime.doctor import run_global_checks` *(lazy)* | `from runtime.orchestration.doctor import run_global_checks` |
| `migration/rewrite_shims.py` | `from specify_cli.runtime.home import get_kittify_home, get_package_asset_root` *(lazy)* | `from runtime.discovery.home import get_kittify_home, get_package_asset_root` |
| `state/doctor.py` | `from specify_cli.runtime.home import get_kittify_home` *(×2: module-level + lazy)* | `from runtime.discovery.home import get_kittify_home` |
| `mission.py` | `from specify_cli.runtime.resolver import resolve_command` *(lazy)* | `from runtime.discovery.resolver import resolve_command` |

---

## Phase 1: Design

### WP01 — Register `src/runtime` in `pyproject.toml`

**Subtasks**:
- T001: In `pyproject.toml`, locate the `packages` list (in `[tool.hatch.build.targets.wheel]` or `[tool.hatch.build]`) and add `"src/runtime"`. Confirm the entry matches the format of existing entries (`"src/kernel"`, etc.).
- T002: Verify the package is importable: `python -c "from runtime import PresentationSink, StepContractExecutor, ProfileInvocationExecutor; print('OK')"` — must exit 0.
- T003: Run `pytest tests/ --ignore=tests/auth -q` and confirm zero new failures relative to the pre-WP01 baseline.

**Files touched**: `pyproject.toml`  
**Acceptance**: Import command exits 0. Test suite stable.

---

### WP02 — Revert upgrade migration imports to shim paths

**Subtasks**:
- T004: Apply the 7 import reversions from the Phase 0 table to the 6 files. All are direct string replacements — do not change any other code in these files.
- T005: Run `spec-kitty upgrade` (or `pytest tests/upgrade/ -v`) and confirm no `MigrationDiscoveryError`.
- T006: Verify no `runtime.*` imports remain in upgrade modules: `rg "from runtime\." src/specify_cli/upgrade/` — expected: zero matches.

**Files touched**: `src/specify_cli/upgrade/compat.py` + 5 migration files  
**Acceptance**: `MigrationDiscoveryError` gone. `rg` scan clean. Upgrade tests pass.

**Critical constraint**: Only the import lines from the Phase 0 table change. No logic, no comments, no other modifications.

---

### WP03 — Migrate 4 residual source callers to canonical paths

**Dependencies**: WP01 (canonical paths safe only after `src/runtime` is registered)

**Subtasks**:
- T007: Apply the 5 import migrations from the Phase 0 table to the 4 files. Three imports are lazy (inside function bodies) — read each file to locate the exact line before editing.
- T008: Run `rg "from specify_cli\.(next|runtime)" src/ -l` and confirm only shim directories appear (`src/specify_cli/next/` and `src/specify_cli/runtime/`).
- T009: Run `pytest tests/ --ignore=tests/auth -q` and confirm zero new failures. Run `spec-kitty next --help` as a CLI smoke test.

**Files touched**: `src/specify_cli/cli/commands/agent/status.py`, `src/specify_cli/migration/rewrite_shims.py`, `src/specify_cli/state/doctor.py`, `src/specify_cli/mission.py`  
**Acceptance**: `rg` scan returns only shim directories. Test suite stable. CLI smoke test passes.

---

## Dependencies & Sequencing

```
WP01 (pyproject.toml)   ──────────────────────────────────► WP03 (residual callers)
WP02 (migration revert) ── independent, no ordering constraint ──────────────────────
```

WP01 and WP02 are **logically independent** (disjoint owned files, no code overlap). WP03 depends on WP01.

**Lane note** (I1): The lane system assigns WP01 and WP02 to the same lane-a worktree, so `spec-kitty agent action implement WP02` will not start until WP01 is committed to the worktree. WP02 does not need to wait for WP01 to be *reviewed or approved* — once WP01's commit is present in the lane-a worktree, WP02 can proceed immediately.

**Critical path**: WP01 → WP03

---

## Success Criteria Mapping

| Spec Success Criterion | Mapped plan artefacts |
|---|---|
| SC-1 Package importable in non-editable install | WP01 T001 + T002 |
| SC-2 `spec-kitty upgrade` clean, no MigrationDiscoveryError | WP02 T004 + T005 |
| SC-3 Test suite stable, zero new failures | WP01 T003 + WP03 T009 |
| SC-4 No residual shim-path callers | WP03 T007 + T008 |
| SC-5 Blocking findings DRIFT-1 and DRIFT-2 cleared | SC-1 + SC-2 together |

---

## Branch Strategy

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW` (current)
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Implementation**: lane-based worktrees allocated by `spec-kitty implement WP##`
- All changes land in the runtime extraction feature branch, which then merges to `main`

---

## Out-of-Scope Reminders

- No version bump in `pyproject.toml` (C-001)
- No changes to `src/runtime/` package files (C-003)
- No changes to shim files in `src/specify_cli/next/` or `src/specify_cli/runtime/` (C-004)
- RISK-1 (merge tooling hardening) — separate mission
- RISK-3 (regression harness snapshot recapture) — separate mission
