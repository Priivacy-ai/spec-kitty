# Implementation Plan: Model Selection per Task

**Branch**: `042-model-selection-per-task` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)

## Summary

Users define a global model mapping in `~/.spec-kitty/config.yaml` (the existing global config location). During `spec-kitty upgrade`, a new migration reads this mapping and injects a `model:` field into the YAML frontmatter of each matching command file across all configured agent directories. The injection uses the existing `FrontmatterManager` from `src/specify_cli/frontmatter.py` and follows the established migration pattern from `src/specify_cli/upgrade/migrations/`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: ruamel.yaml (already in use via `FrontmatterManager`), typer (CLI), pathlib
**Storage**: Filesystem only — `~/.spec-kitty/config.yaml` for global config, agent command `.md` files for injection target
**Testing**: pytest (existing test suite)
**Target Platform**: macOS, Linux (CLI tool)
**Project Type**: Single project (CLI tool extension)
**Performance Goals**: Injection adds negligible time to `spec-kitty upgrade`
**Constraints**: Must be idempotent (safe to re-run), backwards-compatible (no config → no change), must not break existing frontmatter fields

## Constitution Check

*No constitution file found — section skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/042-model-selection-per-task/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)
```

### Source Code (repository root)

This feature touches the following existing paths and adds new files:

```
src/specify_cli/
├── global_config.py                          # NEW: read/write ~/.spec-kitty/config.yaml
└── upgrade/
    └── migrations/
        └── m_2_0_4_model_injection.py        # NEW: migration that injects model: frontmatter

tests/specify_cli/
└── test_model_injection_migration.py         # NEW: unit + integration tests
```

No new directories — all additions are single files that slot into existing structures.

**Structure Decision**: Single project layout. No frontend, no API. One migration file + one config utility + tests.

## Phase 0: Research

### Findings

#### 1. Global Config Location
**Decision**: `~/.spec-kitty/config.yaml`
**Rationale**: Already established as the spec-kitty global state directory (used by `collaboration/session.py`, `events/store.py`, `events/lamport.py`). Consistent with existing conventions. No new path to document or support.
**Alternatives considered**: `~/.config/spec-kitty/config.yaml` (XDG) — rejected because it's inconsistent with the existing `~/.spec-kitty/` usage.

#### 2. Frontmatter Injection Mechanism
**Decision**: Use existing `FrontmatterManager` from `src/specify_cli/frontmatter.py`
**Rationale**: The project mandates going through `FrontmatterManager` for all frontmatter operations ("LLMs and scripts should NEVER manually edit YAML frontmatter"). It uses ruamel.yaml with consistency rules already enforced.
**Alternatives considered**: Raw string manipulation — rejected as fragile and inconsistent with codebase rules.

#### 3. Which Command Files to Target
**Decision**: Files matching `spec-kitty.*.md` in each agent's command subdirectory (same glob as `m_2_0_1_fix_generated_command_templates.py`)
**Rationale**: These are the generated slash command files. The `model:` field in frontmatter is supported by Claude Code's command/skill standard and followed by other agents.
**Note**: Not all agents support `model:` frontmatter. The injection is safe to apply to all — unsupporting agents simply ignore the field.

#### 4. Config Schema
**Decision**: Simple flat `models:` mapping under a top-level key
```yaml
models:
  specify: claude-opus-4-6
  plan: claude-opus-4-6
  tasks: claude-sonnet-4-6
  implement: claude-sonnet-4-6
  review: claude-sonnet-4-6
  accept: claude-sonnet-4-6
  merge: claude-haiku-4-5
  clarify: claude-sonnet-4-6
  status: claude-haiku-4-5
  checklist: claude-haiku-4-5
  analyze: claude-sonnet-4-6
  research: claude-opus-4-6
```
**Rationale**: Minimal structure, easy to read and write by hand. Command names match the `spec-kitty.*` suffix pattern.

#### 5. Migration Versioning
**Decision**: `m_2_0_4_model_injection.py` targeting version `2.0.4`
**Rationale**: Latest migration is `m_2_0_1_fix_generated_command_templates.py`. This is a non-breaking additive migration.

#### 6. Handling Missing `model:` Removal
**Decision**: If a command has a `model:` in frontmatter but the user removes that command from their config, the `model:` key is removed from the frontmatter on next upgrade.
**Rationale**: Config is the source of truth. Stale `model:` fields from a previous config should be cleaned up automatically.

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md).

### Key Entities

**GlobalConfig** (`~/.spec-kitty/config.yaml`)
- `models`: dict mapping command name → model string
- Optional — file may not exist
- Parsed on every `spec-kitty upgrade` run

**CommandName** (string)
- One of: `specify`, `plan`, `tasks`, `implement`, `review`, `accept`, `merge`, `clarify`, `status`, `checklist`, `analyze`, `research`
- Maps to filename `spec-kitty.<command>.md` in agent command directories

**AgentCommandFile** (`.md` file)
- Has optional YAML frontmatter block
- `model:` field added/updated/removed based on global config
- Managed exclusively via `FrontmatterManager`

### Implementation Design

#### `src/specify_cli/global_config.py` (new)

```python
# Responsibilities:
# - Load ~/.spec-kitty/config.yaml
# - Return model mapping (empty dict if file missing or no `models:` key)
# - Validate YAML structure, raise clear error on malformed YAML
# - List unrecognised command keys as warnings

KNOWN_COMMANDS = frozenset([
    "specify", "plan", "tasks", "implement", "review",
    "accept", "merge", "clarify", "status", "checklist",
    "analyze", "research",
])

def load_model_mapping(home: Path | None = None) -> dict[str, str]:
    """Return {command_name: model_string} from ~/.spec-kitty/config.yaml.
    Returns empty dict if file missing or no models key."""

def get_unknown_commands(mapping: dict[str, str]) -> list[str]:
    """Return command names in mapping not in KNOWN_COMMANDS."""
```

#### `src/specify_cli/upgrade/migrations/m_2_0_4_model_injection.py` (new)

```python
# Extends BaseMigration
# migration_id = "2.0.4_model_injection"
# target_version = "2.0.4"
#
# detect(): True if global config has a models: section
# can_apply(): Always True (idempotent)
#
# apply():
#   1. Load model mapping from global_config.load_model_mapping()
#   2. Warn on unknown command keys
#   3. For each configured agent dir (get_agent_dirs_for_project):
#      For each spec-kitty.*.md file in the agent subdir:
#        a. Extract command name from filename (spec-kitty.<cmd>.md → cmd)
#        b. If cmd in mapping: inject/update model: <value> in frontmatter
#        c. If cmd not in mapping: remove model: key if present
#   4. Report changes made
```

#### Frontmatter injection details

- Files **with** existing frontmatter: read via `FrontmatterManager.read()`, update/add `model:` key, write back
- Files **without** frontmatter: prepend minimal `---\nmodel: <value>\n---\n` block
- Use `FrontmatterManager` throughout — never raw string manipulation

### No API Contracts

This is a CLI/filesystem feature — no HTTP API, no contracts directory needed.

### Quickstart

See [quickstart.md](quickstart.md).

## Complexity Tracking

No constitution violations. Feature is minimal and additive.
