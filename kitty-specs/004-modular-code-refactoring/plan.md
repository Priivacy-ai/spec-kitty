# Implementation Plan: Modular Code Refactoring

**Branch**: `004-modular-code-refactoring` | **Date**: 2025-11-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/004-modular-code-refactoring/spec.md`

**Note**: This plan emphasizes parallel agent execution to enable multiple developers to work simultaneously without conflicts.

## Summary

Refactor two monolithic Python files (`__init__.py` with 2,700 lines and `dashboard.py` with 3,030 lines) into a modular architecture with ~21 modules, each under 200 lines. The refactoring uses a hybrid layer-module approach enabling up to 6 agents to work in parallel during peak phases.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, httpx, pyyaml, readchar
**Storage**: File system (no database)
**Testing**: pytest with existing test suite
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows)
**Project Type**: CLI application with embedded web dashboard
**Performance Goals**: Maintain current performance (dashboard startup <1s, command response <500ms)
**Constraints**: Each module must be under 200 lines; imports must work in pip install, local dev, and subprocess contexts
**Scale/Scope**: 5,730 lines to refactor into ~21 modules

## Parallel Work Organization

### Dependency Graph
```
Foundation Layer (Sequential - Day 1)
    ├── core/config.py
    ├── core/utils.py
    └── cli/ui.py
        │
        ├── Wave 1 (Parallel - Days 2-3)
        │   ├── Agent A: Dashboard Infrastructure
        │   │   ├── dashboard/static/*
        │   │   ├── dashboard/templates/*
        │   │   ├── dashboard/scanner.py
        │   │   └── dashboard/diagnostics.py
        │   │
        │   ├── Agent B: Template System
        │   │   ├── template/manager.py
        │   │   ├── template/renderer.py
        │   │   └── template/asset_generator.py
        │   │
        │   └── Agent C: Core Services
        │       ├── core/git_ops.py
        │       ├── core/project_resolver.py
        │       └── core/tool_checker.py
        │
        └── Wave 2 (Parallel - Days 4-5)
            ├── Agent D: Dashboard Handlers
            │   ├── dashboard/handlers/*
            │   ├── dashboard/server.py
            │   └── dashboard/lifecycle.py
            │
            ├── Agent E: CLI Commands
            │   ├── cli/commands/check.py
            │   ├── cli/commands/research.py
            │   ├── cli/commands/accept.py
            │   ├── cli/commands/merge.py
            │   └── cli/commands/verify.py
            │
            └── Agent F: GitHub & Init
                ├── template/github_client.py
                ├── cli/commands/init.py
                └── cli/helpers.py
```

### Agent Coordination Rules
1. **No concurrent edits**: Each agent owns specific files exclusively
2. **Import stubs**: Agents create import statements for not-yet-extracted modules
3. **Interface contracts**: Define function signatures before implementation
4. **Daily sync**: Merge completed work at end of each day

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Since the constitution file is not yet established for this project, we'll follow Python best practices:
- ✅ **Single Responsibility**: Each module has one clear purpose
- ✅ **Testability**: All modules independently testable
- ✅ **No Breaking Changes**: CLI interface remains identical
- ✅ **Documentation**: Each module will have clear docstrings
- ✅ **Import Compatibility**: Works in all execution contexts

## Project Structure

### Documentation (this feature)

```
kitty-specs/[###-feature]/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/
├── __init__.py                    # Main entry point (reduced to ~150 lines)
├── cli/
│   ├── __init__.py
│   ├── ui.py                      # StepTracker, select_with_arrows, multi_select
│   ├── helpers.py                 # Banner, BannerGroup, callbacks
│   └── commands/
│       ├── __init__.py
│       ├── init.py                # Init command implementation
│       ├── check.py               # Dependency checking command
│       ├── research.py            # Research workflow command
│       ├── accept.py              # Feature acceptance command
│       ├── merge.py               # Feature merge command
│       └── verify.py              # Setup verification command
├── core/
│   ├── __init__.py
│   ├── config.py                  # All constants, AI_CHOICES, MISSION_CHOICES, etc.
│   ├── git_ops.py                 # Git operations (is_git_repo, init_git_repo, run_command)
│   ├── tool_checker.py            # Tool verification functions
│   ├── project_resolver.py        # Path resolution and project discovery
│   └── utils.py                   # Shared utility functions
├── template/
│   ├── __init__.py
│   ├── manager.py                 # Template discovery and copying
│   ├── renderer.py                # Template rendering with frontmatter
│   ├── github_client.py           # GitHub API and download operations
│   └── asset_generator.py         # Agent-specific asset generation
├── dashboard/
│   ├── __init__.py                # Public API (ensure_dashboard_running, stop_dashboard)
│   ├── server.py                  # HTTPServer setup and configuration
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseHTTPRequestHandler extensions
│   │   ├── api.py                 # Core API endpoints
│   │   ├── features.py            # Feature-specific endpoints
│   │   └── static.py              # Static file serving
│   ├── scanner.py                 # Feature scanning and metadata
│   ├── diagnostics.py             # Project health diagnostics
│   ├── lifecycle.py               # Dashboard process management
│   ├── templates/
│   │   ├── index.html             # Main dashboard HTML (extracted from string)
│   │   └── components/
│   │       ├── sidebar.html
│   │       └── kanban.html
│   └── static/
│       ├── dashboard.css          # Extracted CSS (1000+ lines)
│       ├── dashboard.js           # Extracted JavaScript
│       └── spec-kitty.png         # Logo asset
└── [existing modules unchanged]
    ├── mission.py
    ├── acceptance.py
    ├── tasks_support.py
    ├── manifest.py
    ├── verify_enhanced.py
    └── gitignore_manager.py

tests/specify_cli/
├── test_cli/
│   ├── test_ui.py
│   ├── test_commands_init.py
│   ├── test_commands_check.py
│   └── ...
├── test_core/
│   ├── test_config.py
│   ├── test_git_ops.py
│   └── ...
├── test_template/
│   ├── test_manager.py
│   ├── test_renderer.py
│   └── ...
└── test_dashboard/
    ├── test_server.py
    ├── test_handlers.py
    └── ...
```

**Structure Decision**: Modular package organization with clear separation between CLI, core utilities, template management, and dashboard subsystems. Each package is self-contained with its own tests.

## Complexity Tracking

*No constitution violations - all practices align with Python best practices and project requirements.*

## Phase 2: Implementation Planning

### Work Package Distribution

Based on the parallel work organization, the implementation will be divided into the following work packages:

#### WP-001: Foundation Layer (Sequential)
- **Owner**: Single developer/agent
- **Duration**: Day 1
- **Deliverables**: core/config.py, core/utils.py, cli/ui.py
- **Dependencies**: None
- **Tests**: Unit tests for each module

#### WP-002: Dashboard Infrastructure (Parallel Wave 1)
- **Owner**: Agent A
- **Duration**: Days 2-3
- **Deliverables**: dashboard/static/*, dashboard/templates/*, dashboard/scanner.py, dashboard/diagnostics.py
- **Dependencies**: Foundation Layer
- **Tests**: Integration tests for scanning and diagnostics

#### WP-003: Template System (Parallel Wave 1)
- **Owner**: Agent B
- **Duration**: Days 2-3
- **Deliverables**: template/manager.py, template/renderer.py, template/asset_generator.py
- **Dependencies**: Foundation Layer
- **Tests**: Unit tests for template operations

#### WP-004: Core Services (Parallel Wave 1)
- **Owner**: Agent C
- **Duration**: Days 2-3
- **Deliverables**: core/git_ops.py, core/project_resolver.py, core/tool_checker.py
- **Dependencies**: Foundation Layer
- **Tests**: Unit tests for each service

#### WP-005: Dashboard Handlers (Parallel Wave 2)
- **Owner**: Agent D
- **Duration**: Days 4-5
- **Deliverables**: dashboard/handlers/*, dashboard/server.py, dashboard/lifecycle.py
- **Dependencies**: Dashboard Infrastructure
- **Tests**: HTTP endpoint tests

#### WP-006: CLI Commands (Parallel Wave 2)
- **Owner**: Agent E
- **Duration**: Days 4-5
- **Deliverables**: cli/commands/* (except init.py)
- **Dependencies**: Foundation Layer, Core Services
- **Tests**: Command integration tests

#### WP-007: GitHub & Init (Parallel Wave 2)
- **Owner**: Agent F
- **Duration**: Days 4-5
- **Deliverables**: template/github_client.py, cli/commands/init.py, cli/helpers.py
- **Dependencies**: Template System
- **Tests**: Mock GitHub API tests, init command tests

#### WP-008: Integration & Cleanup
- **Owner**: 1-2 developers
- **Duration**: Day 6
- **Deliverables**: Updated __init__.py, import fixes, documentation
- **Dependencies**: All previous work packages
- **Tests**: Full regression test suite

### Critical Path

```
Foundation (Day 1) → Wave 1 (Days 2-3) → Wave 2 (Days 4-5) → Integration (Day 6)
```

The critical path is 6 days with proper parallelization. Without parallelization, it would take approximately 15-18 days.

### Risk Mitigation

1. **Import Resolution Issues**: Mitigated by try/except pattern and testing in all contexts
2. **Merge Conflicts**: Mitigated by exclusive file ownership per agent
3. **Behavioral Changes**: Mitigated by comprehensive test coverage
4. **Integration Issues**: Mitigated by daily sync points and integration tests

### Success Metrics

- All modules under 200 lines ✓
- Zero import errors in any context ✓
- All existing tests pass ✓
- 6+ agents can work in parallel ✓
- No behavioral changes in CLI ✓

## Constitution Re-check

Post-design verification:
- ✅ **Single Responsibility**: Each module has one clear purpose (verified in data-model.md)
- ✅ **Testability**: All module interfaces defined for independent testing
- ✅ **No Breaking Changes**: CLI interface preserved exactly
- ✅ **Documentation**: Quickstart.md and data-model.md provide comprehensive docs
- ✅ **Import Compatibility**: Try/except pattern handles all contexts

All constitution requirements satisfied. No gaps or violations identified.

---

**Plan Status**: Complete
**Next Step**: Run `/spec-kitty.tasks` to generate task breakdown and prompt files
