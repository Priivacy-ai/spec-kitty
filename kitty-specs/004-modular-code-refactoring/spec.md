# Feature Specification: Modular Code Refactoring
*Path: [kitty-specs/004-modular-code-refactoring/spec.md](kitty-specs/004-modular-code-refactoring/spec.md)*

**Feature Branch**: `004-modular-code-refactoring`
**Created**: 2025-11-11
**Status**: Draft
**Input**: User description: "__init__ and dashboard are now massive monolithic files. We need to refactor them so that file lengths stay (ideally) under 200 lines. This means identifying the subsystems of each and making libraries or utilities or components in separate files. The imports in each case must work locally and if installed via pip or uv."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Maintains Code (Priority: P1)

A developer needs to fix a bug or add a feature in the spec-kitty codebase. They should be able to quickly locate the relevant code in a well-organized module structure, understand its purpose from the file name and location, and make changes without navigating through thousands of lines in a single file.

**Why this priority**: Code maintainability directly impacts development velocity and bug fix turnaround time. Developers are the primary users of the codebase structure.

**Independent Test**: Can be fully tested by having a developer locate and modify specific functionality (e.g., adding a new CLI command or modifying dashboard endpoint) and measuring time-to-completion compared to current monolithic structure.

**Acceptance Scenarios**:

1. **Given** a developer needs to add a new CLI command, **When** they look at the module structure, **Then** they can identify the correct module to modify within 30 seconds
2. **Given** a developer needs to fix a dashboard route, **When** they navigate to the dashboard modules, **Then** each module has a clear, single responsibility evident from its name
3. **Given** a developer needs to understand a module's purpose, **When** they open any module file, **Then** the file is under 200 lines and has a clear, focused purpose

---

### User Story 2 - Application Runs After Installation (Priority: P2)

Users install spec-kitty via pip or uv and run the application. The refactored module structure must maintain all existing functionality with proper import resolution regardless of installation method.

**Why this priority**: The application must work for end users regardless of internal structure. Import resolution is critical for distributed packages.

**Independent Test**: Can be tested by installing spec-kitty via pip in a clean virtual environment and verifying all commands and dashboard features work correctly.

**Acceptance Scenarios**:

1. **Given** spec-kitty is installed via pip, **When** a user runs any CLI command, **Then** all imports resolve correctly and the command executes successfully
2. **Given** spec-kitty is running from source in development, **When** a developer runs the dashboard, **Then** all modules load correctly with relative imports
3. **Given** the dashboard spawns a subprocess, **When** the subprocess imports modules, **Then** import resolution works in the detached process context

---

### User Story 3 - New Developer Onboards (Priority: P3)

A new developer joins the project and needs to understand the codebase structure. They should be able to comprehend the system architecture by examining the module organization.

**Why this priority**: Clear architecture accelerates onboarding and reduces time to first contribution.

**Independent Test**: Can be tested by having a developer unfamiliar with the codebase navigate the structure and identify where to make specific types of changes.

**Acceptance Scenarios**:

1. **Given** a new developer examines the source tree, **When** they look at module names and organization, **Then** they can identify the purpose of each major subsystem
2. **Given** documentation exists for the module structure, **When** a new developer reads it, **Then** they understand the responsibilities of each module category

---

### Edge Cases

- What happens when circular imports could occur between modules?
- How does the system handle dynamic imports or lazy loading if needed?
- What happens if a module needs to import from a parent package?
- How are shared utilities accessed from different module depths?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain all existing CLI commands with identical behavior after refactoring
- **FR-002**: System MUST preserve all dashboard routes and functionality after refactoring
- **FR-003**: Each module file MUST be under 200 lines of code (excluding comments and docstrings)
- **FR-004**: Module names MUST clearly indicate their purpose and responsibility
- **FR-005**: Imports MUST work correctly when installed via pip, uv, or running from source
- **FR-006**: System MUST organize related functionality into logical module groupings
- **FR-007**: Shared utilities MUST be accessible from all modules that need them
- **FR-008**: Module structure MUST eliminate code duplication where multiple functions serve similar purposes
- **FR-009**: Each module MUST have a single, well-defined responsibility (Single Responsibility Principle)
- **FR-010**: System MUST maintain backwards compatibility for command-line interface
- **FR-011**: Dashboard subprocess spawning MUST continue to work with new module structure
- **FR-012**: Test coverage MUST remain at current level or improve after refactoring

### Key Entities *(include if feature involves data)*

- **CLI Module Group**: Handles command-line interface operations, command parsing, and user interaction
- **Dashboard Module Group**: Manages HTTP server, routes, handlers, and web interface functionality
- **Core Module Group**: Shared utilities, configuration, constants used across the application
- **Feature Module Group**: Domain-specific logic for spec-kitty features (specifications, planning, tasks, etc.)
- **Integration Module Group**: External system integrations (Git operations, file system management, process spawning)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All module files are under 200 lines of code
- **SC-002**: Developers can locate specific functionality within 30 seconds by following module organization
- **SC-003**: Application passes all existing tests without modification after refactoring
- **SC-004**: Time to add a new CLI command reduces by 50% due to clear module boundaries
- **SC-005**: Application successfully installs and runs via pip with zero import errors
- **SC-006**: Code duplication reduced by at least 30% through shared utility extraction
- **SC-007**: New developer can understand system architecture within 15 minutes of reviewing module structure
- **SC-008**: Module cohesion score improves (measured by analyzing cross-module dependencies)
- **SC-009**: 100% of existing functionality remains operational after refactoring

## Assumptions

- The refactoring will be done as a complete replacement with no backwards compatibility requirements
- Python's standard import mechanisms are sufficient (no need for custom import hooks)
- The 200-line limit applies to actual code, not including comments, docstrings, or blank lines
- Current test suite adequately covers functionality to verify refactoring doesn't break features
- Module organization follows Python package best practices and conventions
- Development will happen in a feature branch allowing for iterative refinement

## Risks

- **Risk**: Import resolution might behave differently in various execution contexts
  - **Mitigation**: Test in multiple environments (local development, pip install, subprocess execution)

- **Risk**: Circular dependencies could emerge from poor module separation
  - **Mitigation**: Design module hierarchy carefully with clear dependency flow

- **Risk**: Refactoring could inadvertently change behavior
  - **Mitigation**: Comprehensive test coverage before and after refactoring

## Out of Scope

- Performance optimization (unless it naturally emerges from better organization)
- Adding new features or functionality
- Changing the user interface or command structure
- Modifying the underlying algorithms or business logic
- Creating a plugin architecture or dynamic loading system
- Changing the technology stack or dependencies

## Implementation Details

### Current State Analysis

#### `__init__.py` (2,700 lines)
The main CLI module has grown to 2,700 lines containing 15 distinct subsystems:
- UI Components (140 lines): Interactive menus and progress tracking
- Template Management (550 lines): Template discovery, copying, and rendering
- GitHub Operations (350 lines): API interactions and downloads
- Project Initialization (520 lines): Main init workflow orchestration
- Git Operations (250 lines): Repository management
- Project Resolution (150 lines): Path and worktree handling
- Research Workflow (150 lines): Phase 0 research generation
- Acceptance Logic (330 lines): Feature validation
- Merge Workflow (240 lines): Branch integration
- Tool Checking (40 lines): Dependency verification
- Configuration (100 lines): Constants and settings
- Plus various utilities and helpers

#### `dashboard.py` (3,030 lines)
The dashboard module has grown to 3,030 lines containing 7 major subsystems:
- Utility Functions (195 lines): Path formatting, port finding, etc.
- Diagnostics System (150 lines): Project health checking
- Feature Scanning (125 lines): Feature discovery and metadata
- HTML Template (1,782 lines): Embedded HTML/CSS/JS as strings
- HTTP Handler (474 lines): REST API endpoints
- Server Management (69 lines): HTTPServer lifecycle
- Dashboard Persistence (198 lines): State management

### Proposed Module Structure

```
src/specify_cli/
├── __init__.py                    # Entry point, CLI app setup (~150 lines)
├── cli/
│   ├── __init__.py
│   ├── ui.py                      # StepTracker, menus (~140 lines)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── init.py                # Init command logic (~200 lines)
│   │   ├── check.py               # Dependency checking (~60 lines)
│   │   ├── research.py            # Research command (~150 lines)
│   │   ├── accept.py              # Accept command (~180 lines)
│   │   ├── merge.py               # Merge command (~200 lines)
│   │   └── verify.py              # Verify setup (~60 lines)
│   └── helpers.py                 # Banner, callbacks (~80 lines)
├── core/
│   ├── __init__.py
│   ├── config.py                  # All constants, choices (~100 lines)
│   ├── git_ops.py                 # Git operations (~200 lines)
│   ├── tool_checker.py            # Tool verification (~40 lines)
│   ├── project_resolver.py        # Path resolution (~150 lines)
│   └── utils.py                   # Shared utilities (~100 lines)
├── template/
│   ├── __init__.py
│   ├── manager.py                 # Template operations (~200 lines)
│   ├── renderer.py                # Template rendering (~150 lines)
│   ├── github_client.py           # GitHub downloads (~200 lines)
│   └── asset_generator.py         # Agent assets (~150 lines)
├── dashboard/
│   ├── __init__.py                # Public API (~50 lines)
│   ├── server.py                  # HTTPServer setup (~100 lines)
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseHandler, helpers (~100 lines)
│   │   ├── api.py                 # API endpoints (~200 lines)
│   │   ├── features.py            # Feature endpoints (~150 lines)
│   │   └── static.py              # Static file serving (~50 lines)
│   ├── scanner.py                 # Feature scanning (~125 lines)
│   ├── diagnostics.py             # Diagnostics logic (~150 lines)
│   ├── lifecycle.py               # Process management (~198 lines)
│   ├── templates/
│   │   ├── index.html             # Main dashboard HTML
│   │   └── components/            # HTML components
│   └── static/
│       ├── dashboard.css          # Extracted styles
│       ├── dashboard.js           # Client-side logic
│       └── spec-kitty.png         # Logo asset
└── [existing modules remain as-is]
    ├── mission.py
    ├── acceptance.py
    ├── tasks_support.py
    ├── manifest.py
    └── gitignore_manager.py
```

### Import Strategy

To ensure imports work in all contexts (local development, pip install, subprocess):

1. **Relative imports within packages**:
   ```python
   # Within cli/commands/init.py
   from ..ui import StepTracker
   from ...core import git_ops
   from ...template import manager
   ```

2. **Absolute imports for subprocess/detached contexts**:
   ```python
   # In dashboard handlers that spawn subprocesses
   try:
       from .diagnostics import run_diagnostics  # Normal package
   except ImportError:
       from specify_cli.dashboard.diagnostics import run_diagnostics  # Subprocess
   ```

3. **Entry point compatibility**:
   ```python
   # In __init__.py
   from .cli import commands
   from .core import config
   from .dashboard import ensure_dashboard_running
   ```

### Refactoring Phases

#### Phase 1: Core Infrastructure (Week 1)
1. Create directory structure
2. Extract `core/` modules (config, utils, git_ops)
3. Extract `cli/ui.py` (UI components)
4. Ensure imports work locally

#### Phase 2: Template System (Week 1-2)
1. Extract template manager components
2. Separate GitHub client
3. Move renderer and asset generation
4. Test pip installation

#### Phase 3: Dashboard Decomposition (Week 2)
1. Extract HTML/CSS/JS to files
2. Split HTTP handler into modules
3. Extract diagnostics and scanning
4. Test subprocess imports

#### Phase 4: CLI Commands (Week 3)
1. Move each command to separate module
2. Refactor init command (largest)
3. Update command registration
4. Integration testing

#### Phase 5: Cleanup & Documentation (Week 3)
1. Remove dead code
2. Update import statements
3. Document module structure
4. Performance verification

### Testing Strategy

1. **Unit tests per module**: Each extracted module gets dedicated tests
2. **Integration tests**: Verify command flows work end-to-end
3. **Installation tests**:
   - pip install in clean virtualenv
   - uv installation
   - Development mode
4. **Import tests**: Verify imports in subprocess contexts
5. **Regression tests**: All existing tests must pass

### Success Metrics

- No file exceeds 200 lines (excluding comments/docstrings)
- 90%+ of code in appropriate modules (high cohesion)
- Less than 10% cross-module dependencies
- Zero import errors in any execution context
- All existing functionality preserved