# Data Model: Constitution Packaging Safety and Redesign

**Phase**: 1 (Design & Contracts)
**Date**: 2026-01-12
**Feature**: 011-constitution-packaging-safety-and-redesign

## Overview

This feature primarily involves refactoring and cleanup rather than introducing new domain entities. This document captures the structure of existing entities that are being modified or relocated.

---

## Entity 1: Template File Structure

Templates are source files that get packaged and distributed to users during `spec-kitty init`.

### Before Relocation

```
.kittify/
├── templates/
│   ├── command-templates/
│   │   ├── constitution.md
│   │   ├── plan.md
│   │   ├── specify.md
│   │   ├── implement.md
│   │   ├── review.md
│   │   ├── tasks.md
│   │   ├── analyze.md
│   │   └── ...
│   ├── plan-template.md
│   ├── spec-template.md
│   ├── task-prompt-template.md
│   ├── git-hooks/
│   ├── claudeignore-template
│   └── AGENTS.md
├── missions/
│   ├── software-dev/
│   │   ├── mission.yaml
│   │   ├── templates/
│   │   │   ├── plan-template.md
│   │   │   ├── spec-template.md
│   │   │   └── task-prompt-template.md
│   │   ├── command-templates/
│   │   │   ├── plan.md
│   │   │   ├── specify.md
│   │   │   ├── implement.md
│   │   │   ├── review.md
│   │   │   └── ...
│   │   └── constitution/          # REMOVED: Mission-specific constitution
│   │       └── principles.md
│   └── research/
│       └── [similar structure]
└── scripts/  # May or may not exist
    ├── bash/
    └── powershell/
```

**Issue**: Mixing template source code with project instance location. Developers running `spec-kitty init` in the spec-kitty repo would overwrite template sources.

### After Relocation

```
src/specify_cli/
├── templates/                     # Moved from .kittify/templates/
│   ├── command-templates/
│   │   ├── constitution.md        # UPDATED: Phase-based discovery
│   │   ├── plan.md
│   │   ├── specify.md
│   │   └── ...
│   ├── plan-template.md
│   ├── spec-template.md
│   ├── task-prompt-template.md
│   ├── git-hooks/
│   ├── claudeignore-template
│   └── AGENTS.md
├── missions/                      # Moved from .kittify/missions/
│   ├── software-dev/
│   │   ├── mission.yaml
│   │   ├── templates/
│   │   ├── command-templates/
│   │   └── constitution/          # DELETED: Removed entirely
│   └── research/
└── scripts/                       # Moved from .kittify/scripts/ (if existed)
    ├── bash/
    └── powershell/

.kittify/                          # Spec-kitty's project instance (dogfooding)
├── memory/
│   └── constitution.md            # Can be filled for dogfooding
├── missions/ → ../src/specify_cli/missions/  # Symlink or copy
└── ...                            # Regular project structure
```

**Benefits**: Clean separation, safe dogfooding, no packaging contamination risk.

### Template Loading API

```python
# Before: Loading from .kittify/ (fragile)
repo_root = Path(__file__).parents[2]
template_src = repo_root / ".kittify" / "templates"

# After: Loading from package resources (robust)
from importlib.resources import files

templates_resource = files("specify_cli").joinpath("templates")
```

---

## Entity 2: Migration Structure

Migrations transform project structure from one version to another. This feature modifies 4 existing migrations and adds 1 new migration.

### BaseMigration Interface

```python
class BaseMigration(ABC):
    """Base class for all migrations."""

    migration_id: str          # e.g., "0.10.12_constitution_cleanup"
    description: str           # Human-readable description
    target_version: str        # Version this migration targets

    @abstractmethod
    def detect(self, project_path: Path) -> bool:
        """Return True if migration needs to run."""
        pass

    @abstractmethod
    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Return (True, "") if migration can be applied, else (False, reason)."""
        pass

    @abstractmethod
    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Execute migration. Returns result with changes/warnings/errors."""
        pass
```

### MigrationResult

```python
@dataclass
class MigrationResult:
    """Result of applying a migration."""

    success: bool                    # True if migration completed successfully
    changes_made: list[str]          # List of changes made (for user feedback)
    warnings: list[str]              # Non-fatal issues encountered
    errors: list[str]                # Fatal errors that prevented migration
```

### Modified Migrations

**m_0_7_3_update_scripts.py**

- **Change**: `can_apply()` returns `(True, "")` even if bash scripts missing in package
- **Rationale**: Scripts may have been removed in later version, migration should skip gracefully

**m_0_10_2_update_slash_commands.py**

- **Change**: `apply()` explicitly removes legacy .toml command files
- **Rationale**: Ensure complete cleanup of old format

**m_0_10_6_workflow_simplification.py**

- **Change**: `can_apply()` returns `(True, "")` without checking mission templates first
- **Rationale**: Templates are copied during `apply()`, not before

**m_0_10_0_python_only.py**

- **Change**: Verify `.kittify/scripts/tasks/` directory removal is explicit
- **Rationale**: Ensure obsolete Python task helpers are cleaned up

### New Migration: m_0_10_12_constitution_cleanup.py

```python
{
    "migration_id": "0.10.12_constitution_cleanup",
    "description": "Remove mission-specific constitution directories",
    "target_version": "0.10.12",
    "actions": [
        {
            "action": "remove_directory",
            "path": ".kittify/missions/*/constitution/",
            "recursive": true
        }
    ],
    "warnings": [
        "Mission-specific constitutions removed. Use project-level constitution at .kittify/memory/constitution.md instead."
    ]
}
```

**Behavior:**

- **detect()**: Returns True if any mission has a `constitution/` subdirectory
- **can_apply()**: Always returns `(True, "")` - removal is always safe
- **apply()**: Recursively removes `constitution/` directories from all missions, adds warning message

---

## Entity 3: Constitution Structure

The constitution file captures project-level governance rules and technical standards.

### File Location

- **Before**: Could be in `.kittify/memory/constitution.md` OR `.kittify/missions/*/constitution/principles.md` (confusing)
- **After**: ONLY at `.kittify/memory/constitution.md` (single source of truth)

### Constitution Format

```markdown
# [PROJECT_NAME] Constitution

## Core Principles

### I. [Principle Name]
[Description of principle]

**Rationale**: [Why this principle matters]

### II. [Principle Name]
[Description of principle]

**Rationale**: [Why this principle matters]

[... more principles as needed]

## Technical Standards

[Technical requirements: languages, frameworks, testing, etc.]

## Code Quality

[Quality gates: PR requirements, review process, testing discipline]

## Tribal Knowledge

[Team conventions, lessons learned, historical context]

## Governance

**Amendment Process**: [How to update constitution]
**Compliance Review**: [How features are validated against constitution]
**Version Control**: [How constitution changes are tracked]

---

**Version**: [MAJOR.MINOR.PATCH] | **Ratified**: [YYYY-MM-DD] | **Last Amended**: [YYYY-MM-DD]
```

### Constitution Discovery Phases

The `/spec-kitty.constitution` command collects information in 4 phases:

```json
{
  "phases": [
    {
      "name": "Technical Standards",
      "questions": [
        "What languages and frameworks are required?",
        "What testing framework and coverage requirements?",
        "What are the performance/scale targets?",
        "What are the deployment constraints?"
      ],
      "skip_option": "Skip technical standards (use defaults)",
      "minimal_path": "Usually complete (core requirements)"
    },
    {
      "name": "Code Quality",
      "questions": [
        "What PR approval requirements?",
        "What code review checklist?",
        "What quality gates must pass?",
        "What documentation standards?"
      ],
      "skip_option": "Skip code quality phase",
      "minimal_path": "Often skip (use standard practices)"
    },
    {
      "name": "Tribal Knowledge",
      "questions": [
        "What team conventions exist?",
        "What lessons learned should be captured?",
        "What historical decisions guide future work?",
        "What domain-specific knowledge is critical?"
      ],
      "skip_option": "Skip tribal knowledge phase",
      "minimal_path": "Often skip (for new projects)"
    },
    {
      "name": "Governance",
      "questions": [
        "How are constitution changes approved?",
        "Who validates feature compliance?",
        "How are exceptions handled?",
        "What is the amendment process?"
      ],
      "skip_option": "Skip governance (use simple defaults)",
      "minimal_path": "Use defaults (simple governance)"
    }
  ],
  "paths": {
    "minimal": {
      "phases_completed": 1,
      "questions_answered": "3-5",
      "output_length": "1 page"
    },
    "comprehensive": {
      "phases_completed": 4,
      "questions_answered": "8-12",
      "output_length": "2-3 pages"
    }
  }
}
```

---

## Entity 4: Process Management (Dashboard)

The dashboard runs as a background HTTP server. Process lifecycle management must work cross-platform.

### Process Lifecycle States

```python
class DashboardState(Enum):
    """Dashboard server lifecycle states."""

    NOT_RUNNING = "not_running"      # No dashboard process exists
    STARTING = "starting"             # Process spawned, waiting for HTTP response
    RUNNING = "running"               # Process alive and responding to HTTP
    STOPPING = "stopping"             # Shutdown initiated, waiting for process exit
    ORPHANED = "orphaned"             # PID alive but not responding (needs force kill)
```

### Process Management Operations

**Before (POSIX-only):**

```python
import os
import signal

# Check if alive
try:
    os.kill(pid, 0)  # Signal 0 = check existence
    is_alive = True
except ProcessLookupError:
    is_alive = False

# Graceful shutdown
os.kill(pid, signal.SIGTERM)

# Force kill
os.kill(pid, signal.SIGKILL)  # FAILS ON WINDOWS
```

**After (Cross-platform with psutil):**

```python
import psutil

# Check if alive
try:
    proc = psutil.Process(pid)
    is_alive = proc.is_running()
except psutil.NoSuchProcess:
    is_alive = False

# Graceful shutdown
try:
    proc = psutil.Process(pid)
    proc.terminate()  # SIGTERM on POSIX, TerminateProcess on Windows
    proc.wait(timeout=3)
except psutil.TimeoutExpired:
    proc.kill()  # Force kill if graceful failed
except psutil.NoSuchProcess:
    pass  # Already dead
```

### Dashboard Metadata File

Location: `.kittify/.dashboard`

```json
{
  "pid": 12345,
  "port": 9237,
  "started_at": "2026-01-12T10:30:00Z",
  "version": "0.10.12"
}
```

**Usage:**

- Created when dashboard starts
- Read by `spec-kitty dashboard` to check if already running
- Deleted when dashboard stops cleanly
- Orphaned files cleaned up on next dashboard start

---

## Entity 5: Package Configuration (pyproject.toml)

Controls what gets included in wheel and sdist distributions.

### Before (Packaging Contamination)

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/specify_cli"]

[tool.hatch.build.targets.wheel.force-include]
".kittify/templates" = "specify_cli/templates"      # Line 86
"scripts" = "specify_cli/scripts"                    # Line 87
".kittify/memory" = "specify_cli/memory"            # Line 88 - CONTAMINATES PACKAGE
".kittify/missions" = "specify_cli/missions"        # Line 89

[tool.hatch.build.targets.sdist]
include = [
    "src/**/*",
    ".kittify/templates/**/*",                       # Line 94
    "scripts/**/*",                                   # Line 95
    ".kittify/memory/**/*",                          # Line 96 - CONTAMINATES PACKAGE
    ".kittify/missions/software-dev/**/*",           # Line 97
    ".kittify/missions/research/**/*",               # Line 98
    ...
]

[tool.hatch.build.targets.sdist.force-include]
".kittify/missions/software-dev" = ".kittify/missions/software-dev"  # Line 109
".kittify/missions/research" = ".kittify/missions/research"          # Line 110
```

**Issue**: Lines 88, 96 cause any filled `.kittify/memory/constitution.md` in spec-kitty repo to be packaged and distributed to all users.

### After (Clean Packaging)

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/specify_cli"]
# No force-includes needed - everything under src/ gets packaged automatically

[tool.hatch.build.targets.sdist]
include = [
    "src/**/*",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "pyproject.toml",
]
exclude = [
    ".kittify/active-mission",
]
# No force-includes needed
```

**Dependencies Added:**

```toml
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "ruamel.yaml>=0.17.0",
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
    "psutil>=5.9.0",  # NEW: Cross-platform process management
]
```

---

## Validation Rules

### Template Files

- All files under `src/specify_cli/templates/` must be valid markdown
- Command templates must have YAML frontmatter with `description` field
- Template placeholders must use `[ALL_CAPS]` format

### Migrations

- `migration_id` must follow pattern `X.Y.Z_description`
- `target_version` must be valid semver
- `detect()` must be idempotent (safe to call multiple times)
- `apply()` must handle dry_run=True without side effects
- `apply()` must succeed even if files already cleaned up (idempotency)

### Constitution

- Version must follow semver (MAJOR.MINOR.PATCH)
- Dates must be ISO format (YYYY-MM-DD)
- Must have at least one Core Principle
- Must have Governance section

### Package Configuration

- No paths outside `src/` in force-includes
- No `.kittify/memory/` in include patterns
- All dependencies must specify minimum version

---

## Summary

This feature involves structural refactoring rather than new domain models:

1. **Template relocation** changes file locations, not structure
2. **Migration modifications** improve robustness using existing patterns
3. **Constitution redesign** changes collection workflow, not file format
4. **Process management** switches from os/signal to psutil, not changing lifecycle

All entities follow existing spec-kitty patterns. No new abstractions required.
