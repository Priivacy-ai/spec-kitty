# Implementation Plan: Mission System Architectural Refinement

**Branch**: `005-refactor-mission-system` | **Date**: 2025-01-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/005-refactor-mission-system/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

Planning interrogation completed with validated architectural decisions documented in Technical Context.

## Summary

Refactor the spec-kitty mission system to address 6 architectural concerns identified in comprehensive codebase analysis:

1. **DRY Violations**: Extract duplicated "Location Pre-flight Check" logic (60+ lines across 8 files) to shared Python module `src/specify_cli/guards.py`
2. **Silent Failures**: Add schema validation for mission.yaml to catch typos and structural errors with clear error messages
3. **Research Mission**: Make production-ready with complete templates, integrated CSV tracking (evidence-log, source-register), and citation format validation
4. **Mission Switching**: Implement `spec-kitty mission` CLI command group (list/current/switch/info) with git-clean enforcement
5. **Path Enforcement**: Validate mission-declared path conventions (progressive: warn at switch, error at acceptance)
6. **Terminology**: Clarify Project/Feature/Mission definitions across all documentation
7. **Dashboard**: Display active mission prominently

**Technical Approach**: Python-first architecture with pre-command validation, research-driven schema library selection, API-first mission switching CLI, and progressive path validation.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase requirement)
**Primary Dependencies**:
- **Existing**: typer (CLI), rich (console output), pyyaml (mission.yaml parsing), pathlib (path operations)
- **NEW: Schema Validation**: pydantic>=2.0 (selected after research - superior error messages justify 5MB dependency)
- **Citation Validation**: Python standard library only (csv, re for format validation) - zero new dependencies

**Storage**: Filesystem only (YAML configs, CSV files, markdown templates)
**Testing**: pytest (existing test framework)
**Target Platform**: Cross-platform CLI (macOS, Linux, Windows with symlink fallback)
**Project Type**: Single Python CLI project
**Performance Goals**:
- Mission loading <100ms
- Mission switching <2 seconds
- Schema validation <50ms
- Pre-flight checks <200ms

**Constraints**:
- No breaking changes to existing mission.yaml structure (additive only)
- Backwards compatibility with existing custom missions
- Windows symlink fallback must continue working
- Command prompt interface unchanged (agents call Python validation)
- Zero new runtime dependencies preferred (research will evaluate)

**Scale/Scope**:
- Current: 2 missions (software-dev, research)
- Expected: 5-10 missions long-term
- Custom missions: community-contributed
- Template files: ~50 per mission
- Validation rules: 5-10 per mission

**Architectural Decisions from Planning:**

1. **Pre-flight Validation Location**: Option A - Python validates worktree location BEFORE command prompts execute
   - Rationale: Frees AI agents from validation burden, fails fast with clear errors
   - Implementation: Commands call `python -m specify_cli.guards validate` before prompt execution

2. **Citation Integration Level**: Option B - Validation hooks with format enforcement
   - Rationale: Pragmatic foundation without external tool dependencies
   - Implementation: Python validators check citation completeness and enforce BibTeX/APA format in CSV files

3. **Mission Switching Architecture**: Option B - Python API-first with CLI wrappers
   - Rationale: Enables programmatic use, easier testing, code reusability
   - Implementation: Core logic in `mission.py`, Typer commands call API, extend existing `set_active_mission()`

4. **Path Validation Timing**: Option D - Progressive enforcement
   - Rationale: User-friendly (warn early, error late), supports incremental project setup
   - Implementation: Non-blocking warnings at mission switch, blocking errors at acceptance

**Research Completed** (Phase 0):
- ✅ **Schema Validation**: Pydantic v2 selected for superior error messages (A+ quality, worth 5MB dependency)
- ✅ **Citation Formats**: Progressive validation - enforce completeness, warn on format, support BibTeX/APA/Simple
- ✅ **Dashboard Integration**: Hybrid approach - server-side rendering with manual refresh button (resists complexity per user guidance)

See [research.md](research.md) for detailed analysis and decision rationale.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: Constitution file is currently empty/template-only at `.kittify/memory/constitution.md`

**Default Software Engineering Principles Applied**:

✅ **DRY (Don't Repeat Yourself)**: Primary goal of this refactoring - eliminating 60+ lines of duplication

✅ **Fail Fast**: Pre-flight validation catches errors before command execution

✅ **Backwards Compatibility**: No breaking changes to existing missions or user workflows

✅ **Explicit Over Implicit**: Schema validation makes errors explicit instead of silent failures

✅ **Progressive Enhancement**: Path validation warns first, errors later

**No Constitution Violations**: This refactoring improves adherence to standard software engineering practices without introducing complexity.

## Project Structure

### Documentation (this feature)

```
kitty-specs/005-refactor-mission-system/
├── spec.md              # Feature specification (already created)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0 - Schema validation & citation format research
├── data-model.md        # Phase 1 - Mission schema, validation models, citation formats
├── quickstart.md        # Phase 1 - Developer guide for using new mission features
└── tasks.md             # Phase 2 - Work packages (created by /spec-kitty.tasks)
```

### Source Code (existing spec-kitty codebase)

```
src/specify_cli/
├── guards.py            # NEW - Pre-flight validation module
│   ├── validate_worktree_location()
│   ├── validate_git_clean()
│   └── validate_mission_compatible()
├── mission.py           # MODIFIED - Add schema validation & mission CLI
│   ├── MissionConfig (Pydantic/other model)
│   ├── Mission (enhanced with validation)
│   ├── list_missions()
│   ├── get_mission_info()
│   ├── switch_mission()     # Enhanced with validation
│   └── validate_paths()      # NEW
├── cli/commands/
│   └── mission.py       # NEW - Typer command group for spec-kitty mission
│       ├── list_cmd()
│       ├── current_cmd()
│       ├── switch_cmd()
│       └── info_cmd()
├── validators/
│   ├── research.py      # NEW - Research mission validators
│   │   ├── validate_citations()
│   │   ├── validate_bibliography()
│   │   └── check_source_register()
│   └── paths.py         # NEW - Path convention validators
│       ├── validate_workspace_paths()
│       └── suggest_directory_creation()
└── dashboard/
    └── server.py        # MODIFIED - Add active mission to context

.kittify/missions/
├── software-dev/
│   ├── mission.yaml     # Schema-validated
│   ├── commands/
│   │   ├── plan.md      # MODIFIED - Remove inline pre-flight, call Python
│   │   ├── implement.md # MODIFIED - Remove inline pre-flight, call Python
│   │   ├── review.md    # MODIFIED - Remove inline pre-flight, call Python
│   │   └── merge.md     # MODIFIED - Remove inline pre-flight, call Python
│   └── templates/       # Existing
└── research/
    ├── mission.yaml     # MODIFIED - Add citation validation rules
    ├── commands/
    │   ├── implement.md # MODIFIED - Add citation tracking guidance
    │   └── review.md    # MODIFIED - Add citation validation checks
    └── templates/
        ├── spec-template.md  # MODIFIED - Research question format
        └── plan-template.md  # MODIFIED - Methodology sections

tests/
├── unit/
│   ├── test_guards.py           # NEW - Pre-flight validation tests
│   ├── test_mission_schema.py   # NEW - Schema validation tests
│   ├── test_mission_cli.py      # NEW - CLI command tests
│   └── test_validators.py       # NEW - Research & path validator tests
└── integration/
    ├── test_mission_switching.py  # NEW - End-to-end mission switch
    └── test_research_workflow.py  # NEW - Full research mission workflow
```

**Structure Decision**: Existing single Python CLI project structure. All changes are modifications to existing files or new modules in established directories. No restructuring required.

## Complexity Tracking

*No constitution violations - this section is not applicable.*

This refactoring reduces complexity by eliminating duplication and adding explicit validation.

## Parallel Work Analysis

This feature can be implemented with moderate parallelization. Work streams organized by user story priority.

### Dependency Graph

```
Foundation (Sequential) → Parallel Streams → Integration

Phase 0 - Research (Sequential):
  ├─ Research schema validation libraries
  ├─ Research citation formats
  └─ Research dashboard approaches

Phase 1 - Core Infrastructure (Sequential foundation):
  └─ Create guards.py module + tests → [BLOCKS all command prompt modifications]

Phase 2 - Parallel Streams (can work simultaneously):
  Stream A: Mission Schema & CLI
    ├─ Add schema validation to mission.py
    ├─ Create mission CLI commands
    └─ Add path validation

  Stream B: Research Mission
    ├─ Update research templates
    ├─ Create citation validators
    └─ Update research command prompts

  Stream C: Command Prompts
    ├─ Update software-dev commands (plan/implement/review/merge)
    └─ Requires guards.py from Phase 1

  Stream D: Documentation & Dashboard
    ├─ Update terminology in docs
    └─ Add mission display to dashboard

Phase 3 - Integration (Sequential):
  ├─ Integration tests
  ├─ End-to-end mission switching test
  └─ Full research workflow test
```

### Work Distribution

**Sequential Foundation Work** (must complete first):
1. **Phase 0 Research** (1-2 days)
   - Schema library comparison and selection
   - Citation format patterns
   - Dashboard integration approach

2. **Phase 1 Guards Module** (1 day)
   - Create `src/specify_cli/guards.py`
   - Implement pre-flight validation functions
   - Write unit tests
   - **BLOCKS**: All command prompt modifications depend on this

**Parallel Streams** (can work simultaneously after foundation):

**Stream A - Mission Schema & CLI** (2-3 days)
- Files: `src/specify_cli/mission.py`, `src/specify_cli/cli/commands/mission.py`
- Owner: Agent/dev focused on CLI architecture
- Dependencies: None (can start immediately after research)

**Stream B - Research Mission** (2-3 days)
- Files: `.kittify/missions/research/*`, `src/specify_cli/validators/research.py`
- Owner: Agent/dev with research domain knowledge
- Dependencies: None (can start immediately after research)

**Stream C - Command Prompts** (1-2 days)
- Files: All command `.md` files in both missions
- Owner: Agent/dev focused on AI agent UX
- Dependencies: **Requires guards.py from Phase 1**

**Stream D - Docs & Dashboard** (1-2 days)
- Files: `README.md`, `src/specify_cli/dashboard/server.py`
- Owner: Agent/dev focused on documentation
- Dependencies: None (can start immediately)

### Coordination Points

**Sync Schedule**:
- After Phase 0 Research: Review and confirm schema library selection
- After Phase 1 Guards: Merge to main, tag as milestone, unblock Stream C
- During Parallel Streams: Daily check-ins on progress, no code merges
- After Parallel Streams: Integration testing begins

**Integration Strategy**:
- Use feature worktree (`005-refactor-mission-system`) for all work
- Each stream works on separate files (minimal conflicts)
- Stream C must wait for guards.py merge before starting
- Integration tests run after all streams complete

**File Ownership to Avoid Conflicts**:
- **guards.py**: Stream Foundation only
- **mission.py**: Stream A only
- **validators/**: Stream B only
- **command prompts**: Stream C only
- **docs/dashboard**: Stream D only

**Critical Path**: Foundation (2-3 days) → Stream C (1-2 days) = 3-5 days minimum
**Parallel Benefit**: Streams A, B, D can work during Stream C execution = saves 4-6 days

**Estimated Timeline**:
- Sequential only: ~10-12 days
- With parallelization: ~6-8 days
- Single developer: ~8-10 days (less context switching overhead)
