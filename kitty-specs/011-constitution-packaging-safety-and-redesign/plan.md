# Implementation Plan: Constitution Packaging Safety and Redesign

**Branch**: `011-constitution-packaging-safety-and-redesign` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/011-constitution-packaging-safety-and-redesign/spec.md`

**Note**: This plan was created by `/spec-kitty.plan` command and validated through interactive discovery.

## Summary

Emergency 0.10.x release to resolve critical packaging safety issues and improve constitution system design. Four parallel goals: (1) Segregate template source code from project instances by moving all template sources from `.kittify/` to `src/specify_cli/`, preventing accidental packaging of development artifacts; (2) Redesign constitution as optional interactive command with phase-based discovery workflow (Technical → Quality → Tribal → Governance) and skip options; (3) Fix Windows dashboard ERR_EMPTY_RESPONSE by refactoring to psutil for cross-platform process management; (4) Repair upgrade migration failures from 0.6.4+ by handling missing files gracefully.

**Critical Architectural Change**: Template sources move from `.kittify/` → `src/specify_cli/` to enable safe dogfooding. This eliminates packaging contamination at root cause.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase requirement)
**Primary Dependencies**:

- Existing: typer, rich, pyyaml, ruamel.yaml, httpx, pydantic
- **NEW**: psutil (cross-platform process/signal management for dashboard)

**Storage**: Filesystem only (templates in src/specify_cli/, user projects in .kittify/)
**Testing**: pytest (existing test suite), manual testing for migrations and packaging
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10/11)
**Project Type**: Single Python package with CLI entry points
**Performance Goals**: Migration execution <10s for typical project, dashboard startup <3s
**Constraints**:

- Backward compatibility for 0.6.4+ projects upgrading
- Zero breaking changes to user workflows
- Package size must not increase significantly

**Scale/Scope**:

- ~50+ files affected (Python code, templates, migrations, packaging config)
- 27 functional requirements across 4 major goals
- 2 parallel implementation tracks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: Constitution file exists but is template-only (not filled in for spec-kitty project). This feature affects the constitution system itself, so standard constitution checks don't apply.

**Governance Note**: This is a platform-critical feature requiring:

- Thorough testing of packaging (wheel inspection)
- Migration path validation (0.6.4 → 0.10.12 in clean environment)
- Cross-platform validation (Windows dashboard testing)
- No shortcuts on safety - this prevents contamination of public PyPI releases

**Constitution System Changes**: Removing mission-specific constitutions entirely, keeping only project-level `.kittify/memory/constitution.md`. This simplifies the architecture and removes confusion.

## Project Structure

### Documentation (this feature)

```
kitty-specs/011-constitution-packaging-safety-and-redesign/
├── plan.md              # This file
├── research.md          # Phase 0: Template relocation strategy, psutil patterns
├── data-model.md        # Phase 1: Migration entities, template structure
├── quickstart.md        # Phase 1: Developer guide for template system changes
├── contracts/           # Phase 1: Not needed (internal refactoring)
└── tasks.md             # Created by /spec-kitty.tasks (NOT this command)
```

### Source Code (repository root)

```
src/specify_cli/
├── templates/           # NEW: Moved from .kittify/templates/
│   ├── command-templates/
│   │   ├── constitution.md  # UPDATED: Phase-based discovery
│   │   ├── plan.md
│   │   ├── specify.md
│   │   └── ...
│   ├── plan-template.md
│   ├── spec-template.md
│   └── task-prompt-template.md
├── missions/            # NEW: Moved from .kittify/missions/
│   ├── software-dev/
│   │   ├── mission.yaml
│   │   ├── templates/
│   │   ├── command-templates/
│   │   └── constitution/  # DELETED: Removed entirely
│   └── research/
│       └── ...
├── scripts/             # NEW: Moved from .kittify/scripts/ (if not already there)
│   ├── bash/
│   └── powershell/
├── template/
│   └── manager.py       # UPDATED: Load from src/specify_cli/* not .kittify/*
├── mission.py           # UPDATED: Remove constitution_dir property
├── manifest.py          # UPDATED: Remove constitution scanning
├── dashboard/
│   └── lifecycle.py     # UPDATED: Replace signal.SIGKILL with psutil
├── upgrade/
│   └── migrations/
│       ├── m_0_7_3_update_scripts.py      # UPDATED: Handle missing templates
│       ├── m_0_10_2_update_slash_commands.py  # UPDATED: Remove .toml files
│       ├── m_0_10_6_workflow_simplification.py  # UPDATED: Copy before validate
│       ├── m_0_10_0_python_only.py        # UPDATED: Safe cleanup
│       └── m_0_10_12_constitution_cleanup.py  # NEW: Remove mission constitutions
└── cli/
    └── commands/
        └── init.py      # UPDATED: Reference for constitution in help text

tests/
├── test_packaging.py    # NEW: Verify wheel contents
├── test_migrations/     # UPDATED: Add 0.6.4 → 0.10.12 path tests
└── ...

.kittify/                # Spec-kitty's OWN project instance (for dogfooding)
├── memory/
│   └── constitution.md  # Can be filled for dogfooding, won't be packaged
├── missions/            # Symlink or copy from src/specify_cli/missions/
└── ...

pyproject.toml           # UPDATED: Remove .kittify/* force-includes (lines 86-89, 94-97, 109-110)
```

**Structure Decision**: Template sources move from `.kittify/` to `src/specify_cli/` to achieve clean separation between:

- **Template source code** (in src/, gets packaged, distributed via PyPI)
- **Project instances** (.kittify/ in any repo, never packaged)

This enables spec-kitty developers to safely run `spec-kitty init` and use all commands for dogfooding without risk of packaging their filled-in artifacts.

## Complexity Tracking

*This feature has no constitution violations - it's a safety and quality improvement.*

| Complexity Area | Justification |
|-----------------|---------------|
| Large scope (50+ files) | Necessary to fix critical safety issue and unblock Windows users |
| Major refactoring (template relocation) | Root cause fix for packaging contamination, prevents future issues |
| Cross-platform testing required | Dashboard must work on Windows, not just POSIX systems |
| Migration compatibility testing | Must not break existing users upgrading from 0.6.4+ |

## Parallel Work Analysis

This feature has 2 independent implementation tracks that can proceed in parallel:

### Dependency Graph

```
Foundation Setup (Sequential)
├── Research psutil patterns
├── Research template relocation strategy
└── Plan data model for migrations

↓

Track 1: Critical Safety (Parallel)          Track 2: UX Improvements (Parallel)
├── Move templates to src/specify_cli/       ├── Redesign constitution command
│   ├── Update manager.py                    │   ├── Phase-based discovery workflow
│   ├── Update pyproject.toml                │   ├── Update command template
│   └── Test packaging                       │   └── Test interactive flow
├── Fix migrations                           ├── Fix Windows dashboard
│   ├── m_0_7_3 graceful handling            │   ├── Add psutil dependency
│   ├── m_0_10_6 copy-before-validate        │   ├── Refactor lifecycle.py
│   ├── m_0_10_2 .toml removal               │   └── Test on Windows
│   ├── m_0_10_0 safe cleanup                └── Update init help text
│   └── m_0_10_12 constitution cleanup
└── Remove mission constitutions
    ├── Delete missions/*/constitution/ dirs
    ├── Remove mission.constitution_dir
    ├── Remove manifest constitution scan
    └── Update tests

↓

Integration & Testing (Sequential)
├── End-to-end packaging test (build wheel, inspect contents)
├── Migration path test (0.6.4 → 0.10.12 in clean VM)
├── Constitution workflow test (minimal + comprehensive)
└── Windows dashboard smoke test
```

### Work Distribution

**Track 1: Critical Safety (Priority P0)**

- **Focus**: Packaging fixes and migration repairs
- **Key files**:
  - `src/specify_cli/template/manager.py` (template loading)
  - `pyproject.toml` (force-includes removal)
  - `src/specify_cli/upgrade/migrations/*.py` (4 migration fixes + 1 new)
  - `src/specify_cli/mission.py` (remove constitution_dir)
  - `src/specify_cli/manifest.py` (remove constitution scanning)
- **No conflicts with Track 2**

**Track 2: UX Improvements (Priority P1)**

- **Focus**: Constitution redesign and Windows dashboard
- **Key files**:
  - `.kittify/templates/command-templates/constitution.md` → `src/specify_cli/templates/command-templates/constitution.md` (after Track 1 moves it)
  - `src/specify_cli/dashboard/lifecycle.py` (psutil refactor)
  - `src/specify_cli/cli/commands/init.py` (help text update)
  - `pyproject.toml` (add psutil dependency)
- **Minimal overlap with Track 1** (both touch pyproject.toml but different sections)

**Sequential Foundation (Must complete first)**:

- Phase 0 research (psutil patterns, template relocation strategy)
- Phase 1 design (data model, migration entities)

**Sequential Integration (Must complete last)**:

- Package build and inspection test
- Full migration path test (0.6.4 → 0.10.12)
- Cross-platform validation

### Coordination Points

**Sync Point 1 (After template relocation)**:

- Track 1 completes template move to `src/specify_cli/`
- Track 2 can then update constitution command template in new location
- Merge Track 1 changes first, then Track 2 rebases

**Sync Point 2 (Before integration testing)**:

- Both tracks complete their implementation
- Integration testing verifies all 4 goals work together
- Package build test ensures nothing was accidentally included

**Conflict Resolution**:

- `pyproject.toml`: Track 1 removes force-includes (lines 86-110), Track 2 adds psutil dependency (line ~20). Different sections, no conflict.
- Templates: Track 1 moves entire directory first, Track 2 updates specific file content after. Sequential, no conflict.
- No other file conflicts identified.

## Risk Mitigation

**Risk 1: Template relocation breaks existing code**

- Mitigation: Comprehensive grep for `.kittify/` references, update all to use package resources
- Test: Build package, run `spec-kitty init` from installed package

**Risk 2: Migration fails on edge cases**

- Mitigation: Test with actual 0.6.4 project, not just mocked migrations
- Test: Create VM with 0.6.4, upgrade to 0.10.12, verify all migrations pass

**Risk 3: Windows dashboard still broken after psutil refactor**

- Mitigation: Test on actual Windows 10/11 system, not just WSL
- Test: Dashboard starts, serves HTML, handles shutdown gracefully

**Risk 4: Packaging still includes wrong files**

- Mitigation: Automated test that extracts wheel and asserts no `.kittify/memory/` or filled constitution
- Test: `unzip -l dist/*.whl | grep -E '(constitution.md|memory/)' | wc -l` should be 0 (except templates)
