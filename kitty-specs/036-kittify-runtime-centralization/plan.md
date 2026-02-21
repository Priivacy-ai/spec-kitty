# Implementation Plan: ~/.kittify Runtime Centralization

*Path: kitty-specs/036-kittify-runtime-centralization/plan.md*

**Branch**: `2.x` (backport to `main`) | **Date**: 2026-02-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/036-kittify-runtime-centralization/spec.md`
**Phase**: 1A — Local-First Runtime Convergence Plan

## Summary

Move shared runtime assets (missions, templates, commands, scripts, AGENTS.md) from per-project `.kittify/` directories to a single user-global `~/.kittify/` directory. Implement `ensure_runtime()` with file locking for atomic updates on CLI startup, 4-tier asset resolution with explicit deprecation warnings, `spec-kitty migrate` for project cleanup, `spec-kitty config --show-origin` for debugging, enhanced `spec-kitty doctor` for global health checks, and a streamlined `spec-kitty init` that creates only project-specific files.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, platformdirs (already in pyproject.toml), fcntl (stdlib, Unix), msvcrt (stdlib, Windows)
**Storage**: Filesystem only — `~/.kittify/` (global), `.kittify/` (per-project)
**Testing**: pytest with fixtures for F-Legacy-001..003, F-Pin-001, F-Bootstrap-001; multiprocessing for concurrency tests
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform via platformdirs)
**Project Type**: Single Python package — extends existing `src/specify_cli/` structure
**Performance Goals**: `ensure_runtime()` fast path <100ms; `spec-kitty init` <0.5s
**Constraints**: No new dependencies beyond existing pyproject.toml. No fallback mechanisms. File locking via stdlib only. Branch lockstep between `main` and `2.x`.
**Scale/Scope**: Affects all CLI entry points; must handle N concurrent CLI processes safely

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Python 3.11+ required | PASS | Feature is Python 3.11+ only |
| pytest with 90%+ coverage for new code | PASS | Plan includes unit, integration, and concurrency tests |
| mypy --strict must pass | PASS | All new code will have type annotations |
| Cross-platform: Linux, macOS, Windows 10+ | PASS | `platformdirs` for Windows, `SPEC_KITTY_HOME` override |
| CLI operations < 2 seconds | PASS | `ensure_runtime()` fast path is <100ms; migration is a user-initiated one-time operation |
| No fallback mechanisms | PASS | Resolution raises `FileNotFoundError`; no silent degradation |
| 2.x branch active development | PASS | Primary development on `2.x` with `main` backport |
| spec-kitty-events integration | N/A | Phase 1A has no events dependency; that's Phase 1B/2 |

No constitution violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/036-kittify-runtime-centralization/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 entity design
├── quickstart.md        # Phase 1 developer guide
├── meta.json            # Feature metadata
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```
src/specify_cli/
├── runtime/                     # NEW subpackage
│   ├── __init__.py              # Public API: get_kittify_home, ensure_runtime
│   ├── home.py                  # get_kittify_home() with cross-platform support
│   ├── bootstrap.py             # ensure_runtime() with file locking
│   ├── resolver.py              # 4-tier asset resolution
│   └── merge.py                 # _merge_package_assets() for atomic updates
├── cli/commands/
│   ├── migrate.py               # NEW: spec-kitty migrate command
│   ├── config.py                # MODIFIED: add --show-origin subcommand
│   ├── doctor.py                # MODIFIED: add global runtime health checks
│   └── init.py                  # MODIFIED: create minimal project .kittify/
└── ...

tests/
├── unit/
│   ├── runtime/                 # NEW test subpackage
│   │   ├── test_home.py         # get_kittify_home() cross-platform tests
│   │   ├── test_bootstrap.py    # ensure_runtime() unit tests
│   │   ├── test_resolver.py     # 4-tier resolution tests (G2)
│   │   └── test_merge.py        # _merge_package_assets() tests
│   └── ...
├── integration/
│   ├── test_migrate.py          # Migration tests (G3)
│   ├── test_doctor_global.py    # Doctor global health tests
│   ├── test_init_minimal.py     # Streamlined init tests
│   └── test_config_show_origin.py  # --show-origin tests
├── concurrency/                 # NEW test directory
│   └── test_ensure_runtime_concurrent.py  # Concurrency tests (G5)
└── fixtures/                    # NEW fixture directory
    ├── f_legacy_001/            # Pre-centralization with customized templates
    ├── f_legacy_002/            # Pre-centralization with no customizations
    ├── f_legacy_003/            # Pre-centralization with stale differing template
    ├── f_pin_001/               # Project with runtime.pin_version
    └── f_bootstrap_001/         # Interrupted ensure_runtime() scenario
```

**Structure Decision**: New `runtime/` subpackage within existing `src/specify_cli/` for clean separation. Test fixtures as directory trees in `tests/fixtures/` for deterministic test setup.

## Key Design Decisions

### D1: New `runtime/` Subpackage (not modifying existing modules)

The global runtime logic lives in a new `src/specify_cli/runtime/` subpackage rather than being scattered across existing modules. This provides:

- Clean import boundary: `from specify_cli.runtime import get_kittify_home, ensure_runtime`
- Single responsibility: all global runtime concerns in one place
- Testable in isolation without mocking CLI commands

### D2: File Locking Strategy

Unix: `fcntl.flock(fd, LOCK_EX)` — advisory lock on `~/.kittify/cache/.update.lock`
Windows: `msvcrt.locking(fd, LK_LOCK, 1)` — mandatory lock

Lock acquisition behavior:

- Try non-blocking first (`LOCK_NB`)
- If blocked: wait for exclusive lock (another process is updating)
- After acquiring lock: double-check `version.lock` (another process may have completed)
- Lock released automatically when file descriptor closed (context manager)

### D3: Resolution Integration Point

The existing `Mission.get_command_template()` in `mission.py` and template resolution in `init.py` must be updated to use the new 4-tier resolver. The resolver is a standalone function that can be called from anywhere — it doesn't depend on CLI state.

### D4: Migration Command Architecture

`spec-kitty migrate` uses the existing `MigrationRegistry` pattern but is a separate CLI command (not an auto-migration). It:

1. Scans `.kittify/` for shared asset files
2. Compares each against `~/.kittify/` global version (byte comparison via `filecmp.cmp`)
3. Classifies: identical (remove), customized (move to overrides), project-specific (keep)
4. Applies disposition (unless `--dry-run`)
5. Reports summary

### D5: Init Refactor Scope

The existing `init.py` is ~900 lines. Phase 1A modifies the template copying section only:

- Skip copying missions, templates, commands, scripts, AGENTS.md
- Create only: `.kittify/config.yaml`, `.kittify/metadata.yaml`, `.kittify/memory/constitution.md`
- Agent directory generation still happens (via `generate_agent_assets`)
- The agent asset generation reads from global `~/.kittify/` instead of local `.kittify/`

## Complexity Tracking

No constitution violations to justify. Feature aligns with all architectural principles.
