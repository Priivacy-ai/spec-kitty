# Implementation Plan: Agent Skills Installer Infrastructure

**Branch**: `042-agent-skills-installer-infrastructure` | **Date**: 2026-03-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/042-agent-skills-installer-infrastructure/spec.md`

## Summary

Replace the command-only `AGENT_COMMAND_CONFIG` dict and the separate `AGENT_DIRS` list with a unified `AGENT_SURFACE_CONFIG` dataclass registry. Derive existing access patterns from the new canonical source via compatibility views so no migration call-site rewrites are needed. Add skill-root resolution, managed manifest, and post-init verification plumbing to `spec-kitty init`. Preserve byte-exact wrapper generation backward compatibility.

## Technical Context

**Language/Version**: Python 3.11+ (existing Spec Kitty codebase)
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (YAML/frontmatter), hashlib (content hashing)
**Storage**: Filesystem only — YAML manifest at `.kittify/agent-surfaces/skills-manifest.yaml`
**Testing**: pytest with 90%+ coverage for new code, mypy --strict, ruff check
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Single Python CLI package
**Performance Goals**: Skill root resolution < 100ms (pure data lookup, no network I/O)
**Constraints**: No new external dependencies. hashlib is stdlib.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | All new code targets 3.11+ |
| mypy --strict | PASS | All new dataclasses and functions will have full type annotations |
| pytest 90%+ coverage | PASS | New modules will have dedicated test files |
| Integration tests for CLI commands | PASS | Init with `--skills` flag will have integration tests |
| Cross-platform | PASS | No platform-specific code; uses pathlib throughout |
| No new external dependencies | PASS | hashlib is stdlib; no pip additions |
| Private dependency governance | N/A | No spec-kitty-events interaction in this feature |
| Two-branch strategy | PASS | Targeting main (1.x maintenance line). Phase 0 is infrastructure compatible with both lines. |

## Architectural Decision: Canonical Source with Derived Views

**Decision**: `AGENT_SURFACE_CONFIG` is the single hand-maintained canonical registry. All existing access patterns (`AGENT_DIRS`, `AGENT_DIR_TO_KEY`, `AGENT_COMMAND_CONFIG`) become computed derived views.

**Why**: Unifies the two current registries (`AGENT_COMMAND_CONFIG` in `config.py` and `AGENT_DIRS` in `directories.py`) without a broad call-site rewrite. The 15+ migration files that import `get_agent_dirs_for_project` and the `asset_generator.py` that reads `AGENT_COMMAND_CONFIG` continue to work unchanged.

**Migration strategy**: Compatibility-first, then cleanup later. Old names remain importable but are computed from the canonical source. New code reads `AGENT_SURFACE_CONFIG` directly.

**Acceptance criteria**: Existing init, agent-config, and upgrade behaviors remain identical. New capability metadata (distribution class, skill roots) is available for skill distribution plumbing.

## Project Structure

### Documentation (this feature)

```
kitty-specs/042-agent-skills-installer-infrastructure/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal API contracts)
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   ├── config.py                    # MODIFIED: AGENT_COMMAND_CONFIG becomes derived view
│   ├── agent_config.py              # UNCHANGED
│   ├── agent_surface.py             # NEW: canonical AGENT_SURFACE_CONFIG, dataclasses, derived views
│   └── __init__.py                  # MODIFIED: re-export new public API
├── agent_utils/
│   ├── directories.py               # MODIFIED: AGENT_DIRS/AGENT_DIR_TO_KEY become derived views
│   └── __init__.py                  # MODIFIED: re-export updated symbols
├── skills/
│   ├── __init__.py                  # NEW: public API for skill operations
│   ├── manifest.py                  # NEW: SkillsManifest dataclass, read/write/verify
│   ├── roots.py                     # NEW: skill root resolution and creation
│   └── verification.py             # NEW: post-install verification checks
├── template/
│   └── asset_generator.py           # MODIFIED: import wrapper config from agent_surface
├── cli/commands/
│   ├── init.py                      # MODIFIED: add --skills flag, skill root creation, manifest, verification
│   └── agent/
│       └── config.py                # MODIFIED: sync_agents gains skill root awareness
└── upgrade/migrations/
    └── m_2_1_0_agent_surface_manifest.py  # NEW: upgrade migration

tests/specify_cli/
├── test_core/
│   ├── test_agent_surface.py        # NEW: canonical config, derived views, distribution classes
│   └── test_config.py               # MODIFIED: verify backward compatibility of derived views
├── test_skills/
│   ├── test_manifest.py             # NEW: manifest CRUD and verification
│   ├── test_roots.py                # NEW: skill root resolution logic
│   └── test_verification.py         # NEW: post-init verification checks
├── test_cli/
│   └── test_init_skills.py          # NEW: integration tests for init with --skills flag
└── test_migrations/
    └── test_agent_surface_migration.py  # NEW: upgrade migration tests
```

**Structure Decision**: Single project structure (existing). New modules added under `src/specify_cli/core/` for the canonical config and `src/specify_cli/skills/` for skill-specific operations. No new top-level directories. The `skills/` subpackage isolates skill plumbing from the existing core and template systems.

## Detailed Design

### 1. Canonical Agent Surface Config (`src/specify_cli/core/agent_surface.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

class DistributionClass(Enum):
    SHARED_ROOT_CAPABLE = "shared-root-capable"
    NATIVE_ROOT_REQUIRED = "native-root-required"
    WRAPPER_ONLY = "wrapper-only"

@dataclass(frozen=True)
class WrapperConfig:
    """Wrapper surface config — preserves exact AGENT_COMMAND_CONFIG semantics."""
    dir: str              # e.g. ".claude/commands"
    ext: str              # e.g. "md", "toml", "prompt.md"
    arg_format: str       # e.g. "$ARGUMENTS", "{{args}}"

@dataclass(frozen=True)
class AgentSurface:
    """Full capability profile for one supported agent."""
    key: str                                    # canonical agent key (e.g. "claude", "q")
    display_name: str                           # human-readable (e.g. "Claude Code")
    distribution_class: DistributionClass
    agent_root: str                             # filesystem root (e.g. ".claude")
    wrapper: WrapperConfig                      # wrapper generation config
    wrapper_subdir: str                         # e.g. "commands", "prompts", "workflows"
    skill_roots: tuple[str, ...]                # project skill roots in precedence order
    compat_notes: str = ""                      # optional notes (e.g. "also scans .claude/skills/")

AGENT_SURFACE_CONFIG: dict[str, AgentSurface]   # 12 entries, hand-maintained
```

The 12 entries encode the PRD section 8.1 capability matrix:

| Key | Distribution Class | Skill Roots | Agent Root |
|-----|-------------------|-------------|------------|
| `claude` | native-root-required | `(".claude/skills/",)` | `.claude` |
| `copilot` | shared-root-capable | `(".agents/skills/", ".github/skills/")` | `.github` |
| `gemini` | shared-root-capable | `(".agents/skills/", ".gemini/skills/")` | `.gemini` |
| `cursor` | shared-root-capable | `(".agents/skills/", ".cursor/skills/")` | `.cursor` |
| `qwen` | native-root-required | `(".qwen/skills/",)` | `.qwen` |
| `opencode` | shared-root-capable | `(".agents/skills/", ".opencode/skills/")` | `.opencode` |
| `windsurf` | shared-root-capable | `(".agents/skills/", ".windsurf/skills/")` | `.windsurf` |
| `codex` | shared-root-capable | `(".agents/skills/",)` | `.codex` |
| `kilocode` | native-root-required | `(".kilocode/skills/",)` | `.kilocode` |
| `auggie` | shared-root-capable | `(".agents/skills/", ".augment/skills/")` | `.augment` |
| `roo` | shared-root-capable | `(".agents/skills/", ".roo/skills/")` | `.roo` |
| `q` | wrapper-only | `()` | `.amazonq` |

### 2. Derived Compatibility Views

Computed from `AGENT_SURFACE_CONFIG` — no hand-maintenance:

```python
# In agent_surface.py:

def get_agent_command_config() -> dict[str, dict[str, str]]:
    """Derive AGENT_COMMAND_CONFIG-compatible dict from canonical config."""
    return {
        key: {"dir": s.wrapper.dir, "ext": s.wrapper.ext, "arg_format": s.wrapper.arg_format}
        for key, s in AGENT_SURFACE_CONFIG.items()
    }

def get_agent_dirs() -> list[tuple[str, str]]:
    """Derive AGENT_DIRS-compatible list from canonical config."""
    return [(s.agent_root, s.wrapper_subdir) for s in AGENT_SURFACE_CONFIG.values()]

def get_agent_dir_to_key() -> dict[str, str]:
    """Derive AGENT_DIR_TO_KEY-compatible dict from canonical config."""
    return {s.agent_root: s.key for s in AGENT_SURFACE_CONFIG.values()}

def get_agent_surface(agent_key: str) -> AgentSurface:
    """Return full capability profile for one agent."""
    return AGENT_SURFACE_CONFIG[agent_key]
```

In `config.py`, the existing constant becomes:

```python
from specify_cli.core.agent_surface import get_agent_command_config
AGENT_COMMAND_CONFIG = get_agent_command_config()  # backward-compatible derived view
```

In `directories.py`, the existing constants become:

```python
from specify_cli.core.agent_surface import get_agent_dirs, get_agent_dir_to_key
AGENT_DIRS: list[tuple[str, str]] = get_agent_dirs()       # derived
AGENT_DIR_TO_KEY: dict[str, str] = get_agent_dir_to_key()  # derived
```

This preserves all import paths. The 15+ migration files importing `get_agent_dirs_for_project` continue to work because `AGENT_DIRS` (now derived) feeds into `get_agent_dirs_for_project()` unchanged.

### 3. Skill Root Resolution (`src/specify_cli/skills/roots.py`)

```python
def resolve_skill_roots(
    selected_agents: list[str],
    mode: str = "auto",  # auto | native | shared | wrappers-only
) -> list[str]:
    """Return the minimum set of project skill root directories to create.

    Rules:
    - 'wrappers-only': returns []
    - 'auto'/'shared': .agents/skills/ if any shared-root-capable selected,
      plus native roots for native-root-required agents
    - 'native': vendor-native roots for all skill-capable agents
    - wrapper-only agents never contribute skill roots
    """
```

This is pure data logic, no I/O. Tested exhaustively with parametrized fixtures.

### 4. Skills Manifest (`src/specify_cli/skills/manifest.py`)

```python
@dataclass
class ManagedFile:
    """One managed file entry in the manifest."""
    path: str              # relative to project root
    sha256: str            # content hash
    file_type: str         # "wrapper" | "skill_root_marker"

@dataclass
class SkillsManifest:
    """Persistent record of what Spec Kitty installed."""
    spec_kitty_version: str
    created_at: str                   # ISO timestamp
    updated_at: str                   # ISO timestamp
    skills_mode: str                  # auto | native | shared | wrappers-only
    selected_agents: list[str]
    installed_skill_roots: list[str]  # e.g. [".agents/skills/", ".claude/skills/"]
    managed_files: list[ManagedFile]
```

Stored as `.kittify/agent-surfaces/skills-manifest.yaml`. Functions:

- `write_manifest(project_root, manifest)`: Write to YAML
- `load_manifest(project_root) -> SkillsManifest | None`: Load or None if missing
- `compute_file_hash(file_path) -> str`: SHA-256 of file contents

### 5. Post-Init Verification (`src/specify_cli/skills/verification.py`)

```python
@dataclass
class VerificationResult:
    passed: bool
    errors: list[str]
    warnings: list[str]

def verify_installation(
    project_root: Path,
    selected_agents: list[str],
    manifest: SkillsManifest,
) -> VerificationResult:
    """Check that installation matches expected state."""
```

Checks:
1. Every selected agent has a managed skill root OR a managed wrapper root
2. All skill root directories listed in manifest exist on disk
3. Wrapper counts match expected count for the mission
4. No duplicate skill names in overlapping roots scanned by the same agent

### 6. Init Modifications (`src/specify_cli/cli/commands/init.py`)

New `--skills` flag (typer Option, default `"auto"`):

```python
skills_mode: str = typer.Option(
    "auto",
    "--skills",
    help="Skill distribution: auto, native, shared, or wrappers-only",
),
```

New steps inserted after wrapper generation and before git init:

1. **Resolve skill roots**: Call `resolve_skill_roots(selected_agents, skills_mode)`
2. **Create skill root directories**: `mkdir -p` each resolved root with a `.gitkeep` marker
3. **Write manifest**: Collect all managed files (wrappers + skill root markers), compute hashes, write manifest
4. **Run verification**: Call `verify_installation()`, report errors/warnings

The tracker gets additional steps:
- `skills-resolve`: Resolve skill roots
- `skills-create`: Create skill directories
- `skills-manifest`: Write installation manifest
- `skills-verify`: Verify installation

### 7. Sync Modifications (`src/specify_cli/cli/commands/agent/config.py`)

`sync_agents` gains manifest awareness:

1. Load manifest (if exists)
2. For configured agents: ensure skill roots from manifest exist, recreate if missing
3. For removed agents: remove skill roots only if no other configured agent needs them (shared root protection)
4. Update manifest after changes

### 8. Upgrade Migration (`src/specify_cli/upgrade/migrations/m_2_1_0_agent_surface_manifest.py`)

For pre-Phase-0 projects:

1. **Detect**: Project has `.kittify/config.yaml` but no `.kittify/agent-surfaces/skills-manifest.yaml`
2. **Can apply**: Always (idempotent)
3. **Apply**:
   a. Read configured agents
   b. Resolve skill roots in `auto` mode
   c. Create empty skill root directories with `.gitkeep`
   d. Build manifest from existing wrapper files (hash each managed wrapper)
   e. Write manifest
   f. Run verification

Config-aware: Uses `get_agent_dirs_for_project()` to process only configured agents.

### 9. Asset Generator Update (`src/specify_cli/template/asset_generator.py`)

Minimal change — replace:
```python
from specify_cli.core.config import AGENT_COMMAND_CONFIG
```
with:
```python
from specify_cli.core.agent_surface import get_agent_surface
```

And change line 67 from:
```python
config = AGENT_COMMAND_CONFIG[agent_key]
output_dir = project_path / config["dir"]
```
to:
```python
surface = get_agent_surface(agent_key)
output_dir = project_path / surface.wrapper.dir
```

The rest of the function uses `config["arg_format"]` and `config["ext"]` which map to `surface.wrapper.arg_format` and `surface.wrapper.ext`. This is a safe 1:1 replacement.

## Call-Site Impact Analysis

| Module | Current Import | Phase 0 Change | Risk |
|--------|---------------|----------------|------|
| `core/config.py` | Defines `AGENT_COMMAND_CONFIG` | Becomes derived view | Low — same value, same type |
| `core/__init__.py` | Re-exports `AGENT_COMMAND_CONFIG` | Unchanged (still re-exports) | None |
| `agent_utils/directories.py` | Defines `AGENT_DIRS`, `AGENT_DIR_TO_KEY` | Become derived views | Low — same values |
| `agent_utils/__init__.py` | Re-exports `AGENT_DIRS`, etc. | Unchanged | None |
| `template/asset_generator.py` | `from config import AGENT_COMMAND_CONFIG` | Switch to `get_agent_surface()` | Low — 3 line change |
| 15+ migration files | `from m_0_9_1 import get_agent_dirs_for_project` | Unchanged — `get_agent_dirs_for_project` reads derived `AGENT_DIRS` | None |
| `m_0_14_0` migration | Own `get_agent_dirs_for_project` using `CompleteLaneMigration.AGENT_DIRS` | Unchanged — class attribute reads module-level `AGENT_DIRS` (derived) | None |
| `pre-commit-agent-check` shell script | Hardcoded bash array | Unchanged (separate concern) | None |
| `test_config.py` | Tests `AGENT_COMMAND_CONFIG` structure | Add test that derived view matches expected values | Low |

## Testing Strategy

### Unit Tests

1. **`test_agent_surface.py`**: Verify all 12 agents present, correct distribution classes, skill roots match PRD matrix, derived views produce identical output to old hardcoded values
2. **`test_manifest.py`**: Write/load/verify manifest round-trip, hash computation, missing file detection
3. **`test_roots.py`**: Parametrized resolution for all `--skills` modes × agent combinations, edge cases (empty selection, all-wrapper-only, single native agent)
4. **`test_verification.py`**: Pass case, each failure mode (missing root, missing wrapper, duplicate skills)

### Integration Tests

5. **`test_init_skills.py`**: Full `spec-kitty init` with `--skills auto|native|shared|wrappers-only`, verify filesystem state, manifest content, verification output
6. **Backward compatibility test**: Generate wrappers with old code path, generate with new code path, assert byte-exact match for all 12 agents

### Migration Tests

7. **`test_agent_surface_migration.py`**: Pre-Phase-0 fixture project → migration → verify manifest created, skill roots exist, wrappers untouched. Parametrized across agent configurations.

## Dependency Order

```
WP01: AGENT_SURFACE_CONFIG dataclass + derived views (no external deps)
  ↓
WP02: skill root resolution logic (depends on WP01 for distribution class data)
  ↓
WP03: skills manifest CRUD (no dependency on WP01/WP02 — parallel-capable)
  ↓
WP04: post-init verification (depends on WP02 for root expectations, WP03 for manifest)
  ↓
WP05: init wiring (depends on WP01–WP04)
  ↓
WP06: sync modifications (depends on WP03 for manifest awareness)
  ↓
WP07: upgrade migration (depends on WP01–WP04)
  ↓
WP08: asset_generator refactor (depends on WP01 for new import path)
  ↓
WP09: integration tests + backward compat validation (depends on all above)
```

Note: WP02 and WP03 are independent and can be parallelized. WP06 and WP07 can also be parallelized after WP04 completes.

## Complexity Tracking

No constitution violations. Feature uses:
- Standard Python dataclasses (no ORM, no database)
- Existing file I/O patterns (YAML, pathlib)
- Existing migration framework
- Existing CLI flag patterns (typer)
- No new external dependencies
